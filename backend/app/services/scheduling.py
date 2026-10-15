"""SM-2-lite, the one scheduler every flashcard is reviewed with."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.flashcard import Flashcard, FlashcardSRS
from app.repositories.flashcards import new_srs_entry


def get_or_create_srs_entry(
    db: Session, flashcard_id: uuid.UUID, user_id: uuid.UUID
) -> FlashcardSRS:
    """Get or create SRS entry for a flashcard"""
    srs_entry = (
        db.query(FlashcardSRS).filter(FlashcardSRS.flashcard_id == flashcard_id).first()
    )

    if not srs_entry:
        srs_entry = new_srs_entry(flashcard_id, user_id)
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
