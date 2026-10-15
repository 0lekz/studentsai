import re
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
    summarize_content,
)
from app.auth import (
    get_current_user_id,
)
from app.db.session import get_db
from app.dependencies import optional_owned_course_id
from app.models.note import Note
from app.rate_limiter import check_ai_rate_limit, check_rate_limit
from app.repositories.notes import (
    count_notes_by_user,
    create_note,
    create_note_link,
    delete_note,
    delete_note_link,
    get_backlinks,
    get_note_by_id,
    get_notes_by_titles,
    get_notes_by_user,
    replace_manual_links_for_note,
    set_note_tags,
    update_note,
)
from app.schemas import (
    BacklinkResponse,
    NoteCreate,
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
    SuccessResponse,
    SummarizeRequest,
    SummarizeResponse,
    UpdateTagsRequest,
)
from app.services.courses import get_course
from app.services.embedding_service import (
    refresh_note_embedding,
)

router = APIRouter()


def _note_response(note: Note) -> NoteResponse:
    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        summary=note.summary,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=note.tags or [],
        course_id=note.course_id,
    )


@router.get("/notes", response_model=NoteListResponse)
async def get_notes(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    user_id: uuid.UUID = Depends(get_current_user_id),
    course_id: uuid.UUID | None = Depends(optional_owned_course_id),
    db: Session = Depends(get_db),
):
    """Get user's notes, optionally only those of one course"""
    try:
        await check_rate_limit(request, str(user_id))

        notes = get_notes_by_user(db, user_id, skip, limit, course_id=course_id)

        return NoteListResponse(
            notes=[_note_response(note) for note in notes],
            total=count_notes_by_user(db, user_id, course_id=course_id),
            page=skip // limit + 1,
            per_page=limit,
        )
    except Exception as e:
        print(f"Error in get_notes endpoint: {e!s}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {e!s}",
        ) from e


@router.post("/notes", response_model=NoteResponse)
async def create_new_note(
    note_data: NoteCreate,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Create a new note"""
    await check_rate_limit(request, str(user_id))

    if note_data.course_id is not None and not get_course(
        db, user_id, note_data.course_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )

    note = create_note(
        db, note_data.title, note_data.content, user_id, note_data.course_id
    )
    await refresh_note_embedding(db, note)

    return _note_response(note)


@router.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get a specific note"""
    await check_rate_limit(request, str(user_id))

    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    return _note_response(note)


@router.put("/notes/{note_id}", response_model=NoteResponse)
async def update_existing_note(
    note_id: uuid.UUID,
    note_data: NoteUpdate,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update a note"""
    await check_rate_limit(request, str(user_id))

    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    updated_note = update_note(
        db,
        note,
        title=note_data.title,
        content=note_data.content,
        summary=note_data.summary,
    )

    await refresh_note_embedding(db, updated_note)

    # Parse manual wiki-links [[Title]] and update note_links
    try:
        content_to_parse = updated_note.content or ""
        titles = re.findall(r"\[\[([^\]]+)\]\]", content_to_parse)
        titles = [t.strip() for t in titles if t.strip()]
        targets = get_notes_by_titles(db, user_id, titles)
        replace_manual_links_for_note(
            db, user_id, updated_note.id, [n.id for n in targets]
        )
    except Exception:
        pass

    return _note_response(updated_note)


@router.put("/notes/{note_id}/tags", response_model=NoteResponse)
async def update_note_tags(
    note_id: uuid.UUID,
    request_data: UpdateTagsRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    updated = set_note_tags(db, note, request_data.tags)

    return _note_response(updated)


@router.post("/notes/{note_id}/links", response_model=SuccessResponse)
async def create_manual_link(
    note_id: uuid.UUID,
    target_note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    # Ensure both notes belong to user
    source = get_note_by_id(db, note_id, user_id)
    target = get_note_by_id(db, target_note_id, user_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Note not found")
    create_note_link(
        db, from_note_id=note_id, to_note_id=target_note_id, link_type="manual"
    )
    return SuccessResponse(message="Link created")


@router.delete(
    "/notes/{note_id}/links/{target_note_id}", response_model=SuccessResponse
)
async def delete_manual_link(
    note_id: uuid.UUID,
    target_note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    # Ensure both notes belong to user
    source = get_note_by_id(db, note_id, user_id)
    target = get_note_by_id(db, target_note_id, user_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Note not found")
    delete_note_link(db, from_note_id=note_id, to_note_id=target_note_id)
    return SuccessResponse(message="Link deleted")


@router.get("/notes/{note_id}/backlinks", response_model=list[BacklinkResponse])
async def fetch_backlinks(
    note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    # Verify note exists
    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    linked_notes = get_backlinks(db, note_id)
    return [
        BacklinkResponse(
            note_id=n.id,
            title=n.title,
            excerpt=(n.content[:120] + "...") if len(n.content) > 120 else n.content,
            created_at=n.created_at,
        )
        for n in linked_notes
    ]


@router.delete("/notes/{note_id}")
async def delete_existing_note(
    note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Delete a note"""
    await check_rate_limit(request, str(user_id))

    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    delete_note(db, note)

    return SuccessResponse(message="Note deleted successfully")


@router.post("/ai/summarize", response_model=SummarizeResponse)
async def summarize_text(
    request_data: SummarizeRequest,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Generate summary of text content"""
    await check_ai_rate_limit(request, str(user_id))

    try:
        summary = await summarize_content(request_data.content)

        return SummarizeResponse(
            summary=summary,
            word_count=len(summary.split()),
            original_length=len(request_data.content),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {e!s}",
        ) from e


@router.post("/notes/{note_id}/summarize", response_model=NoteResponse)
async def summarize_note(
    note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Generate summary for a specific note"""
    await check_ai_rate_limit(request, str(user_id))

    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    try:
        summary = await summarize_content(note.content)
        updated_note = update_note(db, note, summary=summary)

        return _note_response(updated_note)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {e!s}",
        ) from e
