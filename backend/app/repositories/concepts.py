import uuid
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.models.concept import Concept, ConceptChunk, ConceptEdge, ConceptExtraction
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.flashcard import Flashcard, FlashcardSRS


@dataclass(frozen=True)
class Source:
    document_id: uuid.UUID
    chunk_id: uuid.UUID
    page_start: int
    page_end: int


@dataclass(frozen=True)
class Occurrence:
    concept_id: uuid.UUID
    order: int
    document_id: uuid.UUID
    chunk_index: int


@dataclass(frozen=True)
class SimilarPair:
    source_id: uuid.UUID
    target_id: uuid.UUID
    similarity: float


def lock_course(db: Session, course_id: uuid.UUID) -> None:
    """Serializes concept writes per course until the transaction ends."""
    key = int.from_bytes(course_id.bytes[:8], "big", signed=True)
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def ready_documents(db: Session, course_id: uuid.UUID) -> list[Document]:
    """The course's extracted documents in upload order."""
    return list(
        db.scalars(
            select(Document)
            .where(
                Document.course_id == course_id,
                Document.status == DocumentStatus.READY.value,
            )
            .order_by(Document.created_at, Document.id)
        )
    )


def extracted_document_ids(
    db: Session, document_ids: Sequence[uuid.UUID], prompt_version: str
) -> set[uuid.UUID]:
    return set(
        db.scalars(
            select(ConceptExtraction.document_id).where(
                ConceptExtraction.document_id.in_(document_ids),
                ConceptExtraction.prompt_version == prompt_version,
            )
        )
    )


def mark_extracted(db: Session, document_id: uuid.UUID, prompt_version: str) -> None:
    db.execute(
        insert(ConceptExtraction)
        .values(document_id=document_id, prompt_version=prompt_version)
        .on_conflict_do_nothing()
    )


def course_concepts(db: Session, course_id: uuid.UUID) -> list[Concept]:
    return list(
        db.scalars(
            select(Concept)
            .where(Concept.course_id == course_id)
            .order_by(Concept.order)
        )
    )


def get_course_concept(
    db: Session, course_id: uuid.UUID, concept_id: uuid.UUID
) -> Concept | None:
    return db.scalar(
        select(Concept).where(Concept.id == concept_id, Concept.course_id == course_id)
    )


def find_concept_by_name(
    db: Session, course_id: uuid.UUID, name: str
) -> Concept | None:
    return db.scalar(
        select(Concept).where(
            Concept.course_id == course_id,
            func.lower(Concept.name) == func.lower(name),
        )
    )


def link_chunks(
    db: Session, links: Iterable[tuple[uuid.UUID, uuid.UUID]], document_id: uuid.UUID
) -> None:
    rows = [
        {"concept_id": concept_id, "chunk_id": chunk_id, "document_id": document_id}
        for concept_id, chunk_id in links
    ]
    if rows:
        db.execute(insert(ConceptChunk).values(rows).on_conflict_do_nothing())


def concept_sources(
    db: Session, course_id: uuid.UUID, concept_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[Source]]:
    """Each concept's chunks, in document upload order and then reading order."""
    rows = db.execute(
        select(
            ConceptChunk.concept_id,
            DocumentChunk.document_id,
            DocumentChunk.id,
            DocumentChunk.page_start,
            DocumentChunk.page_end,
        )
        .join(Concept, Concept.id == ConceptChunk.concept_id)
        .join(DocumentChunk, DocumentChunk.id == ConceptChunk.chunk_id)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Concept.course_id == course_id, Concept.id.in_(concept_ids))
        .order_by(Document.created_at, Document.id, DocumentChunk.index)
    )
    sources: dict[uuid.UUID, list[Source]] = defaultdict(list)
    for concept_id, *source in rows:
        sources[concept_id].append(Source(*source))
    return sources


@dataclass(frozen=True)
class QuestionSchedule:
    """A question on a concept with its SM-2 row; both fields are None when it has none."""

    concept_id: uuid.UUID
    repetitions: int | None
    efactor_hundredths: int | None


def question_schedules(
    db: Session, user_id: uuid.UUID, concept_ids: Sequence[uuid.UUID]
) -> list[QuestionSchedule]:
    rows = db.execute(
        select(Flashcard.concept_id, FlashcardSRS.repetitions, FlashcardSRS.efactor)
        .outerjoin(FlashcardSRS, FlashcardSRS.flashcard_id == Flashcard.id)
        .where(Flashcard.user_id == user_id, Flashcard.concept_id.in_(concept_ids))
    )
    return [QuestionSchedule(*row) for row in rows]


def occurrences(db: Session, course_id: uuid.UUID) -> list[Occurrence]:
    rows = db.execute(
        select(
            Concept.id, Concept.order, DocumentChunk.document_id, DocumentChunk.index
        )
        .join(ConceptChunk, ConceptChunk.concept_id == Concept.id)
        .join(DocumentChunk, DocumentChunk.id == ConceptChunk.chunk_id)
        .where(Concept.course_id == course_id)
    )
    return [Occurrence(*row) for row in rows]


def similar_pairs(
    db: Session, course_id: uuid.UUID, model_name: str, threshold: float
) -> list[SimilarPair]:
    """Pairs of the course's concepts with name embeddings above `threshold`, earlier concept first."""
    earlier = aliased(Concept)
    later = aliased(Concept)
    similarity = 1 - earlier.embedding.cosine_distance(later.embedding)
    rows = db.execute(
        select(earlier.id, later.id, similarity)
        .join(
            later,
            (later.course_id == earlier.course_id) & (later.order > earlier.order),
        )
        .where(
            earlier.course_id == course_id,
            earlier.embedding_model == model_name,
            later.embedding_model == model_name,
            similarity > threshold,
        )
    )
    return [
        SimilarPair(source_id, target_id, min(1.0, float(score)))
        for source_id, target_id, score in rows
    ]


def replace_edges(
    db: Session, course_id: uuid.UUID, edges: Iterable[ConceptEdge]
) -> None:
    db.execute(delete(ConceptEdge).where(ConceptEdge.course_id == course_id))
    db.add_all(edges)


def course_edges(db: Session, course_id: uuid.UUID) -> list[ConceptEdge]:
    source = aliased(Concept)
    target = aliased(Concept)
    return list(
        db.scalars(
            select(ConceptEdge)
            .join(source, source.id == ConceptEdge.source_id)
            .join(target, target.id == ConceptEdge.target_id)
            .where(ConceptEdge.course_id == course_id)
            .order_by(source.order, target.order, ConceptEdge.kind)
        )
    )


def delete_orphan_concepts(db: Session, course_id: uuid.UUID) -> None:
    """Deletes the course's concepts that no chunk links to and no question tests."""
    linked = select(ConceptChunk.concept_id).where(
        ConceptChunk.concept_id == Concept.id
    )
    tested = select(Flashcard.id).where(Flashcard.concept_id == Concept.id)
    db.execute(
        delete(Concept).where(
            Concept.course_id == course_id, ~linked.exists(), ~tested.exists()
        )
    )


def stale_embedding_concepts(
    db: Session, course_id: uuid.UUID, model_name: str
) -> list[Concept]:
    return list(
        db.scalars(
            select(Concept).where(
                Concept.course_id == course_id, Concept.embedding_model != model_name
            )
        )
    )
