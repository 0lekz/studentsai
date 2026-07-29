# StudentsAI v2 - Refactor and Direction Roadmap

Status: planning.
Owner: Oleksii Zhukov.
Created: 2026-07-28.

## Why this document exists

The v1 build ran from 2025-08-07 to 2025-09-25 under a ship-fast mandate and then went dormant for ten months.
That mandate produced a working, deployed product with real users, and it also produced a 3,098-line `main.py`, an empty test directory, and no CI.
v2 is not a rewrite.
The existing system is the asset, and the goal is to bring it to a standard where it can be maintained without fear.

Two things change in v2 beyond code quality:

- The product direction narrows from "AI study assistant" to **PDF and lecture-deck ingestion**.
Students already have course material as slide decks and PDFs, and they do not have it as notes typed into a new app.
Ingestion removes the cold-start problem, sidesteps competing with Notion and Google Docs for where notes live, and creates the corpus that the retrieval work needs.

- The AI layer moves from API calls to actual ML engineering.
TF-IDF similarity becomes embedding-based retrieval with a measured baseline comparison, and generation quality becomes something that is evaluated in CI rather than eyeballed.

## Guiding constraints

This is a secondary project competing with school and a primary codebase.
Every phase must leave the repository in a coherent, shippable state.

A half-finished router migration living on `main` is worse than the current monolith, because a consistent monolith is a defensible engineering choice under time pressure and a stalled refactor is not.
Each phase below is sized so that stopping after it is a valid ending.

The application has real users and stores their notes behind authentication.
Data-destructive migrations and auth regressions are the two failure modes that actually matter, and both are covered by the phase ordering.

## Target backend architecture

Current state is three large modules doing everything: `main.py` holds 70 route handlers, `database.py` holds both SQLAlchemy models and roughly 60 query functions, and `ai_service.py` holds both TF-IDF similarity and OpenAI calls.

Target layout, something like this. Actual architecture drawing and shema later:

```
backend/app/
  main.py              # app factory, middleware, router registration only
  config.py
  dependencies.py      # shared FastAPI dependencies: get_db, get_current_user, rate limits
  db/
    session.py         # engine, SessionLocal, get_db
  models/              # SQLAlchemy ORM declarations only
    user.py
    note.py
    flashcard.py
    srs.py
    event.py
    document.py        # phase 3
  schemas/             # Pydantic request/response models, split from the 556-line schemas.py
  repositories/        # query functions, grouped by domain - this is database.py split up
  services/            # business logic composing repositories and external calls
    auth_service.py
    note_service.py
    flashcard_service.py
    embedding_service.py    # phase 2
    retrieval_service.py    # phase 4
    ingestion_service.py    # phase 3
  api/                 # thin route handlers, one router per domain
    health.py
    auth.py
    notes.py
    ai.py
    flashcards.py
    srs.py
    graph.py
    profile.py
    settings.py
    uploads.py
    documents.py       # phase 3
```

The layering exists to create test seams, not for its own sake.
Services are testable without HTTP, repositories are testable without business logic, and route handlers become thin enough that most of them need only a smoke test.

If a layer is not earning its place during phase 1, collapse it rather than filling it with pass-through functions.

### Route grouping

The 70 handlers map onto routers as follows, taken from the current `main.py`:

| Router | Routes | Notes |
|---|---|---|
| `health` | 3 | `/test/email-config` is unauthenticated and discloses SMTP config - see below |
| `auth` | 16 | Register, login, refresh, Google OAuth, email verification, email change, password reset, account deletion |
| `notes` | 9 | CRUD, tags, links, backlinks |
| `ai` | 5 | Summarize, flashcard generation, keyword extraction |
| `flashcards` | 14 | CRUD, sets, tags, generation |
| `srs` | included above | `/flashcards/due`, `/flashcards/due/srs`, `/flashcards/{id}/review`, `/flashcards/archive/mastered` |
| `graph` | 1 | |
| `profile` | 5 | Summary, activity, recent, export, aggregate |
| `settings` | 14 | Profile, appearance, graph, AI, studyflow, advanced, username check |
| `uploads` | 1 | |
| `events` | 1 | |

Two inconsistencies to resolve during phase 1.

