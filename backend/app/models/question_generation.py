import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChunkQuestionGeneration(Base):
    """Marks a chunk as generated from with a prompt version, including attempts that yielded no questions."""

    __tablename__ = "chunk_question_generations"

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prompt_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
