import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DDL, DateTime, ForeignKey, String, event, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

EMBEDDING_DIMENSIONS = 384


class NoteEmbedding(Base):
    """One embedding per note, kept apart from `notes` so model changes and backfills never touch it."""

    __tablename__ = "note_embeddings"

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# create_tables() builds the schema with create_all on startup, so the table brings its column type.
event.listen(
    NoteEmbedding.__table__,
    "before_create",
    DDL("CREATE EXTENSION IF NOT EXISTS vector"),
)
