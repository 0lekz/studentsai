"""The tutor services: chunk embeddings, retrieval, question generation, grading and Ask."""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models import (
    ChunkEmbedding,
    ChunkQuestionGeneration,
    Concept,
    ConceptChunk,
    Course,
    Document,
    DocumentChunk,
    Flashcard,
    FlashcardSRS,
    LLMCall,
    User,
)
from app.models.document import DocumentStatus
from app.models.flashcard import FlashcardKind
from app.repositories import tutor as tutor_repository
from app.services.embedding_service import FakeEmbedder, content_hash
from app.services.ingestion.chunking import estimate_tokens
from app.services.llm.client import Generation, StopReason
from app.services.tutor import embeddings as tutor_embeddings
from app.services.tutor.ask import (
    ASK_PROMPT_VERSION,
    ASK_PURPOSE,
    ASK_SYSTEM_PROMPT,
    NOT_COVERED_ANSWER,
    CitedSource,
    GroundedAnswer,
    ask_course,
    resolve_citations,
)
from app.services.tutor.concept_links import tag_concepts
from app.services.tutor.embeddings import (
    backfill_chunk_embeddings,
    chunk_text,
    embed_chunks,
)
from app.services.tutor.generation import (
    MAX_QUESTIONS_PER_CHUNK,
    QUESTIONS_PROMPT_VERSION,
    QUESTIONS_PURPOSE,
    GeneratedQuestion,
    draft_questions,
    generate_questions,
    max_questions,
    shuffled,
    validate_question,
)
from app.services.tutor.grading import (
    GRADING_PURPOSE,
    GRADING_SYSTEM_PROMPT,
    InvalidAnswerError,
    RubricGrade,
    Verdict,
    grade_answer,
    reconcile,
)
from app.services.tutor.retrieval import RetrievedChunk, retrieve_chunks
from app.services.tutor.text import fallback_excerpt, quotes, shorten, words
from scripts import backfill_embeddings as backfill_script
from tests.fixtures.pdfs import Slide, slide_deck

UPLOADED = datetime(2026, 10, 1, tzinfo=UTC)
MERGE_SORT = (
    "Merge sort splits the list into two halves, sorts each half recursively, "
    "and merges the sorted halves. It performs O(n log n) comparisons."
)
QUICKSORT = (
    "Quicksort partitions the list around a pivot element. Its average running "
    "time is O(n log n), and its worst case is quadratic."
)
HASHING = (
    "A hash table maps keys to buckets with a hash function. Collisions are "
    "resolved by chaining or by open addressing."
)


@pytest.fixture(scope="module")
def slide_pdf() -> bytes:
    return slide_deck(
        [
            Slide("Merge sort", tuple(MERGE_SORT.split(". "))),
            Slide("Quicksort", tuple(QUICKSORT.split(". "))),
        ]
    )


@pytest.fixture
def owner(db_session) -> User:
    user = User(email="tutor@example.com", username="tutor", verified=True)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def make_course(db_session, owner) -> Callable[..., Course]:
    def make(name: str = "Algorithms", user: User | None = None) -> Course:
        course = Course(user_id=(user or owner).id, name=name)
        db_session.add(course)
        db_session.commit()
        return course

    return make


@pytest.fixture
def course(make_course) -> Course:
    return make_course()


@pytest.fixture
def add_document(db_session) -> Callable[..., Document]:
    uploads = iter(range(100))

    def add(
        course: Course, *texts: str | tuple[list[str], str], embed: bool = True
    ) -> Document:
        document = Document(
            user_id=course.user_id,
            course_id=course.id,
            filename=f"lecture-{uuid.uuid4().hex[:4]}.pdf",
            content_type="application/pdf",
            size_bytes=1,
            storage_path=f"{uuid.uuid4()}.pdf",
            status=DocumentStatus.READY.value,
            created_at=UPLOADED + timedelta(minutes=next(uploads)),
        )
        for index, item in enumerate(texts):
            heading_path, text = item if isinstance(item, tuple) else ([], item)
            document.chunks.append(
                DocumentChunk(
                    index=index,
                    heading_path=heading_path,
                    page_start=index + 1,
                    page_end=index + 2,
                    text=text,
                    token_estimate=estimate_tokens(text),
                )
            )
        db_session.add(document)
        db_session.commit()
        if embed:
            embed_chunks(db_session, FakeEmbedder(), document.chunks)
            db_session.commit()
        return document

    return add


