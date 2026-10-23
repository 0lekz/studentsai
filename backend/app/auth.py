"""
Authentication and authorization for StudentsAI MVP
"""

import uuid
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from .db.session import get_db
from .repositories.users import (
    create_user,
    get_user_by_email,
    get_user_by_oauth,
    get_user_by_username,
)
from .schemas.auth import TokenData, UserCreate

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData | None:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")

        if email is None:
            return None

        return TokenData(email=email)
    except jwt.InvalidTokenError:
        return None


def authenticate_user(db: Session, email: str, password: str):
    """Authenticate user with email and password"""
    user = get_user_by_email(db, email)

    if not user:
        return False

    if not verify_password(password, user.password_hash):
        return False

    return user


def register_user(db: Session, user_data: UserCreate):
    """Register a new user"""
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Check if username is provided and available
    if hasattr(user_data, "username") and user_data.username:
        existing_username = get_user_by_username(db, user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

    # For password-based registration, password is required
    if not user_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for registration",
        )

    # Hash password and create user
    hashed_password = get_password_hash(user_data.password)
    username = getattr(user_data, "username", None)
    user = create_user(db, user_data.email, hashed_password, username)

    return user


def authenticate_oauth_user(db: Session, oauth_provider: str, oauth_id: str):
    """Authenticate user via OAuth"""
    user = get_user_by_oauth(db, oauth_provider, oauth_id)
    if not user:
        return False
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = verify_token(credentials.credentials)
    if token_data is None or token_data.email is None:
        raise credentials_exception

    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception

    return user


def get_current_user_id(current_user=Depends(get_current_user)) -> uuid.UUID:
    """Get current user ID from JWT token"""
    return current_user.id


def get_verified_user_id(current_user=Depends(get_current_user)) -> uuid.UUID:
    """Get current user ID and ensure they are verified"""
    if not current_user.verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please check your email and verify your account before accessing this feature.",
        )
    return current_user.id
