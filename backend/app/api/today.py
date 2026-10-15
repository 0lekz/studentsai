import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.db.session import get_db
from app.dependencies import enforce_rate_limit
from app.schemas.tutor import (
    ConceptMasteryItem,
    CourseRef,
    SuggestedSession,
    TodayCourse,
    TodayResponse,
)
from app.services.tutor.today import today_overview

router = APIRouter(tags=["today"], dependencies=[Depends(enforce_rate_limit)])


@router.get("/today", response_model=TodayResponse)
def get_today(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> TodayResponse:
    """Due cards per active course, its three weakest practiced concepts, and the session to start with."""
    today = today_overview(db, user_id)
    return TodayResponse(
        due_count=today.due_count,
        courses=[
            TodayCourse(
                course=CourseRef(id=row.course.id, name=row.course.name),
                due_count=row.due_count,
                weakest_concepts=[
                    ConceptMasteryItem(
                        id=concept.id, name=concept.name, mastery=concept.mastery
                    )
                    for concept in row.weakest_concepts
                ],
            )
            for row in today.courses
        ],
        suggested=(
            SuggestedSession(
                course_id=today.suggested.course_id, size=today.suggested.size
            )
            if today.suggested
            else None
        ),
    )