def count(db_session, model) -> int:
    return db_session.scalar(select(func.count()).select_from(model))


class RecordingEmbedder(FakeEmbedder):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        return super().embed(texts)


class BrokenEmbedder:
    model_name = "broken"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("model unavailable")


class TestText:
    def test_words_ignore_case_punctuation_and_layout(self):
        assert (
            words("  O(n log n)\ncomparisons — “fast”!") == "o n log n comparisons fast"
        )

    @pytest.mark.parametrize(
        ("excerpt", "expected"),
        [
            ("sorts each half recursively", True),
            ("SORTS each half\nrecursively,", True),
            ("sorts each half quickly", False),
            ("half recur", False),
            ("", False),
            ("...", False),
        ],
    )
    def test_quotes_requires_a_word_for_word_span(self, excerpt, expected):
        assert quotes(MERGE_SORT, excerpt) is expected

    def test_shorten_cuts_at_a_word_boundary(self):
        assert shorten("one two  three\nfour", 100) == "one two three four"
        assert shorten("alpha beta gamma delta", 13) == "alpha beta…"
        assert fallback_excerpt("x " * 400).endswith("…")


class TestChunkEmbeddings:
    def test_uploading_a_pdf_embeds_its_chunks(
        self, auth_client, create_course, upload_pdf, db_session, slide_pdf
    ):
        course = create_course(auth_client)

        document = upload_pdf(auth_client, course["id"], slide_pdf)

        chunks = db_session.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == document["id"])
        ).all()
        stored = {
            row.chunk_id: row for row in db_session.scalars(select(ChunkEmbedding))
        }
        assert chunks and set(stored) == {chunk.id for chunk in chunks}
        for chunk in chunks:
            text = chunk_text(chunk.heading_path, chunk.text)
            assert stored[chunk.id].model_name == FakeEmbedder.model_name
            assert stored[chunk.id].content_hash == content_hash(text)
            assert list(stored[chunk.id].embedding) == pytest.approx(
                FakeEmbedder().embed([text])[0], abs=1e-6
            )

    def test_an_embedding_failure_still_saves_the_document(
        self,
        auth_client,
        create_course,
        upload_pdf,
        db_session,
        slide_pdf,
        monkeypatch,
        caplog,
    ):
        monkeypatch.setattr(tutor_embeddings, "get_embedder", BrokenEmbedder)
        course = create_course(auth_client)

        with caplog.at_level(logging.ERROR):
            document = upload_pdf(auth_client, course["id"], slide_pdf)

        assert document["status"] == "ready"
        assert auth_client.get(f"/documents/{document['id']}").status_code == 200
        assert count(db_session, ChunkEmbedding) == 0
        assert "Embedding failed for" in caplog.text

    def test_deleting_a_document_deletes_its_chunk_embeddings(
        self, auth_client, create_course, upload_pdf, db_session, slide_pdf
    ):
        course = create_course(auth_client)
        document = upload_pdf(auth_client, course["id"], slide_pdf)

        assert auth_client.delete(f"/documents/{document['id']}").status_code == 204

        assert count(db_session, ChunkEmbedding) == 0

    def test_unchanged_chunks_are_not_re_embedded(
        self, db_session, course, add_document
    ):
        document = add_document(course, MERGE_SORT, QUICKSORT, embed=False)
        embedder = RecordingEmbedder()

        assert embed_chunks(db_session, embedder, document.chunks) == 2
        assert embed_chunks(db_session, embedder, document.chunks) == 0
        assert len(embedder.calls) == 1

    def test_nothing_to_embed_skips_the_model(self, db_session):
        embedder = RecordingEmbedder()

        assert embed_chunks(db_session, embedder, []) == 0
        assert embedder.calls == []

    def test_a_model_change_re_embeds(self, db_session, course, add_document):
        document = add_document(course, MERGE_SORT)
        embedder = RecordingEmbedder()
        embedder.model_name = "next-model"

        assert embed_chunks(db_session, embedder, document.chunks) == 1
        db_session.commit()

        assert db_session.scalar(select(ChunkEmbedding.model_name)) == "next-model"

    def test_backfill_embeds_missing_and_stale_chunks_in_committed_batches(
        self, db_session, course, add_document
    ):
        add_document(course, MERGE_SORT, QUICKSORT, HASHING, embed=False)
        embedder = RecordingEmbedder()

        batches = list(backfill_chunk_embeddings(db_session, embedder, batch_size=2))

        assert [(b.scanned, b.embedded) for b in batches] == [(2, 2), (1, 1)]
        assert count(db_session, ChunkEmbedding) == 3
        assert [
            (b.scanned, b.embedded)
            for b in backfill_chunk_embeddings(db_session, embedder, batch_size=2)
        ] == [(2, 0), (1, 0)]

    def test_an_interrupted_backfill_resumes_without_redoing_batches(
        self, db_session, course, add_document
    ):
        add_document(course, MERGE_SORT, QUICKSORT, HASHING, embed=False)
        embedder = RecordingEmbedder()

        first_batch = next(backfill_chunk_embeddings(db_session, embedder, 2))
        resumed = list(backfill_chunk_embeddings(db_session, embedder, 2))

        assert first_batch.embedded == 2
        assert [batch.embedded for batch in resumed] == [0, 1]


