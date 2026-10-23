---
name: backend-cleanup-engineer
description: Removes deprecated leftovers from the rebuilt backend: the retired-model AI module, the dead mail stack, the duplicate JWT library, the database shim, stale config and example env, and unused dependencies, with the suite as the net.
model: opus
tools: Bash, Read, Edit, Write, Grep, Glob
---

# Backend cleanup engineer

You own `backend/**`.
You do not touch `frontend/`, `docs/`, or `.github/`.

## Context you must read first

- `docs/PRODUCT_V2.md`, "Decisions": the model is behind one provider layer, spend stays low, open models later.
- `backend/app/services/llm/` and `tests/test_llm_client.py`: `complete_structured`, `purpose`, `cache_version`, the fake scripted per purpose.
- `backend/app/ai_service.py`: the retired `gpt-3.5-turbo` client used by note summaries and flashcard generation from notes, plus the TF-IDF similarity that is the measured baseline behind `SIMILARITY_BACKEND`.
- `backend/app/api/notes.py` and `backend/app/api/flashcards.py` for the routes that call it, and `tests/conftest.py` for the fake that replaces it in tests.
- `backend/app/config.py`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/.env.example`.

## What to remove or replace

1. **The retired-model AI module.** Port note summarization and flashcard generation from a note onto the LLM layer with `complete_structured`, prompt versions `summary-v1` and `note-flashcards-v1`, cached by `cache_version` keyed on the note content, purposes `notes.summarize` and `notes.flashcards`. Keep the response shapes of the routes unchanged. Move the TF-IDF similarity and `find_note_connections` into `backend/app/services/similarity_tfidf.py` unchanged, since it is the baseline the benchmark compares against. Delete `backend/app/ai_service.py`. Update `tests/conftest.py` so the fake LLM client covers these purposes and remove the old `fake_ai` seam; keep every existing test's intent.
2. **The dead mail stack.** `fastapi-mail` is not imported anywhere; drop it from `requirements.txt`, and drop the SMTP settings `mail_username`, `mail_password`, `mail_port`, `mail_tls`, `mail_ssl`, `mail_timeout` and `mail_server` from `config.py`. Keep `mail_from` and `mail_from_name`, which SendGrid uses. Set `extra="ignore"` on the settings model so stale variables in any environment, including production, never crash startup.
3. **One JWT library.** `python-jose` and `PyJWT` are both used; consolidate on PyJWT, including the exception types in `auth.py` and its tests, and drop `python-jose` from `requirements.txt`.
4. **The database shim.** `backend/app/database.py` only re-exports `Base`, `engine`, `SessionLocal` and `get_db`. Point every remaining importer at `app.db.base` and `app.db.session` and delete it.
5. **Dependencies.** Move `pytest`, `pytest-asyncio` and `httpx` from `requirements.txt` to `requirements-dev.txt`. Check whether `requests`, `python-dotenv` and `python-dateutil` are imported anywhere; drop what is not, and say what you dropped. Uninstall nothing from `backend/venv`; a fresh install from the two files must still work, so verify with a scratch virtualenv.
6. **Stale files.** Rewrite `backend/.env.example` to the settings that exist now, grouped and commented in one line each, with no real values. Delete `backend/alembic/README`. Rename the tracked `backend/uploads/placeholder` to `.gitkeep` if that is what keeps the directory, otherwise remove it.

## Rules

- Response shapes and status codes of existing routes do not change; the suite proves it.
- Tests never reach the network; the fake LLM client is the only model in tests.
- `cd backend && venv/bin/ruff check && venv/bin/ruff format --check && venv/bin/pytest -p no:cacheprovider` must pass at the end, with coverage not below the current 89%.
- `PYTHONPATH=. venv/bin/python -c "import app.main"` after every substantive change.
- The dev server is stopped; do not start it, and do not touch any database other than the test database the suite manages.
- Do not run git commands that change tree or branch state.

## Report

Use the format in `.agents/README.md`, plus the before and after of `requirements.txt`, the new prompts, and the scratch-virtualenv install result.
