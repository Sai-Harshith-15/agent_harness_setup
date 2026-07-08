# Phase 8 — Meta-harness & Dream Cycle

# Phase 8 — Meta-harness & Dream Cycle
The self-improvement layer: a `Program.md` top-level ledger driving what runs next, a `meta` agent, and a nightly **Dream Cycle** that reviews trajectories, drift, and CAPO to propose harness/prompt improvements — which a human promotes. Crucially, the Dream Cycle **never mutates Obsidian directly**; it writes proposals to `okf/log.md` via the governed write path. Copy each file into `D:\GitRepo\agent_harness_setup\` at the path in its heading.
> Depends on Phases 0–7. It reads the drift feed (Phase 5), the CAPO rollups (Phase 7), and the audit log (Phase 2/6) — so nothing new needs indexing; it just synthesizes what those already produce.
* * *
## `Program.md`

```markdown
# Program.md — top-level program ledger

> Drives what the orchestrator runs next. The Dream Cycle appends proposals here for
> human review; opencode reads the top unchecked item each loop.

## Now
- [ ] (PROG-1) Replace EchoAdapter with real filesystem + HTTP agent runners (Phase 3 seam)
- [ ] (PROG-2) Swap //4 token heuristic for a real tokenizer (Phase 5 seam)

## Proposed by Dream Cycle (human promotes ↑)
<!-- meta appends here nightly; never auto-executed -->
```

* * *
## `registry/agents/meta.md`

```markdown
---
id: meta
role: delegate
adapter: http
cost_defaults: { max_turns: 12 }
capabilities: [reflect, propose_improvement, review_trajectory]
schedule: nightly            # run by the Dream Cycle loop, not by user delegation
---
# meta
The reflection agent. Reads drift + CAPO + audit trails and proposes harness/prompt
improvements. Writes proposals ONLY to okf/log.md and Program.md via append_implement.
Never edits Obsidian human notes. Never flips an IMPLEMENT row to accepted.
```

* * *
## `context_server/app/meta/__init__.py`

```python
# empty — marks the package
```

* * *
## `context_server/app/meta/dream_cycle.py`

```python
"""Dream Cycle (Phase 8): nightly self-improvement pass.

Inputs (all already produced by earlier phases):
  - drift banners       (Phase 5)  -> spec/impl divergence
  - CAPO summary/trend   (Phase 7)  -> cost efficiency signal
  - audit log            (Phase 2/6) -> failure/denial patterns

Output: a list of reviewable improvement PROPOSALS. It does NOT execute them and does
NOT touch Obsidian human notes. Proposals are appended to Program.md's 'Proposed'
section and okf/log.md via the governed write path.
"""
from datetime import date

from ..indexing.drift import detect_drift
from ..finops.rollups import capo, totals_by_task
from ..db import connect, CONTROL_DB


