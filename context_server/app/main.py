from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, WebSocket
from pydantic import BaseModel
import uvicorn
import asyncio
import os
import re
from .config import settings
from .db import init_db, audit, connect, CONTROL_DB
from .identity import require_identity, AgentIdentity
from .obsidian_backend import backend
from .middlewares import PolicyMiddleware, DLPFilter
from .registry import load_agents, lookup_agent, find_capability, orchestrator_id
from .delegation import delegate_task as _delegate_task
from .indexing.graphify import graphify
from .indexing.store import all_nodes, all_edges
from .indexing.compactor import compact
from .indexing.drift import detect_drift
from .indexing.headroom import Headroom
from .indexing.watcher import watch_and_index
from .governance.permissions import can_write
from .governance.locks import acquire_lock, release_lock, check_occ
from .governance.hibernation import hibernate, thaw
from .governance.hitl import init_hitl, enqueue, open_items, resolve
from .governance.reconcile import reconcile
from .finops.rollups import totals_by_task, heatmap, capo, capo_trend
from .finops.standup import post_standup
from .finops.meter import mark_accepted
from .meta.runner import run_dream_cycle
from .meta.dream_cycle import analyze
from datetime import datetime, time, timedelta
# Simple in-memory event bus for websocket
dashboard_clients = set()

async def broadcast_event(event_data: dict):
    for client in list(dashboard_clients):
        try:
            await client.send_json(event_data)
        except Exception:
            dashboard_clients.discard(client)

def notify_audit(agent, task_id, tool, ok, detail):
    audit(agent, task_id, tool, ok, detail)
    asyncio.create_task(broadcast_event({
        "type": "audit", "agent": agent, "task_id": task_id, "tool": tool, "ok": ok, "detail": detail
    }))

async def _daily_standup_loop():
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(9, 0))   # 9am local
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await post_standup()
        except Exception as e:
            print("[standup] failed:", e)

async def _dream_loop():
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(3, 0))   # 3am local
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            print("[dream-cycle]", await run_dream_cycle())
        except Exception as e:
            print("[dream-cycle] failed:", e)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_hitl()
    print("[boot] crash reconciliation:", reconcile())   # reap crash-orphaned leases
    asyncio.create_task(_daily_standup_loop())
    asyncio.create_task(_dream_loop())
    # ENABLE_WATCHER defaults to true; tests set it to 'false' so the
    # background file-watcher never starts and can never block teardown.
    if os.environ.get("ENABLE_WATCHER", "true").lower() not in ("0", "false", "no"):
        watcher_task = asyncio.create_task(watch_and_index())
    else:
        watcher_task = None
    try:
        yield
    finally:
        if watcher_task is not None:
            watcher_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(watcher_task), timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        await backend.aclose()

app = FastAPI(title="Agentic OS Context Server", version="0.2.0", lifespan=lifespan)
app.add_middleware(PolicyMiddleware)

# ---------- health + dashboard ----------
@app.get("/health")
async def health():
    obs_ok = await backend.health()
    return {"status": "ok" if obs_ok else "degraded", "obsidian_backend": obs_ok}

@app.get("/dashboard/state")
async def dashboard_state():
    with connect(CONTROL_DB) as c:
        locks = [dict(r) for r in c.execute("SELECT * FROM locks").fetchall()]
        recent = [dict(r) for r in c.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT 25").fetchall()]
    return {"agents": [], "tasks": [], "locks": locks, "recent_activity": recent, "stalls": []}

@app.get("/dashboard/agents")
async def dashboard_agents():
    return {"agents": list(load_agents().values()), "orchestrator": orchestrator_id()}

@app.get("/dashboard/vault")
async def dashboard_vault(path: str = ""):
    """Read-only Obsidian command-center feed (Phase 4 / Phase 9 /vault page).
    Lists or reads notes via the Obsidian backend. No writes here — ever."""
    try:
        if path:
            return {"path": path, "note": await backend.read_note(path)}
        listing = await backend._client.get("/vault/")  # noqa: SLF001 (read-only browse)
        listing.raise_for_status()
        return {"path": "", "entries": listing.json()}
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="Obsidian backend error")

@app.websocket("/dashboard/events")
async def dashboard_events(websocket: WebSocket):
    await websocket.accept()
    dashboard_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        dashboard_clients.discard(websocket)

# ---------- MCP tool surface (identity-bound) ----------
class SearchBody(BaseModel):
    query: str

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

class DelegateBody(BaseModel):
    target_agent: str
    prompt: str

class AcceptBody(BaseModel):
    path: str
    row_id: str

