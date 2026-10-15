import asyncio
import uuid
from datetime import datetime, timedelta

import jwt
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Request,
    status,
)
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_user_id,
    get_password_hash,
    register_user,
)
from app.config import DEBUG, GOOGLE_CLIENT_ID, GOOGLE_REDIRECT_URI, settings
from app.db.session import get_db
from app.dependencies import get_document_storage
from app.email_service import (
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
from app.models.user import User
from app.oauth_service import GoogleOAuthService
from app.rate_limiter import (
    check_auth_rate_limit,
    check_rate_limit,
)
from app.repositories.users import (
    get_user_by_email,
    get_user_by_id,
    update_user_profile,
)
from app.schemas import (
    EmailChangeRequest,
    EmailVerificationRequest,
    EmailVerificationResponse,
    ForgotPasswordRequest,
    GoogleOAuthRequest,
    GoogleOAuthResponse,
    ResetPasswordRequest,
    SuccessResponse,
    Token,
    UserCreate,
    UserLogin,
    VerificationResponse,
    VerifyEmailToken,
)

router = APIRouter()


_background_tasks: set[asyncio.Task] = set()


def _run_in_background(coro) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


@router.post("/auth/register", response_model=Token)
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


@router.post("/auth/login", response_model=Token)
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


@router.post("/auth/refresh", response_model=Token)
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


@router.get("/auth/google/login")
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


@router.get("/auth/google/callback")
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


@router.post("/auth/google", response_model=GoogleOAuthResponse)
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


@router.post("/auth/send-verification", response_model=EmailVerificationResponse)
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


@router.post("/auth/send-email-change-verification", response_model=SuccessResponse)
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


@router.post("/auth/verify-email-change", response_model=VerificationResponse)
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


@router.get("/auth/verify/{token}", response_model=VerificationResponse)
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


@router.post("/auth/verify-email", response_model=VerificationResponse)
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


@router.post("/auth/forgot-password")
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


@router.post("/auth/request-account-deletion", response_model=SuccessResponse)
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


@router.post("/auth/confirm-account-deletion", response_model=SuccessResponse)
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


@router.post("/auth/reset-password")
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
