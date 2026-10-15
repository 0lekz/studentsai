import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import Select, exists, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.concept import Concept, ConceptChunk
from app.models.course import Course
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.flashcard import Flashcard, FlashcardSource, FlashcardSRS
from app.models.question_generation import ChunkQuestionGeneration
from app.repositories.flashcards import new_srs_entry


@dataclass(frozen=True)
class NewQuestion:
    kind: str
    prompt: str
    answer: str
    excerpt: str
    choices: list[str] | None
    concept_id: uuid.UUID | None


@dataclass(frozen=True)
class ChunkSource:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page_start: int
    page_end: int


# Two-key advisory locks never collide with the single-key locks concept writes take.
QUESTION_WRITES_LOCK_SPACE = 0x7475746F


def lock_course_questions(db: Session, course_id: uuid.UUID) -> None:
    """Serializes question writes per course until the transaction ends."""
    key = int.from_bytes(course_id.bytes[:4], "big", signed=True)
    db.execute(
        text(
            "SELECT pg_advisory_xact_lock(CAST(:space AS integer), CAST(:key AS integer))"
        ),
        {"space": QUESTION_WRITES_LOCK_SPACE, "key": key},
    )


def add_generated_questions(
    db: Session,
    *,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    chunk_id: uuid.UUID,
    prompt_version: str,
    questions: Sequence[NewQuestion],
) -> list[Flashcard]:
    """Add the questions with an SRS row each, due today; the caller commits."""
    flashcards = [
        Flashcard(
            question=question.prompt,
            answer=question.answer,
            excerpt=question.excerpt,
            kind=question.kind,
            choices=question.choices,
            source=FlashcardSource.GENERATED.value,
            prompt_version=prompt_version,
            user_id=user_id,
            course_id=course_id,
            chunk_id=chunk_id,
            concept_id=question.concept_id,
        )
        for question in questions
    ]
    db.add_all(flashcards)
    db.flush()
    db.add_all(new_srs_entry(flashcard.id, user_id) for flashcard in flashcards)
    return flashcards


def chunk_question_prompts(
    db: Session, user_id: uuid.UUID, chunk_id: uuid.UUID
) -> list[str]:
    return list(
        db.scalars(
            select(Flashcard.question).where(
                Flashcard.user_id == user_id, Flashcard.chunk_id == chunk_id
            )
        )
    )


def mark_chunk_generated(
    db: Session, chunk_id: uuid.UUID, prompt_version: str, question_count: int
) -> None:
    statement = insert(ChunkQuestionGeneration).values(
        chunk_id=chunk_id, prompt_version=prompt_version, question_count=question_count
    )
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[
                ChunkQuestionGeneration.chunk_id,
                ChunkQuestionGeneration.prompt_version,
            ],
            set_={"question_count": statement.excluded.question_count},
        )
    )


def ungenerated_chunks(
    db: Session,
    course_id: uuid.UUID,
    prompt_version: str,
    *,
    min_tokens: int,
    limit: int | None,
    chunk_ids: Collection[uuid.UUID] | None = None,
) -> list[DocumentChunk]:
    """Chunks of the course not yet generated from with `prompt_version`, in course order."""
    generated = exists().where(
        ChunkQuestionGeneration.chunk_id == DocumentChunk.id,
        ChunkQuestionGeneration.prompt_version == prompt_version,
    )
    query = (
        _course_chunks(course_id)
        .where(DocumentChunk.token_estimate >= min_tokens, ~generated)
        .order_by(Document.created_at, Document.id, DocumentChunk.index)
        .limit(limit)
    )
    if chunk_ids is not None:
        query = query.where(DocumentChunk.id.in_(list(chunk_ids)))
    return list(db.scalars(query))


def get_course_chunk(
    db: Session, course_id: uuid.UUID, chunk_id: uuid.UUID
) -> DocumentChunk | None:
    return db.scalar(_course_chunks(course_id).where(DocumentChunk.id == chunk_id))


def _course_chunks(course_id: uuid.UUID) -> Select[Any]:
    return (
        select(DocumentChunk)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.course_id == course_id)
    )


def get_course_concept(
    db: Session, course_id: uuid.UUID, concept_id: uuid.UUID
) -> Concept | None:
    return db.scalar(
        select(Concept).where(Concept.id == concept_id, Concept.course_id == course_id)
    )


def concept_chunk_ids(db: Session, concept_ids: Sequence[uuid.UUID]) -> list[uuid.UUID]:
    """The chunks of the concepts, grouped in the order the concepts are given."""
    if not concept_ids:
        return []
    rows = db.execute(
        select(ConceptChunk.concept_id, ConceptChunk.chunk_id).where(
            ConceptChunk.concept_id.in_(concept_ids)
        )
    ).all()
    position = {concept_id: index for index, concept_id in enumerate(concept_ids)}
    ordered = sorted(rows, key=lambda row: position[row.concept_id])
    return list(dict.fromkeys(row.chunk_id for row in ordered))


