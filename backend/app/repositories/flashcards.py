import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.flashcard import Flashcard, FlashcardSet, FlashcardSRS


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
    db.add(new_srs_entry(flashcard.id, user_id))
    db.commit()
    db.refresh(flashcard)
    return flashcard


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


def new_srs_entry(flashcard_id: uuid.UUID, user_id: uuid.UUID) -> FlashcardSRS:
    return FlashcardSRS(
        flashcard_id=flashcard_id,
        user_id=user_id,
        efactor=250,  # 2.5 * 100
        interval_days=1,
        due_date=datetime.now(UTC).date(),
        repetitions=0,
    )


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
        current = flashcard.tags or []
        if "recently_learned" not in current:
            flashcard.tags = [*current, "recently_learned"]

    db.commit()
    return flashcards
