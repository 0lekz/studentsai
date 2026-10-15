import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from sqlalchemy.orm import Session

from app.auth import (
    get_current_user_id,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.rate_limiter import check_rate_limit
from app.repositories.users import (
    get_user_by_id,
    get_user_by_username,
    update_user_profile,
)
from app.schemas import (
    SettingsAdvanced,
    SettingsAI,
    SettingsAppearance,
    SettingsGraph,
    SettingsStudyFlow,
    UsernameCheck,
    UserProfileUpdate,
    UserResponse,
)

router = APIRouter()


@router.get("/api/settings/profile", response_model=UserResponse)
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


@router.patch("/api/settings/profile", response_model=UserResponse)
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


@router.get("/api/settings/username/check/{username}", response_model=UsernameCheck)
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


@router.get("/api/settings/appearance", response_model=SettingsAppearance)
async def get_appearance_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user appearance settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsAppearance()


@router.patch("/api/settings/appearance", response_model=SettingsAppearance)
async def update_appearance_settings(
    request: Request,
    settings: SettingsAppearance,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user appearance settings (placeholder - save to database later)"""
    await check_rate_limit(request, str(user_id))
    # TODO: Save to database
    return settings


@router.get("/api/settings/graph", response_model=SettingsGraph)
async def get_graph_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user graph view settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsGraph()


@router.patch("/api/settings/graph", response_model=SettingsGraph)
async def update_graph_settings(
    request: Request,
    settings: SettingsGraph,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user graph view settings (placeholder - save to database later)"""
    await check_rate_limit(request, str(user_id))
    # TODO: Save to database
    return settings


@router.get("/api/settings/ai", response_model=SettingsAI)
async def get_ai_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user AI feature settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsAI()


@router.patch("/api/settings/ai", response_model=SettingsAI)
async def update_ai_settings(
    request: Request,
    settings: SettingsAI,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user AI feature settings (placeholder - save to database later)"""
    return settings


@router.get("/api/settings/studyflow", response_model=SettingsStudyFlow)
async def get_studyflow_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user study flow settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsStudyFlow()


@router.patch("/api/settings/studyflow", response_model=SettingsStudyFlow)
async def update_studyflow_settings(
    request: Request,
    settings: SettingsStudyFlow,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user study flow settings (placeholder - save to database later)"""
    await check_rate_limit(request, str(user_id))
    # TODO: Save to database
    return settings


@router.get("/api/settings/advanced", response_model=SettingsAdvanced)
async def get_advanced_settings(
    request: Request,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Get user advanced settings (placeholder - return defaults for now)"""
    await check_rate_limit(request, str(user_id))
    return SettingsAdvanced()


@router.patch("/api/settings/advanced", response_model=SettingsAdvanced)
async def update_advanced_settings(
    request: Request,
    settings: SettingsAdvanced,
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Update user advanced settings (placeholder - save to database later)"""
    await check_rate_limit(request, str(user_id))
    # TODO: Save to database
    return settings
