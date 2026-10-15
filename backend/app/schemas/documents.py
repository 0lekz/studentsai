import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentKind, DocumentStatus


class OutlineNode(BaseModel):
    title: str
    level: int
    page: int
    children: list["OutlineNode"]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    kind: DocumentKind | None
    page_count: int | None
    status: DocumentStatus
    error: str | None
    created_at: datetime
    updated_at: datetime


class DocumentDetailResponse(DocumentResponse):
    outline: list[OutlineNode] | None


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    index: int
    heading_path: list[str]
    page_start: int
    page_end: int
    text: str
    token_estimate: int
