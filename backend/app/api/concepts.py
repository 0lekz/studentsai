import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.courses import owned_course
from app.db.session import get_db
from app.dependencies import enforce_rate_limit
from app.models.concept import Concept
from app.models.course import Course
from app.repositories.concepts import get_course_concept
from app.schemas.concepts import ConceptMapResponse, ConceptResponse, ConceptUpdate
from app.services.concepts import (
    ConceptNameTakenError,
    NoReadyDocumentsError,
    concept_map,
    delete_concept,
    describe_concept,
    extract_course_concepts,
    list_concepts,
    update_concept,
)
from app.services.llm import LLMUnavailableError


def owned_concept(
    concept_id: uuid.UUID,
    course: Course = Depends(owned_course),
    db: Session = Depends(get_db),
) -> Concept:
    concept = get_course_concept(db, course.id, concept_id)
    if concept is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Concept not found")
    return concept


router = APIRouter(
    prefix="/courses/{course_id}",
    tags=["concepts"],
    dependencies=[Depends(enforce_rate_limit)],
)


@router.get("/concepts", response_model=list[ConceptResponse])
def get_concepts(
    course: Course = Depends(owned_course), db: Session = Depends(get_db)
) -> list[ConceptResponse]:
    """The course's concepts in order of first appearance."""
    return list_concepts(db, course)


@router.post("/concepts/extract", response_model=list[ConceptResponse])
async def extract_concepts(
    course: Course = Depends(owned_course), db: Session = Depends(get_db)
) -> list[ConceptResponse]:
    """Extracts concepts from the course's ready documents not extracted yet, then lists all of them."""
    try:
        await extract_course_concepts(db, course)
    except NoReadyDocumentsError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="The course has no ready documents to extract concepts from.",
        ) from None
    except LLMUnavailableError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The language model is unavailable; try again shortly.",
        ) from None
    return list_concepts(db, course)


@router.get("/map", response_model=ConceptMapResponse)
def get_concept_map(
    course: Course = Depends(owned_course), db: Session = Depends(get_db)
) -> ConceptMapResponse:
    return concept_map(db, course)


@router.patch("/concepts/{concept_id}", response_model=ConceptResponse)
def edit_concept(
    payload: ConceptUpdate,
    course: Course = Depends(owned_course),
    concept: Concept = Depends(owned_concept),
    db: Session = Depends(get_db),
) -> ConceptResponse:
    try:
        update_concept(db, concept, payload.model_dump(exclude_unset=True))
    except ConceptNameTakenError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Another concept in this course already has that name.",
        ) from None
    return describe_concept(db, course, concept)


@router.delete("/concepts/{concept_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_concept(
    concept: Concept = Depends(owned_concept), db: Session = Depends(get_db)
) -> None:
    delete_concept(db, concept)
