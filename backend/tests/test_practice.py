"""Question generation, practice sessions and graded answers through the API."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import (
    Concept,
    ConceptChunk,
    DocumentChunk,
    Flashcard,
    FlashcardSRS,
    LLMCall,
)
from app.services.embedding_service import FakeEmbedder
from app.services.llm import LLMUnavailableError
from app.services.llm.client import Generation
from app.services.tutor.generation import QUESTIONS_PURPOSE
from app.services.tutor.grading import GRADING_PURPOSE
from app.services.tutor.text import fallback_excerpt
from tests.fixtures.pdfs import Slide, slide_deck

DECK = [
    Slide(
        "Merge sort",
        (
            "Merge sort splits the list into two halves and sorts each half recursively",
            "It performs O(n log n) comparisons in the worst case",
        ),
    ),
    Slide(
        "Quicksort",
        (
            "Quicksort partitions the list around a pivot element",
            "Its worst case running time is quadratic",
        ),
    ),
    Slide(
        "Hash tables",
        (
            "A hash table maps keys to buckets with a hash function",
            "Collisions are resolved by chaining or open addressing",
        ),
    ),
]
CHOICES = ["first", "second", "third", "fourth"]
MISSING = "00000000-0000-0000-0000-000000000000"


def slide_questions(request) -> dict:
    """Two grounded questions per slide: a recall on the first bullet, a multiple choice on the second."""
    passage = request.messages[0]["content"]
    topic = passage.split("\n")[1]
    bullets = [line[2:] for line in passage.split("\n") if line.startswith("- ")]
    return {
        "questions": [
            {
                "excerpt": bullets[0],
                "kind": "recall",
                "prompt": f"What does {topic} do?",
                "reference_answer": bullets[0],
                "choices": [],
                "correct_choice": None,
            },
            {
                "excerpt": bullets[1],
                "kind": "mcq",
                "prompt": f"Which is true of {topic}?",
                "reference_answer": CHOICES[0],
                "choices": CHOICES,
                "correct_choice": 0,
            },
        ]
    }


def rubric(verdict: str = "partial", score: int = 60, quality: int = 3) -> dict:
    return {
        "missing_points": ["recursion"],
        "feedback": "You described the split. You left out that each half is sorted recursively.",
        "verdict": verdict,
        "score": score,
        "quality": quality,
    }


@pytest.fixture(scope="module")
def deck_pdf() -> bytes:
    return slide_deck(DECK)


@pytest.fixture
def course(auth_client, create_course) -> dict:
    return create_course(auth_client, "Algorithms")


@pytest.fixture
def document(auth_client, course, upload_pdf, deck_pdf) -> dict:
    return upload_pdf(auth_client, course["id"], deck_pdf, "week-3.pdf")


@pytest.fixture
def llm(tutor_llm):
    return tutor_llm({QUESTIONS_PURPOSE: slide_questions, GRADING_PURPOSE: rubric()})


@pytest.fixture
def chunks(db_session, document) -> list[DocumentChunk]:
    return list(
        db_session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document["id"])
            .order_by(DocumentChunk.index)
        )
    )


@pytest.fixture
def add_concept(db_session, course):
    orders = iter(range(100))

    def add(name: str, *chunks: DocumentChunk) -> Concept:
        [vector] = FakeEmbedder().embed([name])
        concept = Concept(
            course_id=course["id"],
            name=name,
            description=f"{name} as taught.",
            order=next(orders),
            embedding=vector,
            embedding_model=FakeEmbedder.model_name,
        )
        db_session.add(concept)
        db_session.flush()
        db_session.add_all(
            ConceptChunk(
                concept_id=concept.id, chunk_id=chunk.id, document_id=chunk.document_id
            )
            for chunk in chunks
        )
        db_session.commit()
        return concept

    return add


def generate(client, course: dict, **body):
    return client.post(f"/courses/{course['id']}/questions/generate", json=body)


def start_session(client, course: dict, **body):
    return client.post(f"/courses/{course['id']}/practice/session", json=body or None)


def answer(client, question_id: str, **body):
    return client.post(f"/questions/{question_id}/answer", json=body)


def tomorrow():
    return datetime.now(UTC).date() + timedelta(days=1)


class TestGenerate:
    def test_questions_come_back_with_their_source_and_only_recall_answers(
        self, auth_client, course, document, llm
    ):
        response = generate(auth_client, course, count=2)

        assert response.status_code == 200, response.text
        questions = response.json()["questions"]
        assert [(q["kind"], q["prompt"]) for q in questions] == [
            ("recall", "What does Merge sort do?"),
            ("mcq", "Which is true of Merge sort?"),
        ]
        recall, mcq = questions
        assert set(recall) == {
            "id",
            "kind",
            "prompt",
            "choices",
            "reference_answer",
            "concept",
            "source",
        }
        assert recall["choices"] is None
        assert recall["reference_answer"] == DECK[0].bullets[0]
        assert mcq["reference_answer"] is None
        assert sorted(mcq["choices"]) == sorted(CHOICES)
        assert recall["concept"] is None
        assert recall["source"] == {
            "document_id": document["id"],
            "filename": "week-3.pdf",
            "page_start": 1,
            "page_end": 1,
        }
        assert len(llm.requests_for(QUESTIONS_PURPOSE)) == 1

    def test_a_short_answer_question_keeps_its_answer_until_graded(
        self, auth_client, course, document, tutor_llm, chunks
    ):
        tutor_llm(
            {
                QUESTIONS_PURPOSE: {
                    "questions": [
                        {
                            "excerpt": DECK[0].bullets[0],
                            "kind": "short_answer",
                            "prompt": "Why is merge sort recursive?",
                            "reference_answer": "Each half is sorted the same way.",
                            "choices": [],
                            "correct_choice": None,
                        }
                    ]
                }
            }
        )

        [question] = generate(auth_client, course, chunk_id=str(chunks[0].id)).json()[
            "questions"
        ]

        assert (question["kind"], question["reference_answer"]) == (
            "short_answer",
            None,
        )

    def test_every_question_of_the_last_chunk_is_kept(
        self, auth_client, course, document, llm
    ):
        response = generate(auth_client, course, count=3)

        assert len(response.json()["questions"]) == 4

    def test_a_chunk_already_used_adds_nothing(
        self, auth_client, course, document, llm, chunks
    ):
        generate(auth_client, course, chunk_id=str(chunks[1].id))

        again = generate(auth_client, course, chunk_id=str(chunks[1].id))

        assert again.status_code == 200
        assert again.json()["questions"] == []
        assert len(llm.requests_for(QUESTIONS_PURPOSE)) == 1

    def test_course_generation_moves_on_to_unused_chunks(
        self, auth_client, course, document, llm
    ):
        first = generate(auth_client, course, count=2).json()["questions"]
        second = generate(auth_client, course, count=2).json()["questions"]
        third = generate(auth_client, course, count=2).json()["questions"]
        rest = generate(auth_client, course, count=2).json()["questions"]

        pages = [
            {q["source"]["page_start"] for q in batch}
            for batch in (first, second, third)
        ]
        assert pages == [{1}, {2}, {3}]
        assert rest == []

    def test_from_a_concept_uses_its_chunks_and_tags_its_questions(
        self, auth_client, course, document, llm, chunks, add_concept
    ):
        concept = add_concept("Hashing", chunks[2])

        response = generate(auth_client, course, concept_id=str(concept.id))

        questions = response.json()["questions"]
        assert {q["source"]["page_start"] for q in questions} == {3}
        assert {q["concept"]["id"] for q in questions} == {str(concept.id)}
        assert questions[0]["concept"]["name"] == "Hashing"

    @pytest.mark.parametrize(
        "body",
        [{"count": 0}, {"count": 21}, {"chunk_id": "not-a-uuid"}],
    )
    def test_invalid_bodies_are_rejected(self, auth_client, course, body):
        assert generate(auth_client, course, **body).status_code == 422

    def test_a_chunk_and_a_concept_together_are_rejected(
        self, auth_client, course, document, chunks, add_concept
    ):
        concept = add_concept("Sorting", chunks[0])

        response = generate(
            auth_client, course, chunk_id=str(chunks[0].id), concept_id=str(concept.id)
        )

        assert response.status_code == 422

    def test_chunks_and_concepts_of_other_courses_are_not_found(
        self,
        auth_client,
        create_course,
        course,
        document,
        chunks,
        add_concept,
        db_session,
    ):
        other = create_course(auth_client, "Databases")
        concept = add_concept("Sorting", chunks[0])

        assert (
            generate(auth_client, other, chunk_id=str(chunks[0].id)).status_code == 404
        )
        assert (
            generate(auth_client, other, concept_id=str(concept.id)).status_code == 404
        )
        assert generate(auth_client, course, chunk_id=MISSING).status_code == 404

    def test_another_users_course_is_not_found(self, other_auth_client, course):
        assert generate(other_auth_client, course).status_code == 404
        assert start_session(other_auth_client, course).status_code == 404

    def test_an_unverified_user_cannot_spend_on_the_model(
        self, client, register_user, create_course
    ):
        user = register_user("new@example.com", "newbie", verified=False)
        client.headers.update(user.auth_header)
        course = create_course(client)

        assert generate(client, course).status_code == 403

    def test_a_model_outage_is_a_503_and_invalid_output_a_502(
        self, auth_client, course, document, tutor_llm
    ):
        def outage(request):
            raise LLMUnavailableError("overloaded")

        tutor_llm({QUESTIONS_PURPOSE: outage})
        assert generate(auth_client, course).status_code == 503

        tutor_llm({QUESTIONS_PURPOSE: Generation("not json", 10, 10)})
        assert generate(auth_client, course).status_code == 502


def test_a_model_outage_while_filling_a_session_is_a_503(
    auth_client, course, document, tutor_llm
):
    def outage(request):
        raise LLMUnavailableError("overloaded")

    tutor_llm({QUESTIONS_PURPOSE: outage})

    assert start_session(auth_client, course, size=2).status_code == 503


class TestGeneratedQuestionsAsFlashcards:
    def test_they_round_trip_through_the_flashcard_routes_without_a_note(
        self, auth_client, course, document, llm, db_session
    ):
        generated = generate(auth_client, course, count=1).json()["questions"]

        cards = auth_client.get(
            "/flashcards/user", params={"course_id": course["id"]}
        ).json()

        assert {card["id"] for card in cards} == {q["id"] for q in generated}
        recall = next(card for card in cards if card["kind"] == "recall")
        assert recall["source"] == "generated"
        assert recall["excerpt"] == DECK[0].bullets[0]
        assert recall["course_id"] == course["id"]
        stored = db_session.get(Flashcard, uuid.UUID(recall["id"]))
        assert stored.note_id is None
        due = auth_client.get("/flashcards/due/srs").json()
        assert {card["id"] for card in due} == {q["id"] for q in generated}

    def test_note_routes_ignore_questions_without_a_note(
        self, auth_client, course, document, llm, create_note, fake_ai
    ):
        generate(auth_client, course, count=1)
        note = create_note(auth_client, course_id=course["id"])
        made = auth_client.post(
            "/flashcards/generate", json={"note_id": note["id"], "count": 2}
        )
        assert made.status_code == 200, made.text

        note_cards = auth_client.get(f"/notes/{note['id']}/flashcards").json()
        sets = auth_client.get("/flashcards/sets").json()
        assert len(note_cards) == 2
        assert [s["flashcard_count"] for s in sets] == [2]

        assert auth_client.delete(f"/notes/{note['id']}").status_code == 200
        remaining = auth_client.get("/flashcards/user").json()
        assert {card["source"] for card in remaining} == {"generated"}
        assert len(remaining) == 2


class TestGetQuestion:
    def test_one_question_reloads_in_the_session_shape(
        self, auth_client, course, document, llm
    ):
        [first, *_] = start_session(auth_client, course, size=2).json()["questions"]

        response = auth_client.get(f"/questions/{first['id']}")

        assert response.status_code == 200, response.text
        assert response.json() == first

    def test_another_users_question_is_not_found(
        self, auth_client, other_auth_client, course, document, llm
    ):
        [first, *_] = generate(auth_client, course, count=1).json()["questions"]

        assert other_auth_client.get(f"/questions/{first['id']}").status_code == 404
        assert auth_client.get(f"/questions/{MISSING}").status_code == 404

    def test_deleting_a_document_deletes_the_questions_generated_from_it(
        self, auth_client, course, document, llm, create_note, fake_ai, db_session
    ):
        [recall, mcq] = start_session(auth_client, course, size=2).json()["questions"]
        assert recall["source"]["document_id"] == document["id"]
        note = create_note(auth_client, course_id=course["id"])
        auth_client.post(
            "/flashcards/generate", json={"note_id": note["id"], "count": 1}
        )

        assert auth_client.delete(f"/documents/{document['id']}").status_code == 204

        assert auth_client.get(f"/questions/{recall['id']}").status_code == 404
        assert answer(auth_client, mcq["id"], choice_index=0).status_code == 404
        remaining = auth_client.get("/flashcards/user").json()
        assert [(card["source"], card["excerpt"]) for card in remaining] == [
            ("user", None)
        ]
        session = start_session(auth_client, course, size=5).json()["questions"]
        assert [(q["source"], q["kind"]) for q in session] == [(None, "recall")]
        assert db_session.query(FlashcardSRS).count() == 1


class TestPracticeSession:
    def test_an_empty_pool_is_filled_by_generating_on_demand(
        self, auth_client, course, document, llm
    ):
        response = start_session(auth_client, course, size=3)

        assert response.status_code == 200, response.text
        questions = response.json()["questions"]
        assert [q["source"]["page_start"] for q in questions] == [1, 1, 2]
        assert len(llm.requests_for(QUESTIONS_PURPOSE)) == 2

    def test_the_default_size_is_ten_and_the_body_is_optional(
        self, auth_client, course, document, llm
    ):
        response = auth_client.post(f"/courses/{course['id']}/practice/session")

        assert response.status_code == 200, response.text
        assert len(response.json()["questions"]) == 6

    def test_due_reviews_come_first_then_the_weakest_concepts_unseen_questions(
        self, auth_client, course, document, llm, chunks, add_concept, db_session
    ):
        add_concept("Sorting", chunks[0], chunks[1])
        add_concept("Hashing", chunks[2])
        by_prompt = {
            q["prompt"]: q["id"]
            for q in generate(auth_client, course, count=6).json()["questions"]
        }
        failed = by_prompt["Which is true of Merge sort?"]
        mastered = by_prompt["Which is true of Hash tables?"]
        answer(auth_client, failed, choice_index=_wrong_index(auth_client, failed))
        for _ in range(4):
            answer(
                auth_client,
                mastered,
                choice_index=_correct_index(auth_client, mastered),
            )
        _make_due(db_session, failed)

        questions = start_session(auth_client, course, size=4).json()["questions"]

        ids = [q["id"] for q in questions]
        assert ids[0] == failed
        assert set(ids[1:]) == {
            by_prompt["What does Merge sort do?"],
            by_prompt["What does Quicksort do?"],
            by_prompt["Which is true of Quicksort?"],
        }
        assert {q["concept"]["name"] for q in questions} == {"Sorting"}

    def test_reviewed_cards_that_are_not_due_are_left_out(
        self, auth_client, course, document, llm, db_session
    ):
        generated = generate(auth_client, course, count=6).json()["questions"]
        for question in generated:
            body = (
                {"choice_index": 0}
                if question["kind"] == "mcq"
                else {"answer": "something"}
            )
            assert answer(auth_client, question["id"], **body).status_code == 200

        questions = start_session(auth_client, course, size=5).json()["questions"]

        assert questions == []

    def test_unseen_questions_alternate_between_the_weakest_concepts(
        self, auth_client, course, document, llm, chunks, add_concept
    ):
        add_concept("Merge sort", chunks[0])
        add_concept("Quicksort", chunks[1])
        add_concept("Hashing", chunks[2])
        generate(auth_client, course, count=6)

        questions = start_session(auth_client, course, size=3).json()["questions"]

        assert [q["concept"]["name"] for q in questions] == [
            "Merge sort",
            "Quicksort",
            "Hashing",
        ]


def _choices_and_answer(client, question_id: str) -> tuple[list[str], str]:
    card = next(
        card
        for card in client.get("/flashcards/user").json()
        if card["id"] == question_id
    )
    return card["choices"], card["answer"]


def _correct_index(client, question_id: str) -> int:
    choices, correct = _choices_and_answer(client, question_id)
    return choices.index(correct)


def _wrong_index(client, question_id: str) -> int:
    return (_correct_index(client, question_id) + 1) % len(CHOICES)


def _make_due(db_session, question_id: str) -> None:
    srs = db_session.get(FlashcardSRS, uuid.UUID(question_id))
    srs.due_date = datetime.now(UTC).date() - timedelta(days=1)
    db_session.commit()


class TestAnswer:
    @pytest.fixture
    def questions(self, auth_client, course, document, llm) -> dict[str, dict]:
        generated = generate(auth_client, course, count=1).json()["questions"]
        return {question["kind"]: question for question in generated}

    @pytest.fixture
    def correct_index(self, auth_client, questions) -> int:
        return _correct_index(auth_client, questions["mcq"]["id"])

    def test_a_correct_choice_is_graded_locally_and_scheduled(
        self, auth_client, questions, correct_index, llm, document, db_session
    ):
        response = answer(
            auth_client, questions["mcq"]["id"], choice_index=correct_index
        )

        assert response.status_code == 200, response.text
        body = response.json()
        chunk = db_session.scalar(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document["id"], DocumentChunk.index == 0
            )
        )
        assert body == {
            "verdict": "correct",
            "score": 100,
            "feedback": "Correct. The answer is “first”.",
            "missing_points": [],
            "reference_answer": "first",
            "source": {
                "document_id": document["id"],
                "filename": "week-3.pdf",
                "chunk_id": str(chunk.id),
                "page_start": 1,
                "page_end": 1,
                "excerpt": DECK[0].bullets[1],
            },
            "srs": {
                "due_date": tomorrow().isoformat(),
                "interval_days": 1,
                "repetitions": 1,
            },
        }
        assert llm.requests_for(GRADING_PURPOSE) == []

    def test_a_written_answer_is_graded_by_the_rubric_and_feeds_sm2(
        self, auth_client, questions, llm, db_session
    ):
        question_id = questions["recall"]["id"]

        response = answer(auth_client, question_id, answer="It halves the list")

        body = response.json()
        assert (body["verdict"], body["score"]) == ("partial", 60)
        assert body["missing_points"] == ["recursion"]
        assert body["reference_answer"] == DECK[0].bullets[0]
        assert body["srs"]["repetitions"] == 1
        [request] = llm.requests_for(GRADING_PURPOSE)
        assert "It halves the list" in request.messages[0]["content"]
        card = db_session.get(Flashcard, uuid.UUID(question_id))
        db_session.refresh(card)
        assert card.review_count == 1
        srs = db_session.get(FlashcardSRS, card.id)
        assert srs.efactor == 236

    def test_an_incorrect_answer_resets_the_schedule(
        self, auth_client, questions, correct_index
    ):
        wrong = (correct_index + 1) % 4

        body = answer(auth_client, questions["mcq"]["id"], choice_index=wrong).json()

        assert body["verdict"] == "incorrect"
        assert body["srs"] == {
            "due_date": tomorrow().isoformat(),
            "interval_days": 1,
            "repetitions": 0,
        }

    @pytest.mark.parametrize(
        ("kind", "body"),
        [
            ("mcq", {}),
            ("mcq", {"choice_index": 4}),
            ("mcq", {"choice_index": -1}),
            ("recall", {}),
            ("recall", {"choice_index": 0}),
        ],
    )
    def test_answers_that_do_not_fit_the_question_are_rejected(
        self, auth_client, questions, db_session, kind, body
    ):
        question_id = questions[kind]["id"]

        response = answer(auth_client, question_id, **body)

        assert response.status_code == 422
        srs = db_session.get(FlashcardSRS, uuid.UUID(question_id))
        assert srs.repetitions == 0

    def test_another_users_question_is_not_found(
        self, other_auth_client, auth_client, questions
    ):
        assert (
            answer(other_auth_client, questions["recall"]["id"], answer="x").status_code
            == 404
        )
        assert answer(auth_client, MISSING, answer="x").status_code == 404

    def test_a_card_written_from_a_note_has_no_source(
        self, auth_client, create_note, course, fake_ai, llm
    ):
        note = create_note(auth_client, course_id=course["id"])
        made = auth_client.post(
            "/flashcards/generate", json={"note_id": note["id"], "count": 1}
        ).json()

        body = answer(auth_client, made["cards"][0]["id"], answer="Answer 1").json()

        assert body["source"] is None
        assert body["verdict"] == "correct"

    def test_a_question_without_a_stored_excerpt_quotes_the_opening_of_its_chunk(
        self, auth_client, questions, db_session
    ):
        question_id = questions["mcq"]["id"]
        card = db_session.get(Flashcard, uuid.UUID(question_id))
        card.excerpt = None
        db_session.commit()

        body = answer(auth_client, question_id, choice_index=0).json()

        chunk = db_session.get(DocumentChunk, card.chunk_id)
        assert body["source"]["excerpt"] == fallback_excerpt(chunk.text)

    def test_a_model_outage_leaves_the_schedule_untouched(
        self, auth_client, questions, tutor_llm, db_session
    ):
        def outage(request):
            raise LLMUnavailableError("overloaded")

        tutor_llm({GRADING_PURPOSE: outage})
        question_id = questions["recall"]["id"]

        response = answer(auth_client, question_id, answer="It halves the list")

        assert response.status_code == 503
        srs = db_session.get(FlashcardSRS, uuid.UUID(question_id))
        assert srs.repetitions == 0
        assert db_session.scalars(select(LLMCall.purpose)).all() == [QUESTIONS_PURPOSE]
