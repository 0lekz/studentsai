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
