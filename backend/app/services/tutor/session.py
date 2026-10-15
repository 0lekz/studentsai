import itertools
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.models.flashcard import Flashcard
from app.repositories import tutor as tutor_repository
from app.services.tutor.concept_links import (
    ConceptStanding,
    concept_standings,
    weakest_first,
)
from app.services.tutor.generation import (
    MIN_CHUNK_TOKENS,
    QUESTIONS_PROMPT_VERSION,
    generate_questions,
)

# Some chunks yield no questions, so generation may visit a few more chunks than
# it needs questions; this bounds the model calls one request can make.
CHUNK_VISITS_PER_QUESTION = 2
MASTERY_BANDS = 4


@dataclass(frozen=True)
class QuestionContext:
    """What a practice screen shows next to a question: its concept and where it comes from."""

    flashcard: Flashcard
    concept: tuple[uuid.UUID, str] | None
    source: tutor_repository.ChunkSource | None


def today_utc() -> date:
    # Due dates are UTC calendar dates throughout the SRS code (KNOWN_ISSUES 24).
    return datetime.now(UTC).date()


async def generate_for_course(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    *,
    count: int,
    chunk: DocumentChunk | None = None,
    concept_id: uuid.UUID | None = None,
) -> list[Flashcard]:
    """From one chunk, from one concept's chunks, or from the course's chunks in order."""
    if chunk is not None:
        chunks = [chunk]
    else:
        chunk_ids = (
            None
            if concept_id is None
            else tutor_repository.concept_chunk_ids(db, [concept_id])
        )
        chunks = _ungenerated(db, course_id, count, chunk_ids)
    return await generate_questions(db, user_id, course_id, chunks, count)


async def build_session(
    db: Session, user_id: uuid.UUID, course_id: uuid.UUID, size: int
) -> list[Flashcard]:
    """Due reviews first, then unseen questions on the weakest concepts, then any unseen question.

    When the pool is still short, questions are generated on demand from the
    weakest concepts' chunks, then from the rest of the course in order.
    """
    picked = tutor_repository.due_reviews(db, user_id, course_id, today_utc(), size)
    weakest = weakest_first(concept_standings(db, user_id, [course_id]))
    if len(picked) < size:
        picked += _interleaved_unseen(db, user_id, course_id, weakest, picked, size)
    if len(picked) < size:
        picked += tutor_repository.unseen_questions(
            db,
            user_id,
            course_id,
            limit=size - len(picked),
            exclude=[card.id for card in picked],
        )
    if len(picked) < size:
        shortfall = size - len(picked)
        weak_chunk_ids = tutor_repository.concept_chunk_ids(
            db, [standing.id for standing in weakest]
        )
        chunks = _ungenerated(db, course_id, shortfall, weak_chunk_ids)
        chosen = {chunk.id for chunk in chunks}
        chunks += [
            chunk
            for chunk in _ungenerated(db, course_id, shortfall, None)
            if chunk.id not in chosen
        ]
        generated = await generate_questions(db, user_id, course_id, chunks, shortfall)
        picked += generated[:shortfall]
    return picked


def question_contexts(
    db: Session, flashcards: Sequence[Flashcard]
) -> list[QuestionContext]:
    names = tutor_repository.concept_names(
        db, {card.concept_id for card in flashcards if card.concept_id}
    )
    sources = tutor_repository.chunk_sources(
        db, {card.chunk_id for card in flashcards if card.chunk_id}
    )
    return [
        QuestionContext(
            flashcard=card,
            concept=(
                (card.concept_id, names[card.concept_id])
                if card.concept_id in names
                else None
            ),
            source=sources.get(card.chunk_id) if card.chunk_id else None,
        )
        for card in flashcards
    ]


def _interleaved_unseen(
    db: Session,
    user_id: uuid.UUID,
    course_id: uuid.UUID,
    weakest: Sequence[ConceptStanding],
    picked: Sequence[Flashcard],
    size: int,
) -> list[Flashcard]:
    """Unseen questions of the weakest concepts first.

    Concepts of similar mastery share a band, and questions alternate between
    the concepts of a band so one topic never fills the session.
    """
    unseen = tutor_repository.unseen_questions(
        db,
        user_id,
        course_id,
        concept_ids=[standing.id for standing in weakest],
        exclude=[card.id for card in picked],
    )
    by_concept: dict[uuid.UUID, list[Flashcard]] = {
        standing.id: [] for standing in weakest
    }
    for card in unseen:
        by_concept[card.concept_id].append(card)

    ordered: list[Flashcard] = []
    for _, band in itertools.groupby(weakest, key=_mastery_band):
        rounds = itertools.zip_longest(*(by_concept[standing.id] for standing in band))
        ordered += [card for card in itertools.chain.from_iterable(rounds) if card]
    return ordered[: size - len(picked)]


def _mastery_band(standing: ConceptStanding) -> int:
    return min(MASTERY_BANDS - 1, int((standing.mastery or 0.0) * MASTERY_BANDS))


def _ungenerated(
    db: Session,
    course_id: uuid.UUID,
    count: int,
    chunk_ids: Sequence[uuid.UUID] | None,
) -> list[DocumentChunk]:
    """Chunks to generate from, in course order, or in the order of `chunk_ids` when given."""
    visits = count * CHUNK_VISITS_PER_QUESTION
    chunks = tutor_repository.ungenerated_chunks(
        db,
        course_id,
        QUESTIONS_PROMPT_VERSION,
        min_tokens=MIN_CHUNK_TOKENS,
        limit=visits if chunk_ids is None else None,
        chunk_ids=chunk_ids,
    )
    if chunk_ids is None:
        return chunks
    position = {chunk_id: index for index, chunk_id in enumerate(chunk_ids)}
    return sorted(chunks, key=lambda chunk: position[chunk.id])[:visits]