class TestBackfillScript:
    @pytest.fixture
    def run(self, db_session, monkeypatch, capsys):
        class TestSession:
            def __enter__(self):
                return db_session

            def __exit__(self, *exc):
                return False

        monkeypatch.setattr(backfill_script, "SessionLocal", TestSession)

        def run(*argv: str) -> str:
            assert backfill_script.main(list(argv)) == 0
            return capsys.readouterr().out

        return run

    def test_the_chunks_flag_backfills_chunk_embeddings_in_batches(
        self, run, db_session, course, add_document
    ):
        add_document(course, MERGE_SORT, QUICKSORT, HASHING, embed=False)

        output = run("--chunks", "--batch-size", "2")

        assert output.splitlines()[0].startswith("chunks, model: fake-hashed")
        assert "batch 1: scanned 2, embedded 2" in output
        assert "batch 2: scanned 1, embedded 1" in output
        assert count(db_session, ChunkEmbedding) == 3
        assert "done: scanned 3, embedded 0" in run("--chunks")

    def test_without_the_flag_notes_are_backfilled(
        self, run, db_session, course, add_document
    ):
        add_document(course, MERGE_SORT, embed=False)

        output = run()

        assert output.splitlines()[0].startswith("notes, model:")
        assert count(db_session, ChunkEmbedding) == 0


class TestRetrieval:
    async def test_nearest_chunks_of_the_course_come_first_with_their_source(
        self, db_session, course, add_document
    ):
        document = add_document(course, MERGE_SORT, QUICKSORT, HASHING)

        results = await retrieve_chunks(
            db_session, course.id, "quicksort pivot element of the list", k=2
        )

        assert [r.text for r in results] == [QUICKSORT, MERGE_SORT]
        top = results[0]
        assert (top.document_id, top.filename) == (document.id, document.filename)
        assert (top.page_start, top.page_end) == (2, 3)
        assert results[0].similarity > results[1].similarity

    async def test_other_courses_are_never_searched(
        self, db_session, owner, course, make_course, add_document
    ):
        stranger = User(email="stranger@example.com", username="stranger")
        db_session.add(stranger)
        db_session.commit()
        add_document(make_course("Data structures"), QUICKSORT)
        add_document(make_course("Theirs", user=stranger), QUICKSORT)
        add_document(course, HASHING)

        results = await retrieve_chunks(db_session, course.id, "quicksort pivot", k=5)

        assert [r.text for r in results] == [HASHING]

    async def test_the_search_can_be_restricted_to_given_chunks(
        self, db_session, course, add_document
    ):
        document = add_document(course, MERGE_SORT, QUICKSORT, HASHING)
        hashing = document.chunks[2]

        results = await retrieve_chunks(
            db_session, course.id, "quicksort pivot", k=5, chunk_ids=[hashing.id]
        )

        assert [r.chunk_id for r in results] == [hashing.id]
        assert (
            await retrieve_chunks(db_session, course.id, "pivot", k=5, chunk_ids=[])
            == []
        )

    async def test_chunks_embedded_by_another_model_are_not_searched(
        self, db_session, course, add_document
    ):
        add_document(course, MERGE_SORT)
        db_session.execute(ChunkEmbedding.__table__.update().values(model_name="old"))
        db_session.commit()

        assert await retrieve_chunks(db_session, course.id, "merge sort", k=5) == []


def generated(*questions: dict) -> dict:
    return {"questions": list(questions)}


