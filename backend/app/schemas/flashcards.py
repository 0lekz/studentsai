import uuid
from datetime import date, datetime
from typing import Any

from pydantic import Field

from app.models.flashcard import FlashcardKind, FlashcardSource
from app.schemas.common import BaseSchema


class FlashcardResponse(BaseSchema):
    id: uuid.UUID
    question: str
    answer: str
    difficulty: int
    last_reviewed: datetime | None = None
    created_at: datetime
    tags: list[str] | None = Field(default=[])
    review_count: int
    course_id: uuid.UUID | None = None
    kind: FlashcardKind = FlashcardKind.RECALL
    choices: list[Any] | None = None
    source: FlashcardSource = FlashcardSource.USER
    excerpt: str | None = None


class FlashcardReviewRequest(BaseSchema):
    quality_rating: int = Field(ge=0, le=5)


class FlashcardReviewResponse(BaseSchema):
    flashcard_id: uuid.UUID
    quality_rating: int
    repetitions: int
    interval_days: int
    efactor: float
    due_date: date


class FlashcardSetInfo(BaseSchema):
    id: uuid.UUID
    seed_note_id: uuid.UUID
    created_at: datetime
    flashcard_count: int


class FlashcardGenerationRequest(BaseSchema):
    note_id: uuid.UUID
    count: int | None = 5


class FlashcardGenerationResponse(BaseSchema):
    flashcard_set_id: uuid.UUID
    cards: list[FlashcardResponse]
