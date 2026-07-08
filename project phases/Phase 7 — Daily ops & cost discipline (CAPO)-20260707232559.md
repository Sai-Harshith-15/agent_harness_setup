# Phase 7 — Daily ops & cost discipline (CAPO)

# Phase 7 — Daily ops & cost discipline (CAPO)
Operationalizes daily running and FinOps: the token ledger fully populated per (agent, tool, task), CAPO rollups (tokens-per-accepted-outcome), a daily standup appended to the periodic note's `Agent Updates` heading, and the live `/dashboard/tokens` + `/dashboard/capo` surfaces the Phase 9 analytics page consumes. Copy each file into `D:\GitRepo\agent_harness_setup\` at the path in its heading.
> Depends on Phases 0–6. The ledger table already exists (Phase 2 `token_usage.db`); this phase makes every tool call meter into it and adds the rollup views + standup writer.
* * *
## `context_server/app/finops/__init__.py`

```python
# empty — marks the package
```

* * *
## `context_server/app/finops/meter.py`

```python
"""Token metering. Every tool call records a ledger row. accepted=1 is set later,
only by the orchestrator via accept_implement (Phase 3), which is the CAPO numerator.
"""
from ..db import connect, TOKEN_DB


def record(agent: str, task_id: str, tool: str, tokens_in: int, tokens_out: int,
           accepted: bool = False) -> None:
    with connect(TOKEN_DB) as c:
        c.execute(
            "INSERT INTO token_ledger (agent, task_id, tool, tokens_in, tokens_out, accepted) "
            "VALUES (?,?,?,?,?,?)",
            (agent, task_id, tool, tokens_in, tokens_out, 1 if accepted else 0),
        )


def mark_accepted(task_id: str) -> int:
    with connect(TOKEN_DB) as c:
        cur = c.execute("UPDATE token_ledger SET accepted=1 WHERE task_id=?", (task_id,))
        return cur.rowcount
```

* * *
## `context_server/app/finops/rollups.py`

```python
"""SQL rollups for the dashboard. CAPO = total tokens / accepted outcomes.

The frontend /tokens page reads these directly.
"""
from ..db import connect, TOKEN_DB


def totals_by_task(limit: int = 20) -> list[dict]:
    sql = """
        SELECT task_id,
               SUM(tokens_in + tokens_out) AS total_tokens,
               MAX(accepted)               AS accepted
        FROM token_ledger
        GROUP BY task_id
        ORDER BY total_tokens DESC
        LIMIT ?
    """
    with connect(TOKEN_DB) as c:
        return [dict(r) for r in c.execute(sql, (limit,)).fetchall()]


def heatmap() -> list[dict]:
    # (agent x tool) token spend, for the analytics heatmap.
    sql = """
        SELECT agent, tool, SUM(tokens_in + tokens_out) AS tokens
        FROM token_ledger GROUP BY agent, tool ORDER BY tokens DESC
    """
    with connect(TOKEN_DB) as c:
        return [dict(r) for r in c.execute(sql).fetchall()]


def capo() -> dict:
    """Cost per accepted outcome. Numerator = all tokens; denominator = # accepted tasks."""
    sql = """
        SELECT
            SUM(tokens_in + tokens_out) AS total_tokens,
            COUNT(DISTINCT CASE WHEN accepted=1 THEN task_id END) AS accepted_tasks
        FROM token_ledger
    """
    with connect(TOKEN_DB) as c:
        row = dict(c.execute(sql).fetchone())
    total = row["total_tokens"] or 0
    accepted = row["accepted_tasks"] or 0
    return {
        "total_tokens": total,
        "accepted_tasks": accepted,
        "capo": round(total / accepted, 1) if accepted else None,   # None = no accepted outcome yet
    }


def capo_trend(days: int = 14) -> list[dict]:
    sql = """
        SELECT date(ts) AS day,
               SUM(tokens_in + tokens_out) AS tokens,
               COUNT(DISTINCT CASE WHEN accepted=1 THEN task_id END) AS accepted
        FROM token_ledger
        WHERE ts >= date('now', ?)
        GROUP BY day ORDER BY day
    """
    with connect(TOKEN_DB) as c:
        rows = [dict(r) for r in c.execute(sql, (f"-{days} days",)).fetchall()]
    for r in rows:
        r["capo"] = round(r["tokens"] / r["accepted"], 1) if r["accepted"] else None
    return rows
```

* * *
## `context_server/app/finops/standup.py`