def recall(
    excerpt: str,
    prompt: str = "What does merge sort do?",
    answer: str = "It splits, sorts and merges.",
) -> dict:
    return {
        "excerpt": excerpt,
        "kind": "recall",
        "prompt": prompt,
        "reference_answer": answer,
        "choices": [],
        "correct_choice": None,
    }


def mcq(
    excerpt: str,
    choices: list[str],
    correct: int | None,
    prompt: str = "How many comparisons does merge sort make?",
) -> dict:
    return {
        "excerpt": excerpt,
        "kind": "mcq",
        "prompt": prompt,
        "reference_answer": choices[0],
        "choices": choices,
        "correct_choice": correct,
    }


CHOICES = ["O(n log n)", "O(n)", "O(n^2)", "O(log n)"]


class TestGeneration:
    @pytest.fixture
    def chunk(self, course, add_document) -> DocumentChunk:
        return add_document(course, (["Sorting", "Merge sort"], MERGE_SORT)).chunks[0]

    def test_the_question_budget_grows_with_the_chunk(self, chunk):
        chunk.token_estimate = 10
        assert max_questions(chunk) == 2
        chunk.token_estimate = 350
        assert max_questions(chunk) == 4
        chunk.token_estimate = 800
        assert max_questions(chunk) == MAX_QUESTIONS_PER_CHUNK

    async def test_one_cached_call_per_chunk_with_the_passage_and_budget(
        self, db_session, owner, chunk, tutor_llm
    ):
        llm = tutor_llm(
            {QUESTIONS_PURPOSE: generated(recall("sorts each half recursively"))}
        )

        await draft_questions(db_session, chunk, owner.id)
        await draft_questions(db_session, chunk, owner.id)

        [request] = llm.requests
        assert "Write at most 2 questions" in request.system
        assert request.messages[0]["content"] == (
            f"<passage>\nSorting > Merge sort\n\n{MERGE_SORT}\n</passage>"
        )
        assert request.user_id == owner.id
        calls = db_session.scalars(select(LLMCall).order_by(LLMCall.created_at)).all()
        assert [(c.purpose, c.cached) for c in calls] == [
            (QUESTIONS_PURPOSE, False),
            (QUESTIONS_PURPOSE, True),
        ]

    @pytest.mark.parametrize(
        "question",
        [
            recall("merge sort is stable", prompt="Is merge sort stable?"),
            recall("sorts each half recursively", prompt="   "),
            recall("sorts each half recursively", answer=""),
            mcq("O(n log n) comparisons", CHOICES[:3], 0),
            mcq("O(n log n) comparisons", ["a", "b", "A", "c"], 0),
            mcq("O(n log n) comparisons", ["a", "b", " ", "c"], 0),
            mcq("O(n log n) comparisons", CHOICES, 4),
            mcq("O(n log n) comparisons", CHOICES, None),
        ],
        ids=[
            "excerpt-not-in-chunk",
            "blank-prompt",
            "blank-answer",
            "three-choices",
            "duplicate-choices",
            "blank-choice",
            "correct-out-of-range",
            "no-correct-choice",
        ],
    )
    def test_ungrounded_and_malformed_questions_are_dropped(self, chunk, question):
        assert (
            validate_question(chunk, GeneratedQuestion.model_validate(question)) is None
        )

    async def test_a_batch_keeps_its_budget_and_drops_repeats(
        self, db_session, owner, course, add_document, tutor_llm
    ):
        long_chunk = add_document(course, " ".join([MERGE_SORT] * 6)).chunks[0]
        tutor_llm(
            {
                QUESTIONS_PURPOSE: generated(
                    recall("sorts each half recursively"),
                    recall(
                        "sorts each half recursively", prompt="What does MERGE SORT do?"
                    ),
                    recall("merges the sorted halves", prompt="What is merged?"),
                    recall(
                        "It performs O(n log n) comparisons",
                        prompt="How many comparisons?",
                    ),
                )
            }
        )

        drafts = await draft_questions(db_session, long_chunk, owner.id)

        assert max_questions(long_chunk) == 3
        assert [d.prompt for d in drafts] == [
            "What does merge sort do?",
            "What is merged?",
        ]

    def test_a_multiple_choice_answer_is_its_correct_choice_in_shuffled_order(
        self, chunk
    ):
        question = GeneratedQuestion.model_validate(
            mcq("It performs O(n log n) comparisons.", CHOICES, 0)
        )

        draft = validate_question(chunk, question)

        assert draft.answer == "O(n log n)"
        assert sorted(draft.choices) == sorted(CHOICES)
        assert draft.choices == shuffled(CHOICES, question.prompt)
        assert draft.excerpt == "It performs O(n log n) comparisons."

    def test_shuffling_spreads_the_correct_position(self):
        positions = {
            shuffled(CHOICES, f"Question {n}?").index(CHOICES[0]) for n in range(40)
        }
        assert positions == {0, 1, 2, 3}

    async def test_generated_questions_are_stored_with_provenance_and_scheduled(
        self, db_session, owner, course, chunk, tutor_llm
    ):
        tutor_llm(
            {
                QUESTIONS_PURPOSE: generated(
                    recall("sorts each half recursively"),
                    mcq("It performs O(n log n) comparisons.", CHOICES, 0),
                )
            }
        )

        created = await generate_questions(db_session, owner.id, course.id, [chunk], 1)

        assert len(created) == 2
        for card in created:
            assert card.source == "generated"
            assert card.prompt_version == QUESTIONS_PROMPT_VERSION
            assert (card.course_id, card.chunk_id, card.user_id) == (
                course.id,
                chunk.id,
                owner.id,
            )
            assert card.note_id is None
            assert card.concept_id is None
            srs = db_session.get(FlashcardSRS, card.id)
            assert srs.due_date == datetime.now(UTC).date()
        recall_card, mcq_card = created
        assert recall_card.kind == "recall" and recall_card.choices is None
        assert recall_card.excerpt == "sorts each half recursively"
        assert mcq_card.kind == "mcq" and mcq_card.answer == "O(n log n)"
        marker = db_session.get(
            ChunkQuestionGeneration, (chunk.id, QUESTIONS_PROMPT_VERSION)
        )
        assert marker.question_count == 2

    async def test_generating_from_a_chunk_again_adds_nothing(
        self, db_session, owner, course, chunk, tutor_llm
    ):
        llm = tutor_llm(
            {QUESTIONS_PURPOSE: generated(recall("sorts each half recursively"))}
        )
        await generate_questions(db_session, owner.id, course.id, [chunk], 5)

        again = await generate_questions(db_session, owner.id, course.id, [chunk], 5)

        assert again == []
        assert len(llm.requests) == 1
        assert count(db_session, Flashcard) == 1

    async def test_writes_take_the_course_lock_after_the_model_call(
        self, db_session, owner, course, chunk, tutor_llm, monkeypatch
    ):
        events = []
        llm = tutor_llm(
            {
                QUESTIONS_PURPOSE: lambda request: (
                    events.append("model")
                    or generated(recall("sorts each half recursively"))
                )
            }
        )
        real_lock = tutor_repository.lock_course_questions

        def recording_lock(db, course_id):
            events.append(("lock", course_id))
            real_lock(db, course_id)

        monkeypatch.setattr(tutor_repository, "lock_course_questions", recording_lock)

        await generate_questions(db_session, owner.id, course.id, [chunk], 1)
        await generate_questions(db_session, owner.id, course.id, [chunk], 1)

        assert events == ["model", ("lock", course.id), ("lock", course.id)]
        assert len(llm.requests) == 1
        assert count(db_session, Flashcard) == 1

    async def test_generation_stops_once_enough_questions_are_stored(
        self, db_session, owner, course, add_document, tutor_llm
    ):
        chunks = add_document(course, MERGE_SORT, QUICKSORT, HASHING).chunks

        def one_question(request):
            passage = request.messages[0]["content"]
            first_sentence = passage.split("\n")[1].split(".")[0]
            return generated(
                recall(first_sentence, prompt=f"Explain: {first_sentence}?")
            )

        llm = tutor_llm({QUESTIONS_PURPOSE: one_question})

        created = await generate_questions(db_session, owner.id, course.id, chunks, 2)

        assert len(created) == 2
        assert len(llm.requests) == 2
        assert count(db_session, ChunkQuestionGeneration) == 2

    async def test_an_empty_answer_still_marks_the_chunk_as_used(
        self, db_session, owner, course, chunk, tutor_llm
    ):
        tutor_llm({QUESTIONS_PURPOSE: generated()})

        assert (
            await generate_questions(db_session, owner.id, course.id, [chunk], 3) == []
        )

        marker = db_session.get(
            ChunkQuestionGeneration, (chunk.id, QUESTIONS_PROMPT_VERSION)
        )
        assert marker.question_count == 0


