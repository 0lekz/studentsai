"""
Pydantic schemas for API request/response validation
"""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, validator


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    class Config:
        from_attributes = True


# User schemas
class UserBase(BaseSchema):
    email: EmailStr


class UserCreate(UserBase):
    password: str | None = None  # Made optional for OAuth users
    username: str | None = None

    @validator("password")
    def validate_password(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @validator("username")
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

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    verified: bool = False  # NEW: Email verification status
    has_password: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GoogleOAuthResponse(BaseSchema):
    """Schema for Google OAuth response"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserProfileUpdate(BaseSchema):
    """Email changes go through /auth/send-email-change-verification instead."""

    username: str | None = None
    current_password: str | None = None
    new_password: str | None = None

    @validator("username")
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

    @validator("new_password")
    def validate_new_password(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UsernameCheck(BaseSchema):
    username: str
    available: bool


# Password reset schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @validator("new_password")
    def validate_new_password_len(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class SettingsAppearance(BaseSchema):
    theme: str = "dark"  # "light", "dark", "system"
    font_size: str = "medium"  # "small", "medium", "large"
    layout_density: str = "comfortable"  # "compact", "dense", "comfortable"


class SettingsGraph(BaseSchema):
    edge_thickness_scale: float = 1.0
    node_spacing: float = 1.0
    show_backlinks: bool = True
    physics_enabled: bool = True
    clustering_strength: float = 0.5


class SettingsAI(BaseSchema):
    use_openai: bool = True
    daily_request_limit: int = 100
    enable_caching: bool = True


class SettingsStudyFlow(BaseSchema):
    quiz_enabled: bool = True
    flashcard_auto_review: bool = True
    linked_notes_suggestions: bool = True


class SettingsAdvanced(BaseSchema):
    data_export_enabled: bool = True
    analytics_enabled: bool = True


class UserSettings(BaseSchema):
    appearance: SettingsAppearance
    graph: SettingsGraph
    ai: SettingsAI
    study_flow: SettingsStudyFlow
    advanced: SettingsAdvanced


# Authentication schemas
class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseSchema):
    email: str | None = None


# Note schemas
class NoteBase(BaseSchema):
    title: str
    content: str

    @validator("title")
    def validate_title(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Title cannot be empty")
        if len(v) > 500:
            raise ValueError("Title cannot exceed 500 characters")
        return v.strip()

    @validator("content")
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Content cannot be empty")
        return v.strip()


class NoteCreate(NoteBase):
    course_id: uuid.UUID | None = None


class NoteUpdate(BaseSchema):
    title: str | None = None
    content: str | None = None
    summary: str | None = None

    @validator("title")
    def validate_title(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Title cannot be empty")
            if len(v) > 500:
                raise ValueError("Title cannot exceed 500 characters")
            return v.strip()
        return v

    @validator("content")
    def validate_content(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Content cannot be empty")
            return v.strip()
        return v


class Note(NoteBase):
    id: uuid.UUID
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
    user_id: uuid.UUID


class NoteResponse(BaseSchema):
    id: uuid.UUID
    title: str
    content: str
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
    tags: list[str] | None = []
    course_id: uuid.UUID | None = None


class NoteListResponse(BaseSchema):
    notes: list[NoteResponse]
    total: int
    page: int
    per_page: int


# Flashcard schemas
class FlashcardResponse(BaseSchema):
    id: uuid.UUID
    question: str
    answer: str
    difficulty: int
    last_reviewed: datetime | None = None
    created_at: datetime
    tags: list[str] | None = []
    review_count: int
    course_id: uuid.UUID | None = None


class FlashcardReviewRequest(BaseSchema):
    quality_rating: int = Field(ge=0, le=5)


class FlashcardReviewResponse(BaseSchema):
    flashcard_id: uuid.UUID
    quality_rating: int
    repetitions: int
    interval_days: int
    efactor: float
    due_date: date


class FlashcardSetInfo(BaseSchema):
    id: uuid.UUID
    seed_note_id: uuid.UUID
    created_at: datetime
    flashcard_count: int


class FlashcardGenerationRequest(BaseSchema):
    note_id: uuid.UUID
    count: int | None = 5


class FlashcardGenerationResponse(BaseSchema):
    flashcard_set_id: uuid.UUID
    cards: list[FlashcardResponse]


# AI service schemas
class SummarizeRequest(BaseSchema):
    content: str

    @validator("content")
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Content cannot be empty")
        if len(v) > 50000:  # Reasonable limit for AI processing
            raise ValueError("Content too long for processing")
        return v.strip()


class SummarizeResponse(BaseSchema):
    summary: str
    word_count: int
    original_length: int


class GenerateFlashcardsRequest(BaseSchema):
    content: str
    count: int | None = 5

    @validator("content")
    def validate_content(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Content cannot be empty")
        return v.strip()

    @validator("count")
    def validate_count(cls, v):
        if v < 1 or v > 20:
            raise ValueError("Count must be between 1 and 20")
        return v


class GeneratedFlashcard(BaseSchema):
    question: str
    answer: str


class GenerateFlashcardsResponse(BaseSchema):
    flashcards: list[GeneratedFlashcard]
    count: int


# Graph schemas
class NoteConnection(BaseSchema):
    source_id: uuid.UUID
    target_id: uuid.UUID
    similarity: float
    connection_type: str = "similarity"


class GraphNode(BaseSchema):
    id: uuid.UUID
    title: str
    content_preview: str
    created_at: datetime
    word_count: int


class GraphResponse(BaseSchema):
    nodes: list[GraphNode]
    connections: list[NoteConnection]
    total_nodes: int


# Backlink schemas
class BacklinkResponse(BaseSchema):
    note_id: uuid.UUID
    title: str
    excerpt: str | None = None
    created_at: datetime


class UpdateTagsRequest(BaseSchema):
    tags: list[str]


# Error schemas
class ErrorResponse(BaseSchema):
    error: str
    detail: str | None = None
    code: str | None = None


# Success schemas
class SuccessResponse(BaseSchema):
    message: str
    data: dict | None = None


# NEW: Email verification schemas
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
