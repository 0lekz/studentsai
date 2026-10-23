"""
Configuration management for StudentsAI MVP
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Database
    database_url: str = "postgresql://username:password@localhost:5432/studentsai_db"

    # JWT
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = (
        480  # 8 hours for long lectures and study sessions
    )
    verification_token_expire_minutes: int = (
        1440  # 24 hours for email verification token expiry
    )

    # Email, sent through the SendGrid Web API
    mail_from: str = "your-email@gmail.com"
    mail_from_name: str = "StudentsAI"
    sendgrid_api_key: str = "your-sendgrid-api-key"

    # Google OAuth Configuration (NEW)
    google_client_id: str = "your-google-client-id"
    google_client_secret: str = "your-google-client-secret"
    google_redirect_uri: str = "http://localhost:3000/auth/google/callback"

    # App
    host: str = "0.0.0.0"
    port: int = 8000
    frontend_url: str = "http://localhost:3000"  # NEW: Frontend URL for email links (use https://www.studentsai.org for production)
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://www.studentsai.org",
        "https://studentsai.org",
        "https://api.studentsai.org",
    ]
    allowed_origins: str = "http://localhost:3000,http://localhost:8000,https://www.studentsai.org,https://studentsai.org,https://api.studentsai.org"  # For backward compatibility

    # AI Configuration
    openai_api_key: str = "your-openai-api-key"
    ai_requests_per_hour: int = 100  # Hourly AI request limit

    # LLM provider layer; model and base URL default to the provider's own
    llm_provider: Literal["openai", "anthropic", "fake"] = "fake"
    llm_model: str | None = None
    llm_base_url: str | None = None
    anthropic_api_key: str | None = None
    llm_timeout_seconds: float = 120.0
    llm_max_retries: int = 2
    llm_reasoning_effort: str | None = None

    # Note similarity
    similarity_backend: Literal["tfidf", "embeddings"] = "tfidf"
    embedding_backend: Literal["fastembed", "fake"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_cache_dir: str = "~/.cache/fastembed"
    embedding_similarity_threshold: float = 0.7

    # Concepts; thresholds are cosine similarities of concept-name embeddings
    concept_dedup_threshold: float = 0.93
    concept_related_threshold: float = 0.8
    concept_max_prerequisites: int = 2
    concept_extraction_concurrency: int = 4

    # Tutor; below this question-to-chunk cosine similarity, Ask answers that the
    # material does not cover the question. Calibrated for bge-small-en-v1.5.
    ask_min_similarity: float = 0.5

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # seconds

    # Documents, stored outside the public /uploads static mount
    document_storage_dir: Path = (
        Path(__file__).resolve().parent.parent / "storage" / "documents"
    )
    max_document_bytes: int = 25 * 1024 * 1024

    # API docs, error details in responses and no rate limits; False in production
    debug: bool = True

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )


# Global settings instance
settings = Settings()

# Database URL for SQLAlchemy
DATABASE_URL = settings.database_url

# Security configuration
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

# Google OAuth configuration (NEW)
GOOGLE_CLIENT_ID = settings.google_client_id
GOOGLE_CLIENT_SECRET = settings.google_client_secret
GOOGLE_REDIRECT_URI = settings.google_redirect_uri

# Application configuration
DEBUG = settings.debug
HOST = settings.host
PORT = settings.port

# Rate limiting configuration
RATE_LIMIT_REQUESTS = settings.rate_limit_requests
RATE_LIMIT_WINDOW = settings.rate_limit_window

# CORS configuration
ALLOWED_ORIGINS = settings.backend_cors_origins
