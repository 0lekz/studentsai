"""
StudentsAI MVP - FastAPI Backend Application
"""

import asyncio
import contextlib
import os
import re
import shutil
import uuid
from datetime import UTC, datetime, timedelta
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
    ai_service,
    calculate_note_similarities,
    extract_keywords_from_text,
    generate_flashcards_from_content,
    summarize_content,
)
from .api import documents
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
    ActivityDaily,
    Flashcard,
    PendingEmailChange,
    User,
    add_flashcard_tag,
    archive_mastered_flashcards,
    compute_streaks,
    create_contextual_flashcard,
    create_flashcard,
    create_flashcard_set,
    create_note,
    create_note_link,
    create_tables,
    delete_note,
    delete_note_link,
    get_activity_counts,
    get_backlinks,
    get_db,
    get_due_flashcards,
    get_due_flashcards_srs,
    get_flashcard_sets_by_user,
    get_flashcards_by_note,
    get_links_for_user_notes,
    get_note_by_id,
    get_notes_by_titles,
    get_notes_by_user,
    # SRS and flashcard set functions
    get_or_create_srs_entry,
    get_recent_events,
    get_similarities_for_notes,
    get_totals,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    # Enhanced flashcard functions
    get_user_flashcards,
    record_event,
    remove_flashcard_tag,
    replace_manual_links_for_note,
    set_note_tags,
    update_flashcard_progress,
    update_note,
    update_srs_after_review,
    update_user_profile,
)
from .email_service import (
    create_password_reset_token,
    create_verification_token,
    send_account_deletion_email,
    send_email_change_verification_step1,
    send_email_change_verification_step2,
    send_password_reset_email,
    send_verification_email,
    verify_email_change_token,
    verify_password_reset_token,
    verify_verification_token,
)
from .oauth_service import GoogleOAuthService
from .rate_limiter import check_ai_rate_limit, check_auth_rate_limit, check_rate_limit
from .rate_limiter_enhanced import enhanced_rate_limiter
from .schemas import (
    ActivityDayCount,
    ActivityResponse,
    BacklinkResponse,
    EmailChangeRequest,
    # Email verification schemas
    EmailVerificationRequest,
    EmailVerificationResponse,
    EventIngestRequest,
    EventItem,
    FlashcardDetailedReview,
    FlashcardGenerationRequest,
    FlashcardGenerationResponse,
    FlashcardResponse,
    # Enhanced flashcard schemas
    FlashcardReview,
    FlashcardReviewResponse,
    FlashcardReviewResult,
    FlashcardSetInfo,
    # New SRS and flashcard schemas
    FlashcardSRSData,
    ForgotPasswordRequest,
    GenerateFlashcardsRequest,
    GenerateFlashcardsResponse,
    GoogleOAuthRequest,
    GoogleOAuthResponse,
    GraphNode,
    GraphResponse,
    KeywordsSuggestResponse,
    NoteConnection,
    NoteCreate,
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
    ProfileSummaryResponse,
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

app.include_router(documents.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "StudentsAI MVP API"}


@app.post("/test/email")
async def test_email_service(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Test endpoint to verify email service is working"""
    await check_rate_limit(request, str(user_id))

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Test basic email sending
        from .email_service import send_email_via_sendgrid

        success = send_email_via_sendgrid(
            to_email=user.email,
            subject="Email Service Test - StudentsAI",
            html_content="<h2>Email Test</h2><p>If you received this, your email service is working!</p>",
        )

        if not success:
            raise Exception("SendGrid email sending failed")

        return {"status": "success", "message": f"Test email sent to {user.email}"}

    except Exception as e:
        return {
            "status": "error",
            "message": f"Email service failed: {e!s}",
            "details": str(type(e).__name__),
        }


_background_tasks: set[asyncio.Task] = set()


def _run_in_background(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    # Initialize enhanced rate limiter in background
    with contextlib.suppress(Exception):
        _run_in_background(enhanced_rate_limiter.init_redis())


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
                "plan": user.plan,
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
            "plan": user.plan,
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
            "plan": current_user.plan,
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


@app.post("/auth/send-email-change-verification")
async def send_email_change_verification(
    request: EmailChangeRequest,
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Step 1: Initiate email change verification process"""
    try:
        # Get current user
        current_user = get_user_by_id(db, current_user_id)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Check if new email is already in use by another user
        existing_user = get_user_by_email(db, request.new_email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use by another account",
            )

        # Check if there's already a pending email change
        existing_pending = (
            db.query(PendingEmailChange)
            .filter(
                PendingEmailChange.user_id == current_user_id,
                PendingEmailChange.expires_at > datetime.utcnow(),
            )
            .first()
        )

        if existing_pending:
            # Update existing pending change
            existing_pending.new_email = request.new_email
            existing_pending.expires_at = datetime.utcnow() + timedelta(hours=24)
            existing_pending.current_email_verified = False
            existing_pending.new_email_verified = False
        else:
            # Create new pending change
            pending_change = PendingEmailChange(
                user_id=current_user_id,
                current_email=current_user.email,
                new_email=request.new_email,
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            db.add(pending_change)

        db.commit()

        # Send verification email to current email
        success = await send_email_change_verification_step1(
            db, current_user_id, current_user.email, request.new_email
        )

        if success:
            return {"message": "Verification email sent to your current email address"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email",
            )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate email change verification",
        ) from e


@app.get("/auth/verify-email-change-step1/{token}", response_model=VerificationResponse)
async def verify_email_change_step1(
    token: str,
    new_email: str,
    db: Session = Depends(get_db),
):
    """Step 1: Verify current email ownership, then send verification to new email"""
    try:
        # Verify token and get payload
        payload = verify_email_change_token(token)
        if not payload or payload.get("type") != "email_change_step1":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        current_email = payload.get("sub")
        user_id = payload.get("user_id")

        if not current_email or not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token payload",
            )

        # Get pending email change record
        pending_change = (
            db.query(PendingEmailChange)
            .filter(
                PendingEmailChange.user_id == user_id,
                PendingEmailChange.current_email == current_email,
                PendingEmailChange.new_email == new_email,
                PendingEmailChange.expires_at > datetime.utcnow(),
            )
            .first()
        )

        if not pending_change:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending email change found or expired",
            )

        # Mark current email as verified
        pending_change.current_email_verified = True
        db.commit()

        # Send verification email to new email
        success = await send_email_change_verification_step2(db, user_id, new_email)

        if success:
            return VerificationResponse(
                message="Current email verified. Please check your new email for verification.",
                verified=True,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification to new email",
            )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify current email",
        ) from e


