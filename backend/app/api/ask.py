import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.practice import tutor_course, tutor_failure
from app.auth import get_verified_user_id
from app.db.session import get_db
from app.dependencies import enforce_rate_limit
from app.models.course import Course
from app.schemas.tutor import AskRequest, AskResponse, Citation
from app.services.llm import LLMError
from app.services.tutor.ask import ask_course

router = APIRouter(tags=["ask"], dependencies=[Depends(enforce_rate_limit)])


@router.post("/courses/{course_id}/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    course: Course = Depends(tutor_course),
    user_id: uuid.UUID = Depends(get_verified_user_id),
    db: Session = Depends(get_db),
) -> AskResponse:
    """Answer from the course material only, citing the chunks used; `[n]` in the answer is `citations[n - 1]`."""
    try:
        result = await ask_course(db, course.id, payload.question, user_id)
    except LLMError as error:
        raise tutor_failure(error) from error
    return AskResponse(
        answer=result.answer,
        covered=result.covered,
        citations=[
            Citation(
                document_id=citation.chunk.document_id,
                filename=citation.chunk.filename,
                chunk_id=citation.chunk.chunk_id,
                page_start=citation.chunk.page_start,
                page_end=citation.chunk.page_end,
                excerpt=citation.excerpt,
            )
            for citation in result.citations
        ],
    )
