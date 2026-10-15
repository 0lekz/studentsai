import uuid

from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)  # Made nullable for OAuth users
    verified = Column(
        Boolean, default=False, nullable=False
    )  # NEW: Email verification status

    # OAuth fields (NEW)
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'apple', etc.
    oauth_id = Column(
        String(255), nullable=True, unique=True, index=True
    )  # OAuth provider's user ID

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    flashcards = relationship(
        "Flashcard", back_populates="user", cascade="all, delete-orphan"
    )
