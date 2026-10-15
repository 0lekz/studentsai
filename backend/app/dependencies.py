import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.config import settings
from app.db.session import get_db
from app.rate_limiter import check_rate_limit
from app.services.courses import get_course
from app.services.ingestion import DocumentStorage


async def enforce_rate_limit(
    request: Request, user_id: uuid.UUID = Depends(get_current_user_id)
) -> None:
    await check_rate_limit(request, str(user_id))


def get_document_storage() -> DocumentStorage:
    return DocumentStorage(settings.document_storage_dir)


def optional_owned_course_id(
    course_id: uuid.UUID | None = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> uuid.UUID | None:
    """The optional `course_id` filter of list routes; a course the caller does not own is a 404."""
    if course_id is not None and get_course(db, user_id, course_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course_id
