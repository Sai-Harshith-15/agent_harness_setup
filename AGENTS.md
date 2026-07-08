# AGENTS.md — agent_harness_setup

> The operating contract every agent reads before touching this repo.

## Project overview

Agentic OS reference harness. A FastAPI **Context Server** (port 27180) that wraps the
`obsidian-local-rest-api` MCP, holds the secrets bridge + transport identity + two SQLite
stores (token ledger and control plane), and exposes `/health`, `/mcp/*`, and `/dashboard/*`.
A Next.js **Mission Control** shell (port 3000) provides the human-facing dashboard.
The project is built in numbered phases (0–9) documented under `project phases/`.

## Orchestration

- Orchestrator: **opencode** (only `role: orchestrator` in `registry/agents/`).
- Cross-agent work goes through `delegate_task`. Never host another agent via a native subagent protocol.
- Only opencode may flip an `IMPLEMENT.md` row to `accepted: true`.

## Brains

- **Obsidian (primary)** — reached ONLY via the Context Server's Obsidian backend (`obsidian-local-rest-api` MCP). Agents never write arbitrary human notes.
- **OKF (secondary)** — this repo's `okf/` bundle, git-tracked and agent-parseable.

## Repository structure

```
context_server/     # FastAPI backend (app/, tests/)
frontend/           # Next.js Mission Control shell
registry/           # Agent registry (agents/*.md) and adapter contracts
contracts/          # Stable interface contracts (obsidian_backend.md, orchestration.md, …)
okf/                # OKF bundle: log.md (append-only), SPEC.md, concepts/
scripts/            # Utility and smoke-test scripts
tools/              # Repo-level tooling (check_harness.py, …)
project phases/     # Phase spec documents (Phase 0–9)
hooks/              # SQLite stores written here at runtime
```

## Write discipline

- Agent-writable Obsidian targets: designated `log.md` headings + the daily note's `Agent Updates` heading. Everything else = permission-matrix DENY.
- All decisions land in `okf/log.md` via `append_implement` / `log_decision`. The human promotes to Obsidian.
- Every write: acquire lock → OCC version check → DLP scrub → idempotent `vault_patch` (rejectIfContentPreexists).

## Conventions

### Code style

- Python: `ruff` for lint/format. Follow PEP 8.
- TypeScript/React: ESLint + Prettier (via `npm run lint`).
- No bare `except:` — always catch specific exceptions or use `except Exception`.

### Naming

- Python modules: `snake_case`. Classes: `PascalCase`. Constants: `UPPER_SNAKE`.
- Registry agents: lowercase id matching the filename (`hermes.md` → `id: hermes`).

### Testing

```bash
# Backend — run from repo root
python -m pytest context_server/tests/ -v

# Frontend
cd frontend && npm test
```

### Commits

- Atomic, green-only commits. Message: `phase-N: <short description>`.
- Never push to `main` without all tests passing.

## Tool permissions

Allowed:
- Read and edit files under `context_server/`, `frontend/`, `registry/`, `contracts/`, `okf/`, `scripts/`, `tools/`
- Run `python -m pytest`, `ruff .`, `npm test`, `npm run lint`
- Run `python tools/check_harness.py`
- Read `project phases/` documents

Restricted (ask before proceeding):
- Modifying `context_server/.env` or `.env.example`
- Running destructive commands (`rm -rf`, database drops, etc.)
- Pushing to `main` or creating releases
- Installing new Python/npm packages

Not allowed:
- Modifying CI/CD pipeline configuration without explicit instruction
- Writing to human Obsidian notes outside the designated `Agent Updates` heading

## Known constraints

- Obsidian backend is optional for tests; `ALLOW_HTTP_FALLBACK=true` means tests pass without a live Obsidian instance (health returns `degraded`, not a 5xx).
- SQLite stores live under `hooks/` at runtime (gitignored).
- `registry.py` re-reads disk on every call — acceptable at Phase 3 scale; cache in Phase 5+.

## Definition of Done (every task)

- `ruff .` and `pytest` (backend) / `npm test` (frontend) green.
- An `IMPLEMENT.md` row appended with phase, green checks, and agent id.
- `HARNESS_CHECKLIST.md` passes (`python tools/check_harness.py`).
- Commit small, atomic, green-only.

## Verification gates

Before marking any task complete, the agent must verify:

- [ ] Tests pass (`python -m pytest context_server/tests/ -v`)
- [ ] Linter passes (`ruff .`)
- [ ] `python tools/check_harness.py` exits 0
- [ ] No new warnings introduced
- [ ] Changed files are within the permitted scope above

## Contact / escalation

If the agent cannot proceed without a decision that falls outside its permitted scope, it should stop and describe the blocker clearly rather than making an assumption.
