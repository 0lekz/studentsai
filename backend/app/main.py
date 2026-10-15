"""
StudentsAI MVP - FastAPI Backend Application
"""

import asyncio
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta
from urllib.parse import urlparse

import jwt
from fastapi import (
    Body,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from .ai_service import (
    calculate_note_similarities,
    generate_flashcards_from_content,
    summarize_content,
)
from .api import courses, documents
from .auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_user_id,
    get_password_hash,
    get_verified_user_id,
    register_user,
    verify_password,
)
from .config import (
    ALLOWED_ORIGINS,
    DEBUG,
    GOOGLE_CLIENT_ID,
    GOOGLE_REDIRECT_URI,
    HOST,
    PORT,
    settings,
)
from .database import (
    Flashcard,
    Note,
    User,
    add_flashcard_tag,
    apply_flashcard_review,
    archive_mastered_flashcards,
    count_notes_by_user,
    create_flashcard,
    create_flashcard_set,
    create_note,
    create_note_link,
    create_tables,
    delete_note,
    delete_note_link,
    get_backlinks,
    get_db,
    get_due_flashcards_srs,
    get_flashcard_sets_by_user,
    get_flashcards_by_note,
    get_links_for_user_notes,
    get_note_by_id,
    get_notes_by_titles,
    get_notes_by_user,
    get_similarities_for_notes,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_flashcard,
    get_user_flashcards,
    remove_flashcard_tag,
    replace_manual_links_for_note,
    set_note_tags,
    update_note,
    update_user_profile,
)
from .dependencies import get_document_storage, optional_owned_course_id
from .email_service import (
    create_email_change_token,
    create_password_reset_token,
    create_verification_token,
    send_account_deletion_email,
    send_email_change_verification,
    send_password_reset_email,
    send_verification_email,
    verify_email_change_token,
    verify_password_reset_token,
    verify_verification_token,
)
from .oauth_service import GoogleOAuthService
from .rate_limiter import check_ai_rate_limit, check_auth_rate_limit, check_rate_limit
from .schemas import (
    BacklinkResponse,
    EmailChangeRequest,
    # Email verification schemas
    EmailVerificationRequest,
    EmailVerificationResponse,
    FlashcardGenerationRequest,
    FlashcardGenerationResponse,
    FlashcardResponse,
    FlashcardReviewRequest,
    FlashcardReviewResponse,
    FlashcardSetInfo,
    ForgotPasswordRequest,
    GenerateFlashcardsRequest,
    GenerateFlashcardsResponse,
    GoogleOAuthRequest,
    GoogleOAuthResponse,
    GraphNode,
    GraphResponse,
    NoteConnection,
    NoteCreate,
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
    ResetPasswordRequest,
    SettingsAdvanced,
    SettingsAI,
    SettingsAppearance,
    SettingsGraph,
    SettingsStudyFlow,
    SuccessResponse,
    SummarizeRequest,
    SummarizeResponse,
    Token,
    UpdateTagsRequest,
    UserCreate,
    UserLogin,
    UsernameCheck,
    UserProfileUpdate,
    UserResponse,
    VerificationResponse,
    VerifyEmailToken,
)
from .services.courses import get_course
from .services.embedding_service import (
    find_embedding_connections,
    refresh_note_embedding,
)

# Create FastAPI app
app = FastAPI(
    title="StudentsAI MVP API",
    description="AI-powered study assistant API",
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
)


# Add CORS middleware
# Build robust CORS origins from env (supports both list and comma-separated string,
# and automatically includes www/non-www variants of FRONTEND_URL)
def _origin_variants(url: str) -> list[str]:
    try:
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return []
        base = f"{p.scheme}://{p.netloc}"
        hosts = {base}
        host = p.netloc
        if host.startswith("www."):
            hosts.add(f"{p.scheme}://{host[4:]}")
        else:
            hosts.add(f"{p.scheme}://www.{host}")
        return list(hosts)
    except Exception:
        return []


origins_set = set()

# From list env (BACKEND_CORS_ORIGINS)
for o in ALLOWED_ORIGINS:
    o = o.strip()
    if o:
        origins_set.add(o)

