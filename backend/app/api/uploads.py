import os
import shutil
import uuid
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)

from app.auth import (
    get_current_user_id,
)
from app.rate_limiter import check_rate_limit

router = APIRouter()


UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
)


@router.post("/upload/image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    await check_rate_limit(request, str(user_id))
    try:
        # Basic validation
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400, detail="Only image uploads are allowed"
            )

        ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
        safe_ext = ext if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"] else ".png"
        ts = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        filename = f"{user_id}-{ts}{safe_ext}"
        dest_path = os.path.join(UPLOAD_DIR, filename)
        with open(dest_path, "wb") as out:
            shutil.copyfileobj(file.file, out)
        url_path = f"/uploads/{filename}"
        absolute_url = str(request.base_url).rstrip("/") + url_path
        return {
            "url": absolute_url,
            "filename": filename,
            "content_type": file.content_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e!s}") from e
