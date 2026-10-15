import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.ai_service import (
    generate_flashcards_from_content,
)
from app.auth import (
    get_current_user_id,
    get_verified_user_id,
)
from app.db.session import get_db
from app.dependencies import optional_owned_course_id
from app.models.flashcard import Flashcard
from app.rate_limiter import check_ai_rate_limit, check_rate_limit
from app.repositories.flashcards import (
    add_flashcard_tag,
    archive_mastered_flashcards,
    create_flashcard,
    create_flashcard_set,
    get_due_flashcards_srs,
    get_flashcard_sets_by_user,
    get_flashcards_by_note,
    get_user_flashcard,
    get_user_flashcards,
    remove_flashcard_tag,
)
from app.repositories.notes import (
    get_note_by_id,
)
from app.schemas import (
    FlashcardGenerationRequest,
    FlashcardGenerationResponse,
    FlashcardResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    FlashcardSetInfo,
    GenerateFlashcardsRequest,
    GenerateFlashcardsResponse,
)
from app.services.scheduling import apply_flashcard_review

router = APIRouter()


def _flashcard_response(flashcard: Flashcard) -> FlashcardResponse:
    return FlashcardResponse(
        id=flashcard.id,
        question=flashcard.question,
        answer=flashcard.answer,
        difficulty=flashcard.difficulty,
        last_reviewed=flashcard.last_reviewed,
        created_at=flashcard.created_at,
        tags=flashcard.tags or [],
        review_count=flashcard.review_count,
        course_id=flashcard.course_id,
        kind=flashcard.kind,
        choices=flashcard.choices,
        source=flashcard.source,
    )


