"""add note_embeddings table on pgvector

Revision ID: 2958e8e6a34e
Revises: c297091e7da0
Create Date: 2026-10-14 16:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "2958e8e6a34e"
down_revision: Union[str, None] = "911975c5e1cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSIONS = 384


def upgrade() -> None:
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except sa.exc.DBAPIError as error:
        raise RuntimeError(
            "Could not create the pgvector extension. Install pgvector on the "
            "Postgres server, then have a superuser run `CREATE EXTENSION vector;` "
            "in this database and re-run this migration."
        ) from error

    # create_tables() on app startup may already have built this table via create_all.
    if sa.inspect(op.get_bind()).has_table("note_embeddings"):
        return

    op.create_table(
        "note_embeddings",
        sa.Column(
            "note_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("note_embeddings")
