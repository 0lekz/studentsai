import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.config import settings
from app.models import (
    Concept,
    ConceptChunk,
    ConceptEdge,
    ConceptExtraction,
    Course,
    Document,
    DocumentChunk,
    LLMCall,
    User,
)
from app.models.document import DocumentStatus
from app.services.concepts import extraction
from app.services.concepts.extraction import (
    MAX_CONCEPTS_PER_CHUNK,
    MIN_CHUNK_TOKENS,
    PROMPT_VERSION,
    PURPOSE,
    SYSTEM_PROMPT,
    NoReadyDocumentsError,
    extract_course_concepts,
)
from app.services.embedding_service import FakeEmbedder
from app.services.ingestion.chunking import estimate_tokens
from app.services.llm import LLMUnavailableError
from app.services.llm.client import Generation, StopReason
from app.services.llm.fake_client import FakeLLMClient

UPLOADED = datetime(2026, 10, 1, tzinfo=UTC)
FILLER = (
    " The lecture explains it step by step with a worked example from the textbook,"
    " then closes the section with two short review questions for students to practice."
)


def lecture_text(topic: str) -> str:
    return f"{topic}.{FILLER}"


def concepts(*names: str) -> dict:
    return {
        "concepts": [
            {"name": name, "description": f"{name} as taught."} for name in names
        ]
    }


def by_topic(replies: dict[str, dict]) -> Callable:
    """A fake reply that answers each chunk by the topic its text starts with."""

    def reply(request):
        chunk = request.messages[0]["content"]
        for topic, answer in replies.items():
            if f"<chunk>\n{topic}." in chunk:
                return answer
        return concepts()

    return reply


@pytest.fixture
def course(db_session) -> Course:
    owner = User(email="owner@example.com", username="owner", verified=True)
    db_session.add(owner)
    db_session.flush()
    course = Course(user_id=owner.id, name="Cell biology")
    db_session.add(course)
    db_session.commit()
    return course


@pytest.fixture
def add_document(db_session, course) -> Callable[..., Document]:
    uploads = iter(range(100))

    def add(
        *sections: str | tuple[list[str], str],
        status: DocumentStatus = DocumentStatus.READY,
        filename: str = "lecture.pdf",
    ) -> Document:
        document = Document(
            user_id=course.user_id,
            course_id=course.id,
            filename=filename,
            content_type="application/pdf",
            size_bytes=1,
            storage_path=f"{uuid.uuid4()}.pdf",
            status=status.value,
            created_at=UPLOADED + timedelta(minutes=next(uploads)),
        )
        for index, section in enumerate(sections):
            heading_path, text = (
                section if isinstance(section, tuple) else ([], lecture_text(section))
            )
            document.chunks.append(
                DocumentChunk(
                    index=index,
                    heading_path=heading_path,
                    page_start=index + 1,
                    page_end=index + 1,
                    text=text,
                    token_estimate=estimate_tokens(text),
                )
            )
        db_session.add(document)
        db_session.commit()
        return document

    return add


@pytest.fixture
def embedder() -> FakeEmbedder:
    return FakeEmbedder()


@pytest.fixture
def extract(db_session, course, embedder):
    async def run(client: FakeLLMClient):
        return await extract_course_concepts(
            db_session, course, client=client, embedder=embedder
        )

    return run


def stored_concepts(db_session, course) -> list[Concept]:
    db_session.expire_all()
    return list(
        db_session.scalars(
            select(Concept)
            .where(Concept.course_id == course.id)
            .order_by(Concept.order)
        )
    )


def names(db_session, course) -> list[str]:
    return [concept.name for concept in stored_concepts(db_session, course)]


def chunk_links(db_session, concept: Concept) -> list[tuple[uuid.UUID, int]]:
    rows = db_session.execute(
        select(ConceptChunk.document_id, DocumentChunk.index)
        .join(DocumentChunk, DocumentChunk.id == ConceptChunk.chunk_id)
        .where(ConceptChunk.concept_id == concept.id)
        .order_by(DocumentChunk.index)
    )
    return [tuple(row) for row in rows]


def edges(db_session, course) -> set[tuple[str, str, str]]:
    by_id = {
        concept.id: concept.name for concept in stored_concepts(db_session, course)
    }
    return {
        (by_id[edge.source_id], by_id[edge.target_id], edge.kind)
        for edge in db_session.scalars(
            select(ConceptEdge).where(ConceptEdge.course_id == course.id)
        )
    }


async def test_each_chunk_is_one_cached_structured_call_attributed_to_the_owner(
    db_session, course, add_document, extract
):
    add_document(
        (["Cells", "Membranes"], lecture_text("Membranes")),
        (["Cells", "Nucleus"], lecture_text("Nucleus")),
    )
    fake = FakeLLMClient({PURPOSE: concepts("Cell membrane")})

    await extract(fake)

    first, second = fake.requests_for(PURPOSE)
    assert first.system == SYSTEM_PROMPT
    assert first.messages == (
        {
            "role": "user",
            "content": f"<section>Cells > Membranes</section>\n<chunk>\n{lecture_text('Membranes')}\n</chunk>",
        },
    )
    assert first.json_schema["required"] == ["concepts"]
    assert first.temperature is None
    assert first.user_id == course.user_id
    assert "<section>Cells > Nucleus</section>" in second.messages[0]["content"]
    logged = db_session.scalars(select(LLMCall).where(LLMCall.purpose == PURPOSE)).all()
    assert [call.user_id for call in logged] == [course.user_id] * 2


