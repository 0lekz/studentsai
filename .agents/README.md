# Agent definitions

This directory holds the role definitions for the subagents used to work on this repository.
An orchestrating Claude Code session reads a definition, then spawns the agent with the Agent tool using `model: opus` and a task brief that points back at the definition file.

All agents in this directory run on Claude Opus.
Do not define an agent here with any other model.

## Files

| File | Role | Owns |
|---|---|---|
| `backend-test-engineer.md` | pytest foundation and characterization tests | `backend/tests/**`, `backend/requirements-dev.txt`, the `[tool.pytest.ini_options]` table in `backend/pyproject.toml` |
| `backend-hygiene-engineer.md` | lint, security fixes, CI workflow, Dependabot | `backend/app/**`, the `[tool.ruff*]` tables in `backend/pyproject.toml`, `.github/workflows/**`, `.github/dependabot.yml` |
| `frontend-build-engineer.md` | type-check, lint and build gates for the Next.js app | `frontend/**` |
| `ml-retrieval-engineer.md` | embedding-based note similarity on pgvector, flag-gated, with a committed benchmark against TF-IDF | `backend/app/services/embedding_service.py`, `backend/app/models/note_embedding.py`, `backend/scripts/backfill_embeddings.py`, `backend/tests/eval/**`, its tests and migration |
| `ingestion-engineer.md` | PDF and slide-deck ingestion with structured extraction and chunking | `backend/app/models/document.py`, `backend/app/services/ingestion/**`, `backend/app/api/documents.py`, its tests and migration |
| `backend-rescope-engineer.md` | cuts the features PRODUCT_V2 removes, adds Course, resets the schema to one baseline, extracts routers | `backend/app/**` except the LLM layer, `backend/alembic/**`, `backend/tests/**` except LLM tests |
| `llm-platform-engineer.md` | one LLM provider interface with OpenAI, Anthropic and fake clients, cost logging, caching, eval harness skeleton | `backend/app/services/llm/**`, `backend/app/models/llm_call.py`, `backend/tests/test_llm*.py`, `backend/tests/eval/llm/**` |
| `frontend-foundation-engineer.md` | design tokens, course-centric app shell, decomposition, cut-feature removal, generated typed client, Playwright screenshots | `frontend/**` |
| `concept-engineer.md` | concept extraction per course with cached structured calls, local dedup, mastery, concept map | `backend/app/models/concept.py`, `backend/app/services/concepts/**`, `backend/app/api/concepts.py`, its tests and eval |
| `tutor-engineer.md` | chunk retrieval, question generation with provenance, rubric grading into SM-2, grounded ask, practice sessions, today feed | `backend/app/services/tutor/**`, `backend/app/models/chunk_embedding.py`, `backend/app/api/{practice,ask,today}.py`, its tests and eval |
| `frontend-product-engineer.md` | Today, Practice, Ask and Map screens on the shell, phone-first, citations first-class, Playwright-verified | `frontend/**` |

## Shared rules

Every agent follows these rules in addition to its own definition.

- Work only inside the files the role owns.
  If a change outside that boundary is needed, stop and report it instead of making it.
- Never run git commands that change the working tree or branch state: no `checkout`, `stash`, `reset`, `clean`, `commit`, `rebase`, or `push`.
  Read-only git commands such as `status`, `diff`, and `log` are fine.
- Other agents are editing other parts of the same working tree at the same time.
  A transient failure in a file outside the owned boundary is probably in-progress work by another agent; retry once before reporting it.
- Do not change runtime behavior unless the brief explicitly asks for a specific behavior change.
  Phase 0 of `docs/ROADMAP_V2.md` is a characterization phase: tests describe the system as it is, bugs included.
- Never call a paid API.
  OpenAI and SendGrid are always stubbed in tests.
- Follow the engineering rules in the user's global instructions: self-documenting code, minimal comments, no em dashes, one sentence per line in long Markdown.
- Finish with a report that lists: files created or changed, the exact commands used to verify the work and their results, anything left undone and why, and any bug discovered but deliberately not fixed.

## New code layout

From phase 2 on, new backend code lands in the target layout from `docs/ROADMAP_V2.md` and existing code is not moved to make room for it.

- ORM models in `backend/app/models/<domain>.py`, importing `Base` from `app.database`, re-exported from `backend/app/models/__init__.py`.
- Business logic in `backend/app/services/`.
- Route handlers in `backend/app/api/<domain>.py` as an `APIRouter`, registered with one `include_router` line in `main.py`.
- Each feature ships its own Alembic revision; the orchestrator chains revisions when parallel agents both branch from the same head.

## Spawning

Example call from the orchestrator:

```
Agent(
  subagent_type="general-purpose",
  model="opus",
  prompt="Read .agents/backend-test-engineer.md first and follow it. Task: ..."
)
```

Claude Code also discovers agents from `.claude/agents/*.md`.
If these roles should be selectable by name as a `subagent_type`, symlink or copy the files there.