def _recent_denials(limit: int = 50) -> list[dict]:
    with connect(CONTROL_DB) as c:
        rows = c.execute(
            "SELECT tool, detail, COUNT(*) AS n FROM audit_log "
            "WHERE ok=0 GROUP BY tool, detail ORDER BY n DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def analyze() -> list[dict]:
    proposals: list[dict] = []

    # 1. Drift -> propose reconciling spec vs impl.
    for b in detect_drift():
        proposals.append({
            "kind": "drift",
            "proposal": f"Reconcile {b['spec']} with impl-ahead files {b.get('changed_code')}",
            "evidence": b,
        })

    # 2. CAPO regression -> propose cost review on the priciest task.
    c = capo()
    if c["capo"] and c["capo"] > 5000:   # tune threshold to your budget
        top = totals_by_task(limit=1)
        proposals.append({
            "kind": "cost",
            "proposal": f"CAPO is {c['capo']} tokens/accepted; investigate top task "
                        f"{top[0]['task_id'] if top else 'n/a'} for wasted turns",
            "evidence": c,
        })

    # 3. Repeated denials/failures -> propose a harness or prompt fix.
    for d in _recent_denials():
        if d["n"] >= 3:
            proposals.append({
                "kind": "reliability",
                "proposal": f"{d['tool']} failed {d['n']}x with '{d['detail']}' — "
                            f"add a guard or clarify the contract",
                "evidence": d,
            })

    return proposals


def render_markdown(proposals: list[dict]) -> str:
    if not proposals:
        return f"### Dream Cycle {date.today().isoformat()}
- No proposals; system nominal.
"
    lines = [f"### Dream Cycle {date.today().isoformat()}"]
    for i, p in enumerate(proposals, 1):
        lines.append(f"- [ ] ({p['kind']}-{i}) {p['proposal']}")
    return "
".join(lines) + "
"
```

* * *
## `context_server/app/meta/runner.py`

```python
"""Runs the Dream Cycle and persists proposals via the GOVERNED write path only.

Writes go to okf/log.md ('Agent Updates' heading) — the same permission-matrix-approved
target every other agent uses. Never to Obsidian human notes.
"""
from .dream_cycle import analyze, render_markdown
from ..obsidian_backend import backend
from ..governance.permissions import can_write
from ..governance.locks import acquire_lock, release_lock

OKF_LOG = "okf/log.md"
HEADING = "Agent Updates"


async def run_dream_cycle() -> dict:
    proposals = analyze()
    md = render_markdown(proposals)

    decision = can_write(OKF_LOG, "heading", HEADING)   # must pass the matrix
    if not decision.allowed:
        return {"ok": False, "reason": decision.reason}

    acquire_lock(OKF_LOG, "meta", "dream-cycle")
    try:
        # idempotent: re-running the same night won't double-append the same section.
        await backend.patch(OKF_LOG, "heading", HEADING, md, reject_if_preexists=True)
    finally:
        release_lock(OKF_LOG, "dream-cycle")

    return {"ok": True, "proposals": proposals, "written_to": OKF_LOG}
```

* * *
## Wire the Dream Cycle into `context_server/app/main.py`

```python
# --- imports ---
from .meta.runner import run_dream_cycle
from .meta.dream_cycle import analyze


@app.get("/dashboard/dream")
async def dashboard_dream():
    # Preview proposals WITHOUT writing (for the UI 'dry run' button).
    return {"proposals": analyze()}


@app.post("/mcp/run_dream_cycle")
async def run_dream_cycle_ep(ident: AgentIdentity = Depends(require_identity)):
    # Only meta or the orchestrator may trigger it.
    if ident.agent not in ("meta", "opencode"):
        raise HTTPException(status_code=403, detail="Only meta or opencode may run the Dream Cycle")
    result = await run_dream_cycle()
    audit(ident.agent, ident.task_id, "run_dream_cycle", result["ok"],
          f"{len(result.get('proposals', []))} proposals")
    return result
```

* * *
## Optional: nightly scheduler (add to lifespan in `main.py`)

```python
import asyncio
from datetime import datetime, time, timedelta

async def _dream_loop():
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(3, 0))   # 3am local — the 'dream' hour
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            print("[dream-cycle]", await run_dream_cycle())
        except Exception as e:  # noqa: BLE001
            print("[dream-cycle] failed:", e)

# in lifespan: asyncio.create_task(_dream_loop())
```

* * *
## Smoke test (Definition of Done)

```bash
# 1. Dry-run preview: proposals computed from drift + CAPO + denials, no write
curl http://127.0.0.1:27180/dashboard/dream
# -> {"proposals": [{"kind":"drift"|"cost"|"reliability", "proposal": "...", "evidence": {...}}, ...]}

# 2. Run it: proposals get written to okf/log.md via the GOVERNED path (not human notes)
curl -X POST http://127.0.0.1:27180/mcp/run_dream_cycle -H "X-Agent-Identity: meta:dream-1"
# -> {"ok": true, "proposals": [...], "written_to": "okf/log.md"}

# 3. A non-meta/non-orchestrator agent is blocked
curl -X POST http://127.0.0.1:27180/mcp/run_dream_cycle -H "X-Agent-Identity: codex:dream-1"
# -> 403 Only meta or opencode may run the Dream Cycle

# 4. Re-run same night: idempotent, no duplicate section in okf/log.md
curl -X POST http://127.0.0.1:27180/mcp/run_dream_cycle -H "X-Agent-Identity: meta:dream-1"
# -> patch rejected by rejectIfContentPreexists; log not duplicated
```

A nightly run produces reviewable proposals from real signals (1), writes them only through the governed permission-matrix path to `okf/log.md` (2), refuses unauthorized callers (3), and can't double-write (4). Human promotes the good proposals from `okf/log.md` / `Program.md` back into Obsidian and the harness. That's the Phase 8 Definition of Done, and it closes the self-improvement loop without ever letting an agent edit a human note.

One page left: **Phase 9 — the full Mission Control frontend** (Kanban, /tokens analytics, /task trajectory, /hitl, /crash, /agents, /vault) built on every `/dashboard/*` surface Phases 2–8 now expose.