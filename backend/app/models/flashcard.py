import uuid
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class FlashcardKind(StrEnum):
    RECALL = "recall"
    SHORT_ANSWER = "short_answer"
    MCQ = "mcq"


class FlashcardSource(StrEnum):
    USER = "user"
    GENERATED = "generated"


def _one_of(column: str, values: type[StrEnum]) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({allowed})"


class Flashcard(Base):
    """A question and answer generated from a note, scheduled by `FlashcardSRS`"""

    __tablename__ = "flashcards"
    __table_args__ = (
        CheckConstraint(_one_of("kind", FlashcardKind), name="ck_flashcards_kind"),
        CheckConstraint(
            _one_of("source", FlashcardSource), name="ck_flashcards_source"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty = Column(Integer, default=1)  # 1-5 scale
    last_reviewed = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tags = Column(
        ARRAY(String), nullable=True, default=list
    )  # e.g., ["visit_later", "revisited", "recently_learned"]
    review_count = Column(Integer, default=0)
    kind = Column(
        String(16),
        nullable=False,
        default=FlashcardKind.RECALL.value,
        server_default=FlashcardKind.RECALL.value,
    )
    choices = Column(JSONB, nullable=True)
    source = Column(
        String(16),
        nullable=False,
        default=FlashcardSource.USER.value,
        server_default=FlashcardSource.USER.value,
    )
    prompt_version = Column(String(64), nullable=True)

    # Foreign keys
    note_id = Column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_id = Column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    concept_id = Column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    note = relationship("Note", back_populates="flashcards")
    user = relationship("User", back_populates="flashcards")


class FlashcardSRS(Base):
    """Spaced repetition system data for flashcards using SM-2-lite algorithm"""

    __tablename__ = "flashcard_srs"

    flashcard_id = Column(
        UUID(as_uuid=True),
        ForeignKey("flashcards.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    efactor = Column(Integer, default=250)  # E-Factor * 100 (2.5 -> 250)
    interval_days = Column(Integer, default=1)
    due_date = Column(Date, nullable=False)
    repetitions = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    flashcard = relationship("Flashcard")


class FlashcardSet(Base):
    """One generation run of flashcards from a seed note"""

    __tablename__ = "flashcard_sets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    seed_note_id = Column(
        UUID(as_uuid=True), ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")
    seed_note = relationship("Note")