@router.post("/ai/flashcards", response_model=GenerateFlashcardsResponse)
async def generate_flashcards(
    request_data: GenerateFlashcardsRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Generate flashcards from content"""
    await check_ai_rate_limit(request, str(user_id))

    try:
        flashcards = await generate_flashcards_from_content(
            request_data.content, request_data.count
        )

        return GenerateFlashcardsResponse(flashcards=flashcards, count=len(flashcards))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {e!s}",
        ) from e


@router.get("/notes/{note_id}/flashcards", response_model=list[FlashcardResponse])
async def get_note_flashcards(
    note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get flashcards for a note"""
    await check_rate_limit(request, str(user_id))

    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    flashcards = get_flashcards_by_note(db, note_id)

    return [_flashcard_response(flashcard) for flashcard in flashcards]


@router.post(
    "/notes/{note_id}/flashcards/generate", response_model=list[FlashcardResponse]
)
async def generate_note_flashcards(
    note_id: uuid.UUID,
    count: int = 5,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Generate and save flashcards for a note"""
    await check_ai_rate_limit(request, str(user_id))

    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    try:
        generated_flashcards = await generate_flashcards_from_content(
            note.content, count
        )

        saved_flashcards = [
            _flashcard_response(
                create_flashcard(
                    db,
                    flashcard_data.question,
                    flashcard_data.answer,
                    note_id,
                    user_id,
                    note.course_id,
                )
            )
            for flashcard_data in generated_flashcards
        ]

        return saved_flashcards

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {e!s}",
        ) from e


@router.get("/flashcards/user", response_model=list[FlashcardResponse])
async def get_user_flashcards_endpoint(
    tags: str | None = None,
    search: str | None = None,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    course_id: uuid.UUID | None = Depends(optional_owned_course_id),
    db: Session = Depends(get_db),
):
    """Get all flashcards for a user, optionally filtered by course, tags and search query"""
    await check_rate_limit(request, str(user_id))

    tag_list = tags.split(",") if tags else None
    flashcards = get_user_flashcards(db, user_id, tag_list, search, course_id)

    return [_flashcard_response(flashcard) for flashcard in flashcards]


@router.post(
    "/flashcards/{flashcard_id}/review", response_model=FlashcardReviewResponse
)
async def review_flashcard(
    flashcard_id: uuid.UUID,
    review_data: FlashcardReviewRequest,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Reschedule a card with SM-2 from the student's own 0-5 rating"""
    await check_rate_limit(request, str(user_id))

    flashcard = get_user_flashcard(db, flashcard_id, user_id)
    if not flashcard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found"
        )

    srs_entry = apply_flashcard_review(db, flashcard, review_data.quality_rating)

    return FlashcardReviewResponse(
        flashcard_id=flashcard.id,
        quality_rating=review_data.quality_rating,
        repetitions=srs_entry.repetitions,
        interval_days=srs_entry.interval_days,
        efactor=srs_entry.efactor / 100.0,
        due_date=srs_entry.due_date,
    )


@router.post("/flashcards/{flashcard_id}/tags/{tag}")
async def add_flashcard_tag_endpoint(
    flashcard_id: uuid.UUID,
    tag: str,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Add a tag to a flashcard"""
    await check_rate_limit(request, str(user_id))

    try:
        flashcard = add_flashcard_tag(db, flashcard_id, user_id, tag)
        return {"message": f"Tag '{tag}' added successfully", "tags": flashcard.tags}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.delete("/flashcards/{flashcard_id}/tags/{tag}")
async def remove_flashcard_tag_endpoint(
    flashcard_id: uuid.UUID,
    tag: str,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Remove a tag from a flashcard"""
    await check_rate_limit(request, str(user_id))

    try:
        flashcard = remove_flashcard_tag(db, flashcard_id, user_id, tag)
        return {"message": f"Tag '{tag}' removed successfully", "tags": flashcard.tags}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/flashcards/generate", response_model=FlashcardGenerationResponse)
async def generate_flashcards_enhanced(
    request_data: FlashcardGenerationRequest,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_verified_user_id),
    db: Session = Depends(get_db),
):
    """Generate a set of flashcards from one note"""
    await check_ai_rate_limit(request, str(user_id))

    note = get_note_by_id(db, request_data.note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    try:
        generated_flashcards = await generate_flashcards_from_content(
            note.content, request_data.count or 5
        )

        flashcard_set = create_flashcard_set(db, user_id, note.id)

        saved_flashcards = [
            _flashcard_response(
                create_flashcard(
                    db,
                    flashcard_data.question,
                    flashcard_data.answer,
                    note.id,
                    user_id,
                    note.course_id,
                )
            )
            for flashcard_data in generated_flashcards
        ]

        return FlashcardGenerationResponse(
            flashcard_set_id=flashcard_set.id, cards=saved_flashcards
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {e!s}",
        ) from e


@router.get("/flashcards/sets", response_model=list[FlashcardSetInfo])
async def get_flashcard_sets(
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get all flashcard sets for a user"""
    await check_rate_limit(request, str(user_id))

    sets = get_flashcard_sets_by_user(db, user_id)

    # Add flashcard count to each set
    set_infos = []
    for set_item in sets:
        flashcard_count = (
            db.query(Flashcard)
            .filter(
                Flashcard.note_id == set_item.seed_note_id, Flashcard.user_id == user_id
            )
            .count()
        )

        set_infos.append(
            FlashcardSetInfo(
                id=set_item.id,
                seed_note_id=set_item.seed_note_id,
                created_at=set_item.created_at,
                flashcard_count=flashcard_count,
            )
        )

    return set_infos


@router.get("/flashcards/due/srs", response_model=list[FlashcardResponse])
async def get_due_flashcards_srs_endpoint(
    limit: int = 20,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get flashcards due for review using SRS algorithm"""
    await check_rate_limit(request, str(user_id))

    flashcards = get_due_flashcards_srs(db, user_id, limit)

    return [_flashcard_response(flashcard) for flashcard in flashcards]


@router.post("/flashcards/archive/mastered")
async def archive_mastered_flashcards_endpoint(
    min_repetitions: int = 3,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Find and tag mastered flashcards for archiving"""
    await check_rate_limit(request, str(user_id))

    try:
        mastered_flashcards = archive_mastered_flashcards(db, user_id, min_repetitions)

        return {
            "message": f"Found {len(mastered_flashcards)} mastered flashcards",
            "flashcards": [
                {
                    "id": str(f.id),
                    "question": f.question[:100] + "..."
                    if len(f.question) > 100
                    else f.question,
                    "tags": f.tags or [],
                }
                for f in mastered_flashcards
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive mastered flashcards: {e!s}",
        ) from e