# From comma-separated env (allowed_origins)
for o in (settings.allowed_origins or "").split(","):
    o = o.strip()
    if o:
        origins_set.add(o)

# From FRONTEND_URL with www/non-www variants
for v in _origin_variants(settings.frontend_url):
    origins_set.add(v)

allowed_origins = list(origins_set)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://([a-zA-Z0-9-]+\.)?(studentsai\.org|vercel\.app)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extra safety: ensure CORS headers are present on all responses when Origin matches
_cors_regex = re.compile(r"https://([a-zA-Z0-9-]+\.)?(studentsai\.org|vercel\.app)$")


@app.middleware("http")
async def ensure_cors_headers(request: Request, call_next):
    response = await call_next(request)
    origin = request.headers.get("origin")
    if origin and (origin in allowed_origins or _cors_regex.match(origin)):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# Serve uploaded files (development convenience)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(courses.router)
app.include_router(documents.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "StudentsAI MVP API"}


_background_tasks: set[asyncio.Task] = set()


def _run_in_background(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


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
    )


# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if DEBUG else None,
        },
    )


# (removed duplicate /health handler)


# Authentication endpoints
@app.post("/auth/register", response_model=Token)
async def register(
    user_data: UserCreate, request: Request, db: Session = Depends(get_db)
):
    """Register a new user"""
    await check_auth_rate_limit(request)

    try:
        user = register_user(db, user_data)

        # Send verification email asynchronously (don't block registration)
        async def send_email_background():
            try:
                verification_token = create_verification_token(user.email)
                verification_url = (
                    f"{settings.frontend_url}/verify/{verification_token}"
                )
                await send_verification_email(
                    user.email, user.username, verification_url
                )
            except Exception as e:
                # Log the error but don't fail registration
                if DEBUG:
                    print(f"Failed to send verification email: {e}")

        _run_in_background(send_email_background())

        access_token = create_access_token(data={"sub": user.email})

        return Token(
            access_token=access_token,
            user={
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "verified": user.verified,
                "has_password": bool(user.password_hash),
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        ) from e


@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login user"""
    await check_auth_rate_limit(request)

    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user has verified their email
    if not user.verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in. Check your inbox for the verification link.",
        )

    access_token = create_access_token(data={"sub": user.email})

    return Token(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "verified": user.verified,
            "has_password": bool(user.password_hash),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        },
    )


@app.post("/auth/refresh", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Refresh access token"""
    # Create a new access token for the current user
    access_token = create_access_token(data={"sub": current_user.email})

    return Token(
        access_token=access_token,
        user={
            "id": current_user.id,
            "email": current_user.email,
            "username": current_user.username,
            "verified": current_user.verified,
            "has_password": bool(current_user.password_hash),
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
        },
    )


@app.get("/auth/google/login")
async def google_oauth_login():
    """Initiate Google OAuth login - redirects to Google consent screen"""
    from urllib.parse import urlencode

    # Build Google OAuth URL
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }

    google_oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    )

    # Redirect to Google OAuth consent screen
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=google_oauth_url)


@app.get("/auth/google/callback")
async def google_oauth_callback(code: str, db: Session = Depends(get_db)):
    """Handle Google OAuth callback - redirects to frontend with token"""
    try:
        # Process the OAuth code

        result = GoogleOAuthService.authenticate_user(db, code)

        # Redirect to frontend with the token and user data
        user = result["user"]
        frontend_url = f"{settings.frontend_url}/auth/google/callback?token={result['access_token']}&user_id={user['id']}&email={user['email']}&username={user['username']}&verified={user['verified']}"

        from fastapi.responses import RedirectResponse

        return RedirectResponse(url=frontend_url)

    except Exception as e:
        import logging
        import traceback

        logging.error(f"Google OAuth error: {e!s}\n{traceback.format_exc()}")

        # Redirect to frontend with error
        error_url = f"{settings.frontend_url}/auth/google/callback?error=oauth_failed&message={e!s}"
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url=error_url)


@app.post("/auth/google", response_model=GoogleOAuthResponse)
async def google_oauth(
    request: GoogleOAuthRequest, request_obj: Request, db: Session = Depends(get_db)
):
    """Google OAuth authentication"""
    await check_auth_rate_limit(request_obj)

    try:
        result = GoogleOAuthService.authenticate_user(db, request.code)
        return GoogleOAuthResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth authentication failed: {e!s}",
        ) from e


