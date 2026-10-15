import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.db.session import get_db
from app.dependencies import enforce_rate_limit, get_document_storage
from app.models.course import Course
from app.schemas.courses import (
    CourseCreate,
    CourseListItem,
    CourseResponse,
    CourseUpdate,
)
from app.services.courses import (
    create_course,
    delete_course,
    get_course,
    list_courses,
    update_course,
)
from app.services.ingestion import DocumentStorage


def owned_course(
    course_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Course:
    course = get_course(db, user_id, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


router = APIRouter(
    prefix="/courses",
    tags=["courses"],
    dependencies=[Depends(enforce_rate_limit)],
)


@router.get("", response_model=list[CourseListItem])
def get_courses(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[CourseListItem]:
    return [
        CourseListItem(
            **CourseResponse.model_validate(summary.course).model_dump(),
            documents_count=summary.documents_count,
            notes_count=summary.notes_count,
            flashcards_count=summary.flashcards_count,
        )
        for summary in list_courses(db, user_id)
    ]


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def add_course(
    payload: CourseCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> Course:
    return create_course(db, user_id, **payload.model_dump())


@router.get("/{course_id}", response_model=CourseResponse)
def get_course_detail(course: Course = Depends(owned_course)) -> Course:
    return course


@router.patch("/{course_id}", response_model=CourseResponse)
def edit_course(
    payload: CourseUpdate,
    course: Course = Depends(owned_course),
    db: Session = Depends(get_db),
) -> Course:
    return update_course(db, course, payload.model_dump(exclude_unset=True))


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_course(
    course: Course = Depends(owned_course),
    db: Session = Depends(get_db),
    storage: DocumentStorage = Depends(get_document_storage),
) -> None:
    delete_course(db, storage, course)