class TestConceptTags:
    @pytest.fixture
    def link(self, db_session) -> Callable[..., Concept]:
        orders = iter(range(100))

        def link(course: Course, name: str, *chunks: DocumentChunk) -> Concept:
            [vector] = FakeEmbedder().embed([name])
            concept = Concept(
                course_id=course.id,
                name=name,
                description=f"{name} as taught.",
                order=next(orders),
                embedding=vector,
                embedding_model=FakeEmbedder.model_name,
            )
            db_session.add(concept)
            db_session.flush()
            for chunk in chunks:
                db_session.add(
                    ConceptChunk(
                        concept_id=concept.id,
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                    )
                )
            db_session.commit()
            return concept

        return link

    async def test_a_chunk_without_concepts_tags_nothing(
        self, db_session, course, add_document
    ):
        chunk = add_document(course, MERGE_SORT).chunks[0]

        assert await tag_concepts(db_session, chunk.id, ["q1", "q2"]) == [None, None]

    async def test_a_chunk_with_one_concept_tags_every_question_with_it(
        self, db_session, course, add_document, link
    ):
        chunk = add_document(course, MERGE_SORT).chunks[0]
        concept = link(course, "Merge sort", chunk)

        assert await tag_concepts(db_session, chunk.id, ["a", "b"]) == [
            concept.id,
            concept.id,
        ]

    async def test_with_several_concepts_each_question_gets_the_nearest(
        self, db_session, course, add_document, link
    ):
        chunk = add_document(course, f"{MERGE_SORT} {QUICKSORT}").chunks[0]
        merge = link(course, "merge sort halves", chunk)
        quick = link(course, "quicksort pivot partition", chunk)

        tags = await tag_concepts(
            db_session,
            chunk.id,
            [
                "How does quicksort choose a pivot?",
                "What does merge sort do with the halves?",
            ],
        )

        assert tags == [quick.id, merge.id]

    async def test_generated_questions_carry_their_concept(
        self, db_session, owner, course, add_document, link, tutor_llm
    ):
        chunk = add_document(course, MERGE_SORT).chunks[0]
        concept = link(course, "Merge sort", chunk)
        tutor_llm({QUESTIONS_PURPOSE: generated(recall("sorts each half recursively"))})

        [card] = await generate_questions(db_session, owner.id, course.id, [chunk], 1)

        assert card.concept_id == concept.id