# Email verification endpoints
@app.post("/auth/send-verification", response_model=EmailVerificationResponse)
async def send_verification_email_endpoint(
    request: EmailVerificationRequest, db: Session = Depends(get_db)
):
    """Send verification email to user"""
    try:
        # Check if user exists
        user = get_user_by_email(db, request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if user.verified:
            return EmailVerificationResponse(
                message="Email already verified", email=request.email
            )

        # Generate verification token
        verification_token = create_verification_token(request.email)
        verification_url = f"{settings.frontend_url}/verify/{verification_token}"

        # Send verification email
        await send_verification_email(request.email, user.username, verification_url)

        return EmailVerificationResponse(
            message="Verification email sent successfully", email=request.email
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        ) from e


@app.post("/auth/send-email-change-verification", response_model=SuccessResponse)
async def send_email_change_verification_endpoint(
    payload: EmailChangeRequest,
    request: Request,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Email a confirmation link to the new address; the address changes when it is followed"""
    await check_rate_limit(request, str(current_user_id))

    current_user = get_user_by_id(db, current_user_id)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if payload.new_email == current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is already your email address",
        )

    if get_user_by_email(db, payload.new_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already in use by another account",
        )

    token = create_email_change_token(
        current_user.id, current_user.email, payload.new_email
    )
    verification_url = f"{settings.frontend_url}/verify-email-change/{token}"
    try:
        await send_email_change_verification(payload.new_email, verification_url)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        ) from e

    return SuccessResponse(message="Verification email sent to your new email address")


@app.post("/auth/verify-email-change", response_model=VerificationResponse)
async def verify_email_change(payload: VerifyEmailToken, db: Session = Depends(get_db)):
    """Switch the account to the new address the token was sent to"""
    invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification token",
    )
    claims = verify_email_change_token(payload.token)
    if not claims:
        raise invalid_token
    try:
        user_id = uuid.UUID(claims["user_id"])
        new_email = claims["sub"]
    except (KeyError, TypeError, ValueError):
        raise invalid_token from None

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user.email == new_email:
        return VerificationResponse(
            message="Email address already updated", verified=True
        )

    # A link sent before an earlier change went through is stale
    if user.email != claims.get("current_email"):
        raise invalid_token

    if get_user_by_email(db, new_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already in use by another account",
        )

    user.email = new_email
    user.verified = True
    db.commit()

    return VerificationResponse(
        message="Email address updated successfully",
        verified=True,
        access_token=create_access_token(data={"sub": new_email}),
    )


@app.get("/auth/verify/{token}", response_model=VerificationResponse)
async def verify_email_get_endpoint(token: str, db: Session = Depends(get_db)):
    """Verify user email with token (GET endpoint for browser links)"""
    try:
        # Verify token and get email
        email = verify_verification_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # Get user and update verification status
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if user.verified:
            return VerificationResponse(message="Email already verified", verified=True)

        # Update user verification status
        user.verified = True
        db.commit()

        return VerificationResponse(
            message="Email verified successfully", verified=True
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        ) from e


@app.post("/auth/verify-email", response_model=VerificationResponse)
async def verify_email_endpoint(
    request: VerifyEmailToken, db: Session = Depends(get_db)
):
    """Verify user email with token"""
    try:
        # Verify token and get email
        email = verify_verification_token(request.token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # Get user and update verification status
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        if user.verified:
            return VerificationResponse(message="Email already verified", verified=True)

        # Update user verification status
        user.verified = True
        db.commit()

        return VerificationResponse(
            message="Email verified successfully", verified=True
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify email",
        ) from e


# Note endpoints
@app.get("/notes", response_model=NoteListResponse)
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


@app.post("/notes", response_model=NoteResponse)
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


@app.get("/notes/{note_id}", response_model=NoteResponse)
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


@app.put("/notes/{note_id}", response_model=NoteResponse)
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


@app.put("/notes/{note_id}/tags", response_model=NoteResponse)
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


@app.post("/notes/{note_id}/links", response_model=SuccessResponse)
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


@app.delete("/notes/{note_id}/links/{target_note_id}", response_model=SuccessResponse)
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


@app.get("/notes/{note_id}/backlinks", response_model=list[BacklinkResponse])
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


@app.delete("/notes/{note_id}")
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


# AI endpoints
@app.post("/ai/summarize", response_model=SummarizeResponse)
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


@app.post("/ai/flashcards", response_model=GenerateFlashcardsResponse)
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


@app.post("/notes/{note_id}/summarize", response_model=NoteResponse)
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


# Flashcard endpoints
@app.get("/notes/{note_id}/flashcards", response_model=list[FlashcardResponse])
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


@app.post(
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


# Enhanced flashcard endpoints
@app.get("/flashcards/user", response_model=list[FlashcardResponse])
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


@app.post("/flashcards/{flashcard_id}/review", response_model=FlashcardReviewResponse)
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


@app.post("/flashcards/{flashcard_id}/tags/{tag}")
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


@app.delete("/flashcards/{flashcard_id}/tags/{tag}")
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


# Enhanced flashcard system endpoints
@app.post("/flashcards/generate", response_model=FlashcardGenerationResponse)
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


@app.get("/flashcards/sets", response_model=list[FlashcardSetInfo])
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


@app.get("/flashcards/due/srs", response_model=list[FlashcardResponse])
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


@app.post("/flashcards/archive/mastered")
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


# Graph endpoints
@app.get("/graph", response_model=GraphResponse)
async def get_notes_graph(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    course_id: uuid.UUID | None = Depends(optional_owned_course_id),
    db: Session = Depends(get_db),
):
    """Get graph visualization of all of a user's notes, optionally one course's"""
    await check_rate_limit(request, str(user_id))

    notes = get_notes_by_user(db, user_id, course_id=course_id)

    if len(notes) < 2:
        return GraphResponse(
            nodes=[
                GraphNode(
                    id=note.id,
                    title=note.title,
                    content_preview=note.content[:200] + "..."
                    if len(note.content) > 200
                    else note.content,
                    created_at=note.created_at,
                    word_count=len(note.content.split()),
                )
                for note in notes
            ],
            connections=[],
            total_nodes=len(notes),
        )

    # Prepare notes data for similarity calculation
    notes_data = [
        {"id": note.id, "title": note.title, "content": note.content} for note in notes
    ]
    note_ids = [note.id for note in notes]
    in_graph = set(note_ids)

    # Calculate connections
    if settings.similarity_backend == "embeddings":
        connections = find_embedding_connections(db, note_ids)
    else:
        connections = calculate_note_similarities(notes_data)

    # Create graph nodes
    nodes = [
        GraphNode(
            id=note.id,
            title=note.title,
            content_preview=note.content[:200] + "..."
            if len(note.content) > 200
            else note.content,
            created_at=note.created_at,
            word_count=len(note.content.split()),
        )
        for note in notes
    ]

    # Create graph connections
    graph_connections = [
        NoteConnection(
            source_id=conn["source_id"],
            target_id=conn["target_id"],
            similarity=conn["similarity"],
            connection_type=conn["connection_type"],
        )
        for conn in connections
    ]

    # Merge manual links that stay inside the graph
    links = get_links_for_user_notes(db, note_ids)
    for link_row in links:
        if link_row.to_note_id not in in_graph:
            continue
        graph_connections.append(
            NoteConnection(
                source_id=link_row.from_note_id,
                target_id=link_row.to_note_id,
                similarity=1.0,
                connection_type="manual",
            )
        )

    # Merge stored similarities (authoritative values for edge thickness)
    sims = get_similarities_for_notes(db, note_ids)
    for s in sims:
        if s.note_a_id not in in_graph or s.note_b_id not in in_graph:
            continue
        graph_connections.append(
            NoteConnection(
                source_id=s.note_a_id,
                target_id=s.note_b_id,
                similarity=float(s.similarity) / 1000.0,
                connection_type="similarity",
            )
        )

    return GraphResponse(
        nodes=nodes, connections=graph_connections, total_nodes=len(notes)
    )


# Profile endpoints
@app.post("/api/profile/export")
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


# Image upload endpoint for pasted images (separate from static mount)
@app.post("/upload/image")
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


# Settings endpoints
@app.get("/api/settings/profile", response_model=UserResponse)
async def get_profile_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get current user profile information"""
    await check_rate_limit(request, str(user_id))
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        verified=user.verified,
        has_password=bool(user.password_hash),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@app.patch("/api/settings/profile", response_model=UserResponse)
async def update_profile_settings(
    request: Request,
    profile_update: UserProfileUpdate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Update user profile settings"""
    await check_rate_limit(request, str(user_id))

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if username is being changed and if it's available
    if profile_update.username and profile_update.username != user.username:
        existing_user = get_user_by_username(db, profile_update.username)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Username already taken")

    # Update password if provided
    if profile_update.new_password:
        # If user has no password yet (OAuth-only), allow setting it without current_password
        if user.password_hash is None:
            hashed = get_password_hash(profile_update.new_password)
        else:
            if not profile_update.current_password:
                raise HTTPException(
                    status_code=400,
                    detail="Current password required to change password",
                )

            # Verify current password
            if not verify_password(profile_update.current_password, user.password_hash):
                raise HTTPException(
                    status_code=400, detail="Current password is incorrect"
                )

            # Hash new password
            hashed = get_password_hash(profile_update.new_password)

    # Prepare update data
    update_data = {}
    if profile_update.username:
        update_data["username"] = profile_update.username
    if profile_update.new_password:
        update_data["password_hash"] = hashed

    # Update user
    updated_user = update_user_profile(db, user_id, **update_data)
    if not updated_user:
        raise HTTPException(status_code=500, detail="Failed to update profile")

    # Ensure has_password is included in response
    response = UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        username=updated_user.username,
        verified=updated_user.verified,
        has_password=bool(updated_user.password_hash),
        created_at=updated_user.created_at,
        updated_at=updated_user.updated_at,
    )

    return response


@app.post("/auth/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    """Send password reset email (does not reveal if email exists)."""
    # Always return success to prevent user enumeration
    user = get_user_by_email(db, payload.email)
    if user:
        try:
            token = create_password_reset_token(user.email)
            reset_url = f"{settings.frontend_url}/verify/{token}?type=password_reset"
            await send_password_reset_email(user.email, reset_url)
        except Exception:
            # Do not leak errors
            pass
    return {"message": "If that email exists, a reset link has been sent."}


@app.post("/auth/request-account-deletion", response_model=SuccessResponse)
async def request_account_deletion(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Initiate account deletion via email confirmation."""
    await check_rate_limit(request, str(user_id))
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Reuse verification token machinery with a dedicated type
    token_data = {
        "sub": user.email,
        "user_id": str(user.id),
        "type": "account_delete",
        "exp": datetime.utcnow()
        + timedelta(minutes=settings.verification_token_expire_minutes),
    }
    token = jwt.encode(token_data, settings.secret_key, algorithm=settings.algorithm)
    confirm_url = f"{settings.frontend_url}/verify/{token}?type=account_delete"

    try:
        await send_account_deletion_email(user.email, confirm_url)
        return SuccessResponse(
            message="Account deletion confirmation email sent successfully."
        )
    except Exception as e:
        # Log the error for debugging but don't leak details to user
        if DEBUG:
            print(f"Failed to send account deletion email to {user.email}: {e!s}")

        # Still return success to prevent email enumeration, but log the issue
        return SuccessResponse(
            message="If your email is valid, a confirmation link was sent."
        )


@app.post("/auth/confirm-account-deletion", response_model=SuccessResponse)
async def confirm_account_deletion(
    payload: dict = Body(...), db: Session = Depends(get_db)
):
    """Confirm account deletion via token and delete user data."""
    try:
        token = payload.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Missing token")
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Token expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid token") from None

    if payload.get("type") != "account_delete":
        raise HTTPException(status_code=400, detail="Invalid token type")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid token payload")

    user_uuid = uuid.UUID(user_id)
    user = get_user_by_id(db, user_uuid)
    if not user:
        # Already gone; a retry still removes files an interrupted deletion left behind
        get_document_storage().delete_user_files(user_uuid)
        return SuccessResponse(message="Account deleted")

    # Delete user-related data (DB-level, handle FKs manually to avoid violations)
    uid = str(user.id)
    try:
        # Delete SRS data first (depends on flashcards/users)
        db.execute(
            sql_text("DELETE FROM flashcard_srs WHERE user_id = :uid"), {"uid": uid}
        )
        db.execute(
            sql_text("DELETE FROM flashcard_sets WHERE user_id = :uid"), {"uid": uid}
        )

        # Delete note relations that reference user's notes
        db.execute(
            sql_text(
                "DELETE FROM note_similarities WHERE note_a_id IN (SELECT id FROM notes WHERE user_id = :uid) OR note_b_id IN (SELECT id FROM notes WHERE user_id = :uid)"
            ),
            {"uid": uid},
        )
        db.execute(
            sql_text(
                "DELETE FROM note_links WHERE from_note_id IN (SELECT id FROM notes WHERE user_id = :uid) OR to_note_id IN (SELECT id FROM notes WHERE user_id = :uid)"
            ),
            {"uid": uid},
        )

        # Delete flashcards and notes owned by user
        db.execute(
            sql_text("DELETE FROM flashcards WHERE user_id = :uid"), {"uid": uid}
        )
        db.execute(sql_text("DELETE FROM notes WHERE user_id = :uid"), {"uid": uid})

        # Finally delete the user; courses and documents go with it by cascade
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    get_document_storage().delete_user_files(uid)
    return SuccessResponse(message="Account deleted")


@app.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using a valid token."""
    email = verify_password_reset_token(payload.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Set new password
    hashed = get_password_hash(payload.new_password)
    update_user_profile(db, user.id, password_hash=hashed)

    return {"message": "Password has been reset successfully."}


@app.get("/api/settings/username/check/{username}", response_model=UsernameCheck)
async def check_username_availability(
    request: Request,
    username: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Check if a username is available"""
    await check_rate_limit(request, str(user_id))

    # Check if username is valid
    try:
        UserProfileUpdate(username=username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Check if username is available
    existing_user = get_user_by_username(db, username)
    available = existing_user is None or existing_user.id == user_id

    return UsernameCheck(username=username, available=available)


@app.get("/api/settings/appearance", response_model=SettingsAppearance)
async def get_appearance_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user appearance settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsAppearance()


@app.patch("/api/settings/appearance", response_model=SettingsAppearance)
async def update_appearance_settings(
    request: Request,
    settings: SettingsAppearance,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user appearance settings (placeholder - save to database later)"""
    await check_rate_limit(request, str(user_id))
    # TODO: Save to database
    return settings


@app.get("/api/settings/graph", response_model=SettingsGraph)
async def get_graph_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user graph view settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsGraph()


@app.patch("/api/settings/graph", response_model=SettingsGraph)
async def update_graph_settings(
    request: Request,
    settings: SettingsGraph,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user graph view settings (placeholder - save to database later)"""
    await check_rate_limit(request, str(user_id))
    # TODO: Save to database
    return settings


@app.get("/api/settings/ai", response_model=SettingsAI)
async def get_ai_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user AI feature settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsAI()


@app.patch("/api/settings/ai", response_model=SettingsAI)
async def update_ai_settings(
    request: Request,
    settings: SettingsAI,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user AI feature settings (placeholder - save to database later)"""
    return settings


@app.get("/api/settings/studyflow", response_model=SettingsStudyFlow)
async def get_studyflow_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user study flow settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsStudyFlow()


@app.patch("/api/settings/studyflow", response_model=SettingsStudyFlow)
async def update_studyflow_settings(
    request: Request,
    settings: SettingsStudyFlow,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user study flow settings (placeholder - save to database later)"""
    await check_rate_limit(request, str(user_id))
    # TODO: Save to database
    return settings


@app.get("/api/settings/advanced", response_model=SettingsAdvanced)
async def get_advanced_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user advanced settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsAdvanced()


@app.patch("/api/settings/advanced", response_model=SettingsAdvanced)
async def update_advanced_settings(
    request: Request,
    settings: SettingsAdvanced,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user advanced settings (placeholder - save to database later)"""
    await check_rate_limit(request, str(user_id))
    # TODO: Save to database
    return settings


# Run the application
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)