def chunk_concepts(db: Session, chunk_id: uuid.UUID) -> list[Concept]:
    return list(
        db.scalars(
            select(Concept)
            .join(ConceptChunk, ConceptChunk.concept_id == Concept.id)
            .where(ConceptChunk.chunk_id == chunk_id)
            .order_by(Concept.order, Concept.id)
        )
    )


def concept_names(
    db: Session, concept_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not concept_ids:
        return {}
    rows = db.execute(
        select(Concept.id, Concept.name).where(Concept.id.in_(list(concept_ids)))
    )
    return {concept_id: name for concept_id, name in rows}


def chunk_sources(
    db: Session, chunk_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, ChunkSource]:
    if not chunk_ids:
        return {}
    rows = db.execute(
        select(
            DocumentChunk.id,
            Document.id,
            Document.filename,
            DocumentChunk.page_start,
            DocumentChunk.page_end,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.id.in_(list(chunk_ids)))
    )
    return {row[0]: ChunkSource(*row) for row in rows}


def get_user_question(
    db: Session, user_id: uuid.UUID, question_id: uuid.UUID
) -> Flashcard | None:
    return db.scalar(
        select(Flashcard).where(
            Flashcard.id == question_id, Flashcard.user_id == user_id
        )
    )


def get_chunk(db: Session, chunk_id: uuid.UUID) -> DocumentChunk | None:
    return db.get(DocumentChunk, chunk_id)


def _reviewed() -> Any:
    return func.coalesce(Flashcard.review_count, 0) > 0


def due_reviews(
    db: Session, user_id: uuid.UUID, course_id: uuid.UUID, today: date, limit: int
) -> list[Flashcard]:
    """Cards reviewed before and due again, most overdue first."""
    return list(
        db.scalars(
            select(Flashcard)
            .join(FlashcardSRS, FlashcardSRS.flashcard_id == Flashcard.id)
            .where(
                Flashcard.user_id == user_id,
                Flashcard.course_id == course_id,
                FlashcardSRS.due_date <= today,
                _reviewed(),
            )
            .order_by(FlashcardSRS.due_date, Flashcard.created_at, Flashcard.id)
            .limit(limit)
        )
    )


def unseen_questions(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    *,
    limit: int | None = None,
    concept_ids: Collection[uuid.UUID] | None = None,
    exclude: Collection[uuid.UUID] = (),
) -> list[Flashcard]:
    """Cards never reviewed, oldest first."""
    query = (
        select(Flashcard)
        .where(
            Flashcard.user_id == user_id,
            Flashcard.course_id == course_id,
            ~_reviewed(),
        )
        .order_by(Flashcard.created_at, Flashcard.id)
        .limit(limit)
    )
    if concept_ids is not None:
        query = query.where(Flashcard.concept_id.in_(list(concept_ids)))
    if exclude:
        query = query.where(Flashcard.id.not_in(list(exclude)))
    return list(db.scalars(query))


def courses_concepts(db: Session, course_ids: Collection[uuid.UUID]) -> list[Concept]:
    if not course_ids:
        return []
    return list(
        db.scalars(
            select(Concept)
            .where(Concept.course_id.in_(list(course_ids)))
            .order_by(Concept.course_id, Concept.order, Concept.id)
        )
    )


def active_courses(db: Session, user_id: uuid.UUID) -> list[Course]:
    return list(
        db.scalars(
            select(Course)
            .where(Course.user_id == user_id, Course.archived.is_(False))
            .order_by(func.lower(Course.name), Course.created_at)
        )
    )


def due_counts(
    db: Session, user_id: uuid.UUID, course_ids: Collection[uuid.UUID], today: date
) -> dict[uuid.UUID, int]:
    """Cards due by `today` per course, the same set `GET /flashcards/due/srs` serves."""
    if not course_ids:
        return {}
    rows = db.execute(
        select(Flashcard.course_id, func.count())
        .join(FlashcardSRS, FlashcardSRS.flashcard_id == Flashcard.id)
        .where(
            Flashcard.user_id == user_id,
            Flashcard.course_id.in_(list(course_ids)),
            FlashcardSRS.due_date <= today,
        )
        .group_by(Flashcard.course_id)
    )
    return {course_id: count for course_id, count in rows}


def courses_with_material(
    db: Session, user_id: uuid.UUID, course_ids: Collection[uuid.UUID]
) -> set[uuid.UUID]:
    """Courses with a ready document or any card, the ones a session can be built for."""
    if not course_ids:
        return set()
    ids = list(course_ids)
    with_documents = select(Document.course_id).where(
        Document.user_id == user_id,
        Document.course_id.in_(ids),
        Document.status == DocumentStatus.READY.value,
    )
    with_cards = select(Flashcard.course_id).where(
        Flashcard.user_id == user_id, Flashcard.course_id.in_(ids)
    )
    return set(db.scalars(with_documents.union(with_cards)))
