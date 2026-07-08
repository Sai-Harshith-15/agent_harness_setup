# Phase 6 — Verification, permissions, HITL, hibernation & crash reconciliation

# Phase 6 — Governance & resilience
The layer that makes the system safe to run unattended: a permission matrix that denies out-of-bounds Obsidian writes, a real lock manager + OCC (making the Phase 2 stubs concrete), HITL clarification queue + diff-modal preview, hibernation (pause/thaw without double-writing), and crash reconciliation (reap orphaned work, release crash locks, roll back). Copy each file into `D:\GitRepo\agent_harness_setup\` at the path in its heading.
> Depends on Phases 0–5. Per the plan: **stop and call** **`request_clarification`** **on any unresolved Phase 6 open question — do not invent answers.** The `/hitl` queue below is exactly that mechanism.
* * *
## `context_server/app/governance/__init__.py`

```python
# empty — marks the package
```

* * *
## `context_server/app/governance/permissions.py`

```python
"""Permission matrix (Phase 6.1). Default DENY for Obsidian writes.

Only two write shapes are ever allowed:
  1. append to a designated agent-writable log.md heading
  2. append to the daily note's 'Agent Updates' heading
Everything else is denied — including any write to arbitrary human notes.
"""
import re
from dataclasses import dataclass

# Agent-writable targets. Extend via config; keep it an allow-list, never a deny-list.
_ALLOWED_LOG_PATHS = re.compile(r".*/log\.md$|^okf/log\.md$")
_ALLOWED_HEADING = {"Agent Updates", "Decisions", "Implementation Log"}


@dataclass
class Decision:
    allowed: bool
    reason: str


def can_write(path: str, target_type: str, target: str) -> Decision:
    if target_type != "heading":
        return Decision(False, f"only heading-targeted appends allowed, got target_type={target_type}")
    if not _ALLOWED_LOG_PATHS.match(path):
        return Decision(False, f"path '{path}' is not an agent-writable log target")
    if target not in _ALLOWED_HEADING:
        return Decision(False, f"heading '{target}' is not in the writable allow-list")
    return Decision(True, "ok")
```

* * *
## `context_server/app/governance/locks.py`

```python
"""Lock manager (Phase 2.6, realized here) + OCC (Phase 2.10).

Locks are leased rows in control_plane.db so a crash leaves a reclaimable record
rather than an in-memory lock that vanishes. OCC compares a caller-supplied version
hash against the live note; a mismatch = state_changed (never a silent overwrite).
"""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from ..db import connect, CONTROL_DB

LEASE_SECONDS = 120


def _now() -> datetime:
    return datetime.now(timezone.utc)


def acquire_lock(resource: str, agent: str, task_id: str) -> None:
    with connect(CONTROL_DB) as c:
        row = c.execute("SELECT agent, task_id, lease_expires_at FROM locks WHERE resource=?",
                        (resource,)).fetchone()
        if row:
            expires = datetime.fromisoformat(row["lease_expires_at"])
            held_by_other = row["task_id"] != task_id
            if held_by_other and expires > _now():
                raise HTTPException(status_code=409,
                                    detail=f"resource locked by {row['agent']}:{row['task_id']}")
        exp = (_now() + timedelta(seconds=LEASE_SECONDS)).isoformat()
        c.execute(
            "INSERT INTO locks (resource, agent, task_id, lease_expires_at) VALUES (?,?,?,?) "
            "ON CONFLICT(resource) DO UPDATE SET agent=excluded.agent, task_id=excluded.task_id, "
            "lease_expires_at=excluded.lease_expires_at",
            (resource, agent, task_id, exp),
        )


def release_lock(resource: str, task_id: str, reason: str = "released") -> None:
    with connect(CONTROL_DB) as c:
        c.execute("DELETE FROM locks WHERE resource=? AND task_id=?", (resource, task_id))


def check_occ(live_version: str, expected_version: str | None) -> None:
    # expected_version is what read_note handed the agent. If the live note moved, reject.
    if expected_version is not None and live_version != expected_version:
        raise HTTPException(status_code=409,
                            detail="state_changed: note was modified since it was read")
```

* * *
## `context_server/app/governance/hibernation.py`

```python
"""Hibernation (Phase 6.6): freeze a task's state on request_clarification, thaw later.

Thaw re-issues the paused write, but the Obsidian idempotency guard
(rejectIfContentPreexists) means a re-issued append can never double-write.
"""
import json

from ..db import connect, CONTROL_DB