async def test_a_chunk_without_headings_is_sent_without_a_section_line(
    course, add_document, extract
):
    add_document("Osmosis")
    fake = FakeLLMClient()

    await extract(fake)

    [request] = fake.requests_for(PURPOSE)
    assert (
        request.messages[0]["content"]
        == f"<chunk>\n{lecture_text('Osmosis')}\n</chunk>"
    )


async def test_chunks_under_the_token_minimum_are_skipped(
    db_session, course, add_document, extract
):
    short = "Reading: chapter 3."
    long_enough = "x" * (MIN_CHUNK_TOKENS * 4)
    assert estimate_tokens(long_enough) == MIN_CHUNK_TOKENS
    add_document(([], short), ([], long_enough))
    fake = FakeLLMClient()

    report = await extract(fake)

    [request] = fake.requests_for(PURPOSE)
    assert long_enough in request.messages[0]["content"]
    assert (report.chunks_sent, report.chunks_too_short) == (1, 1)


async def test_concepts_are_ordered_by_first_appearance_across_documents_in_upload_order(
    db_session, course, add_document, extract
):
    add_document("Glycolysis", "Krebs")
    add_document("Transport")
    fake = FakeLLMClient(
        {
            PURPOSE: by_topic(
                {
                    "Glycolysis": concepts("Glycolysis", "ATP"),
                    "Krebs": concepts("Krebs cycle", "ATP"),
                    "Transport": concepts("Active transport", "ATP"),
                }
            )
        }
    )

    await extract(fake)

    assert [(c.name, c.order) for c in stored_concepts(db_session, course)] == [
        ("Glycolysis", 0),
        ("ATP", 1),
        ("Krebs cycle", 2),
        ("Active transport", 3),
    ]


async def test_the_same_name_in_any_case_merges_into_the_earlier_concept(
    db_session, course, add_document, extract
):
    first = add_document("Glycolysis")
    second = add_document("Respiration")
    fake = FakeLLMClient(
        {
            PURPOSE: by_topic(
                {
                    "Glycolysis": {
                        "concepts": [
                            {"name": "ATP", "description": "The energy currency."},
                            {"name": "atp", "description": "Repeated in one chunk."},
                        ]
                    },
                    "Respiration": {
                        "concepts": [
                            {"name": "Atp", "description": "Made in mitochondria."}
                        ]
                    },
                }
            )
        }
    )

    report = await extract(fake)

    [atp] = stored_concepts(db_session, course)
    assert (atp.name, atp.description) == ("ATP", "The energy currency.")
    assert chunk_links(db_session, atp) == [(first.id, 0), (second.id, 0)]
    assert (report.mentions, report.concepts_created) == (3, 1)
    assert report.dedup_rate == pytest.approx(2 / 3)


async def test_a_name_with_a_similar_embedding_merges_and_a_dissimilar_one_does_not(
    db_session, course, add_document, extract, monkeypatch
):
    monkeypatch.setattr(settings, "concept_dedup_threshold", 0.93)
    add_document("Pumps", "Channels")
    fake = FakeLLMClient(
        {
            PURPOSE: by_topic(
                {
                    "Pumps": concepts("Sodium-potassium pump"),
                    "Channels": concepts("Sodium potassium pump", "Potassium channel"),
                }
            )
        }
    )

    report = await extract(fake)

    pump, channel = stored_concepts(db_session, course)
    assert (pump.name, channel.name) == ("Sodium-potassium pump", "Potassium channel")
    assert [index for _, index in chunk_links(db_session, pump)] == [0, 1]
    assert report.merged_by_embedding == 1


async def test_a_later_mention_fills_an_empty_description(
    db_session, course, add_document, extract
):
    add_document("Glycolysis", "Krebs")
    fake = FakeLLMClient(
        {
            PURPOSE: by_topic(
                {
                    "Glycolysis": {"concepts": [{"name": "ATP", "description": " "}]},
                    "Krebs": {"concepts": [{"name": "ATP", "description": "Energy."}]},
                }
            )
        }
    )

    await extract(fake)

    [atp] = stored_concepts(db_session, course)
    assert atp.description == "Energy."


async def test_a_document_without_concepts_is_still_recorded(
    db_session, course, add_document, extract
):
    add_document("Agenda")

    report = await extract(FakeLLMClient({PURPOSE: concepts()}))

    assert (report.documents, report.mentions, report.dedup_rate) == (1, 0, None)
    assert stored_concepts(db_session, course) == []
    assert db_session.scalar(select(ConceptExtraction.prompt_version)) == PROMPT_VERSION


