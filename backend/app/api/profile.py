import uuid

from fastapi import (
    APIRouter,
    Depends,
    Request,
)
from sqlalchemy.orm import Session

from app.auth import (
    get_current_user_id,
)
from app.db.session import get_db
from app.rate_limiter import check_rate_limit
from app.repositories.flashcards import (
    get_flashcards_by_note,
)
from app.repositories.notes import (
    get_notes_by_user,
)

router = APIRouter()


@router.post("/api/profile/export")
async def profile_export(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    # Collect user notes and flashcards
    notes = get_notes_by_user(db, user_id)
    out = {
        "notes": [
            {
                "id": str(n.id),
                "title": n.title,
                "content": n.content,
                "summary": n.summary,
                "tags": n.tags,
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            }
            for n in notes
        ],
        "flashcards": [],
    }
    for n in notes:
        fcs = get_flashcards_by_note(db, n.id)
        for f in fcs:
            out["flashcards"].append(
                {
                    "id": str(f.id),
                    "note_id": str(n.id),
                    "question": f.question,
                    "answer": f.answer,
                    "difficulty": f.difficulty,
                    "last_reviewed": f.last_reviewed.isoformat()
                    if f.last_reviewed
                    else None,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
            )

    return out
