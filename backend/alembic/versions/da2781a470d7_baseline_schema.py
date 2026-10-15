"""baseline schema

Revision ID: da2781a470d7
Revises:
Create Date: 2026-10-14 23:19:49.981890

Generated from Base.metadata after the concept and tutor stages. Creating the vector
extension needs a superuser unless it already exists; on a managed database, create
it once by hand before running this revision.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "da2781a470d7"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "llm_cache",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "parsed",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("oauth_provider", sa.String(length=50), nullable=True),
        sa.Column("oauth_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_oauth_id"), "users", ["oauth_id"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_table(
        "courses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("term", sa.String(length=60), nullable=True),
        sa.Column("exam_date", sa.Date(), nullable=True),
        sa.Column("archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_courses_name_not_blank"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_user_id"), "courses", ["user_id"], unique=False)
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=16, scale=10), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("cached", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('openai', 'anthropic', 'fake')", name="ck_llm_calls_provider"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_calls_user_id_created_at",
        "llm_calls",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "concepts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(dim=384), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0", name="ck_concepts_name_not_blank"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_concepts_course_id"), "concepts", ["course_id"], unique=False
    )
    op.create_index(
        "uq_concepts_course_id_lower_name",
        "concepts",
        ["course_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("outline", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("kind IN ('slides', 'pdf')", name="ck_documents_kind"),
        sa.CheckConstraint(
            "status IN ('pending', 'ready', 'failed')", name="ck_documents_status"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_documents_course_id"), "documents", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_documents_user_id"), "documents", ["user_id"], unique=False
    )
    op.create_table(
        "notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notes_course_id"), "notes", ["course_id"], unique=False)
    op.create_table(
        "concept_edges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('prerequisite', 'related')", name="ck_concept_edges_kind"
        ),
        sa.CheckConstraint(
            "source_id <> target_id", name="ck_concept_edges_not_a_loop"
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id",
            "target_id",
            "kind",
            name="uq_concept_edges_source_id_target_id_kind",
        ),
    )
    op.create_index(
        op.f("ix_concept_edges_course_id"), "concept_edges", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_concept_edges_target_id"), "concept_edges", ["target_id"], unique=False
    )
    op.create_table(
        "concept_extractions",
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "prompt_version"),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column(
            "heading_path", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("page_start", sa.Integer(), nullable=False),
        sa.Column("page_end", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id", "index", name="uq_document_chunks_document_id_index"
        ),
    )
    op.create_table(
        "flashcard_sets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("seed_note_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["seed_note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "note_embeddings",
        sa.Column("note_id", sa.UUID(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(dim=384), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("note_id"),
    )
    op.create_table(
        "note_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("from_note_id", sa.UUID(), nullable=False),
        sa.Column("to_note_id", sa.UUID(), nullable=False),
        sa.Column("link_type", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["from_note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_note_links_from_note_id"), "note_links", ["from_note_id"], unique=False
    )
    op.create_index(
        op.f("ix_note_links_to_note_id"), "note_links", ["to_note_id"], unique=False
    )
    op.create_table(
        "note_similarities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("note_a_id", sa.UUID(), nullable=False),
        sa.Column("note_b_id", sa.UUID(), nullable=False),
        sa.Column("similarity", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["note_a_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_b_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_note_similarities_note_a_id"),
        "note_similarities",
        ["note_a_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_note_similarities_note_b_id"),
        "note_similarities",
        ["note_b_id"],
        unique=False,
    )
    op.create_table(
        "chunk_embeddings",
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(dim=384), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("chunk_id"),
    )
    op.create_table(
        "chunk_question_generations",
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("chunk_id", "prompt_version"),
    )
    op.create_table(
        "concept_chunks",
        sa.Column("concept_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("concept_id", "chunk_id"),
    )
    op.create_index(
        op.f("ix_concept_chunks_chunk_id"), "concept_chunks", ["chunk_id"], unique=False
    )
    op.create_index(
        op.f("ix_concept_chunks_document_id"),
        "concept_chunks",
        ["document_id"],
        unique=False,
    )
    op.create_table(
        "flashcards",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=True),
        sa.Column("last_reviewed", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column(
            "kind", sa.String(length=16), server_default="recall", nullable=False
        ),
        sa.Column("choices", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "source", sa.String(length=16), server_default="user", nullable=False
        ),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("note_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=True),
        sa.Column("chunk_id", sa.UUID(), nullable=True),
        sa.Column("concept_id", sa.UUID(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('recall', 'short_answer', 'mcq')", name="ck_flashcards_kind"
        ),
        sa.CheckConstraint(
            "source IN ('user', 'generated')", name="ck_flashcards_source"
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_flashcards_chunk_id"), "flashcards", ["chunk_id"], unique=False
    )
    op.create_index(
        op.f("ix_flashcards_concept_id"), "flashcards", ["concept_id"], unique=False
    )
    op.create_index(
        op.f("ix_flashcards_course_id"), "flashcards", ["course_id"], unique=False
    )
    op.create_table(
        "flashcard_srs",
        sa.Column("flashcard_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("efactor", sa.Integer(), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("repetitions", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["flashcard_id"], ["flashcards.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("flashcard_id"),
    )


def downgrade() -> None:
    op.drop_table("flashcard_srs")
    op.drop_index(op.f("ix_flashcards_course_id"), table_name="flashcards")
    op.drop_index(op.f("ix_flashcards_concept_id"), table_name="flashcards")
    op.drop_index(op.f("ix_flashcards_chunk_id"), table_name="flashcards")
    op.drop_table("flashcards")
    op.drop_index(op.f("ix_concept_chunks_document_id"), table_name="concept_chunks")
    op.drop_index(op.f("ix_concept_chunks_chunk_id"), table_name="concept_chunks")
    op.drop_table("concept_chunks")
    op.drop_table("chunk_question_generations")
    op.drop_table("chunk_embeddings")
    op.drop_index(
        op.f("ix_note_similarities_note_b_id"), table_name="note_similarities"
    )
    op.drop_index(
        op.f("ix_note_similarities_note_a_id"), table_name="note_similarities"
    )
    op.drop_table("note_similarities")
    op.drop_index(op.f("ix_note_links_to_note_id"), table_name="note_links")
    op.drop_index(op.f("ix_note_links_from_note_id"), table_name="note_links")
    op.drop_table("note_links")
    op.drop_table("note_embeddings")
    op.drop_table("flashcard_sets")
    op.drop_table("document_chunks")
    op.drop_table("concept_extractions")
    op.drop_index(op.f("ix_concept_edges_target_id"), table_name="concept_edges")
    op.drop_index(op.f("ix_concept_edges_course_id"), table_name="concept_edges")
    op.drop_table("concept_edges")
    op.drop_index(op.f("ix_notes_course_id"), table_name="notes")
    op.drop_table("notes")
    op.drop_index(op.f("ix_documents_user_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_course_id"), table_name="documents")
    op.drop_table("documents")
    op.drop_index("uq_concepts_course_id_lower_name", table_name="concepts")
    op.drop_index(op.f("ix_concepts_course_id"), table_name="concepts")
    op.drop_table("concepts")
    op.drop_index("ix_llm_calls_user_id_created_at", table_name="llm_calls")
    op.drop_table("llm_calls")
    op.drop_index(op.f("ix_courses_user_id"), table_name="courses")
    op.drop_table("courses")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_oauth_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_table("llm_cache")
    # The vector extension is left installed; other database objects may use it.
