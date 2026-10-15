---
name: concept-engineer
description: Extracts concepts from a course's documents with cached structured LLM calls, deduplicates them locally with embeddings, derives per-concept mastery from review history, and serves the concept map.
model: opus
tools: Bash, Read, Edit, Write, Grep, Glob
---

# Concept engineer

You own `backend/app/models/concept.py`, `backend/app/services/concepts/**`, `backend/app/api/concepts.py`, `backend/app/repositories/concepts.py`, `backend/tests/test_concepts*.py`, and `backend/tests/eval/concepts/**`.
You may make small anchored edits to `backend/app/models/__init__.py`, `backend/app/main.py` (one router registration), and `backend/tests/conftest.py`.
You do not touch the tutor engineer's files (`services/tutor/**`, `api/practice.py`, `api/ask.py`, `api/today.py`) or anything under `frontend/`.

## Context you must read first

- `docs/PRODUCT_V2.md`: use case 4, "Domain model", "Measurement", "Decisions".
- `backend/app/services/llm/` and its tests: the only way to call a model.
  `complete_structured` with a `StructuredOutput` model, `purpose` tags, `cache_version` for anything you want cached, `user_id` for cost attribution.
- `backend/app/services/embedding_service.py`: the `Embedder` for concept vectors; the fake is active in tests.
- `backend/app/models/document.py` and `backend/app/services/ingestion/`: chunks carry `heading_path`, `page_start`, `page_end`, `text`.
- `backend/app/models/flashcard.py` (or wherever `Flashcard` and `FlashcardSRS` live after the rescope): questions carry `concept_id`, and SM-2 state lives in `FlashcardSRS`.

## Design

- `Concept`: id, course_id, name (unique per course, case-insensitive), description (one or two sentences in the professor's terms), order (first appearance across documents in upload order), embedding `vector(384)`, created_at, updated_at.
- `ConceptChunk`: concept_id, chunk_id, with the document id denormalized for cheap provenance queries.
- `ConceptEdge`: course_id, source_id, target_id, kind (`prerequisite` or `related`), weight.
  Prerequisite edges follow document and chunk order: a concept first seen earlier is a prerequisite of one first seen later when both appear in the same chunk or adjacent chunks.
  Related edges come from concept embedding similarity above a threshold in settings.
  No LLM call for edges.
- Extraction, `services/concepts/extraction.py`: one structured call per chunk returning a list of concepts with name and description, prompt version `concepts-v1`, cached by `cache_version` so re-running is free.
  Chunks of fewer than 40 tokens are skipped.
  Dedup per course by exact name, then by concept embedding cosine above a settings threshold; keep the earlier name and merge chunk links.
  Idempotent per document and prompt version: record which documents were extracted with which version.
- Mastery, `services/concepts/mastery.py`: a pure function over the concept's questions and their SM-2 state.
  Never reviewed counts as 0.
  Otherwise `min(1, repetitions / 4) * (0.5 + 0.5 * (efactor - 1.3) / 1.2)`, averaged across the concept's questions.
  Document the formula in the docstring; it is a heuristic the product can tune later.
  A concept with no questions has `mastery = null`.
- Routes:
  - `GET /courses/{id}/concepts` returns concepts in order, each with `id, name, description, order, mastery, question_count, sources: [{document_id, chunk_id, page_start, page_end}]`.
  - `POST /courses/{id}/concepts/extract` runs extraction over the course's ready documents synchronously and returns the same list.
    Return 409 if the course has no ready documents.
  - `GET /courses/{id}/map` returns `{nodes: [{id, name, mastery, question_count, order}], edges: [{source, target, kind, weight}]}`.
  - `DELETE /courses/{id}/concepts/{concept_id}` and `PATCH` for renaming, since wrong automatic organization must be editable.
- Ownership through the course; 404 for another user's course.

## Evaluation

Under `backend/tests/eval/concepts/`: a small synthetic labeled set of 4 to 6 generated documents with known concepts per document, and a runner reporting precision and recall of extracted concept names against the labels with fuzzy matching, plus the dedup rate.
Runs with the fake client scripted to return the labeled concepts, to prove the plumbing; the real run waits for keys.

## Rules

- No migration file; the orchestrator regenerates the single baseline from `Base.metadata` at the end of the stage.
  Keep `app/models/__init__.py` importing your models.
- The tutor engineer is working in parallel and owns the question generation and the `chunk_embeddings`; do not add chunk embeddings yourself.
- Tests use the fake LLM client and the fake embedder and never reach the network.
- Lint and format clean, suite green: `cd backend && venv/bin/ruff check && venv/bin/ruff format --check && venv/bin/pytest -p no:cacheprovider`.
- Do not run git commands that change tree or branch state.

## Report

Use the format in `.agents/README.md`, plus the prompt you settled on, the cost per chunk at the default model's list price, and the eval numbers with the fake.