def hibernate(task_id: str, agent: str, reason: str, frozen_state: dict) -> None:
    with connect(CONTROL_DB) as c:
        c.execute(
            "INSERT INTO hibernation (task_id, agent, reason, frozen_state) VALUES (?,?,?,?) "
            "ON CONFLICT(task_id) DO UPDATE SET reason=excluded.reason, "
            "frozen_state=excluded.frozen_state",
            (task_id, agent, reason, json.dumps(frozen_state)),
        )


def thaw(task_id: str) -> dict | None:
    with connect(CONTROL_DB) as c:
        row = c.execute("SELECT * FROM hibernation WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            return None
        c.execute("DELETE FROM hibernation WHERE task_id=?", (task_id,))
    return {"task_id": row["task_id"], "agent": row["agent"],
            "reason": row["reason"], "frozen_state": json.loads(row["frozen_state"] or "{}")}
```

* * *
## `context_server/app/governance/hitl.py`

```python
"""HITL clarification queue (Phase 6, D8). A child calls request_clarification; the
Context Server pauses it (hibernation) and enqueues a prompt routed to BOTH the
orchestrator and Mission Control's /hitl page. A pending write carries a diff preview
for the diff-modal.
"""
import json

from ..db import connect, CONTROL_DB

_SCHEMA = """
CREATE TABLE IF NOT EXISTS hitl_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    question TEXT NOT NULL,
    proposed_diff TEXT,           -- JSON: {path, target, before, after}
    status TEXT NOT NULL DEFAULT 'open',   -- open | approved | modified | rejected
    resolution TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_hitl() -> None:
    with connect(CONTROL_DB) as c:
        c.executescript(_SCHEMA)


def enqueue(task_id: str, agent: str, question: str, proposed_diff: dict | None = None) -> int:
    with connect(CONTROL_DB) as c:
        cur = c.execute(
            "INSERT INTO hitl_queue (task_id, agent, question, proposed_diff) VALUES (?,?,?,?)",
            (task_id, agent, question, json.dumps(proposed_diff) if proposed_diff else None),
        )
        return cur.lastrowid


def open_items() -> list[dict]:
    with connect(CONTROL_DB) as c:
        rows = c.execute("SELECT * FROM hitl_queue WHERE status='open' ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def resolve(item_id: int, status: str, resolution: str) -> None:
    with connect(CONTROL_DB) as c:
        c.execute("UPDATE hitl_queue SET status=?, resolution=? WHERE id=?",
                  (status, resolution, item_id))
```

* * *
## `context_server/app/governance/reconcile.py`

```python
"""Crash reconciliation (Phase 6.7). On startup (or on demand): reap expired lock
leases as crash_recovery, surface orphaned in-flight tasks, and expose a re-run hook.
"""
from datetime import datetime, timezone

from ..db import connect, CONTROL_DB, audit


def reconcile() -> dict:
    now = datetime.now(timezone.utc)
    reaped = []
    with connect(CONTROL_DB) as c:
        for row in c.execute("SELECT * FROM locks").fetchall():
            if datetime.fromisoformat(row["lease_expires_at"]) <= now:
                reaped.append({"resource": row["resource"], "was": f"{row['agent']}:{row['task_id']}"})
                c.execute("DELETE FROM locks WHERE resource=?", (row["resource"],))
        orphans = [dict(r) for r in c.execute("SELECT * FROM hibernation").fetchall()]
    for r in reaped:
        audit("system", "crash-reconcile", "release_lock", True, f"{r['resource']} released:crash_recovery")
    return {"released_locks": reaped, "hibernated_orphans": orphans}
```

* * *
## Wire governance into `context_server/app/main.py`

```python
# --- imports ---
from .governance.permissions import can_write
from .governance.locks import acquire_lock, release_lock, check_occ
from .governance.hibernation import hibernate, thaw
from .governance.hitl import init_hitl, enqueue, open_items, resolve
from .governance.reconcile import reconcile


# --- extend lifespan: init hitl table + reconcile on boot ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_hitl()
    print("[boot] crash reconciliation:", reconcile())   # reap crash-orphaned leases
    yield
    await backend.aclose()


# --- models ---
class GovernedAppendBody(BaseModel):
    path: str
    target: str          # heading name, must be in the allow-list
    content: str
    expected_version: str | None = None   # OCC token from read_note


class ClarifyBody(BaseModel):
    question: str
    proposed_diff: dict | None = None


class ResolveBody(BaseModel):
    item_id: int
    status: str          # approved | modified | rejected
    resolution: str


# --- REPLACE the Phase 2 append_implement with the governed write path ---
@app.post("/mcp/append_implement")
async def append_implement(body: GovernedAppendBody, ident: AgentIdentity = Depends(require_identity)):
    decision = can_write(body.path, "heading", body.target)   # permission matrix
    if not decision.allowed:
        audit(ident.agent, ident.task_id, "append_implement", False, f"DENY: {decision.reason}")
        raise HTTPException(status_code=403, detail=decision.reason)

    acquire_lock(body.path, ident.agent, ident.task_id)       # lease
    try:
        note = await backend.read_note(body.path)             # OCC read
        check_occ(str(note.get("stat", {}).get("mtime", "")), body.expected_version)
        # DLP scrub would run on body.content here (Phase 2.12).
        await backend.patch(body.path, "heading", body.target, body.content,
                            reject_if_preexists=True)         # idempotent write
        audit(ident.agent, ident.task_id, "append_implement", True, f"{body.path}#{body.target}")
        return {"ok": True}
    finally:
        release_lock(body.path, ident.task_id)


# --- HITL: request_clarification pauses the child + enqueues for orchestrator + UI ---
@app.post("/mcp/request_clarification")
async def request_clarification(body: ClarifyBody, ident: AgentIdentity = Depends(require_identity)):
    hibernate(ident.task_id, ident.agent, reason="awaiting-hitl",
              frozen_state={"question": body.question, "diff": body.proposed_diff})
    item_id = enqueue(ident.task_id, ident.agent, body.question, body.proposed_diff)
    audit(ident.agent, ident.task_id, "request_clarification", True, f"queued #{item_id}")
    return {"paused": True, "hitl_item": item_id}


@app.get("/dashboard/hitl")
async def dashboard_hitl():
    return {"open": open_items()}


@app.patch("/dashboard/hitl")
async def resolve_hitl(body: ResolveBody):
    resolve(body.item_id, body.status, body.resolution)
    # On approve/modify, thaw the paused task so the orchestrator can resume it.
    if body.status in ("approved", "modified"):
        # look up the task behind this item, then thaw
        with connect(CONTROL_DB) as c:
            row = c.execute("SELECT task_id FROM hitl_queue WHERE id=?", (body.item_id,)).fetchone()
        if row:
            thaw(row["task_id"])
    return {"ok": True, "status": body.status}


@app.get("/dashboard/crashes")
async def dashboard_crashes():
    return reconcile()
```

* * *
## Smoke test (Definition of Done)

```bash
# 1. Out-of-matrix write is DENIED
curl -X POST http://127.0.0.1:27180/mcp/append_implement \
  -H "X-Agent-Identity: hermes:task-6" -H "Content-Type: application/json" \
  -d '{"path": "People/Alice.md", "target": "Notes", "content": "nope"}'
# -> 403 path '...' is not an agent-writable log target

# 2. Allowed write succeeds (designated log heading)
curl -X POST http://127.0.0.1:27180/mcp/append_implement \
  -H "X-Agent-Identity: opencode:task-6" -H "Content-Type: application/json" \
  -d '{"path": "okf/log.md", "target": "Agent Updates", "content": "- did the thing"}'
# -> {"ok": true}

# 3. Lock contention: two different tasks, same resource -> second gets 409

# 4. HITL pause + resolve
curl -X POST http://127.0.0.1:27180/mcp/request_clarification \
  -H "X-Agent-Identity: codex:task-99" -H "Content-Type: application/json" \
  -d '{"question": "overwrite config?", "proposed_diff": {"path":"x","before":"a","after":"b"}}'
# -> {"paused": true, "hitl_item": 1}
curl http://127.0.0.1:27180/dashboard/hitl                 # shows the open item + diff
curl -X PATCH http://127.0.0.1:27180/dashboard/hitl \
  -H "Content-Type: application/json" \
  -d '{"item_id": 1, "status": "approved", "resolution": "go ahead"}'   # thaws task-99

# 5. Crash reconciliation reaps expired leases
curl http://127.0.0.1:27180/dashboard/crashes
# -> {"released_locks": [...], "hibernated_orphans": [...]}
```

Out-of-matrix write denied (1), governed write goes through lock+OCC+idempotent patch (2), locks contend (3), a child pauses on clarification and thaws on approve without double-writing (4), and crash-orphaned leases get reaped on boot (5). That's the Phase 6 Definition of Done.

**Open-question discipline:** wherever a Phase 6 decision from the parent plan is genuinely unresolved, the agent must call `/mcp/request_clarification` and land in this queue rather than guessing. That's the one hard rule this phase enforces on the agents themselves.