```python
"""Daily standup writer (Phase 7.1). Builds a summary from the ledger + audit log and
appends it to the daily note's 'Agent Updates' heading via the Obsidian backend.

Uses the periodic-note path from the plugin, then the same governed write path as
everything else: lock + idempotent patch (rejectIfContentPreexists) so re-running the
standup twice in a day cannot double-append.
"""
from datetime import date

from .rollups import totals_by_task, capo
from ..obsidian_backend import backend
from ..governance.locks import acquire_lock, release_lock


def build_standup_markdown() -> str:
    c = capo()
    top = totals_by_task(limit=5)
    lines = [f"### Standup {date.today().isoformat()}",
             f"- CAPO: {c['capo']} tokens/accepted ({c['accepted_tasks']} accepted, "
             f"{c['total_tokens']} total tokens)",
             "- Top tasks by spend:"]
    for t in top:
        flag = "✓" if t["accepted"] else "…"
        lines.append(f"  - {flag} {t['task_id']}: {t['total_tokens']} tokens")
    return "
".join(lines) + "
"


async def post_standup() -> dict:
    # periodic_note path for today's daily note (plugin exposes this).
    resp = await backend._client.get("/periodic/daily/")   # noqa: SLF001
    resp.raise_for_status()
    daily_path = resp.json().get("path") if resp.headers.get("content-type", "").startswith("application/json") else None
    daily_path = daily_path or "Daily Notes/" + date.today().isoformat() + ".md"

    md = build_standup_markdown()
    acquire_lock(daily_path, "system", "standup")
    try:
        await backend.patch(daily_path, "heading", "Agent Updates", md, reject_if_preexists=True)
    finally:
        release_lock(daily_path, "standup")
    return {"posted": True, "path": daily_path}
```

* * *
## Wire FinOps into `context_server/app/main.py`

```python
# --- imports ---
from .finops.rollups import totals_by_task, heatmap, capo, capo_trend
from .finops.standup import post_standup
from .finops.meter import mark_accepted


@app.get("/dashboard/tokens")
async def dashboard_tokens():
    return {"by_task": totals_by_task(), "heatmap": heatmap()}


@app.get("/dashboard/capo")
async def dashboard_capo():
    return {"summary": capo(), "trend": capo_trend()}


@app.post("/mcp/post_standup")
async def post_standup_ep(ident: AgentIdentity = Depends(require_identity)):
    result = await post_standup()
    audit(ident.agent, ident.task_id, "post_standup", True, result["path"])
    return result
```

> Also update `accept_implement` (Phase 3) to call `mark_accepted(body.row_id)` so the CAPO numerator moves the moment the orchestrator accepts an outcome.
* * *
## Live push: `/dashboard/tokens/ws` websocket (optional, Phase 9 uses it)

```python
from fastapi import WebSocket
import asyncio

@app.websocket("/dashboard/tokens/ws")
async def tokens_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({"by_task": totals_by_task(), "capo": capo()})
            await asyncio.sleep(3)   # push every 3s; swap for a change-trigger later
    except Exception:  # noqa: BLE001
        await ws.close()
```

* * *
## Optional: schedule the standup daily (simple in-process scheduler)

```python
# add to lifespan in main.py
import asyncio
from datetime import datetime, time, timedelta

async def _daily_standup_loop():
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(9, 0))   # 9am local
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await post_standup()
        except Exception as e:  # noqa: BLE001
            print("[standup] failed:", e)

# in lifespan: asyncio.create_task(_daily_standup_loop())
```

* * *
## Smoke test (Definition of Done)

```bash
# 1. Generate some spend: delegate a couple tasks (Phase 3), then accept one.
curl -X POST http://127.0.0.1:27180/mcp/delegate_task \
  -H "X-Agent-Identity: opencode:task-A" -H "Content-Type: application/json" \
  -d '{"target_agent": "hermes", "prompt": "research X"}'
curl -X POST http://127.0.0.1:27180/mcp/accept_implement \
  -H "X-Agent-Identity: opencode:task-A" -H "Content-Type: application/json" \
  -d '{"path": "IMPLEMENT.md", "row_id": "task-A"}'

# 2. Token rollups return real numbers
curl http://127.0.0.1:27180/dashboard/tokens
# -> {"by_task": [{"task_id":"task-A","total_tokens":N,"accepted":1}, ...], "heatmap": [...]}

# 3. CAPO computes (total tokens / accepted tasks)
curl http://127.0.0.1:27180/dashboard/capo
# -> {"summary": {"total_tokens":N,"accepted_tasks":1,"capo":N.0}, "trend": [...]}

# 4. Standup appends idempotently to today's daily note (run twice -> no double-append)
curl -X POST http://127.0.0.1:27180/mcp/post_standup -H "X-Agent-Identity: opencode:task-A"
curl -X POST http://127.0.0.1:27180/mcp/post_standup -H "X-Agent-Identity: opencode:task-A"
# -> second call's patch is rejected by rejectIfContentPreexists; no duplicate section
```

A completed task's cost lands in the ledger (2), CAPO returns a real value the moment an outcome is accepted (3), and the standup writes once per day no matter how many times it runs (4). That's the Phase 7 Definition of Done. The `/dashboard/tokens` + `/dashboard/capo` + the websocket are exactly what the Phase 9 `/tokens` analytics page renders.