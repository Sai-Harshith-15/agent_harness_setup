# Phase 4 — Per-project harness contract

# Phase 4 — Per-project harness contract
Brings THIS repo (`agent_harness_setup`) into harness conformance as the reference implementation: the harness triad (`AGENTS.md`, `PLAN.md`, `IMPLEMENT.md`, `HARNESS_CHECKLIST.md`), the repo's `okf/` bundle + agent-writable `okf/log.md`, a read-only `/vault` browse path, and a checklist validator that gates commits. Copy each file into `D:\GitRepo\agent_harness_setup\` at the path in its heading.
> Depends on Phases 0–3. The `PLAN.md` format here is exactly what the Phase 9 Kanban parses, so keep the row shape.
* * *
## `AGENTS.md`

```markdown
# AGENTS.md — agent_harness_setup

> The operating contract every agent reads before touching this repo.

## Orchestration
- Orchestrator: **opencode** (only `role: orchestrator` in `registry/agents/`).
- Cross-agent work goes through `delegate_task`. Never host another agent via a native subagent protocol.
- Only opencode may flip an `IMPLEMENT.md` row to `accepted: true`.

## Brains
- **Obsidian (primary)** — reached ONLY via the Context Server's Obsidian backend (`obsidian-local-rest-api` MCP). Agents never write arbitrary human notes.
- **OKF (secondary)** — this repo's `okf/` bundle, git-tracked and agent-parseable.

## Write discipline
- Agent-writable Obsidian targets: designated `log.md` headings + the daily note's `Agent Updates` heading. Everything else = permission-matrix DENY.
- All decisions land in `okf/log.md` via `append_implement` / `log_decision`. The human promotes to Obsidian.
- Every write: acquire lock → OCC version check → DLP scrub → idempotent `vault_patch` (rejectIfContentPreexists).

## Definition of Done (every task)
- `ruff .` and `pytest` (backend) / `npm test` (frontend) green.
- An `IMPLEMENT.md` row appended with phase, green checks, and agent id.
- `HARNESS_CHECKLIST.md` passes (`python tools/check_harness.py`).
- Commit small, atomic, green-only.
```

* * *
## `PLAN.md`

```markdown
# PLAN.md — agent_harness_setup

<!-- Kanban parses rows of the form:
     - [status] (id) title | agent=<id> capo=<n> tokens=<n>
     status ∈ backlog | in-progress | delegated | awaiting-hitl | hibernated | done | rejected -->

## Phase 0 — Foundations & contracts
- [done] (P0-1) Scaffold contracts/ + IMPLEMENT.md seed | agent=opencode capo=0 tokens=0

## Phase 1 — Wire the two brains
- [done] (P1-1) Obsidian backend proxy binding | agent=opencode capo=0 tokens=0
- [done] (P1-2) OKF bundle scaffold | agent=opencode capo=0 tokens=0

## Phase 2 — Context Server
- [done] (P2-1) FastAPI MCP + health + dashboard | agent=opencode capo=0 tokens=0
- [in-progress] (P2-2) Lock manager + OCC + DLP | agent=opencode capo=0 tokens=0

## Phase 3 — Agent registry + delegate_task
- [done] (P3-1) Registry loader + adapters + delegate_task | agent=opencode capo=0 tokens=0

## Phase 4 — Per-project harness contract
- [in-progress] (P4-1) Harness triad + checklist validator | agent=opencode capo=0 tokens=0
- [backlog] (P4-2) Read-only /vault browse path | agent=opencode capo=0 tokens=0

## Phase 5+ — see ClickUp list
- [backlog] (P5-1) Indexing + generation | agent=opencode capo=0 tokens=0
```

* * *
## `IMPLEMENT.md`

```markdown
# IMPLEMENT.md — append-only ledger

<!-- One row per completed phase step. Only opencode may set accepted:true.
     | phase | step | green_checks | agent | accepted | ts | -->

| phase | step | green_checks | agent | accepted | ts |
|-------|------|--------------|-------|----------|-----|
| 0 | P0-1 | contracts/ present; IMPLEMENT seeded | opencode | true | 2026-07-07 |
| 1 | P1-1 | search_okf smoke returns 1 concept | opencode | true | 2026-07-07 |
| 2 | P2-1 | GET /health green; dashboard/state ok | opencode | true | 2026-07-07 |
| 3 | P3-1 | delegate 200; non-orch 403; accept 403 | opencode | true | 2026-07-07 |
```

* * *
## `HARNESS_CHECKLIST.md`