def card(**fields) -> Flashcard:
    defaults = {
        "question": "What does merge sort do?",
        "answer": "It splits the list in halves, sorts them and merges them.",
        "excerpt": "Merge sort splits the list into two halves",
        "kind": FlashcardKind.RECALL.value,
        "choices": None,
    }
    return Flashcard(**(defaults | fields))


def rubric(
    verdict: str, score: int, quality: int, missing: list[str] | None = None
) -> dict:
    return {
        "missing_points": missing or [],
        "feedback": "You named the split. You did not mention merging.",
        "verdict": verdict,
        "score": score,
        "quality": quality,
    }


class TestGrading:
    async def test_multiple_choice_is_graded_locally(self, db_session, tutor_llm):
        llm = tutor_llm()
        question = card(
            kind="mcq",
            choices=["O(n)", "O(n log n)", "O(1)", "O(n^2)"],
            answer="O(n log n)",
        )

        right = await grade_answer(
            db_session, question, answer=None, choice_index=1, user_id=None
        )
        wrong = await grade_answer(
            db_session, question, answer=None, choice_index=3, user_id=None
        )

        assert (right.verdict, right.score, right.quality) == (Verdict.CORRECT, 100, 4)
        assert (wrong.verdict, wrong.score, wrong.quality) == (Verdict.INCORRECT, 0, 1)
        assert wrong.missing_points == ["O(n log n)"]
        assert "“O(n^2)”" in wrong.feedback and "“O(n log n)”" in wrong.feedback
        assert llm.requests == []

    @pytest.mark.parametrize("choice_index", [None, 4])
    async def test_a_multiple_choice_answer_needs_a_valid_choice(
        self, db_session, choice_index
    ):
        question = card(kind="mcq", choices=["a", "b", "c", "d"], answer="a")

        with pytest.raises(InvalidAnswerError, match="between 0 and 3"):
            await grade_answer(
                db_session,
                question,
                answer="a",
                choice_index=choice_index,
                user_id=None,
            )

    async def test_a_written_question_needs_an_answer(self, db_session):
        with pytest.raises(InvalidAnswerError):
            await grade_answer(
                db_session, card(), answer=None, choice_index=0, user_id=None
            )

    async def test_blank_and_verbatim_answers_are_graded_without_a_model(
        self, db_session, tutor_llm
    ):
        llm = tutor_llm()
        question = card()

        blank = await grade_answer(
            db_session, question, answer="  ", choice_index=None, user_id=None
        )
        verbatim = await grade_answer(
            db_session,
            question,
            answer="it splits the list in halves; sorts them, and merges them",
            choice_index=None,
            user_id=None,
        )

        assert (blank.verdict, blank.score, blank.quality) == (Verdict.INCORRECT, 0, 0)
        assert blank.missing_points == [question.answer]
        assert (verbatim.verdict, verbatim.score, verbatim.quality) == (
            Verdict.CORRECT,
            100,
            5,
        )
        assert llm.requests == []

    async def test_written_answers_are_graded_by_an_uncached_rubric_call(
        self, db_session, owner, tutor_llm
    ):
        llm = tutor_llm({GRADING_PURPOSE: rubric("partial", 50, 3, ["merging"])})
        question = card()

        first = await grade_answer(
            db_session,
            question,
            answer="It splits the list",
            choice_index=None,
            user_id=owner.id,
        )
        await grade_answer(
            db_session,
            question,
            answer="It splits the list",
            choice_index=None,
            user_id=owner.id,
        )

        assert (first.verdict, first.score, first.quality) == (Verdict.PARTIAL, 50, 3)
        assert first.missing_points == ["merging"]
        assert first.feedback == "You named the split. You did not mention merging."
        assert len(llm.requests) == 2
        request = llm.requests[0]
        assert request.system == GRADING_SYSTEM_PROMPT
        assert "Accept paraphrases, synonyms" in request.system
        assert request.messages[0]["content"] == (
            f"<question>\n{question.question}\n</question>\n"
            f"<reference_answer>\n{question.answer}\n</reference_answer>\n"
            f"<course_excerpt>\n{question.excerpt}\n</course_excerpt>\n"
            "<student_answer>\nIt splits the list\n</student_answer>"
        )
        assert request.user_id == owner.id
        cached = db_session.scalars(select(LLMCall.cached)).all()
        assert cached == [False, False]

    async def test_a_card_without_an_excerpt_is_graded_on_its_answer(
        self, db_session, tutor_llm
    ):
        llm = tutor_llm({GRADING_PURPOSE: rubric("correct", 90, 5)})

        await grade_answer(
            db_session,
            card(excerpt=None),
            answer="halves",
            choice_index=None,
            user_id=None,
        )

        assert "<course_excerpt>" not in llm.requests[0].messages[0]["content"]

    @pytest.mark.parametrize(
        ("verdict", "score", "quality", "expected"),
        [
            ("correct", 40, 1, (80, 4)),
            ("correct", 95, 5, (95, 5)),
            ("partial", 100, 5, (79, 3)),
            ("partial", 10, 0, (30, 2)),
            ("incorrect", 70, 4, (29, 1)),
            ("incorrect", -5, 0, (0, 0)),
        ],
    )
    def test_score_and_quality_are_clamped_into_the_verdict_ranges(
        self, verdict, score, quality, expected
    ):
        grade = reconcile(RubricGrade.model_validate(rubric(verdict, score, quality)))

        assert grade.verdict == Verdict(verdict)
        assert (grade.score, grade.quality) == expected


