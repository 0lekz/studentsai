"""
Pydantic schemas for API request/response validation
"""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, validator


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
    plan: str = "free"
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
    username: str | None = None
    email: EmailStr | None = None
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
    pass


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


class NoteListResponse(BaseSchema):
    notes: list[NoteResponse]
    total: int
    page: int
    per_page: int


# Flashcard schemas
class FlashcardBase(BaseSchema):
    question: str
    answer: str
    flashcard_type: str = "single_note"  # "single_note" or "contextual"
    context_notes: list[uuid.UUID] | None = None

    @validator("question", "answer")
    def validate_text(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Question and answer cannot be empty")
        return v.strip()

    @validator("flashcard_type")
    def validate_flashcard_type(cls, v):
        if v not in ["single_note", "contextual"]:
            raise ValueError("Flashcard type must be 'single_note' or 'contextual'")
        return v


class FlashcardCreate(FlashcardBase):
    pass


class Flashcard(FlashcardBase):
    id: uuid.UUID
    difficulty: int
    last_reviewed: datetime | None = None
    next_review: datetime | None = None
    created_at: datetime
    note_id: uuid.UUID
    user_id: uuid.UUID
    tags: list[str] | None = []
    review_count: int = 0
    mastery_level: int = 0
    last_performance: int | None = None
    user_answer_history: dict[str, Any] | None = None


class FlashcardResponse(BaseSchema):
    id: uuid.UUID
    question: str
    answer: str
    difficulty: int
    last_reviewed: datetime | None = None
    created_at: datetime
    flashcard_type: str
    context_notes: list[uuid.UUID] | None = None
    tags: list[str] | None = []
    review_count: int
    mastery_level: int
    last_performance: int | None = None


class FlashcardReview(BaseSchema):
    flashcard_id: uuid.UUID
    user_answer: str
    performance_score: int | None = None  # 0-100 score


class FlashcardReviewResponse(BaseSchema):
    flashcard_id: uuid.UUID
    performance_score: int
    feedback: str
    mastery_level: int
    next_review_date: datetime | None = None
    tags_updated: list[str] = []


# New schemas for enhanced flashcard system
class FlashcardSRSData(BaseSchema):
    flashcard_id: uuid.UUID
    efactor: float  # E-Factor (2.5, 3.0, etc.)
    interval_days: int
    due_date: date
    repetitions: int
    next_review_date: date


class FlashcardSetInfo(BaseSchema):
    id: uuid.UUID
    mode: str  # 'single' or 'context'
    seed_note_id: uuid.UUID
    neighbor_note_ids: list[uuid.UUID] | None = []
    created_at: datetime
    flashcard_count: int


class FlashcardDetailedReview(BaseSchema):
    flashcard_id: uuid.UUID
    typed_answer: str
    quality_rating: int | None = None  # 0-5 rating for manual override


class FlashcardReviewResult(BaseSchema):
    flashcard_id: uuid.UUID
    ai_score: int  # 0-100 score from LLM
    verdict: str  # 'correct', 'partial', 'incorrect'
    feedback: str
    missing_points: list[str]
    confidence: int  # 0-100 confidence from LLM
    next_review_date: date
    srs_data: FlashcardSRSData
    tags_updated: list[str] = []


class FlashcardGenerationRequest(BaseSchema):
    mode: str  # 'single' or 'context'
    note_id: uuid.UUID
    count: int | None = 5
    neighbors: int | None = 5
    token_cap: int | None = 2500


class FlashcardGenerationResponse(BaseSchema):
    flashcard_set_id: uuid.UUID
    cards: list[FlashcardResponse]
    context_notes: list[uuid.UUID] | None = []
    total_tokens_used: int | None = None


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


class KeywordsSuggestResponse(BaseSchema):
    note_id: uuid.UUID
    keywords: list[str]


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


# Events / Profile schemas
class EventType(str):
    NOTE_CREATED = "NOTE_CREATED"
    NOTE_REVIEWED = "NOTE_REVIEWED"
    NOTE_UPDATED = "NOTE_UPDATED"
    FLASHCARD_CREATED = "FLASHCARD_CREATED"
    FLASHCARD_REVIEWED = "FLASHCARD_REVIEWED"
    FLASHCARD_UPDATED = "FLASHCARD_UPDATED"
    FLASHCARD_TAGGED = "FLASHCARD_TAGGED"


class EventItem(BaseSchema):
    id: uuid.UUID
    event_type: str
    occurred_at: datetime
    target_id: uuid.UUID | None = None
    metadata: dict | None = None


class ProfileSummaryResponse(BaseSchema):
    notes_created: int
    notes_reviewed: int
    flashcards_created: int
    flashcards_reviewed: int
    current_streak: int
    best_streak: int
    activity_7d: int
    activity_30d: int


class ActivityDayCount(BaseSchema):
    date: str  # YYYY-MM-DD (UTC)
    count: int
    top_type: str | None = None


class ActivityResponse(BaseSchema):
    from_date: str
    to_date: str
    kind: str
    days: list[ActivityDayCount]


class EventIngestRequest(BaseSchema):
    event_type: str
    target_id: uuid.UUID | None = None
    occurred_at: datetime | None = None
    metadata: dict | None = None


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
    new_email: str
