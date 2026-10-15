"""
Database configuration and models for StudentsAI MVP
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    or_,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker
from sqlalchemy.sql import func

from .config import DATABASE_URL

# Database engine and session
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database models
class User(Base):
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Made nullable for OAuth users
    verified = Column(
        Boolean, default=False, nullable=False
    )  # NEW: Email verification status

    # OAuth fields (NEW)
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'apple', etc.
    oauth_id = Column(
        String(255), nullable=True, unique=True, index=True
    )  # OAuth provider's user ID

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    flashcards = relationship(
        "Flashcard", back_populates="user", cascade="all, delete-orphan"
    )


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


class Flashcard(Base):
    """A question and answer generated from a note, scheduled by `FlashcardSRS`"""

    __tablename__ = "flashcards"

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


# Database dependency
def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database initialization
def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (for testing)"""
    Base.metadata.drop_all(bind=engine)


# Database utilities
def get_user_by_email(db: Session, email: str) -> User | None:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    email: str,
    password_hash: str | None = None,
    username: str | None = None,
    oauth_provider: str | None = None,
    oauth_id: str | None = None,
) -> User:
    """Create new user (supports both password and OAuth)"""
    if username is None:
        # Generate a unique username if none provided
        import uuid

        base_username = f"user_{str(uuid.uuid4())[:8]}"
        username = base_username
        counter = 1
        while get_user_by_username(db, username):
            username = f"{base_username}_{counter}"
            counter += 1

    user = User(
        email=email,
        username=username,
        password_hash=password_hash,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_oauth(db: Session, oauth_provider: str, oauth_id: str) -> User | None:
    """Get user by OAuth provider and ID"""
    return (
        db.query(User)
        .filter(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id)
        .first()
    )


def create_or_get_oauth_user(
    db: Session,
    email: str,
    oauth_provider: str,
    oauth_id: str,
    username: str | None = None,
) -> User:
    """Create new OAuth user or get existing one"""
    # First try to find by OAuth ID
    existing_user = get_user_by_oauth(db, oauth_provider, oauth_id)
    if existing_user:
        return existing_user

    # Then try to find by email (in case user signed up with password first)
    existing_user = get_user_by_email(db, email)
    if existing_user:
        # Link existing user to OAuth
        existing_user.oauth_provider = oauth_provider
        existing_user.oauth_id = oauth_id
        existing_user.verified = True  # OAuth users are automatically verified
        db.commit()
        db.refresh(existing_user)
        return existing_user

    # Create new OAuth user
    user = create_user(
        db,
        email=email,
        username=username,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
    )
    # OAuth sign-ups are considered verified (provider verified email)
    user.verified = True
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def update_user_profile(db: Session, user_id: uuid.UUID, **kwargs) -> User | None:
    """Update user profile fields"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    for field, value in kwargs.items():
        if hasattr(user, field):
            setattr(user, field, value)

    user.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def _notes_of(db: Session, user_id: uuid.UUID, course_id: uuid.UUID | None):
    query = db.query(Note).filter(Note.user_id == user_id)
    if course_id is not None:
        query = query.filter(Note.course_id == course_id)
    return query


def get_notes_by_user(
    db: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int | None = None,
    course_id: uuid.UUID | None = None,
) -> list[Note]:
    """Get a user's notes, optionally one course's, all of them unless a limit is given"""
    return _notes_of(db, user_id, course_id).offset(skip).limit(limit).all()


def count_notes_by_user(
    db: Session, user_id: uuid.UUID, course_id: uuid.UUID | None = None
) -> int:
    return _notes_of(db, user_id, course_id).count()


def get_notes_by_titles(
    db: Session, user_id: uuid.UUID, titles: list[str]
) -> list[Note]:
    """Get notes for a user by exact titles."""
    if not titles:
        return []
    return (
        db.query(Note)
        .filter(Note.user_id == user_id)
        .filter(Note.title.in_(titles))
        .all()
    )


def get_note_by_id(db: Session, note_id: uuid.UUID, user_id: uuid.UUID) -> Note | None:
    """Get note by ID for a specific user"""
    return db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()


def create_note(
    db: Session,
    title: str,
    content: str,
    user_id: uuid.UUID,
    course_id: uuid.UUID | None = None,
) -> Note:
    """Create new note"""
    note = Note(title=title, content=content, user_id=user_id, course_id=course_id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_note(
    db: Session,
    note: Note,
    title: str | None = None,
    content: str | None = None,
    summary: str | None = None,
) -> Note:
    """Update existing note"""
    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
    if summary is not None:
        note.summary = summary
    # Tags update handled via separate helper to avoid accidental wipes

    note.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note: Note):
    """Delete note and all related data"""
    try:
        # First delete related flashcards and their SRS data
        flashcards = db.query(Flashcard).filter(Flashcard.note_id == note.id).all()
        for flashcard in flashcards:
            # Delete SRS data first
            db.query(FlashcardSRS).filter(
                FlashcardSRS.flashcard_id == flashcard.id
            ).delete()
            # Delete the flashcard
            db.delete(flashcard)

        # Delete note similarities
        db.query(NoteSimilarity).filter(
            (NoteSimilarity.note_a_id == note.id)
            | (NoteSimilarity.note_b_id == note.id)
        ).delete()

        # Delete note links
        db.query(NoteLink).filter(
            (NoteLink.from_note_id == note.id) | (NoteLink.to_note_id == note.id)
        ).delete()

        # Finally delete the note
        db.delete(note)
        db.commit()

    except Exception as e:
        db.rollback()
        raise Exception(f"Failed to delete note: {e!s}") from e


def get_flashcards_by_note(db: Session, note_id: uuid.UUID):
    """Get flashcards for a note"""
    return db.query(Flashcard).filter(Flashcard.note_id == note_id).all()


def create_flashcard(
    db: Session,
    question: str,
    answer: str,
    note_id: uuid.UUID,
    user_id: uuid.UUID,
    course_id: uuid.UUID | None = None,
) -> Flashcard:
    """Create a flashcard, due for review today"""
    flashcard = Flashcard(
        question=question,
        answer=answer,
        note_id=note_id,
        user_id=user_id,
        course_id=course_id,
    )
    db.add(flashcard)
    db.flush()
    db.add(_new_srs_entry(flashcard.id, user_id))
    db.commit()
    db.refresh(flashcard)
    return flashcard


# Backlinks and tags helpers
def set_note_tags(db: Session, note: Note, tags: list[str]) -> Note:
    note.tags = tags
    note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    return note


def create_note_link(
    db: Session,
    from_note_id: uuid.UUID,
    to_note_id: uuid.UUID,
    link_type: str = "manual",
) -> NoteLink:
    link = NoteLink(
        from_note_id=from_note_id, to_note_id=to_note_id, link_type=link_type
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def delete_note_link(
    db: Session, from_note_id: uuid.UUID, to_note_id: uuid.UUID
) -> None:
    db.query(NoteLink).filter(
        NoteLink.from_note_id == from_note_id, NoteLink.to_note_id == to_note_id
    ).delete()
    db.commit()


def get_backlinks(db: Session, note_id: uuid.UUID) -> list[Note]:
    # Notes that link to this note
    from_links = db.query(NoteLink).filter(NoteLink.to_note_id == note_id).all()
    from_ids = [link_to_note.from_note_id for link_to_note in from_links]
    if not from_ids:
        return []
    return db.query(Note).filter(Note.id.in_(from_ids)).all()


def replace_manual_links_for_note(
    db: Session,
    user_id: uuid.UUID,
    from_note_id: uuid.UUID,
    to_note_ids: list[uuid.UUID],
) -> None:
    """Replace manual links for a note with provided targets."""
    # delete existing manual links from this note
    db.query(NoteLink).filter(NoteLink.from_note_id == from_note_id).delete()
    # insert new ones
    for tid in to_note_ids:
        if tid == from_note_id:
            continue
        link = NoteLink(from_note_id=from_note_id, to_note_id=tid, link_type="manual")
        db.add(link)
    db.commit()


def get_links_for_user_notes(db: Session, note_ids: list[uuid.UUID]) -> list[NoteLink]:
    if not note_ids:
        return []
    return db.query(NoteLink).filter(NoteLink.from_note_id.in_(note_ids)).all()


def upsert_note_similarity(
    db: Session,
    note_a_id: uuid.UUID,
    note_b_id: uuid.UUID,
    similarity_float: float,
):
    """Store similarity scaled to 0..1000. Order ids to keep uniqueness."""
    a, b = (
        (note_a_id, note_b_id)
        if str(note_a_id) < str(note_b_id)
        else (note_b_id, note_a_id)
    )
    scaled = int(max(0.0, min(1.0, similarity_float)) * 1000)
    row = (
        db.query(NoteSimilarity)
        .filter(NoteSimilarity.note_a_id == a, NoteSimilarity.note_b_id == b)
        .first()
    )
    if row:
        row.similarity = scaled
    else:
        row = NoteSimilarity(note_a_id=a, note_b_id=b, similarity=scaled)
        db.add(row)
    db.commit()
    return row


def get_similarities_for_notes(db: Session, note_ids: list[uuid.UUID]):
    if not note_ids:
        return []
    return (
        db.query(NoteSimilarity)
        .filter(
            NoteSimilarity.note_a_id.in_(note_ids)
            | NoteSimilarity.note_b_id.in_(note_ids)
        )
        .all()
    )


# Flashcard functions
def get_user_flashcard(
    db: Session, flashcard_id: uuid.UUID, user_id: uuid.UUID
) -> Flashcard | None:
    return (
        db.query(Flashcard)
        .filter(Flashcard.id == flashcard_id, Flashcard.user_id == user_id)
        .first()
    )


def get_user_flashcards(
    db: Session,
    user_id: uuid.UUID,
    tags: list[str] | None = None,
    search: str | None = None,
    course_id: uuid.UUID | None = None,
) -> list[Flashcard]:
    """Get all flashcards for a user, optionally filtered by course, tags and search query"""
    query = db.query(Flashcard).filter(Flashcard.user_id == user_id)

    if course_id is not None:
        query = query.filter(Flashcard.course_id == course_id)

    # Filter by tags if provided
    if tags:
        query = query.filter(Flashcard.tags.overlap(tags))

    # Filter by search query if provided
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Flashcard.question).like(search_term),
                func.lower(Flashcard.answer).like(search_term),
            )
        )

    return query.order_by(Flashcard.created_at.desc()).all()


def get_flashcards_by_tag(db: Session, user_id: uuid.UUID, tag: str) -> list[Flashcard]:
    """Get flashcards with a specific tag for a user"""
    return (
        db.query(Flashcard)
        .filter(Flashcard.user_id == user_id, Flashcard.tags.contains([tag]))
        .all()
    )


def add_flashcard_tag(
    db: Session, flashcard_id: uuid.UUID, user_id: uuid.UUID, tag: str
) -> Flashcard:
    """Add a tag to one of the user's flashcards"""
    flashcard = get_user_flashcard(db, flashcard_id, user_id)
    if not flashcard:
        raise ValueError("Flashcard not found")

    current = flashcard.tags or []
    if tag not in current:
        flashcard.tags = [*current, tag]
        db.commit()
        db.refresh(flashcard)

    return flashcard


def remove_flashcard_tag(
    db: Session, flashcard_id: uuid.UUID, user_id: uuid.UUID, tag: str
) -> Flashcard:
    """Remove a tag from one of the user's flashcards"""
    flashcard = get_user_flashcard(db, flashcard_id, user_id)
    if not flashcard:
        raise ValueError("Flashcard not found")

    if flashcard.tags and tag in flashcard.tags:
        flashcard.tags = [existing for existing in flashcard.tags if existing != tag]
        db.commit()
        db.refresh(flashcard)

    return flashcard


# SRS Engine Functions (SM-2-lite algorithm)
def _new_srs_entry(flashcard_id: uuid.UUID, user_id: uuid.UUID) -> FlashcardSRS:
    return FlashcardSRS(
        flashcard_id=flashcard_id,
        user_id=user_id,
        efactor=250,  # 2.5 * 100
        interval_days=1,
        due_date=datetime.now(UTC).date(),
        repetitions=0,
    )


def get_or_create_srs_entry(
    db: Session, flashcard_id: uuid.UUID, user_id: uuid.UUID
) -> FlashcardSRS:
    """Get or create SRS entry for a flashcard"""
    srs_entry = (
        db.query(FlashcardSRS).filter(FlashcardSRS.flashcard_id == flashcard_id).first()
    )

    if not srs_entry:
        srs_entry = _new_srs_entry(flashcard_id, user_id)
        db.add(srs_entry)
        db.commit()
        db.refresh(srs_entry)

    return srs_entry


def update_srs_after_review(
    db: Session,
    flashcard_id: uuid.UUID,
    user_id: uuid.UUID,
    quality: int,  # 0-5 quality rating
) -> FlashcardSRS:
    """Update SRS data after a review using SM-2-lite algorithm"""
    srs_entry = get_or_create_srs_entry(db, flashcard_id, user_id)

    # SM-2-lite algorithm
    if quality < 3:
        # Failed - reset to beginning
        srs_entry.repetitions = 0
        srs_entry.interval_days = 1
    else:
        # Passed - increase interval
        srs_entry.repetitions += 1

        if srs_entry.repetitions == 1:
            srs_entry.interval_days = 1
        elif srs_entry.repetitions == 2:
            srs_entry.interval_days = 6
        else:
            # Calculate new interval using E-Factor
            ef = srs_entry.efactor / 100.0  # Convert back to float
            new_interval = round(srs_entry.interval_days * ef)
            srs_entry.interval_days = max(1, new_interval)

        # Update E-Factor based on quality
        ef = srs_entry.efactor / 100.0
        ef_change = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        new_ef = max(1.3, ef + ef_change)
        srs_entry.efactor = round(new_ef * 100)  # Store as integer

    # Calculate next due date
    next_due = datetime.now(UTC).date() + timedelta(days=srs_entry.interval_days)
    srs_entry.due_date = next_due
    srs_entry.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(srs_entry)
    return srs_entry


def apply_flashcard_review(
    db: Session, flashcard: Flashcard, quality: int
) -> FlashcardSRS:
    """Count the review on the card and reschedule it with SM-2"""
    flashcard.review_count = (flashcard.review_count or 0) + 1
    flashcard.last_reviewed = datetime.now(UTC)
    return update_srs_after_review(db, flashcard.id, flashcard.user_id, quality)


def get_due_flashcards_srs(
    db: Session, user_id: uuid.UUID, limit: int = 20
) -> list[Flashcard]:
    """Get flashcards that are due for review using SRS data"""
    today = datetime.now(UTC).date()

    # Get flashcards due today or overdue
    due_srs = (
        db.query(FlashcardSRS)
        .filter(FlashcardSRS.user_id == user_id, FlashcardSRS.due_date <= today)
        .order_by(FlashcardSRS.due_date.asc())
        .limit(limit)
        .all()
    )

    # Get flashcard IDs
    flashcard_ids = [srs.flashcard_id for srs in due_srs]

    if not flashcard_ids:
        return []

    # Get actual flashcard objects
    flashcards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

    # Sort by due date (overdue first)
    flashcards.sort(
        key=lambda f: next(srs.due_date for srs in due_srs if srs.flashcard_id == f.id)
    )

    return flashcards


def create_flashcard_set(
    db: Session, user_id: uuid.UUID, seed_note_id: uuid.UUID
) -> FlashcardSet:
    """Record one generation run from a seed note"""
    flashcard_set = FlashcardSet(user_id=user_id, seed_note_id=seed_note_id)
    db.add(flashcard_set)
    db.commit()
    db.refresh(flashcard_set)
    return flashcard_set


def get_flashcard_sets_by_user(db: Session, user_id: uuid.UUID) -> list[FlashcardSet]:
    """Get all flashcard sets for a user"""
    return (
        db.query(FlashcardSet)
        .filter(FlashcardSet.user_id == user_id)
        .order_by(FlashcardSet.created_at.desc())
        .all()
    )


def archive_mastered_flashcards(
    db: Session, user_id: uuid.UUID, min_repetitions: int = 3
) -> list[Flashcard]:
    """Find flashcards that have been mastered and suggest archiving"""
    mastered_srs = (
        db.query(FlashcardSRS)
        .filter(
            FlashcardSRS.user_id == user_id,
            FlashcardSRS.repetitions >= min_repetitions,
            FlashcardSRS.efactor >= 300,  # E-Factor >= 3.0 indicates mastery
        )
        .all()
    )

    if not mastered_srs:
        return []

    flashcard_ids = [srs.flashcard_id for srs in mastered_srs]
    flashcards = db.query(Flashcard).filter(Flashcard.id.in_(flashcard_ids)).all()

    # Add recently_learned tag to mastered flashcards
    for flashcard in flashcards:
        if not flashcard.tags:
            flashcard.tags = []
        if "recently_learned" not in flashcard.tags:
            flashcard.tags.append("recently_learned")

    db.commit()
    return flashcards


# Registers the models declared under app/models on Base.metadata.
import app.models  # noqa: E402, F401