async def test_names_are_tidied_blank_names_dropped_and_each_chunk_capped(
    db_session, course, add_document, extract
):
    add_document("Many")
    many = [f"Concept {n}." for n in range(MAX_CONCEPTS_PER_CHUNK + 2)]
    fake = FakeLLMClient({PURPOSE: concepts("  ", *many)})

    await extract(fake)

    assert names(db_session, course) == [
        f"Concept {n}" for n in range(MAX_CONCEPTS_PER_CHUNK - 1)
    ]


async def test_a_second_run_skips_extracted_documents_and_a_new_version_replays_the_cache(
    db_session, course, add_document, extract
):
    document = add_document("Glycolysis")
    fake = FakeLLMClient({PURPOSE: concepts("Glycolysis")})

    await extract(fake)
    again = await extract(fake)

    assert len(fake.requests) == 1
    assert again.documents == 0
    extracted = db_session.scalars(select(ConceptExtraction)).all()
    assert [(row.document_id, row.prompt_version) for row in extracted] == [
        (document.id, PROMPT_VERSION)
    ]

    db_session.delete(extracted[0])
    db_session.commit()
    await extract(fake)

    assert len(fake.requests) == 1
    calls = db_session.scalars(select(LLMCall).order_by(LLMCall.created_at)).all()
    assert [call.cached for call in calls] == [False, True]
    assert names(db_session, course) == ["Glycolysis"]


async def test_only_ready_documents_are_extracted(
    db_session, course, add_document, extract
):
    add_document(status=DocumentStatus.FAILED)
    with pytest.raises(NoReadyDocumentsError):
        await extract(FakeLLMClient())

    add_document("Osmosis")
    report = await extract(FakeLLMClient())

    assert report.documents == 1


async def test_a_refused_or_invalid_chunk_is_skipped_and_the_document_still_recorded(
    db_session, course, add_document, extract, caplog
):
    add_document("Refused", "Invalid", "Fine")
    refusal = Generation("", 10, 0, StopReason.REFUSAL)
    fake = FakeLLMClient(
        {
            PURPOSE: by_topic(
                {
                    "Refused": refusal,
                    "Invalid": {"concepts": "not a list"},
                    "Fine": concepts("Osmosis"),
                }
            )
        }
    )

    with caplog.at_level(logging.WARNING, logger=extraction.__name__):
        report = await extract(fake)

    assert names(db_session, course) == ["Osmosis"]
    assert report.chunks_failed == 2
    assert len(caplog.records) == 2
    assert db_session.scalar(select(ConceptExtraction.prompt_version)) == PROMPT_VERSION


async def test_an_unreachable_provider_aborts_without_recording_the_document(
    db_session, course, add_document, extract
):
    finished = add_document("Glycolysis")
    add_document("Krebs")

    def unavailable(request):
        if "Krebs" in request.messages[0]["content"]:
            raise LLMUnavailableError("overloaded")
        return concepts("Glycolysis")

    with pytest.raises(LLMUnavailableError):
        await extract(FakeLLMClient({PURPOSE: unavailable}))

    db_session.expire_all()
    assert db_session.scalars(select(ConceptExtraction.document_id)).all() == [
        finished.id
    ]
    assert names(db_session, course) == ["Glycolysis"]


async def test_prerequisite_edges_follow_order_and_related_edges_name_similarity(
    db_session, course, add_document, extract, monkeypatch
):
    monkeypatch.setattr(settings, "concept_related_threshold", 0.6)
    add_document("Intro", "Detail", "Later")
    add_document("Far")
    fake = FakeLLMClient(
        {
            PURPOSE: by_topic(
                {
                    "Intro": concepts("Cell membrane", "Phospholipid"),
                    "Detail": concepts("Membrane protein"),
                    "Later": concepts("Osmosis"),
                    "Far": concepts("Cell membrane transport"),
                }
            )
        }
    )

    await extract(fake)

    assert edges(db_session, course) == {
        ("Cell membrane", "Phospholipid", "prerequisite"),
        ("Phospholipid", "Membrane protein", "prerequisite"),
        ("Membrane protein", "Osmosis", "prerequisite"),
        ("Cell membrane", "Cell membrane transport", "related"),
    }


async def test_concepts_embedded_by_another_model_are_re_embedded(
    db_session, course, add_document, extract, embedder
):
    add_document("Osmosis")
    await extract(FakeLLMClient({PURPOSE: concepts("Osmosis")}))
    [osmosis] = stored_concepts(db_session, course)
    osmosis.embedding_model = "an-older-model"
    osmosis.embedding = [0.0] * 383 + [1.0]
    db_session.commit()

    await extract(FakeLLMClient())

    [osmosis] = stored_concepts(db_session, course)
    assert osmosis.embedding_model == embedder.model_name
    assert list(osmosis.embedding) == pytest.approx(embedder.embed(["Osmosis"])[0])
