"""Embed every note whose embedding is missing or stale.

Run from backend/: venv/bin/python -m scripts.backfill_embeddings
Each batch commits on its own, so the run is safe to interrupt and re-run.
"""

import argparse
import sys
import time

from app.database import SessionLocal
from app.services.embedding_service import backfill_note_embeddings, get_embedder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    embedder = get_embedder()
    print(f"model: {embedder.model_name}, batch size: {args.batch_size}", flush=True)
    started = time.perf_counter()
    scanned = embedded = 0
    try:
        with SessionLocal() as db:
            batches = backfill_note_embeddings(db, embedder, args.batch_size)
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
