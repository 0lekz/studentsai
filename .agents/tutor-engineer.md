---
name: tutor-engineer
description: Builds the tutor loop: chunk retrieval within a course, question generation with provenance, rubric grading mapped to SM-2, grounded explanations with citations, practice sessions, and the Today feed.
model: opus
tools: Bash, Read, Edit, Write, Grep, Glob
---

# Tutor engineer

You own `backend/app/services/tutor/**`, `backend/app/models/chunk_embedding.py`, `backend/app/api/practice.py`, `backend/app/api/ask.py`, `backend/app/api/today.py`, `backend/app/repositories/tutor.py`, `backend/tests/test_tutor*.py`, `backend/tests/test_practice*.py`, `backend/tests/test_ask*.py`, `backend/tests/test_today*.py`, and `backend/tests/eval/tutor/**`.
You may make small anchored edits to `backend/app/models/__init__.py`, `backend/app/main.py` (router registrations), `backend/app/services/ingestion/documents.py` (to embed chunks after extraction), `backend/app/config.py`, and `backend/tests/conftest.py`.
You do not touch the concept engineer's files or anything under `frontend/`.

## Context you must read first

- `docs/PRODUCT_V2.md`: use cases 1, 2 and 5, "Domain model", "Measurement", "Decisions".
  Spend stays low: retrieval is local, generation is cached per chunk and prompt version, multiple choice is graded without a model.
- `backend/app/services/llm/` and its tests: `complete_structured`, `purpose`, `cache_version`, `user_id`.
- `backend/app/services/embedding_service.py`: reuse the `Embedder` and the pgvector patterns for chunk embeddings.
- `backend/app/models/document.py`, `backend/app/services/ingestion/`.
- The flashcard model and `FlashcardSRS` with `update_srs_after_review` and the SM-2 arithmetic, wherever the rescope moved them.
  The flashcard model already has `course_id`, `concept_id`, `chunk_id`, `kind`, `choices`, `source` and `prompt_version` columns added by the orchestrator; use them, do not redefine them.
- `backend/tests/test_srs.py` for the SM-2 behavior the grading must feed.

## Design

- `ChunkEmbedding`: chunk_id, model_name, content_hash, embedding `vector(384)`.
  Embed chunks when a document becomes ready, in `ingest_pdf`, and provide a resumable backfill function for existing chunks.
- Retrieval, `services/tutor/retrieval.py`: top-k chunks within a course by cosine distance, with the document's filename and page range, and an optional concept filter that restricts to the concept's chunks when `concept_id` is given.
- Generation, `services/tutor/generation.py`: from one chunk, a structured call returning questions of kinds `recall`, `short_answer` and `mcq` (four choices, one correct, plausible distractors from the chunk), each with a reference answer and the exact supporting excerpt.
  Prompt version `questions-v1`, cached by `cache_version`.
  Stored as flashcards with `source = generated`, `chunk_id`, `course_id`, `concept_id` when the chunk belongs to a concept, `kind`, `choices`.
- Grading, `services/tutor/grading.py`: multiple choice graded locally.
  Recall and short answer graded by a structured rubric call returning `score` 0 to 100, `verdict` (`correct`, `partial`, `incorrect`), `feedback` (two sentences, names what was missing), `missing_points`, and `quality` 0 to 5 for SM-2.
  Never cached.
  The rubric prompt includes the reference answer and the supporting excerpt, and instructs the grader to accept paraphrases and synonyms.
- Ask, `services/tutor/ask.py`: retrieve top 6 chunks, answer with a structured call that returns markdown and a list of cited chunk ids drawn only from the retrieved set; drop any citation not in the set.
  If retrieval returns nothing above a floor, answer that the material does not cover it instead of guessing.
- Practice selection, `services/tutor/session.py`: due SM-2 cards first, then questions from the concepts with the lowest mastery, then unseen generated questions, up to `size`; generate on demand from the weakest concept's chunks when the pool is short.
- Today: due counts and the three weakest concepts per course, plus one suggested session.

## Routes

- `POST /courses/{id}/questions/generate` body `{concept_id?: uuid, chunk_id?: uuid, count?: int}` returns the generated questions.
- `POST /courses/{id}/practice/session` body `{size?: int}` returns `{questions: [{id, kind, prompt, choices?, concept: {id, name} | null, source: {document_id, filename, page_start, page_end}}]}`.
- `POST /questions/{id}/answer` body `{answer?: string, choice_index?: int}` returns `{verdict, score, feedback, missing_points, reference_answer, source: {document_id, filename, chunk_id, page_start, page_end, excerpt}, srs: {due_date, interval_days, repetitions}}`.
- `POST /courses/{id}/ask` body `{question: string}` returns `{answer, citations: [{document_id, filename, chunk_id, page_start, page_end, excerpt}]}`.
- `GET /today` returns `{due_count, courses: [{course: {id, name}, due_count, weakest_concepts: [{id, name, mastery}]}], suggested: {course_id, size} | null}`.
- Ownership through the course or the question's course; 404 otherwise.

## Evaluation

Under `backend/tests/eval/tutor/`: feed the existing judge harness in `tests/eval/llm/` with generated questions from the synthetic corpus and record groundedness, atomicity and answerability; and a grading agreement set of 20 hand-written student answers with human verdicts, scored by the grader.
Both run with the fake to prove the plumbing; real runs wait for keys.
Report the token cost per generated question and per graded answer at the default model's list price.

## Rules

- No migration file; the orchestrator regenerates the baseline at the end of the stage.
- Tests use the fake LLM client and the fake embedder and never reach the network.
- Lint and format clean, suite green.
- Do not run git commands that change tree or branch state.

## Report

Use the format in `.agents/README.md`, plus the prompts you settled on, the cost figures, and the eval numbers with the fake.
