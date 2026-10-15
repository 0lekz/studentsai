import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema


class NoteBase(BaseSchema):
    title: str
    content: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Title cannot be empty")
        if len(v) > 500:
            raise ValueError("Title cannot exceed 500 characters")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Content cannot be empty")
        return v.strip()


class NoteCreate(NoteBase):
    course_id: uuid.UUID | None = None


class NoteUpdate(BaseSchema):
    title: str | None = None
    content: str | None = None
    summary: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Title cannot be empty")
            if len(v) > 500:
                raise ValueError("Title cannot exceed 500 characters")
            return v.strip()
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Content cannot be empty")
            return v.strip()
        return v


class Note(NoteBase):
    id: uuid.UUID
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
    user_id: uuid.UUID


class NoteResponse(BaseSchema):
    id: uuid.UUID
    title: str
    content: str
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
    tags: list[str] | None = Field(default=[])
    course_id: uuid.UUID | None = None


class NoteListResponse(BaseSchema):
    notes: list[NoteResponse]
    total: int
    page: int
    per_page: int


class BacklinkResponse(BaseSchema):
    note_id: uuid.UUID
    title: str
    excerpt: str | None = None
    created_at: datetime


class UpdateTagsRequest(BaseSchema):
    tags: list[str]
