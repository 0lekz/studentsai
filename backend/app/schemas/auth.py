import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.common import BaseSchema


class UserBase(BaseSchema):
    email: EmailStr


class UserCreate(UserBase):
    password: str | None = None  # Made optional for OAuth users
    username: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if v is not None:
            if len(v.strip()) < 3:
                raise ValueError("Username must be at least 3 characters long")
            if len(v.strip()) > 50:
                raise ValueError("Username cannot exceed 50 characters")
            if not v.strip().replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    "Username can only contain letters, numbers, underscores, and hyphens"
                )
            return v.strip()
        return v


class GoogleOAuthRequest(BaseSchema):
    """Schema for Google OAuth callback"""

    code: str


class UserLogin(BaseSchema):
    email: EmailStr
    password: str


class User(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    verified: bool = False  # NEW: Email verification status
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    verified: bool = False  # NEW: Email verification status
    has_password: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GoogleOAuthResponse(BaseSchema):
    """Schema for Google OAuth response"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password_len(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseSchema):
    email: str | None = None


class EmailVerificationRequest(BaseModel):
    email: str


class EmailVerificationResponse(BaseModel):
    message: str
    email: str


class VerifyEmailToken(BaseModel):
    token: str


class VerificationResponse(BaseModel):
    message: str
    verified: bool
    access_token: str | None = None


class EmailChangeRequest(BaseModel):
    new_email: EmailStr
