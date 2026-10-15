import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.document import Document
from app.models.flashcard import Flashcard
from app.models.note import Note
from app.services.ingestion import DocumentStorage


@dataclass(frozen=True)
class CourseSummary:
    course: Course
    documents_count: int
    notes_count: int
    flashcards_count: int


def _count_in_course(model: type) -> Any:
    return (
        select(func.count())
        .select_from(model)
        .where(model.course_id == Course.id)
        .correlate(Course)
        .scalar_subquery()
    )


def list_courses(db: Session, user_id: uuid.UUID) -> list[CourseSummary]:
    """Active courses before archived ones, each group alphabetical."""
    rows = db.execute(
        select(
            Course,
            _count_in_course(Document),
            _count_in_course(Note),
            _count_in_course(Flashcard),
        )
        .where(Course.user_id == user_id)
        .order_by(Course.archived, func.lower(Course.name), Course.created_at)
    ).all()
    return [CourseSummary(*row) for row in rows]


def get_course(db: Session, user_id: uuid.UUID, course_id: uuid.UUID) -> Course | None:
    return db.scalar(
        select(Course).where(Course.id == course_id, Course.user_id == user_id)
    )


def create_course(
    db: Session,
    user_id: uuid.UUID,
    *,
    name: str,
    term: str | None,
    exam_date: date | None,
) -> Course:
    course = Course(user_id=user_id, name=name, term=term, exam_date=exam_date)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def update_course(db: Session, course: Course, changes: dict[str, Any]) -> Course:
    for field, value in changes.items():
        setattr(course, field, value)
    db.commit()
    db.refresh(course)
    return course


def delete_course(db: Session, storage: DocumentStorage, course: Course) -> None:
    """The database cascades to the course's rows; the document files are removed after the commit."""
    storage_paths = db.scalars(
        select(Document.storage_path).where(Document.course_id == course.id)
    ).all()
    db.delete(course)
    db.commit()
    for storage_path in storage_paths:
        storage.delete(storage_path)