@app.get("/mcp/lookup_agent")
async def lookup_agent_ep(agent_id: str, ident: AgentIdentity = Depends(require_identity)):
    meta = lookup_agent(agent_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return meta

@app.get("/mcp/find_capability")
async def find_capability_ep(capability: str, ident: AgentIdentity = Depends(require_identity)):
    return {"capability": capability, "agents": find_capability(capability)}

@app.post("/mcp/search_notes")
async def search_notes(body: SearchBody, ident: AgentIdentity = Depends(require_identity)):
    try:
        results = await backend.search_simple(body.query)
        if isinstance(results, list):
            for i in range(len(results)):
                if "content" in results[i]:
                    results[i]["content"] = DLPFilter.scrub(results[i]["content"])
        notify_audit(ident.agent, ident.task_id, "search_notes", True, f"{len(results)} hits")
        return {"results": results}
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "search_notes", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")

@app.post("/mcp/read_note")
async def read_note(path: str, ident: AgentIdentity = Depends(require_identity)):
    try:
        note = await backend.read_note(path)
        if "content" in note:
            note["content"] = DLPFilter.scrub(note["content"])
        notify_audit(ident.agent, ident.task_id, "read_note", True, path)
        return note
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "read_note", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")

@app.post("/mcp/append_implement")
async def append_implement(body: GovernedAppendBody, ident: AgentIdentity = Depends(require_identity)):
    decision = can_write(body.path, "heading", body.target)   # permission matrix
    if not decision.allowed:
        notify_audit(ident.agent, ident.task_id, "append_implement", False, f"DENY: {decision.reason}")
        raise HTTPException(status_code=403, detail=decision.reason)

    acquire_lock(body.path, ident.agent, ident.task_id)       # lease
    try:
        note = await backend.read_note(body.path)             # OCC read
        check_occ(str(note.get("stat", {}).get("mtime", "")), body.expected_version)
        scrubbed_content = DLPFilter.scrub(body.content)
        await backend.patch(body.path, "heading", body.target, scrubbed_content,
                            reject_if_preexists=True)         # idempotent write
        notify_audit(ident.agent, ident.task_id, "append_implement", True, f"{body.path}#{body.target}")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "append_implement", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")
    finally:
        release_lock(body.path, ident.task_id)

@app.post("/mcp/delegate_task")
async def delegate_task_ep(body: DelegateBody, ident: AgentIdentity = Depends(require_identity)):
    result = await _delegate_task(ident.agent, ident.task_id, body.target_agent, body.prompt)
    return {"ok": result.ok, "agent": result.agent, "output": result.output,
            "tokens_in": result.tokens_in, "tokens_out": result.tokens_out}

@app.post("/mcp/accept_implement")
async def accept_implement(body: AcceptBody, ident: AgentIdentity = Depends(require_identity)):
    if ident.agent != orchestrator_id():
        raise HTTPException(status_code=403, detail="Only the orchestrator may accept IMPLEMENT rows")
    mark_accepted(body.row_id)
    notify_audit(ident.agent, ident.task_id, "accept_implement", True, f"{body.path}#{body.row_id}")
    return {"ok": True, "accepted": body.row_id}

@app.post("/mcp/request_clarification")
async def request_clarification(body: ClarifyBody, ident: AgentIdentity = Depends(require_identity)):
    hibernate(ident.task_id, ident.agent, reason="awaiting-hitl",
              frozen_state={"question": body.question, "diff": body.proposed_diff})
    item_id = enqueue(ident.task_id, ident.agent, body.question, body.proposed_diff)
    notify_audit(ident.agent, ident.task_id, "request_clarification", True, f"queued #{item_id}")
    return {"paused": True, "hitl_item": item_id}

@app.get("/dashboard/hitl")
async def dashboard_hitl():
    return {"open": open_items()}

@app.patch("/dashboard/hitl")
async def resolve_hitl(body: ResolveBody):
    resolve(body.item_id, body.status, body.resolution)
    if body.status in ("approved", "modified"):
        with connect(CONTROL_DB) as c:
            row = c.execute("SELECT task_id FROM hitl_queue WHERE id=?", (body.item_id,)).fetchone()
        if row:
            thaw(row["task_id"])
    return {"ok": True, "status": body.status}

@app.get("/dashboard/crashes")
async def dashboard_crashes():
    return reconcile()

# ---------- Phase 7: FinOps ----------

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

@app.websocket("/dashboard/tokens/ws")
async def tokens_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({"by_task": totals_by_task(), "capo": capo()})
            await asyncio.sleep(3)
    except Exception:
        await ws.close()

# ---------- Phase 5: indexing + generation endpoints ----------

@app.post("/mcp/reindex")
async def reindex(ident: AgentIdentity = Depends(require_identity)):
    stats = graphify()
    audit(ident.agent, ident.task_id, "reindex", True, str(stats))
    return stats


@app.post("/mcp/compress")
async def compress(budget_tokens: int = 4000, ident: AgentIdentity = Depends(require_identity)):
    result = compact(budget_tokens)
    audit(ident.agent, ident.task_id, "compress", True,
          f"kept={len(result['kept'])} collapsed={result['collapsed_nodes']}")
    return result


@app.get("/dashboard/graph")
async def dashboard_graph():
    return {"nodes": all_nodes(), "edges": all_edges()}


@app.get("/dashboard/drift")
async def dashboard_drift():
    return {"banners": detect_drift()}


@app.get("/dashboard/headroom")
async def dashboard_headroom(used: int = 0, incoming: int = 0):
    h = Headroom()
    return {"remaining": h.remaining(used), "must_compact": h.must_compact(used, incoming)}

# ---------- Phase 9: Kanban PLAN.md parsing ----------

_PLAN_ROW = re.compile(
    r"- \[(?P<status>[^\]]+)\] \((?P<id>[^)]+)\) (?P<title>.+?) \| agent=(?P<agent>\S+)"
    r"(?: capo=(?P<capo>\d+))?(?: tokens=(?P<tokens>\d+))?"
)

@app.get("/dashboard/plan")
async def dashboard_plan():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "PLAN.md")
    rows = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            m = _PLAN_ROW.match(line.strip())
            if m:
                d = m.groupdict()
                rows.append({"status": d["status"], "id": d["id"], "title": d["title"],
                             "agent": d["agent"], "capo": int(d["capo"] or 0), "tokens": int(d["tokens"] or 0)})
    return {"rows": rows}

# ---------- Phase 8: Meta-harness & Dream Cycle ----------

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


if __name__ == "__main__":
    uvicorn.run(app, host=settings.context_server_host, port=settings.context_server_port)
