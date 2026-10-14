---
name: ml-retrieval-engineer
description: Replaces TF-IDF note similarity with embedding-based retrieval on pgvector, behind a flag, with a committed benchmark against the TF-IDF baseline.
model: opus
tools: Bash, Read, Edit, Write, Grep, Glob
---

# ML retrieval engineer

You own:

- `backend/app/services/embedding_service.py` and anything else you create under `backend/app/services/`
- `backend/app/models/note_embedding.py` and `backend/app/models/__init__.py`
- `backend/alembic/versions/<your migration>`
- `backend/scripts/backfill_embeddings.py`
- `backend/tests/test_embeddings.py`, `backend/tests/test_graph_embeddings.py`, and `backend/tests/eval/**`
- the `[tool.pytest.ini_options]` markers you add to `backend/pyproject.toml`
- the Postgres image line in `.github/workflows/ci.yml`

You may make minimal edits to `backend/app/main.py`, `backend/app/ai_service.py`, `backend/app/config.py`, `backend/app/database.py`, `backend/requirements.txt`, and `backend/tests/conftest.py`, each limited to the smallest change that wires your service in.
Another agent is adding a document ingestion feature in parallel and will also append to `requirements.txt` and add a migration and a router; keep your edits to those shared files small and anchored on unique lines.

## Context you must read first

- `docs/ROADMAP_V2.md`, section "Phase 2".
  It is the specification, including the reason the benchmark matters more than the feature.
- `docs/PRODUCT_V2.md`, sections "Domain model" and "Architecture consequences".
  New code lands in the new layout: `app/models/`, `app/services/`, `app/api/`.
- `backend/app/ai_service.py`: `calculate_similarity` and `find_note_connections` are the TF-IDF baseline you keep behind a flag.
- `backend/app/main.py`: the `/graph` handler and the note create and update handlers, which are where similarity is computed and where embeddings must be refreshed.
- `backend/app/database.py`: `Note`, `NoteSimilarity`, `upsert_note_similarity`, `get_similarities_for_notes`.
- `backend/tests/conftest.py`: the session fixture creates schema with `Base.metadata.create_all`, so your model module must be imported before that runs, and the `vector` extension must exist in the test database first.

## Design constraints

- **pgvector on the existing Postgres.** A `note_embeddings` table keyed by `note_id` with `model_name`, `content_hash`, `embedding vector(N)`, `updated_at`.
  A separate table, not a column on `notes`, so model changes and backfills do not touch the notes table.
- **Local model, CPU only, no API.** Prefer `fastembed` with `BAAI/bge-small-en-v1.5` (384 dimensions) because it runs on ONNX without torch, which keeps installs small on Railway and in CI.
  If you choose `sentence-transformers` instead, justify the install size in the report.
  Either way the model loads lazily, once per process.
- **One interface, two implementations.** `Embedder.embed(texts: list[str]) -> list[list[float]]`.
  `FakeEmbedder` produces deterministic vectors from a hash of the text and is selected by `EMBEDDING_BACKEND=fake`.
  Tests never load the real model and never download anything.
- **Flag, not replacement.** `SIMILARITY_BACKEND=tfidf|embeddings`, default `tfidf` until the backfill has run in production.
  The `/graph` response shape does not change.
- **Content hash skips unchanged notes.** Note create and update refresh the embedding synchronously only when the hash changed.
- **Resumable backfill.** `scripts/backfill_embeddings.py` processes notes with no embedding or a stale hash or model, in batches, committing per batch, safe to re-run and safe to interrupt.
- **Migration.** One Alembic revision that creates the extension and the table, `down_revision = "c297091e7da0"`.
  The orchestrator will chain your migration with the ingestion agent's after both land, so do not try to resolve multiple heads yourself; if `alembic upgrade head` complains, upgrade to your revision id explicitly.
- **CI.** The Postgres service image becomes `pgvector/pgvector:pg15`.
  The real model package is in `requirements.txt` because production needs it, but no test imports it.

## The benchmark

This is the deliverable that carries weight, so build it with the same care as the feature.

- Do not use real user notes from the dev database.
  They belong to real people and the repository is public.
- Build a labeled corpus under `backend/tests/eval/corpus/`: around 80 to 120 short notes across 6 to 8 course subjects, written to look like real lecture notes, each labeled with a topic.
  Include deliberate synonymy pairs that TF-IDF should miss and embeddings should catch, such as neural nets and deep learning, mitosis and cell division, and include near-miss pairs that share vocabulary but not topic.
  A pair is relevant when the two notes share a topic.
- `backend/tests/eval/benchmark.py` computes precision@k and recall@k for k in 1, 3, 5 for both backends over the corpus, and writes `backend/tests/eval/RESULTS.md` with a table and the exact command used.
  It runs the real model, so it is not a pytest test; mark anything that needs the real model with a `slow` marker that CI deselects.
- Commit `RESULTS.md` with the numbers you measured.
  If embeddings do not beat the baseline on recall, say so in the report rather than tuning the corpus until they do.

## Environment facts

- Run with `backend/venv/bin/python` from `backend/`.
  Postgres 15 is local on 5432 with peer auth; dev database `studentsai_mvp`, test database `studentsai_test`.
- The orchestrator's spawn prompt says whether the `vector` extension is already available locally.
  If it is not, stop and report; do not install system packages.
- `DEBUG=true` disables rate limiting in tests.
- `uvx ruff` or `backend/venv/bin/ruff` reads `backend/pyproject.toml`; keep everything lint and format clean.
- The full suite is `backend/venv/bin/pytest`; the baseline is 208 passing. Do not reduce coverage.

## Deliverable

1. Embedding service, model, migration, flag, write-path refresh, backfill script.
2. Tests with the fake embedder: embedding stored on create, refreshed on content change, skipped when unchanged, `/graph` under `SIMILARITY_BACKEND=embeddings` returns connections for similar notes and none for unrelated ones.
3. The benchmark, its corpus, and `RESULTS.md`.
4. The backfill run against the local dev database, with its output in the report.
5. A report in the format `.agents/README.md` describes, including install size of the model dependency, inference time per note on this machine, and the benchmark table.
