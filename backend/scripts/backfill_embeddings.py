"""Embed every note, or with --chunks every document chunk, whose embedding is missing or stale.

Run from backend/: venv/bin/python -m scripts.backfill_embeddings [--chunks]
Each batch commits on its own, so the run is safe to interrupt and re-run.
"""

import argparse
import sys
import time
from collections.abc import Sequence

from app.db.session import SessionLocal
from app.services.embedding_service import backfill_note_embeddings, get_embedder
from app.services.tutor.embeddings import backfill_chunk_embeddings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument(
        "--chunks",
        action="store_true",
        help="embed document chunks for course retrieval instead of notes",
    )
    args = parser.parse_args(argv)

    embedder = get_embedder()
    backfill = backfill_chunk_embeddings if args.chunks else backfill_note_embeddings
    target = "chunks" if args.chunks else "notes"
    print(
        f"{target}, model: {embedder.model_name}, batch size: {args.batch_size}",
        flush=True,
    )
    started = time.perf_counter()
    scanned = embedded = 0
    try:
        with SessionLocal() as db:
            batches = backfill(db, embedder, args.batch_size)
            for number, batch in enumerate(batches, start=1):
                scanned += batch.scanned
                embedded += batch.embedded
                print(
                    f"batch {number}: scanned {batch.scanned}, embedded {batch.embedded}",
                    flush=True,
                )
    except KeyboardInterrupt:
        print("interrupted: finished batches are saved, re-run to continue")
        return 130

    elapsed = time.perf_counter() - started
    print(
        f"done: scanned {scanned}, embedded {embedded}, "
        f"already current {scanned - embedded}, {elapsed:.2f}s"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
