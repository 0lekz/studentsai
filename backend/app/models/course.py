import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

COURSE_NAME_MAX_LENGTH = 120
COURSE_TERM_MAX_LENGTH = 60


class Course(Base):
    """The container a student studies in; deleting it deletes its documents, notes and flashcards."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_courses_name_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(COURSE_NAME_MAX_LENGTH), nullable=False)
    term: Mapped[str | None] = mapped_column(String(COURSE_TERM_MAX_LENGTH))
    exam_date: Mapped[date | None] = mapped_column(Date)
    archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
