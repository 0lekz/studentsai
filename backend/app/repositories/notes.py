import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.flashcard import Flashcard, FlashcardSRS
from app.models.note import Note, NoteLink, NoteSimilarity


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