Prefixes are mixed: `/notes` and `/flashcards` are unprefixed while `/api/profile` and `/api/settings` are prefixed.
Standardizing on `/api/v1` is correct but is a breaking change for the deployed frontend, so it must ship as an additive alias with the old paths retained and deprecated, not as a rename.

Route registration order currently matters in ways that are easy to break.
Literal paths such as `/flashcards/sets` and `/flashcards/due/srs` are declared several hundred lines after parameterized `/flashcards/{flashcard_id}/...` paths, and moving handlers between files reorders them.
This is the single most likely way to silently break production during extraction, and it is precisely what phase 0 exists to catch.

### Unauthenticated config disclosure

`GET /test/email-config` at `main.py:299` has no authentication dependency and returns `mail_username`, `mail_from`, `mail_server`, `mail_port`, `frontend_url`, and the TLS/SSL flags to any caller.
The password itself is only exposed as a boolean, so this is information disclosure rather than credential leakage, but it hands out the SMTP account address and mail infrastructure details for free.

By contrast `POST /test/email` is authenticated via `get_current_user_id`, rate limited, and only sends to the caller's own address, so it is fine as-is aside from not belonging in production.

Fix this in phase 0 rather than waiting for phase 1, since it is a two-line change and the app is live.
Delete the endpoint or gate it behind `DEBUG`.

## Target frontend architecture

Lower priority than the backend, and independent of it, so it can proceed in parallel or later.

Current problems: `NotesGraph.tsx` is 763 lines, `ProfileSettings.tsx` is 711, `FlashcardDashboard.tsx` is 613, and four dead files are still tracked (`page_old.tsx`, `NoteEditor.old.tsx`, `label-old.tsx`, `select-old.tsx`).
There is no type-check or lint gate in CI, and `api.ts` at 624 lines is a single untyped-at-the-boundary client.

Target: dead files deleted, the three oversized components decomposed into presentational plus container pieces, and the API client generated or at least typed from the backend OpenAPI schema so that backend changes surface as frontend type errors.

## Phases

### Phase 0 - Test foundation and CI

This is the prerequisite for everything else and it is the phase most directly aligned with the pytest and GitHub Actions learning goal.
No architectural changes happen here.
Tests are written against current behavior exactly as it is, bugs included, so that the refactor has a net to fall into.

Scope:

- `pytest` configuration in `backend/pyproject.toml`, replacing the currently empty `backend/tests/`.
- `conftest.py` with a transactional session fixture that rolls back per test, a `TestClient` fixture overriding `get_db`, and an authenticated-client fixture.
- Postgres for tests, not SQLite, because pgvector arrives in phase 2 and a SQLite test path would diverge from production immediately.
  Local via docker-compose, CI via the GitHub Actions `services: postgres` container.
- OpenAI calls stubbed at the service boundary in all tests.
  CI must never make a paid API call, both for cost and for flakiness.
- Characterization tests covering, in priority order: the auth flow end to end, notes CRUD and linking, flashcard generation and review, SRS scheduling arithmetic, and the graph endpoint.
- `ruff` for backend lint and format, replacing the manual formatting visible in the commit history.
- GitHub Actions workflow: backend lint plus tests with coverage, frontend `eslint` plus `tsc --noEmit` plus `next build`, running on pull requests and pushes to `main`.
- Dependabot enabled.
  `python-jose`, `passlib`, and `fastapi` are roughly two years stale and sit directly under authentication.
- Delete the four dead frontend files.

Exit criteria: CI green on a pull request, and the SRS and auth paths covered well enough that a deliberate injected bug in either is caught.

Coverage policy: do not set an absolute threshold.
Record whatever phase 0 achieves and enforce no-decrease from there.

### Phase 1 - Backend decomposition

One pull request per domain, each one green and mergeable on its own.
Order matters: start with the domains that have the least coupling and the best test coverage from phase 0.

Suggested order: `health`, `graph`, `uploads`, `events`, `profile`, `settings`, `notes`, `flashcards`, `srs`, `ai`, `auth`.
Auth is last because it is the highest-risk surface and benefits from the pattern being settled by then.

Within each domain: extract the router, split the ORM model out of `database.py`, split the query functions into the matching repository, and lift business logic into a service.
Do not change behavior in the same pull request as a move.

