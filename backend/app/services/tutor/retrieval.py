import asyncio
import uuid
from collections.abc import Collection
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk_embedding import ChunkEmbedding
from app.models.document import Document, DocumentChunk
from app.services.embedding_service import get_embedder


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    heading_path: list[str]
    page_start: int
    page_end: int
    text: str
    similarity: float


async def retrieve_chunks(
    db: Session,
    course_id: uuid.UUID,
    query: str,
    *,
    k: int,
    chunk_ids: Collection[uuid.UUID] | None = None,
) -> list[RetrievedChunk]:
    """The `k` chunks of the course nearest to `query` by cosine distance, nearest first.

    `chunk_ids` restricts the search, for example to one concept's chunks.
    Chunks without an embedding from the current model are not searched until
    ingestion or the backfill embeds them.
    """
    embedder = get_embedder()
    [vector] = await asyncio.to_thread(embedder.embed, [query])
    return nearest_chunks(
        db, course_id, vector, embedder.model_name, k=k, chunk_ids=chunk_ids
    )


def nearest_chunks(
    db: Session,
    course_id: uuid.UUID,
    vector: list[float],
    model_name: str,
    *,
    k: int,
    chunk_ids: Collection[uuid.UUID] | None = None,
) -> list[RetrievedChunk]:
    distance = ChunkEmbedding.embedding.cosine_distance(vector)
    query = (
        select(DocumentChunk, Document.filename, distance)
        .join(ChunkEmbedding, ChunkEmbedding.chunk_id == DocumentChunk.id)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(Document.course_id == course_id, ChunkEmbedding.model_name == model_name)
        .order_by(distance, DocumentChunk.id)
        .limit(k)
    )
    if chunk_ids is not None:
        query = query.where(DocumentChunk.id.in_(list(chunk_ids)))
    return [
        RetrievedChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            filename=filename,
            heading_path=list(chunk.heading_path),
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            text=chunk.text,
            similarity=max(-1.0, min(1.0, 1 - float(chunk_distance))),
        )
        for chunk, filename, chunk_distance in db.execute(query)
    ]
