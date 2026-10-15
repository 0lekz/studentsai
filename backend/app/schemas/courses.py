import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.course import COURSE_NAME_MAX_LENGTH, COURSE_TERM_MAX_LENGTH


class CourseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=COURSE_NAME_MAX_LENGTH)
    term: str | None = Field(default=None, max_length=COURSE_TERM_MAX_LENGTH)
    exam_date: date | None = None

    @field_validator("term")
    @classmethod
    def blank_term_is_none(cls, value: str | None) -> str | None:
        return value or None


class CourseUpdate(CourseCreate):
    """Only the fields sent are changed; `term` and `exam_date` can be cleared with null."""

    name: str | None = Field(
        default=None, min_length=1, max_length=COURSE_NAME_MAX_LENGTH
    )
    archived: bool | None = None

    @field_validator("name", "archived")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("must not be null")
        return value


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    term: str | None
    exam_date: date | None
    archived: bool
    created_at: datetime
    updated_at: datetime


class CourseListItem(CourseResponse):
    documents_count: int
    notes_count: int
    flashcards_count: int