The `/api/v1` prefix alias ships at the end of this phase as an additive change.

Exit criteria: `main.py` under roughly 150 lines and doing only app construction, `database.py` gone, and CI still green.

### Phase 2 - Embeddings, and the first real ML artifact

Replace TF-IDF cosine similarity at `ai_service.py:198` with embedding-based similarity.

TF-IDF fails on synonymy, which is the common case in course material: "neural nets" and "deep learning" will not connect, and neither will "mitosis" and "cell division."
This is a genuine quality problem.

Approach:

- pgvector extension on the existing Postgres, so no new infrastructure.
- A local sentence-transformer in the small, CPU-viable class such as `all-MiniLM-L6-v2` or `bge-small-en`.
  Running a model rather than calling an API is the point, and it also removes per-note API cost.
- Backfill migration for existing users' notes, written to be resumable.
- Keep the TF-IDF implementation behind a flag rather than deleting it, because it is the baseline.

The focus that hopes to carry portfolio weight is not the feature, it is the evaluation.
Build a small hand-labeled set of note pairs from real corpus data, and report precision@k and recall@k for TF-IDF versus embeddings in the README.
A table showing a measured improvement over a baseline I build myself is worth more than three shipped features.

Exit criteria: embeddings serving graph connections in production, benchmark committed under `backend/tests/eval/`, results in the README.

### Phase 3 - Document ingestion, the product direction

The pitch becomes: drop a semester of lecture PDFs and slide decks, get back an organized, searchable, quizzable knowledge base.

Two sub-parts, and they are separable.

**Extraction.**
PyMuPDF for text and layout, with slide decks and lecture PDFs as the two target shapes.
Preserve heading structure where it exists, because it feeds both chunking and organization.
Store the source document as a first-class entity so notes generated from it retain provenance.

**Auto-organization.**
This is the feature described as: given ten PDFs, propose that files one and two are Lecture 1-2, three is Biology, and four through seven are Chemistry.

It decomposes into two different problems that should not be conflated.

Topic grouping is clustering over document embeddings, using agglomerative clustering with a distance threshold or HDBSCAN.

Cluster labeling is the one place an LLM belongs: hand it representative titles and snippets from a cluster and ask for a folder name.

Present the result as a proposed folder tree that the user accepts or edits rather than one that is applied automatically.
Wrong automatic organization of someone's coursework is worse than no organization.

This also has a clean evaluation story: collect documents with known course boundaries and report clustering agreement against that ground truth.

Exit criteria: upload to organized-tree flow working end to end, clustering evaluated against a labeled set.

### Phase 4 - Retrieval and generation evaluation

With a real document corpus in place, flashcard and summary generation moves from single-note prompting to retrieval over chunks with citations back to source documents.

The higher-value half of this phase is the evaluation harness, which almost nobody builds.
Score generated flashcards on groundedness in the source, atomicity, and standalone answerability, using an LLM judge with a fixed rubric.
Run it in CI on every prompt change and track the scores over time.

Shipping LLM features without measurement is the default, and demonstrating the alternative is the strongest single differentiator available in this project.

Also in this phase: move off `gpt-3.5-turbo`, which is retired and reads as abandoned, and add per-user cost logging since free-tier users currently cost money with no visibility.

### Phase 5 - Frontend

Component decomposition, design pass, and a typed API client generated from the backend OpenAPI schema.
Independent of phases 1 through 4 and can be pulled earlier if motivation favors it.

## Working agreement

Feature branches off `main`, one pull request per unit, CI green before merge.
Not a long-lived `dev` integration branch, because accumulating a large diff reintroduces exactly the risk this plan is structured to avoid.
The existing `dev` branch is 35 commits behind `main` with nothing unique on it, and should be deleted or reset.

Behavior changes and code moves never share a pull request.

Every phase ends with the repository in a state where stopping is acceptable.

## Non-goals

Mobile application.
There are designs ready and designs are a portfolio asset as designs, and building a second platform on a project that went dormant on one is not a priority right now.

Growth features: social, sharing, gamification, streak mechanics as engagement hooks.

The engineering and ML artifacts are the deliverable, and the product direction exists to make those artifacts coherent and demonstrable rather than to capture a market and more users.
