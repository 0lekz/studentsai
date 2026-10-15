import uuid
from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DDL,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.note_embedding import EMBEDDING_DIMENSIONS

CONCEPT_NAME_MAX_LENGTH = 120


class ConceptEdgeKind(StrEnum):
    PREREQUISITE = "prerequisite"
    RELATED = "related"


_EDGE_KINDS = ", ".join(f"'{kind}'" for kind in ConceptEdgeKind)


class Concept(Base):
    """An idea a course teaches, the node of the concept map that mastery attaches to.

    `order` is the concept's first appearance across the course's documents in
    upload order; `embedding` encodes the name, for deduplication and related edges.
    """

    __tablename__ = "concepts"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_concepts_name_not_blank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(CONCEPT_NAME_MAX_LENGTH), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


Index(
    "uq_concepts_course_id_lower_name",
    Concept.course_id,
    func.lower(Concept.name),
    unique=True,
)

# create_tables() builds the schema with create_all on startup, so the table brings its column type.
event.listen(
    Concept.__table__,
    "before_create",
    DDL("CREATE EXTENSION IF NOT EXISTS vector"),
)


class ConceptChunk(Base):
    """A chunk a concept was extracted from; the document is denormalized for provenance queries."""

    __tablename__ = "concept_chunks"

    concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class ConceptEdge(Base):
    """A directed prerequisite edge, or a related edge from the earlier concept to the later one."""

    __tablename__ = "concept_edges"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_EDGE_KINDS})", name="ck_concept_edges_kind"),
        CheckConstraint("source_id <> target_id", name="ck_concept_edges_not_a_loop"),
        UniqueConstraint(
            "source_id",
            "target_id",
            "kind",
            name="uq_concept_edges_source_id_target_id_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("concepts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)


class ConceptExtraction(Base):
    """Marks a document as extracted with a prompt version, so re-running extraction skips it."""

    __tablename__ = "concept_extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    prompt_version: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
