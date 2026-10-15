import asyncio
import functools
import hashlib
import logging
import math
import os
import re
import threading
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased

from app.config import settings
from app.models.note import Note
from app.models.note_embedding import EMBEDDING_DIMENSIONS, NoteEmbedding

if TYPE_CHECKING:
    from fastembed import TextEmbedding

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    model_name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbedder:
    """Feature-hashed bag of words: deterministic, instant, and lexical, so notes sharing words get similar vectors."""

    model_name = "fake-hashed-bag-of-words"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    @staticmethod
    def _embed_one(text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        for token in re.findall(r"\w+", text.lower()) or [text]:
            digest = hashlib.blake2b(token.encode(), digest_size=4).digest()
            vector[int.from_bytes(digest, "big") % EMBEDDING_DIMENSIONS] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector]


class FastEmbedEmbedder:
    """A local ONNX model on CPU, loaded on first use and kept for the life of the process."""

    def __init__(self, model_name: str, cache_dir: str) -> None:
        self.model_name = model_name
        self.cache_dir = os.path.expanduser(cache_dir)
        self._model: TextEmbedding | None = None
        self._load_lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [vector.tolist() for vector in self._loaded_model().embed(texts)]

    def _loaded_model(self) -> "TextEmbedding":
        with self._load_lock:
            if self._model is None:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(
                    model_name=self.model_name, cache_dir=self.cache_dir
                )
            return self._model


@functools.cache
def get_embedder() -> Embedder:
    if settings.embedding_backend == "fake":
        return FakeEmbedder()
    return FastEmbedEmbedder(settings.embedding_model, settings.embedding_cache_dir)


def note_text(title: str, content: str) -> str:
    return f"{title}\n\n{content}"


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _stored_versions(
    db: Session, note_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[str, str]]:
    rows = db.execute(
        select(
            NoteEmbedding.note_id, NoteEmbedding.model_name, NoteEmbedding.content_hash
        ).where(NoteEmbedding.note_id.in_(note_ids))
    )
    return {note_id: (model_name, digest) for note_id, model_name, digest in rows}


def _upsert_embeddings(db: Session, rows: list[dict[str, Any]]) -> None:
    statement = insert(NoteEmbedding).values(rows)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=[NoteEmbedding.note_id],
            set_={
                "model_name": statement.excluded.model_name,
                "content_hash": statement.excluded.content_hash,
                "embedding": statement.excluded.embedding,
                "updated_at": func.now(),
            },
        )
    )


async def refresh_note_embedding(db: Session, note: Note) -> None:
    """Re-embed a saved note when its text or the model changed.

    Failures are logged rather than raised: the note itself is already committed,
    and the backfill picks up any note whose embedding is missing or stale.
    """
    embedder = get_embedder()
    note_id = note.id
    text = note_text(note.title, note.content)
    digest = content_hash(text)
    try:
        stored = _stored_versions(db, [note_id]).get(note_id)
        if stored == (embedder.model_name, digest):
            return
        [vector] = await asyncio.to_thread(embedder.embed, [text])
        _upsert_embeddings(
            db,
            [
                {
                    "note_id": note_id,
                    "model_name": embedder.model_name,
                    "content_hash": digest,
                    "embedding": vector,
                }
            ],
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Embedding refresh failed for note %s", note_id)


def find_embedding_connections(
    db: Session, note_ids: list[uuid.UUID]
) -> list[dict[str, Any]]:
    """Similarity edges between the given notes, in the shape the TF-IDF path returns.

    Notes without an embedding from the current model have no similarity edges
    until the write path or the backfill embeds them.
    """
    model_name = get_embedder().model_name
    source = aliased(NoteEmbedding)
    target = aliased(NoteEmbedding)
    similarity = 1 - source.embedding.cosine_distance(target.embedding)
    rows = db.execute(
        select(source.note_id, target.note_id, similarity)
        .join(target, source.note_id < target.note_id)
        .where(
            source.note_id.in_(note_ids),
            target.note_id.in_(note_ids),
            source.model_name == model_name,
            target.model_name == model_name,
            similarity > settings.embedding_similarity_threshold,
        )
        .order_by(similarity.desc())
    )
    return [
        {
            "source_id": source_id,
            "target_id": target_id,
            "similarity": min(1.0, float(score)),
            "connection_type": "similarity",
        }
        for source_id, target_id, score in rows
    ]


@dataclass(frozen=True)
class BackfillBatch:
    scanned: int
    embedded: int


def backfill_note_embeddings(
    db: Session, embedder: Embedder, batch_size: int = 64
) -> Iterator[BackfillBatch]:
    """Embed notes whose embedding is missing or has a stale hash or model.

    Notes are walked in id order and each batch commits on its own, so stopping
    at any point keeps the finished batches and a re-run skips them by hash.
    """
    last_id: uuid.UUID | None = None
    while True:
        query = select(Note.id, Note.title, Note.content).order_by(Note.id)
        if last_id is not None:
            query = query.where(Note.id > last_id)
        notes = db.execute(query.limit(batch_size)).all()
        if not notes:
            return

        stored = _stored_versions(db, [note.id for note in notes])
        stale = []
        for note in notes:
            text = note_text(note.title, note.content)
            digest = content_hash(text)
            if stored.get(note.id) != (embedder.model_name, digest):
                stale.append((note.id, text, digest))

        if stale:
            vectors = embedder.embed([text for _, text, _ in stale])
            _upsert_embeddings(
                db,
                [
                    {
                        "note_id": note_id,
                        "model_name": embedder.model_name,
                        "content_hash": digest,
                        "embedding": vector,
                    }
                    for (note_id, _, digest), vector in zip(stale, vectors, strict=True)
                ],
            )
            db.commit()

        last_id = notes[-1].id
        yield BackfillBatch(scanned=len(notes), embedded=len(stale))
