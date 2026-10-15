import logging
import uuid
from collections.abc import Iterator, Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import DocumentChunk
from app.services.embedding_service import (
    BackfillBatch,
    Embedder,
    content_hash,
    get_embedder,
)

logger = logging.getLogger(__name__)


def chunk_text(heading_path: Sequence[str], text: str) -> str:
    """The heading path gives a slide's bullets the topic they are about."""
    if not heading_path:
        return text
    return f"{' > '.join(heading_path)}\n\n{text}"


def embed_chunks(db: Session, embedder: Embedder, chunks: Sequence[Any]) -> int:
    """Embed the chunks whose embedding is missing or stale; returns how many were embedded.

    `chunks` are rows with `id`, `heading_path` and `text`. The caller commits.
    """
    if not chunks:
        return 0
    stored = _stored_versions(db, [chunk.id for chunk in chunks])
    stale = []
    for chunk in chunks:
        text = chunk_text(chunk.heading_path, chunk.text)
        digest = content_hash(text)
        if stored.get(chunk.id) != (embedder.model_name, digest):
            stale.append((chunk.id, text, digest))
    if not stale:
        return 0

    vectors = embedder.embed([text for _, text, _ in stale])
    _upsert(
        db,
        [
            {
                "chunk_id": chunk_id,
                "model_name": embedder.model_name,
                "content_hash": digest,
                "embedding": vector,
            }
            for (chunk_id, _, digest), vector in zip(stale, vectors, strict=True)
        ],
    )
    return len(stale)


def embed_document_chunks(db: Session, chunks: Sequence[DocumentChunk]) -> None:
    """Embed a newly ready document's chunks.

    Failures are logged rather than raised: the document is already committed,
    and the backfill picks up any chunk whose embedding is missing or stale.
    """
    try:
        embed_chunks(db, get_embedder(), chunks)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Embedding failed for %d document chunks", len(chunks))


def backfill_chunk_embeddings(
    db: Session, embedder: Embedder, batch_size: int = 64
) -> Iterator[BackfillBatch]:
    """Embed chunks whose embedding is missing or has a stale hash or model.

    Chunks are walked in id order and each batch commits on its own, so stopping
    at any point keeps the finished batches and a re-run skips them by hash.
    """
    last_id: uuid.UUID | None = None
    while True:
        query = select(
            DocumentChunk.id, DocumentChunk.heading_path, DocumentChunk.text
        ).order_by(DocumentChunk.id)
        if last_id is not None:
            query = query.where(DocumentChunk.id > last_id)
        chunks = db.execute(query.limit(batch_size)).all()
        if not chunks:
            return
        embedded = embed_chunks(db, embedder, chunks)
        db.commit()
        last_id = chunks[-1].id
        yield BackfillBatch(scanned=len(chunks), embedded=embedded)


def _stored_versions(
    db: Session, chunk_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[str, str]]:
    rows = db.execute(
        select(
            ChunkEmbedding.chunk_id,
            ChunkEmbedding.model_name,
            ChunkEmbedding.content_hash,
        ).where(ChunkEmbedding.chunk_id.in_(chunk_ids))
    )
    return {chunk_id: (model_name, digest) for chunk_id, model_name, digest in rows}


def _upsert(db: Session, rows: list[dict[str, Any]]) -> None:
    statement = insert(ChunkEmbedding).values(rows)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[ChunkEmbedding.chunk_id],
            set_={
                "model_name": statement.excluded.model_name,
                "content_hash": statement.excluded.content_hash,
                "embedding": statement.excluded.embedding,
                "updated_at": func.now(),
            },
        )
    )
