import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def create_user(
    db: Session,
    email: str,
    password_hash: str | None = None,
    username: str | None = None,
    oauth_provider: str | None = None,
    oauth_id: str | None = None,
) -> User:
    """Create new user (supports both password and OAuth)"""
    if username is None:
        # Generate a unique username if none provided
        import uuid

        base_username = f"user_{str(uuid.uuid4())[:8]}"
        username = base_username
        counter = 1
        while get_user_by_username(db, username):
            username = f"{base_username}_{counter}"
            counter += 1

    user = User(
        email=email,
        username=username,
        password_hash=password_hash,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_oauth(db: Session, oauth_provider: str, oauth_id: str) -> User | None:
    """Get user by OAuth provider and ID"""
    return (
        db.query(User)
        .filter(User.oauth_provider == oauth_provider, User.oauth_id == oauth_id)
        .first()
    )


def create_or_get_oauth_user(
    db: Session,
    email: str,
    oauth_provider: str,
    oauth_id: str,
    username: str | None = None,
) -> User:
    """Create new OAuth user or get existing one"""
    # First try to find by OAuth ID
    existing_user = get_user_by_oauth(db, oauth_provider, oauth_id)
    if existing_user:
        return existing_user

    # Then try to find by email (in case user signed up with password first)
    existing_user = get_user_by_email(db, email)
    if existing_user:
        # Link existing user to OAuth
        existing_user.oauth_provider = oauth_provider
        existing_user.oauth_id = oauth_id
        existing_user.verified = True  # OAuth users are automatically verified
        db.commit()
        db.refresh(existing_user)
        return existing_user

    # Create new OAuth user
    user = create_user(
        db,
        email=email,
        username=username,
        oauth_provider=oauth_provider,
        oauth_id=oauth_id,
    )
    # OAuth sign-ups are considered verified (provider verified email)
    user.verified = True
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def update_user_profile(db: Session, user_id: uuid.UUID, **kwargs) -> User | None:
    """Update user profile fields"""
    user = get_user_by_id(db, user_id)
    if not user:
        return None

    for field, value in kwargs.items():
        if hasattr(user, field):
            setattr(user, field, value)

    user.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user
