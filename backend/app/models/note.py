import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Note(Base):
    """Note model for storing user notes"""

    __tablename__ = "notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Tags for keywords
    tags = Column(ARRAY(String), nullable=True, default=list)

    # Foreign keys
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Relationships
    user = relationship("User", back_populates="notes")
    flashcards = relationship(
        "Flashcard", back_populates="note", cascade="all, delete-orphan"
    )


class NoteLink(Base):
    """Explicit links between notes (manual or AI-suggested)."""

    __tablename__ = "note_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    link_type = Column(String(50), nullable=False, default="manual")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NoteSimilarity(Base):
    """Stores similarity scores between pairs of notes to drive edge styling.

    The pair is stored as (note_a_id, note_b_id) with note_a_id < note_b_id to ensure uniqueness.
    """

    __tablename__ = "note_similarities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_a_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note_b_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    similarity = Column(
        Integer, nullable=False
    )  # store as int 0..1000 (similarity*1000) for stability
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