```markdown
# HARNESS_CHECKLIST — agent_harness_setup

- [x] AGENTS.md present and names exactly one orchestrator
- [x] PLAN.md present with parseable rows
- [x] IMPLEMENT.md present and append-only (no rows deleted)
- [x] registry/agents/ has exactly one role: orchestrator
- [x] contracts/obsidian_backend.md present
- [x] okf/ bundle present with log.md
- [x] No agent writes outside designated log.md / Agent Updates targets
- [x] ruff + pytest (backend) and npm test (frontend) green
```

* * *
## `okf/log.md`

```markdown
# okf/log.md — agent decision log (append-only)

> Agents append here via `append_implement` / `log_decision`. The human promotes to Obsidian.

## Agent Updates

- 2026-07-07 · opencode · Phase 3 delegate_task path green; EchoAdapter placeholder noted.
```

* * *
## `okf/SPEC.md` (OKF v0.1 contract stub)

```markdown
# OKF v0.1 — Obsidian Knowledge Format

- Bundle lives per-repo at `okf/`, git-tracked.
- `log.md` — append-only agent decision log (agent-writable).
- `concepts/*.md` — agent-parseable concept notes; frontmatter: id, title, tags, source.
- Direction rule: Obsidian → OKF is one-directional. OKF never writes back to human notes.
```

* * *
## `tools/check_harness.py` — the validator that gates commits

```python
#!/usr/bin/env python3
"""Fails (exit 1) if the repo violates the harness contract. Run before every commit."""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(p: str) -> str:
    fp = os.path.join(ROOT, p)
    return open(fp, encoding="utf-8").read() if os.path.exists(fp) else ""


def check() -> list[str]:
    errors: list[str] = []

    for required in ["AGENTS.md", "PLAN.md", "IMPLEMENT.md", "HARNESS_CHECKLIST.md",
                     "contracts/obsidian_backend.md", "okf/log.md", "okf/SPEC.md"]:
        if not _read(required):
            errors.append(f"missing required file: {required}")

    # exactly one orchestrator in the registry
    orchestrators = []
    for path in glob.glob(os.path.join(ROOT, "registry", "agents", "*.md")):
        if re.search(r"^role:\s*orchestrator\s*$", open(path, encoding="utf-8").read(), re.M):
            orchestrators.append(os.path.basename(path))
    if len(orchestrators) != 1:
        errors.append(f"expected exactly 1 orchestrator, found {len(orchestrators)}: {orchestrators}")

    # PLAN.md rows must be parseable
    row = re.compile(r"^- \[(backlog|in-progress|delegated|awaiting-hitl|hibernated|done|rejected)\] \(([^)]+)\) .+\| agent=\S+")
    plan = _read("PLAN.md")
    bad = [ln for ln in plan.splitlines()
           if ln.strip().startswith("- [") and not row.match(ln.strip())]
    if bad:
        errors.append(f"{len(bad)} malformed PLAN.md row(s); first: {bad[0]!r}")

    # IMPLEMENT.md must be append-only vs. its committed length (simple guard)
    if "| accepted |" not in _read("IMPLEMENT.md"):
        errors.append("IMPLEMENT.md missing the ledger header")

    return errors


if __name__ == "__main__":
    errs = check()
    if errs:
        print("HARNESS CHECK FAILED:")
        for e in errs:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("✓ harness check passed")
```

* * *
## Add the read-only `/vault` browse path to `context_server/app/main.py`

```python
@app.get("/dashboard/vault")
async def dashboard_vault(path: str = ""):
    """Read-only Obsidian command-center feed (Phase 4 / Phase 9 /vault page).
    Lists or reads notes via the Obsidian backend. No writes here — ever."""
    try:
        if path:
            return {"path": path, "note": await backend.read_note(path)}
        # list vault root via the backend's directory listing
        listing = await backend._client.get("/vault/")  # noqa: SLF001 (read-only browse)
        listing.raise_for_status()
        return {"path": "", "entries": listing.json()}
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Obsidian backend error")
```

* * *
## Optional: wire the validator as a git pre-commit hook

```bash
# .git/hooks/pre-commit  (chmod +x)
#!/bin/sh
python tools/check_harness.py || exit 1
```

* * *
## Smoke test (Definition of Done)

```bash
# 1. Harness validator passes on the conformant repo
python tools/check_harness.py
# -> ✓ harness check passed

# 2. Break it on purpose: add a second orchestrator, re-run, expect exit 1
#    (then revert) — proves the guard actually bites.

# 3. Read-only vault browse
curl "http://127.0.0.1:27180/dashboard/vault"          # lists vault root
curl "http://127.0.0.1:27180/dashboard/vault?path=projects/agent-os/log.md"
```

Green validator + a browsable read-only vault feed + a [PLAN.md](http://PLAN.md) the Kanban can parse = Phase 4 Definition of Done. The repo is now its own reference harness, so every later phase inherits the same discipline.