from pydantic import field_validator

from app.schemas.common import BaseSchema


class SummarizeRequest(BaseSchema):
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Content cannot be empty")
        if len(v) > 50000:  # Reasonable limit for AI processing
            raise ValueError("Content too long for processing")
        return v.strip()


class SummarizeResponse(BaseSchema):
    summary: str
    word_count: int
    original_length: int


class GenerateFlashcardsRequest(BaseSchema):
    content: str
    count: int | None = 5

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Content cannot be empty")
        return v.strip()

    @field_validator("count")
    @classmethod
    def validate_count(cls, v):
        if v < 1 or v > 20:
            raise ValueError("Count must be between 1 and 20")
        return v


class GeneratedFlashcard(BaseSchema):
    question: str
    answer: str


class GenerateFlashcardsResponse(BaseSchema):
    flashcards: list[GeneratedFlashcard]
    count: int