def retrieved(text: str, number: int = 0) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.UUID(int=number + 1),
        document_id=uuid.UUID(int=100),
        filename="lecture.pdf",
        heading_path=["Sorting"],
        page_start=number + 1,
        page_end=number + 1,
        text=text,
        similarity=0.9,
    )


class TestAsk:
    def test_citations_keep_retrieved_sources_in_order_of_first_use(self):
        chunks = [
            retrieved(MERGE_SORT, 0),
            retrieved(QUICKSORT, 1),
            retrieved(HASHING, 2),
        ]
        answer = GroundedAnswer(
            covered=True,
            answer=(
                "Quicksort partitions [2]. Merge sort merges [1][7], unlike [9]. "
                "Both are fast [2, 1]. Code: `a[3]`\n```\nb[1]\n```"
            ),
            citations=[
                CitedSource(source=2, excerpt="partitions the list around a pivot"),
                CitedSource(source=1, excerpt="not in the source"),
                CitedSource(source=7, excerpt="anything"),
            ],
        )

        result = resolve_citations(answer, chunks)

        assert result.answer == (
            "Quicksort partitions [1]. Merge sort merges [2], unlike. "
            "Both are fast [1][2]. Code: `a[3]`\n```\nb[1]\n```"
        )
        assert [c.chunk.text for c in result.citations] == [QUICKSORT, MERGE_SORT]
        assert result.citations[0].excerpt == "partitions the list around a pivot"
        assert result.citations[1].excerpt == fallback_excerpt(MERGE_SORT)

    def test_a_listed_citation_without_a_marker_is_kept_after_the_marked_ones(self):
        chunks = [retrieved(MERGE_SORT, 0), retrieved(QUICKSORT, 1)]
        answer = GroundedAnswer(
            covered=True,
            answer="Merge sort merges [2].",
            citations=[CitedSource(source=1, excerpt="merges the sorted halves")],
        )

        result = resolve_citations(answer, chunks)

        assert [c.chunk.text for c in result.citations] == [QUICKSORT, MERGE_SORT]

    def test_an_answer_the_model_marks_uncovered_keeps_no_citations(self):
        answer = GroundedAnswer(
            covered=False,
            answer="The sources do not cover this [1].",
            citations=[CitedSource(source=1, excerpt="merges the sorted halves")],
        )

        result = resolve_citations(answer, [retrieved(MERGE_SORT)])

        assert (result.answer, result.covered, result.citations) == (
            "The sources do not cover this.",
            False,
            [],
        )

    def test_an_answer_without_a_valid_citation_is_not_covered(self):
        answer = GroundedAnswer(
            covered=True, answer="Merge sort merges [4].", citations=[]
        )

        result = resolve_citations(answer, [retrieved(MERGE_SORT)])

        assert (result.answer, result.covered) == ("Merge sort merges.", False)

    async def test_nothing_above_the_floor_is_answered_without_a_model(
        self, db_session, course, add_document, tutor_llm
    ):
        add_document(course, MERGE_SORT)
        llm = tutor_llm()

        result = await ask_course(
            db_session, course.id, "who painted the mona lisa", None
        )

        assert (result.answer, result.covered, result.citations) == (
            NOT_COVERED_ANSWER,
            False,
            [],
        )
        assert llm.requests == []

    async def test_relevant_chunks_are_numbered_sources_for_a_cached_call(
        self, db_session, owner, course, add_document, tutor_llm, monkeypatch
    ):
        from app.config import settings

        monkeypatch.setattr(settings, "ask_min_similarity", 0.2)
        document = add_document(
            course, (["Sorting", "Merge sort"], MERGE_SORT), HASHING
        )
        llm = tutor_llm(
            {
                ASK_PURPOSE: {
                    "covered": True,
                    "answer": "It merges sorted halves [1].",
                    "citations": [{"source": 1, "excerpt": "merges the sorted halves"}],
                }
            }
        )

        result = await ask_course(
            db_session,
            course.id,
            "how does merge sort merge the sorted halves",
            owner.id,
        )

        [request] = llm.requests
        assert request.system == ASK_SYSTEM_PROMPT
        assert request.messages[0]["content"] == (
            "<sources>\n"
            f'<source number="1" document="{document.filename}" pages="1-2" '
            f'section="Sorting > Merge sort">\n{MERGE_SORT}\n</source>\n'
            "</sources>\n<question>\nhow does merge sort merge the sorted halves\n</question>"
        )
        assert (result.answer, result.covered) == ("It merges sorted halves [1].", True)
        [citation] = result.citations
        assert (citation.chunk.chunk_id, citation.excerpt) == (
            document.chunks[0].id,
            "merges the sorted halves",
        )
        logged = db_session.scalars(select(LLMCall.purpose)).all()
        assert logged == [ASK_PURPOSE]
        assert ASK_PROMPT_VERSION == "ask-v1"

    async def test_a_truncated_answer_is_retried_then_raises(
        self, db_session, owner, course, add_document, tutor_llm, monkeypatch
    ):
        from app.config import settings
        from app.services.llm import StructuredOutputError

        monkeypatch.setattr(settings, "ask_min_similarity", 0.0)
        add_document(course, MERGE_SORT)
        tutor_llm({ASK_PURPOSE: Generation("{", 10, 8000, StopReason.MAX_TOKENS)})

        with pytest.raises(StructuredOutputError):
            await ask_course(db_session, course.id, "merge sort", owner.id)