@app.get("/auth/verify-email-change-step2/{token}", response_model=VerificationResponse)
async def verify_email_change_step2(
    token: str,
    current_email: str,
    db: Session = Depends(get_db),
):
    """Step 2: Verify new email, then finalize email change"""
    try:
        # Verify token and get payload
        payload = verify_email_change_token(token)
        if not payload or payload.get("type") != "email_change_step2":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        new_email = payload.get("sub")
        user_id = payload.get("user_id")

        if not new_email or not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token payload",
            )

        # Get pending email change record
        pending_change = (
            db.query(PendingEmailChange)
            .filter(
                PendingEmailChange.user_id == user_id,
                PendingEmailChange.current_email == current_email,
                PendingEmailChange.new_email == new_email,
                PendingEmailChange.current_email_verified.is_(True),
                PendingEmailChange.expires_at > datetime.utcnow(),
            )
            .first()
        )

        if not pending_change:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid pending email change found",
            )

        # Mark new email as verified
        pending_change.new_email_verified = True
        db.commit()

        # Now both emails are verified - update the user's email
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Update user email
        user.email = new_email
        user.verified = True  # New email is verified
        db.commit()

        # Clean up pending change record
        db.delete(pending_change)
        db.commit()

        # Generate new access token with updated email
        new_access_token = create_access_token(data={"sub": new_email})

        return VerificationResponse(
            message="Email address updated successfully",
            verified=True,
            access_token=new_access_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email address",
        ) from e


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
    db: Session = Depends(get_db),
):
    """Get user's notes"""
    try:
        await check_rate_limit(request, str(user_id))

        notes = get_notes_by_user(db, user_id, skip, limit)

        return NoteListResponse(
            notes=[
                NoteResponse(
                    id=note.id,
                    title=note.title,
                    content=note.content,
                    summary=note.summary,
                    created_at=note.created_at,
                    updated_at=note.updated_at,
                    tags=note.tags or [],
                )
                for note in notes
            ],
            total=len(notes),
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

    note = create_note(db, note_data.title, note_data.content, user_id)
    await refresh_note_embedding(db, note)
    with contextlib.suppress(Exception):
        record_event(db, user_id, "NOTE_CREATED", target_id=note.id)

    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        summary=note.summary,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=note.tags or [],
    )


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

    return NoteResponse(
        id=note.id,
        title=note.title,
        content=note.content,
        summary=note.summary,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


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

    # Record the note update event
    with contextlib.suppress(Exception):
        record_event(db, user_id, "NOTE_UPDATED", target_id=updated_note.id)

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

    return NoteResponse(
        id=updated_note.id,
        title=updated_note.title,
        content=updated_note.content,
        summary=updated_note.summary,
        created_at=updated_note.created_at,
        updated_at=updated_note.updated_at,
        tags=updated_note.tags or [],
    )


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

    # Record the tag update event
    with contextlib.suppress(Exception):
        record_event(db, user_id, "NOTE_UPDATED", target_id=updated.id)

    return NoteResponse(
        id=updated.id,
        title=updated.title,
        content=updated.content,
        summary=updated.summary,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        tags=updated.tags or [],
    )


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
        with contextlib.suppress(Exception):
            record_event(db, user_id, "NOTE_REVIEWED", target_id=note.id)

        return NoteResponse(
            id=updated_note.id,
            title=updated_note.title,
            content=updated_note.content,
            summary=updated_note.summary,
            created_at=updated_note.created_at,
            updated_at=updated_note.updated_at,
            tags=updated_note.tags or [],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {e!s}",
        ) from e


@app.post("/notes/{note_id}/extract-keywords", response_model=NoteResponse)
async def extract_note_keywords(
    note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Extract keywords from a note using TF-IDF"""
    await check_ai_rate_limit(request, str(user_id))

    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    try:
        # Extract keywords using TF-IDF
        keywords = extract_keywords_from_text(note.content)

        # Update note with keywords
        updated_note = set_note_tags(db, note, keywords)

        with contextlib.suppress(Exception):
            record_event(db, user_id, "NOTE_REVIEWED", target_id=note.id)

        return NoteResponse(
            id=updated_note.id,
            title=updated_note.title,
            content=updated_note.content,
            summary=updated_note.summary,
            created_at=updated_note.created_at,
            updated_at=updated_note.updated_at,
            tags=updated_note.tags or [],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract keywords: {e!s}",
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
    with contextlib.suppress(Exception):
        record_event(db, user_id, "NOTE_REVIEWED", target_id=note_id)

    return [
        FlashcardResponse(
            id=flashcard.id,
            question=flashcard.question,
            answer=flashcard.answer,
            difficulty=flashcard.difficulty,
            last_reviewed=flashcard.last_reviewed,
            created_at=flashcard.created_at,
            flashcard_type=flashcard.flashcard_type,
            context_notes=flashcard.context_notes,
            tags=flashcard.tags or [],
            review_count=flashcard.review_count,
            mastery_level=flashcard.mastery_level,
            last_performance=flashcard.last_performance,
        )
        for flashcard in flashcards
    ]


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

        saved_flashcards = []
        for flashcard_data in generated_flashcards:
            flashcard = create_flashcard(
                db, flashcard_data.question, flashcard_data.answer, note_id, user_id
            )
            with contextlib.suppress(Exception):
                record_event(db, user_id, "FLASHCARD_CREATED", target_id=flashcard.id)
            saved_flashcards.append(
                FlashcardResponse(
                    id=flashcard.id,
                    question=flashcard.question,
                    answer=flashcard.answer,
                    difficulty=flashcard.difficulty,
                    last_reviewed=flashcard.last_reviewed,
                    created_at=flashcard.created_at,
                    flashcard_type=flashcard.flashcard_type,
                    context_notes=flashcard.context_notes,
                    tags=flashcard.tags or [],
                    review_count=flashcard.review_count,
                    mastery_level=flashcard.mastery_level,
                    last_performance=flashcard.last_performance,
                )
            )

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
    db: Session = Depends(get_db),
):
    """Get all flashcards for a user, optionally filtered by tags and search query"""
    await check_rate_limit(request, str(user_id))

    tag_list = tags.split(",") if tags else None
    flashcards = get_user_flashcards(db, user_id, tag_list, search)

    return [
        FlashcardResponse(
            id=flashcard.id,
            question=flashcard.question,
            answer=flashcard.answer,
            difficulty=flashcard.difficulty,
            last_reviewed=flashcard.last_reviewed,
            created_at=flashcard.created_at,
            flashcard_type=flashcard.flashcard_type,
            context_notes=flashcard.context_notes,
            tags=flashcard.tags or [],
            review_count=flashcard.review_count,
            mastery_level=flashcard.mastery_level,
            last_performance=flashcard.last_performance,
        )
        for flashcard in flashcards
    ]


@app.get("/flashcards/due", response_model=list[FlashcardResponse])
async def get_due_flashcards_endpoint(
    limit: int = 20,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get flashcards that are due for review"""
    await check_rate_limit(request, str(user_id))

    flashcards = get_due_flashcards(db, user_id, limit)

    return [
        FlashcardResponse(
            id=flashcard.id,
            question=flashcard.question,
            answer=flashcard.answer,
            difficulty=flashcard.difficulty,
            last_reviewed=flashcard.last_reviewed,
            created_at=flashcard.created_at,
            flashcard_type=flashcard.flashcard_type,
            context_notes=flashcard.context_notes,
            tags=flashcard.tags or [],
            review_count=flashcard.review_count,
            mastery_level=flashcard.mastery_level,
            last_performance=flashcard.last_performance,
        )
        for flashcard in flashcards
    ]


@app.post("/flashcards/{flashcard_id}/review", response_model=FlashcardReviewResponse)
async def review_flashcard(
    flashcard_id: uuid.UUID,
    review_data: FlashcardReview,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Review a flashcard and update progress"""
    await check_rate_limit(request, str(user_id))

    try:
        # Update flashcard progress
        flashcard = update_flashcard_progress(
            db,
            flashcard_id,
            review_data.performance_score or 0,
            review_data.user_answer,
        )

        # Record review event
        with contextlib.suppress(Exception):
            record_event(db, user_id, "FLASHCARD_REVIEWED", target_id=flashcard_id)

        # Determine quality rating (manual override or AI evaluation)
        quality_rating = review_data.quality_rating
        ai_score = None
        verdict = None
        feedback = None
        confidence = None

        if quality_rating is None:
            # Check if user has access to LLM evaluation (paid feature)
            user_has_llm_access = True  # TODO: Implement paid user check

            if user_has_llm_access:
                # LLM-based evaluation for accurate answer scoring
                try:
                    # Prepare the evaluation prompt
                    evaluation_prompt = f"""
                    You are an expert educator evaluating a student's answer to a flashcard question.
                    
                    Question: {flashcard.question}
                    Correct Answer: {flashcard.answer}
                    Student Answer: {review_data.typed_answer}
                    
                    Evaluate the student's answer based on:
                    1. Accuracy of key concepts
                    2. Completeness of the response
                    3. Understanding demonstrated
                    4. Relevance to the question
                    
                    Return ONLY a JSON response with this exact format:
                    {{
                        "score": <number 0-100>,
                        "quality_rating": <number 1-5>,
                        "verdict": "<correct|partial|incorrect>",
                        "feedback": "<detailed feedback explaining the score>",
                        "key_points_covered": <number of key concepts correctly addressed>,
                        "key_points_missing": ["<list of missing key concepts>"],
                        "confidence": <number 0-100>
                    }}
                    
                    Scoring guidelines:
                    - 90-100: Excellent understanding, all key points covered (quality 5)
                    - 75-89: Good understanding, most key points covered (quality 4)
                    - 60-74: Partial understanding, some key points covered (quality 3)
                    - 40-59: Limited understanding, few key points covered (quality 2)
                    - 0-39: Poor understanding, minimal key points covered (quality 1)
                    
                    Be fair but strict. Consider synonyms and different ways of expressing the same concept.
                    """

                    # Call LLM for evaluation (you'll need to implement this)
                    from .ai_service import evaluate_answer_with_llm

                    llm_result = await evaluate_answer_with_llm(evaluation_prompt)

                    # Parse LLM response
                    import json

                    try:
                        evaluation = json.loads(llm_result)
                        quality_rating = evaluation.get("quality_rating", 3)
                        ai_score = evaluation.get("score", 60)
                        verdict = evaluation.get("verdict", "partial")
                        feedback = evaluation.get("feedback", "AI evaluation completed")
                        confidence = evaluation.get("confidence", 80)
                    except (json.JSONDecodeError, KeyError):
                        # Fallback to simple evaluation if LLM fails
                        quality_rating = 3
                        ai_score = 60
                        verdict = "partial"
                        feedback = "AI evaluation completed with fallback scoring"
                        confidence = 70

                except Exception as e:
                    # Fallback to simple evaluation if LLM service fails
                    if DEBUG:
                        print(f"LLM evaluation failed: {e}")

                    # Simple fallback evaluation (case-insensitive, symbol-ignoring)
                    typed_answer = review_data.typed_answer.lower().strip()
                    correct_answer = flashcard.answer.lower().strip()

                    # Remove ALL punctuation, symbols, and extra whitespace for comparison
                    import re

                    typed_clean = re.sub(r"[^\w\s]", "", typed_answer).strip()
                    correct_clean = re.sub(r"[^\w\s]", "", correct_answer).strip()

                    # Normalize whitespace (replace multiple spaces with single space)
                    typed_clean = re.sub(r"\s+", " ", typed_clean)
                    correct_clean = re.sub(r"\s+", " ", correct_clean)

                    if typed_clean == correct_clean:
                        quality_rating = 5
                        ai_score = 100
                        verdict = "correct"
                        feedback = "Perfect answer!"
                    else:
                        # Word-based similarity (case-insensitive, symbol-ignoring)
                        typed_words = set(typed_clean.split())
                        correct_words = set(correct_clean.split())

                        if len(correct_words) == 0:
                            quality_rating = 1
                            ai_score = 20
                            verdict = "incorrect"
                            feedback = "Answer needs improvement"
                        else:
                            overlap = len(typed_words.intersection(correct_words))
                            similarity_score = (overlap / len(correct_words)) * 100

                            # Much more generous scoring for real-world answers
                            if similarity_score >= 0.8:  # Lowered from 0.9
                                quality_rating = 5
                                ai_score = 95
                                verdict = "correct"
                                feedback = "Excellent answer!"
                            elif similarity_score >= 0.6:  # Lowered from 0.75
                                quality_rating = 4
                                ai_score = 80
                                verdict = "correct"
                                feedback = "Very good answer!"
                            elif similarity_score >= 0.4:  # Lowered from 0.6
                                quality_rating = 3
                                ai_score = 65
                                verdict = "partial"
                                feedback = "Good effort, but missing some key points"
                            elif similarity_score >= 0.2:  # Lowered from 0.4
                                quality_rating = 2
                                ai_score = 45
                                verdict = "partial"
                                feedback = (
                                    "Some understanding shown, but needs improvement"
                                )
                            else:
                                quality_rating = 1
                                ai_score = 25
                                verdict = "incorrect"
                                feedback = "Answer needs significant improvement"

                    confidence = 70
            else:
                # Free user - use simple evaluation
                typed_answer = review_data.typed_answer.lower().strip()
                correct_answer = flashcard.answer.lower().strip()

                # Remove ALL punctuation, symbols, and extra whitespace for comparison
                import re

                typed_clean = re.sub(r"[^\w\s]", "", typed_answer).strip()
                correct_clean = re.sub(r"[^\w\s]", "", correct_answer).strip()

                # Normalize whitespace (replace multiple spaces with single space)
                typed_clean = re.sub(r"\s+", " ", typed_clean)
                correct_clean = re.sub(r"\s+", " ", correct_clean)

                if typed_clean == correct_clean:
                    quality_rating = 5
                    ai_score = 100
                    verdict = "correct"
                    feedback = "Perfect answer!"
                else:
                    # Word-based similarity (case-insensitive, symbol-ignoring)
                    typed_words = set(typed_clean.split())
                    correct_words = set(correct_clean.split())

                    if len(correct_words) == 0:
                        quality_rating = 1
                        ai_score = 20
                        verdict = "incorrect"
                        feedback = "Answer needs improvement"
                    else:
                        overlap = len(typed_words.intersection(correct_words))
                        similarity_score = (overlap / len(correct_words)) * 100

                        # Much more generous scoring for real-world answers
                        if similarity_score >= 0.8:  # Lowered from 0.9
                            quality_rating = 5
                            ai_score = 95
                            verdict = "correct"
                            feedback = "Excellent answer!"
                        elif similarity_score >= 0.6:  # Lowered from 0.75
                            quality_rating = 4
                            ai_score = 80
                            verdict = "correct"
                            feedback = "Very good answer!"
                        elif similarity_score >= 0.4:  # Lowered from 0.6
                            quality_rating = 3
                            ai_score = 65
                            verdict = "partial"
                            feedback = "Good effort, but missing some key points"
                        elif similarity_score >= 0.2:  # Lowered from 0.4
                            quality_rating = 2
                            ai_score = 45
                            verdict = "partial"
                            feedback = "Some understanding shown, but needs improvement"
                        else:
                            quality_rating = 1
                            ai_score = 25
                            verdict = "incorrect"
                            feedback = "Answer needs significant improvement"

                confidence = 70

        # Update SRS
        srs_entry = update_srs_after_review(db, flashcard_id, user_id, quality_rating)

        # Update flashcard progress
        flashcard.review_count += 1
        flashcard.last_reviewed = datetime.now(UTC)

        # Map quality to performance score
        performance_map = {0: 0, 1: 20, 2: 40, 3: 60, 4: 80, 5: 100}
        performance_score = performance_map.get(quality_rating, 60)
        flashcard.last_performance = performance_score

        # Update mastery level
        if performance_score >= 80:
            flashcard.mastery_level = min(100, flashcard.mastery_level + 20)
        elif performance_score < 50:
            flashcard.mastery_level = max(0, flashcard.mastery_level - 10)

        # Update tags based on performance
        if not flashcard.tags:
            flashcard.tags = []

        if performance_score >= 80 and srs_entry.repetitions >= 3:
            if "recently_learned" not in flashcard.tags:
                flashcard.tags.append("recently_learned")
        elif performance_score < 50 and "recently_learned" in flashcard.tags:
            flashcard.tags.remove("recently_learned")

        db.commit()

        # Record review event
        with contextlib.suppress(Exception):
            record_event(db, user_id, "FLASHCARD_REVIEWED", target_id=flashcard_id)

        # Generate feedback based on LLM evaluation
        if (
            "feedback" in locals()
            and feedback != "AI evaluation completed with fallback scoring"
        ):
            # Use LLM-generated feedback
            pass
        else:
            # Fallback feedback generation
            if quality_rating >= 4:
                feedback = "Excellent! You've mastered this concept."
            elif quality_rating == 3:
                feedback = "Good job! Keep practicing to improve."
            else:
                feedback = (
                    "Keep studying this material. Review the answer and try again."
                )

        # Create SRS data response
        srs_data = FlashcardSRSData(
            flashcard_id=flashcard_id,
            efactor=srs_entry.efactor / 100.0,  # Convert back to float
            interval_days=srs_entry.interval_days,
            due_date=srs_entry.due_date,
            repetitions=srs_entry.repetitions,
            next_review_date=srs_entry.due_date,
        )

        return FlashcardReviewResponse(
            flashcard_id=flashcard_id,
            performance_score=flashcard.last_performance,
            feedback=feedback,
            mastery_level=flashcard.mastery_level,
            next_review_date=flashcard.next_review,
            tags_updated=flashcard.tags or [],
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review flashcard: {e!s}",
        ) from e


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
        flashcard = add_flashcard_tag(db, flashcard_id, tag)

        # Record the flashcard tag event
        with contextlib.suppress(Exception):
            record_event(
                db,
                user_id,
                "FLASHCARD_TAGGED",
                target_id=flashcard_id,
                metadata={"tag": tag, "action": "added"},
            )

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
        flashcard = remove_flashcard_tag(db, flashcard_id, tag)

        # Record the flashcard tag removal event
        with contextlib.suppress(Exception):
            record_event(
                db,
                user_id,
                "FLASHCARD_TAGGED",
                target_id=flashcard_id,
                metadata={"tag": tag, "action": "removed"},
            )

        return {"message": f"Tag '{tag}' removed successfully", "tags": flashcard.tags}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@app.post(
    "/notes/{note_id}/flashcards/contextual/generate",
    response_model=list[FlashcardResponse],
)
async def generate_contextual_flashcards(
    note_id: uuid.UUID,
    count: int = 10,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Generate contextual flashcards using the note and its strongest connections"""
    await check_ai_rate_limit(request, str(user_id))

    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    try:
        # Get note similarities to find strongest connections
        notes_data = [{"id": note.id, "title": note.title, "content": note.content}]
        similarities = calculate_note_similarities(notes_data)

        # Get top 5 most similar notes
        context_notes = []
        if similarities:
            # Sort by similarity and get top 5
            sorted_sims = sorted(
                similarities, key=lambda x: x["similarity"], reverse=True
            )
            top_notes = sorted_sims[:5]

            for sim in top_notes:
                if sim["source_id"] != note_id:
                    context_notes.append(sim["source_id"])
                elif sim["target_id"] != note_id:
                    context_notes.append(sim["target_id"])

        # Generate flashcards with context
        contextual_content = note.content
        if context_notes:
            # Add context from related notes
            for ctx_note_id in context_notes:
                ctx_note = get_note_by_id(db, ctx_note_id, user_id)
                if ctx_note:
                    contextual_content += f"\n\nRelated context from '{ctx_note.title}':\n{ctx_note.content[:500]}..."

        generated_flashcards = await generate_flashcards_from_content(
            contextual_content, count
        )

        saved_flashcards = []
        for flashcard_data in generated_flashcards:
            flashcard = create_contextual_flashcard(
                db,
                flashcard_data.question,
                flashcard_data.answer,
                note_id,
                user_id,
                context_notes,
            )
            with contextlib.suppress(Exception):
                record_event(db, user_id, "FLASHCARD_CREATED", target_id=flashcard.id)
            saved_flashcards.append(
                FlashcardResponse(
                    id=flashcard.id,
                    question=flashcard.question,
                    answer=flashcard.answer,
                    difficulty=flashcard.difficulty,
                    last_reviewed=flashcard.last_reviewed,
                    created_at=flashcard.created_at,
                    flashcard_type=flashcard.flashcard_type,
                    context_notes=flashcard.context_notes,
                    tags=flashcard.tags or [],
                    review_count=flashcard.review_count,
                    mastery_level=flashcard.mastery_level,
                    last_performance=flashcard.last_performance,
                )
            )

        return saved_flashcards

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate contextual flashcards: {e!s}",
        ) from e


# Enhanced flashcard system endpoints
@app.post("/flashcards/generate", response_model=FlashcardGenerationResponse)
async def generate_flashcards_enhanced(
    request_data: FlashcardGenerationRequest,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_verified_user_id),
    db: Session = Depends(get_db),
):
    """Generate flashcards using the new enhanced system"""
    await check_ai_rate_limit(request, str(user_id))

    note = get_note_by_id(db, request_data.note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
        )

    try:
        if request_data.mode == "single":
            # Single note mode
            generated_flashcards = await generate_flashcards_from_content(
                note.content, request_data.count or 5
            )

            # Create flashcard set
            flashcard_set = create_flashcard_set(
                db, user_id, "single", request_data.note_id
            )

            # Save flashcards
            saved_flashcards = []
            for flashcard_data in generated_flashcards:
                flashcard = create_flashcard(
                    db,
                    flashcard_data.question,
                    flashcard_data.answer,
                    request_data.note_id,
                    user_id,
                    "single_note",
                )

                # Create SRS entry
                get_or_create_srs_entry(db, flashcard.id, user_id)

                with contextlib.suppress(Exception):
                    record_event(
                        db, user_id, "FLASHCARD_CREATED", target_id=flashcard.id
                    )

                saved_flashcards.append(
                    FlashcardResponse(
                        id=flashcard.id,
                        question=flashcard.question,
                        answer=flashcard.answer,
                        difficulty=flashcard.difficulty,
                        last_reviewed=flashcard.last_reviewed,
                        created_at=flashcard.created_at,
                        flashcard_type=flashcard.flashcard_type,
                        context_notes=flashcard.context_notes,
                        tags=flashcard.tags or [],
                        review_count=flashcard.review_count,
                        mastery_level=flashcard.mastery_level,
                        last_performance=flashcard.last_performance,
                    )
                )

            return FlashcardGenerationResponse(
                flashcard_set_id=flashcard_set.id,
                cards=saved_flashcards,
                context_notes=[request_data.note_id],
            )

        elif request_data.mode == "context":
            # Context-graph mode
            notes_data = [{"id": note.id, "title": note.title, "content": note.content}]
            similarities = calculate_note_similarities(notes_data)

            # Get top neighbors
            context_notes = []
            if similarities:
                sorted_sims = sorted(
                    similarities, key=lambda x: x["similarity"], reverse=True
                )
                top_notes = sorted_sims[: request_data.neighbors or 5]

                for sim in top_notes:
                    if sim["source_id"] != request_data.note_id:
                        context_notes.append(sim["source_id"])
                    elif sim["target_id"] != request_data.note_id:
                        context_notes.append(sim["target_id"])

            # Generate contextual content
            contextual_content = note.content
            total_tokens = len(note.content.split())  # Rough token estimate

            for ctx_note_id in context_notes:
                if total_tokens >= (request_data.token_cap or 2500):
                    break

                ctx_note = get_note_by_id(db, ctx_note_id, user_id)
                if ctx_note:
                    note_content = ctx_note.content[:500]  # Limit context per note
                    contextual_content += f"\n\nRelated context from '{ctx_note.title}':\n{note_content}..."
                    total_tokens += len(note_content.split())

            # Generate flashcards
            generated_flashcards = await generate_flashcards_from_content(
                contextual_content, request_data.count or 10
            )

            # Create flashcard set
            flashcard_set = create_flashcard_set(
                db, user_id, "context", request_data.note_id, context_notes
            )

            # Save flashcards
            saved_flashcards = []
            for flashcard_data in generated_flashcards:
                flashcard = create_contextual_flashcard(
                    db,
                    flashcard_data.question,
                    flashcard_data.answer,
                    request_data.note_id,
                    user_id,
                    context_notes,
                )

                # Create SRS entry
                get_or_create_srs_entry(db, flashcard.id, user_id)

                with contextlib.suppress(Exception):
                    record_event(
                        db, user_id, "FLASHCARD_CREATED", target_id=flashcard.id
                    )

                saved_flashcards.append(
                    FlashcardResponse(
                        id=flashcard.id,
                        question=flashcard.question,
                        answer=flashcard.answer,
                        difficulty=flashcard.difficulty,
                        last_reviewed=flashcard.last_reviewed,
                        created_at=flashcard.created_at,
                        flashcard_type=flashcard.flashcard_type,
                        context_notes=flashcard.context_notes,
                        tags=flashcard.tags or [],
                        review_count=flashcard.review_count,
                        mastery_level=flashcard.mastery_level,
                        last_performance=flashcard.last_performance,
                    )
                )

            return FlashcardGenerationResponse(
                flashcard_set_id=flashcard_set.id,
                cards=saved_flashcards,
                context_notes=context_notes,
                total_tokens_used=total_tokens,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mode must be 'single' or 'context'",
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate flashcards: {e!s}",
        ) from e


@app.post(
    "/flashcards/{flashcard_id}/review/enhanced", response_model=FlashcardReviewResult
)
async def review_flashcard_enhanced(
    flashcard_id: uuid.UUID,
    review_data: FlashcardDetailedReview,
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Enhanced flashcard review with SRS and detailed evaluation"""
    await check_rate_limit(request, str(user_id))

    try:
        # Get flashcard
        flashcard = db.query(Flashcard).filter(Flashcard.id == flashcard_id).first()
        if not flashcard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Flashcard not found"
            )

        # Determine quality rating (manual override or AI evaluation)
        quality_rating = review_data.quality_rating
        ai_score = None
        verdict = None
        feedback = None
        confidence = None

        if quality_rating is None:
            # Enhanced AI evaluation based on answer similarity and content
            typed_answer = review_data.typed_answer.lower().strip()
            correct_answer = flashcard.answer.lower().strip()

            # Calculate similarity score (0-100)
            if typed_answer == correct_answer:
                similarity_score = 100
            else:
                # Enhanced scoring algorithm
                typed_words = set(typed_answer.split())
                correct_words = set(correct_answer.split())

                if len(correct_words) == 0:
                    similarity_score = 0
                else:
                    # Word overlap scoring
                    overlap = len(typed_words.intersection(correct_words))
                    word_similarity = (overlap / len(correct_words)) * 100

                    # Length similarity (penalize very short answers)
                    length_ratio = len(typed_answer) / max(len(correct_answer), 1)
                    length_score = min(100, length_ratio * 100)

                    # Combined score with weights
                    similarity_score = (word_similarity * 0.7) + (length_score * 0.3)

                    # Bonus for partial matches
                    if overlap > 0 and overlap < len(correct_words):
                        similarity_score = min(100, similarity_score + 10)

                    # Penalty for completely wrong answers
                    if overlap == 0:
                        similarity_score = max(0, similarity_score - 20)

            # Map similarity to quality rating (1-5) with better thresholds
            if similarity_score >= 95:
                quality_rating = 5  # Excellent - Nearly perfect
            elif similarity_score >= 80:
                quality_rating = 4  # Good - Most key points covered
            elif similarity_score >= 60:
                quality_rating = 3  # Partial - Some key points covered
            elif similarity_score >= 30:
                quality_rating = 2  # Poor - Few key points covered
            else:
                quality_rating = 1  # Very Poor - Almost no key points

        # Update SRS
        srs_entry = update_srs_after_review(db, flashcard_id, user_id, quality_rating)

        # Update flashcard progress
        flashcard.review_count += 1
        flashcard.last_reviewed = datetime.now(UTC)

        # Map quality to performance score
        performance_map = {0: 0, 1: 20, 2: 40, 3: 60, 4: 80, 5: 100}
        performance_score = performance_map.get(quality_rating, 60)
        flashcard.last_performance = performance_score

        # Update mastery level
        if performance_score >= 80:
            flashcard.mastery_level = min(100, flashcard.mastery_level + 20)
        elif performance_score < 50:
            flashcard.mastery_level = max(0, flashcard.mastery_level - 10)

        # Update tags based on performance
        if not flashcard.tags:
            flashcard.tags = []

        if performance_score >= 80 and srs_entry.repetitions >= 3:
            if "recently_learned" not in flashcard.tags:
                flashcard.tags.append("recently_learned")
        elif performance_score < 50 and "recently_learned" in flashcard.tags:
            flashcard.tags.remove("recently_learned")

        db.commit()

        # Record review event
        with contextlib.suppress(Exception):
            record_event(db, user_id, "FLASHCARD_REVIEWED", target_id=flashcard_id)

        # Generate feedback based on LLM evaluation
        if (
            "feedback" in locals()
            and feedback != "AI evaluation completed with fallback scoring"
        ):
            # Use LLM-generated feedback
            pass
        else:
            # Fallback feedback generation
            if quality_rating >= 4:
                feedback = "Excellent! You've mastered this concept."
            elif quality_rating == 3:
                feedback = "Good job! Keep practicing to improve."
            else:
                feedback = (
                    "Keep studying this material. Review the answer and try again."
                )

        # Create SRS data response
        srs_data = FlashcardSRSData(
            flashcard_id=flashcard_id,
            efactor=srs_entry.efactor / 100.0,  # Convert back to float
            interval_days=srs_entry.interval_days,
            due_date=srs_entry.due_date,
            repetitions=srs_entry.repetitions,
            next_review_date=srs_entry.due_date,
        )

        return FlashcardReviewResult(
            flashcard_id=flashcard_id,
            ai_score=ai_score if ai_score is not None else performance_score,
            verdict=verdict
            if verdict is not None
            else (
                "correct"
                if quality_rating >= 4
                else "partial"
                if quality_rating >= 3
                else "incorrect"
            ),
            feedback=feedback if feedback is not None else "Evaluation completed",
            missing_points=[],  # TODO: Extract from LLM response
            confidence=confidence if confidence is not None else 80,
            next_review_date=srs_entry.due_date,
            srs_data=srs_data,
            tags_updated=flashcard.tags or [],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review flashcard: {e!s}",
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
                mode=set_item.mode,
                seed_note_id=set_item.seed_note_id,
                neighbor_note_ids=set_item.neighbor_note_ids or [],
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

    return [
        FlashcardResponse(
            id=flashcard.id,
            question=flashcard.question,
            answer=flashcard.answer,
            difficulty=flashcard.difficulty,
            last_reviewed=flashcard.last_reviewed,
            created_at=flashcard.created_at,
            flashcard_type=flashcard.flashcard_type,
            context_notes=flashcard.context_notes,
            tags=flashcard.tags or [],
            review_count=flashcard.review_count,
            mastery_level=flashcard.mastery_level,
            last_performance=flashcard.last_performance,
        )
        for flashcard in flashcards
    ]


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
    db: Session = Depends(get_db),
):
    """Get graph visualization of notes"""
    await check_rate_limit(request, str(user_id))

    notes = get_notes_by_user(db, user_id)

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

    # Calculate connections
    if settings.similarity_backend == "embeddings":
        connections = find_embedding_connections(db, [note.id for note in notes])
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

    # Merge manual links
    links = get_links_for_user_notes(db, [n.id for n in notes])
    for link_row in links:
        graph_connections.append(
            NoteConnection(
                source_id=link_row.from_note_id,
                target_id=link_row.to_note_id,
                similarity=1.0,
                connection_type="manual",
            )
        )

    # Merge stored similarities (authoritative values for edge thickness)
    sims = get_similarities_for_notes(db, [n.id for n in notes])
    for s in sims:
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


# Keyword suggestion endpoint (local, cheap)
@app.get("/notes/{note_id}/keywords", response_model=KeywordsSuggestResponse)
async def suggest_keywords(
    note_id: uuid.UUID,
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    note = get_note_by_id(db, note_id, user_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    word_count = len((note.content or "").split())
    max_keywords = 8 if word_count < 400 else 12 if word_count < 1200 else 18
    keywords = ai_service.extract_keywords(note.content, max_keywords=max_keywords)
    return KeywordsSuggestResponse(note_id=note.id, keywords=keywords)


# Profile/Events endpoints
@app.get("/api/profile/summary", response_model=ProfileSummaryResponse)
async def profile_summary(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    totals = get_totals(db, user_id)
    current_streak, best_streak = compute_streaks(db, user_id)

    # activity windows
    now = datetime.now(UTC)
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)
    a7_rows = get_activity_counts(db, user_id, d7, now, kind="all")
    a30_rows = get_activity_counts(db, user_id, d30, now, kind="all")

    return ProfileSummaryResponse(
        notes_created=totals["notes_created"],
        notes_reviewed=totals["notes_reviewed"],
        flashcards_created=totals["flashcards_created"],
        flashcards_reviewed=totals["flashcards_reviewed"],
        current_streak=current_streak,
        best_streak=best_streak,
        activity_7d=sum(r[1] for r in a7_rows),
        activity_30d=sum(r[1] for r in a30_rows),
    )


@app.get("/api/profile/activity", response_model=ActivityResponse)
async def profile_activity(
    from_date: str,
    to_date: str,
    kind: str = "all",
    request: Request = None,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    # Parse dates as UTC-midnight boundaries
    start = datetime.fromisoformat(from_date).replace(tzinfo=UTC)
    end_inclusive = datetime.fromisoformat(to_date).replace(tzinfo=UTC)
    # Set end to the end of the day (23:59:59.999999) to include all activity on that date
    end = end_inclusive.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Try to use daily aggregates first; fall back to on-the-fly if missing
    agg_rows = (
        db.query(ActivityDaily.day, ActivityDaily.count)
        .filter(
            ActivityDaily.user_id == user_id,
            ActivityDaily.day >= start.date(),
            ActivityDaily.day <= end_inclusive.date(),
            ActivityDaily.kind == kind,
        )
        .order_by(ActivityDaily.day)
        .all()
    )
    if agg_rows:
        rows = [(d, c, None) for (d, c) in agg_rows]
    else:
        rows = get_activity_counts(db, user_id, start, end, kind=kind)

    # Materialize day list for continuity
    days_out: list[ActivityDayCount] = []
    cursor = start.date()
    while cursor <= end_inclusive.date():
        # find row for cursor
        found = next((r for r in rows if r[0].date() == cursor), None)
        if found:
            days_out.append(
                ActivityDayCount(
                    date=str(cursor),
                    count=int(found[1]),
                    top_type=(str(found[2]) if len(found) > 2 and found[2] else None),
                )
            )
        else:
            days_out.append(ActivityDayCount(date=str(cursor), count=0, top_type=None))
        cursor = cursor + timedelta(days=1)

    return ActivityResponse(
        from_date=from_date, to_date=to_date, kind=kind, days=days_out
    )


@app.get("/api/profile/recent", response_model=list[EventItem])
async def profile_recent(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    events = get_recent_events(db, user_id, limit=10)
    return [
        EventItem(
            id=e.id,
            event_type=e.event_type,
            occurred_at=e.occurred_at,
            target_id=e.target_id,
            metadata=getattr(e, "event_metadata", None),
        )
        for e in events
    ]


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


@app.post("/api/events", response_model=SuccessResponse)
async def ingest_event(
    request: Request,
    body: EventIngestRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    await check_rate_limit(request, str(user_id))
    try:
        record_event(
            db,
            user_id=user_id,
            event_type=body.event_type,
            target_id=body.target_id,
            metadata=body.metadata,
            occurred_at=body.occurred_at,
        )
        return SuccessResponse(message="Event recorded")
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to record event: {e}"
        ) from e


@app.post("/api/profile/aggregate", response_model=SuccessResponse)
async def profile_aggregate(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Compute daily aggregates for the authenticated user over all time.
    Dev-friendly: safe to run repeatedly (upserts).
    """
    await check_rate_limit(request, str(user_id))
    # Use raw SQL for concise upsert aggregates
    for kind, filter_clause in (
        ("all", ""),
        ("notes", "AND event_type IN ('NOTE_CREATED','NOTE_REVIEWED')"),
        ("flashcards", "AND event_type IN ('FLASHCARD_CREATED','FLASHCARD_REVIEWED')"),
    ):
        stmt = sql_text(
            f"""
            INSERT INTO activity_daily (user_id, day, kind, count)
            SELECT :uid AS user_id,
                   DATE(occurred_at AT TIME ZONE 'UTC') AS day,
                   :kind AS kind,
                   COUNT(*) AS count
            FROM events
            WHERE user_id = :uid
            {filter_clause}
            GROUP BY DATE(occurred_at AT TIME ZONE 'UTC')
            ON CONFLICT (user_id, day, kind)
            DO UPDATE SET count = EXCLUDED.count;
            """
        )
        db.execute(stmt, {"uid": str(user_id), "kind": kind})
    db.commit()
    return SuccessResponse(message="Aggregates updated")


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
        plan=user.plan,
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

    # Check if email is being changed and if it's available
    if profile_update.email and profile_update.email != user.email:
        existing_user = get_user_by_email(db, profile_update.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(status_code=400, detail="Email already taken")

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
    if profile_update.email:
        update_data["email"] = profile_update.email
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
        plan=updated_user.plan,
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

    user = get_user_by_id(db, uuid.UUID(user_id))
    if not user:
        # Already gone
        return SuccessResponse(message="Account deleted")

    # Delete user-related data (DB-level, handle FKs manually to avoid violations)
    uid = str(user.id)
    try:
        # Delete review and SRS data first (depend on flashcards/users)
        db.execute(
            sql_text("DELETE FROM flashcard_reviews WHERE user_id = :uid"), {"uid": uid}
        )
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

        # Delete pending email changes, activity, events
        db.execute(
            sql_text("DELETE FROM pending_email_changes WHERE user_id = :uid"),
            {"uid": uid},
        )
        db.execute(
            sql_text("DELETE FROM activity_daily WHERE user_id = :uid"), {"uid": uid}
        )
        db.execute(sql_text("DELETE FROM events WHERE user_id = :uid"), {"uid": uid})

        # Finally delete the user
        db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
        raise

    documents.get_document_storage().delete_user_files(uid)
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
