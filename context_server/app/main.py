from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, WebSocket
from pydantic import BaseModel
import uvicorn
import asyncio
import os
from .config import settings
from .db import init_db, audit, connect, CONTROL_DB, TOKEN_DB
from .identity import require_identity, AgentIdentity
from .obsidian_backend import backend
from .lock_manager import LockManager
from .middlewares import PolicyMiddleware, DLPFilter
from .registry import load_agents, lookup_agent, find_capability, orchestrator_id
from .delegation import delegate_task as _delegate_task
from .indexing.graphify import graphify
from .indexing.store import all_nodes, all_edges
from .indexing.compactor import compact
from .indexing.drift import detect_drift
from .indexing.headroom import Headroom
from .indexing.watcher import watch_and_index

# Simple in-memory event bus for websocket
dashboard_clients = set()

async def broadcast_event(event_data: dict):
    for client in list(dashboard_clients):
        try:
            await client.send_json(event_data)
        except:
            dashboard_clients.discard(client)

def notify_audit(agent, task_id, tool, ok, detail):
    audit(agent, task_id, tool, ok, detail)
    asyncio.create_task(broadcast_event({
        "type": "audit", "agent": agent, "task_id": task_id, "tool": tool, "ok": ok, "detail": detail
    }))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
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
    except:
        dashboard_clients.discard(websocket)

# ---------- MCP tool surface (identity-bound) ----------
class SearchBody(BaseModel):
    query: str

class AppendBody(BaseModel):
    path: str
    content: str

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
async def append_implement(body: AppendBody, ident: AgentIdentity = Depends(require_identity)):
    LockManager.acquire(resource=body.path, agent=ident.agent, task_id=ident.task_id)
    try:
        scrubbed_content = DLPFilter.scrub(body.content)
        await backend.append(body.path, scrubbed_content)
        notify_audit(ident.agent, ident.task_id, "append_implement", True, body.path)
        return {"ok": True}
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "append_implement", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")
    finally:
        LockManager.release(resource=body.path, task_id=ident.task_id)

@app.post("/mcp/delegate_task")
async def delegate_task_ep(body: DelegateBody, ident: AgentIdentity = Depends(require_identity)):
    result = await _delegate_task(ident.agent, ident.task_id, body.target_agent, body.prompt)
    return {"ok": result.ok, "agent": result.agent, "output": result.output,
            "tokens_in": result.tokens_in, "tokens_out": result.tokens_out}

@app.post("/mcp/accept_implement")
async def accept_implement(body: AcceptBody, ident: AgentIdentity = Depends(require_identity)):
    if ident.agent != orchestrator_id():
        raise HTTPException(status_code=403, detail="Only the orchestrator may accept IMPLEMENT rows")
    with connect(TOKEN_DB) as c:
        c.execute("UPDATE token_ledger SET accepted=1 WHERE task_id=?", (body.row_id,))
    audit(ident.agent, ident.task_id, "accept_implement", True, f"{body.path}#{body.row_id}")
    return {"ok": True, "accepted": body.row_id}

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


if __name__ == "__main__":
    uvicorn.run(app, host=settings.context_server_host, port=settings.context_server_port)
