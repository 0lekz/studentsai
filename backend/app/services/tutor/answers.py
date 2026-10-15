import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.flashcard import Flashcard, FlashcardSRS
from app.repositories import tutor as tutor_repository
from app.services.scheduling import apply_flashcard_review
from app.services.tutor.grading import Grade, grade_answer
from app.services.tutor.text import fallback_excerpt


@dataclass(frozen=True)
class AnswerSource:
    chunk: tutor_repository.ChunkSource
    excerpt: str


@dataclass(frozen=True)
class AnswerOutcome:
    grade: Grade
    reference_answer: str
    source: AnswerSource | None
    srs: FlashcardSRS


async def answer_question(
    db: Session,
    flashcard: Flashcard,
    *,
    answer: str | None,
    choice_index: int | None,
    user_id: uuid.UUID,
) -> AnswerOutcome:
    """Grade the answer, reschedule the card with the grade's SM-2 quality, and say where the answer lives."""
    grade = await grade_answer(
        db, flashcard, answer=answer, choice_index=choice_index, user_id=user_id
    )
    reference_answer = flashcard.answer
    source = _source(db, flashcard)
    srs = apply_flashcard_review(db, flashcard, grade.quality)
    return AnswerOutcome(grade, reference_answer, source, srs)


def _source(db: Session, flashcard: Flashcard) -> AnswerSource | None:
    chunk_ids = [flashcard.chunk_id] if flashcard.chunk_id else []
    chunk_source = tutor_repository.chunk_sources(db, chunk_ids).get(flashcard.chunk_id)
    if chunk_source is None:
        return None
    excerpt = flashcard.excerpt
    if not excerpt:
        chunk = tutor_repository.get_chunk(db, flashcard.chunk_id)
        excerpt = fallback_excerpt(chunk.text) if chunk else ""
    return AnswerSource(chunk_source, excerpt)
