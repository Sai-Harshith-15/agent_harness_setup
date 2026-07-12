import asyncio
import hashlib
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel

from .config import settings
from .db import CONTROL_DB, audit, connect, init_db
from .delegation import delegate_task as _delegate_task
from .finops.meter import mark_accepted
from .finops.meter import record as meter_record
from .finops.rollups import capo, capo_trend, heatmap, raw_ledger, totals_by_task
from .finops.standup import post_standup
from .governance.hibernation import hibernate, thaw
from .governance.hitl import enqueue, init_hitl, open_items, resolve
from .governance.locks import check_occ, governed_write
from .governance.permissions import can_write
from .governance.reconcile import reconcile
from .governance.secrets_bridge import bridge as secrets_bridge
from .identity import AgentIdentity, require_identity
from .indexing.compactor import compact
from .indexing.drift import detect_drift
from .indexing.graphify import graphify
from .indexing.headroom import Headroom
from .indexing.store import all_edges, all_nodes, init_index
from .indexing.watcher import watch_and_index
from .meta.dream_cycle import analyze
from .meta.runner import run_dream_cycle
from .middlewares import DLPFilter, PolicyMiddleware
from .obsidian_backend import backend
from .okf_backend import get_concept as okf_get_concept
from .okf_backend import search_okf as okf_search
from .registry import find_capability, load_agents, lookup_agent, orchestrator_id

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
    failures = 0
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(9, 0))   # 9am local
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await post_standup()
            failures = 0
        except Exception as e:
            failures += 1
            print(f"[standup] failed ({failures}):", e)
            audit("system", "standup_loop", "post_standup", False, str(e))
            if failures >= 3:
                await asyncio.sleep(min(300, 2 ** failures))

async def _dream_loop():
    failures = 0
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(3, 0))
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            print("[dream-cycle]", await run_dream_cycle())
            failures = 0
        except Exception as e:
            failures += 1
            print(f"[dream-cycle] failed ({failures}):", e)
            audit("system", "dream_loop", "run_dream_cycle", False, str(e))
            if failures >= 3:
                await asyncio.sleep(min(300, 2 ** failures))

async def _secrets_rotation_loop():
    failures = 0
    while True:
        await asyncio.sleep(3600)
        try:
            rotated = secrets_bridge.auto_rotate_expired()
            if rotated:
                audit("system", "secrets-bridge", "auto_rotate", True, f"rotated={','.join(rotated)}")
        except Exception as e:
            failures += 1
            print(f"[secrets-bridge] rotation check failed ({failures}):", e)
            if failures >= 3:
                await asyncio.sleep(min(300, 2 ** failures))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_hitl()
    init_index()

    # Configure Langfuse for LLM + agent traces (Gap 3.3)
    if os.environ.get("ENABLE_LANGFUSE", "").lower() in ("1", "true", "yes"):
        try:
            from langfuse import Langfuse
            app.state.langfuse = Langfuse(
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
                host=os.environ.get("LANGFUSE_HOST", "http://localhost:3001"),
            )
            print("[boot] Langfuse tracing enabled")
        except ImportError:
            print("[boot] Langfuse SDK not installed; run: pip install langfuse")
        except Exception as e:
            print(f"[boot] Langfuse init failed: {e}")

        try:
            import litellm
            litellm.success_callback = ["langfuse"]
            litellm.failure_callback = ["langfuse"]
        except ImportError:
            pass

    print("[boot] crash reconciliation:", reconcile(startup=True))   # reap crash-orphaned leases
    asyncio.create_task(_daily_standup_loop())
    asyncio.create_task(_dream_loop())
    asyncio.create_task(_secrets_rotation_loop())
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

resource = Resource.create({"service.name": "context_server"})
provider = TracerProvider(resource=resource)
if os.environ.get("ENABLE_OTEL", "true").lower() not in ("0", "false", "no"):
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("TEST_MODE") == "true":
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
        class NoOpSpanExporter(SpanExporter):
            def export(self, spans): return SpanExportResult.SUCCESS
            def shutdown(self): pass
        processor = SimpleSpanProcessor(NoOpSpanExporter())
    else:
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True))
    provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)

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
        stalls = [dict(r) for r in c.execute("SELECT * FROM hitl_queue WHERE status='open'").fetchall()]
        tasks = [dict(r) for r in c.execute("SELECT DISTINCT task_id, agent FROM audit_log ORDER BY id DESC LIMIT 50").fetchall()]
    agents = list(load_agents().values())
    return {"agents": agents, "tasks": tasks, "locks": locks, "recent_activity": recent, "stalls": stalls}

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
        return {"path": "", "entries": await backend.list_vault()}
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
    task_id: str
    row_id: str

class CredentialsBody(BaseModel):
    service: str
    sandbox_id: str = "default"
    scope: str = "default"

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
        meter_record(ident.agent, ident.task_id, "search_notes")
        return {"results": results}
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "search_notes", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")

@app.post("/mcp/read_note")
async def read_note(path: str, ident: AgentIdentity = Depends(require_identity)):
    try:
        note = await backend.read_note(path)
        if "content" in note:
            note["version_hash"] = hashlib.sha256((note["content"] or "").encode("utf-8")).hexdigest()
            note["content"] = DLPFilter.scrub(note["content"])
        notify_audit(ident.agent, ident.task_id, "read_note", True, path)
        meter_record(ident.agent, ident.task_id, "read_note")
        return note
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "read_note", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")

@app.post("/mcp/append_implement")
async def append_implement(body: GovernedAppendBody, ident: AgentIdentity = Depends(require_identity)):
    decision = can_write(body.path, "heading", body.target, ident.agent, ident.task_id)   # permission matrix
    if not decision.allowed:
        notify_audit(ident.agent, ident.task_id, "append_implement", False, f"DENY: {decision.reason}")
        raise HTTPException(status_code=403, detail=decision.reason)

    with governed_write(body.path, ident.agent, ident.task_id):
        try:
            note = await backend.read_note(body.path)             # OCC read
            current_version = hashlib.sha256((note.get("content") or "").encode("utf-8")).hexdigest()
            check_occ(current_version, body.expected_version)
            scrubbed_content = DLPFilter.scrub(body.content)
            await backend.patch(body.path, "heading", body.target, scrubbed_content,
                                reject_if_preexists=True)         # idempotent write
            notify_audit(ident.agent, ident.task_id, "append_implement", True, f"{body.path}#{body.target}")
            meter_record(ident.agent, ident.task_id, "append_implement")
            return {"ok": True}
        except HTTPException:
            raise
        except Exception as e:
            notify_audit(ident.agent, ident.task_id, "append_implement", False, str(e))
            raise HTTPException(status_code=502, detail="Obsidian backend error")

@app.post("/mcp/log_decision")
async def log_decision(body: GovernedAppendBody, ident: AgentIdentity = Depends(require_identity)):
    decision = can_write(body.path, "heading", body.target, ident.agent, ident.task_id)   # permission matrix
    if not decision.allowed:
        notify_audit(ident.agent, ident.task_id, "log_decision", False, f"DENY: {decision.reason}")
        raise HTTPException(status_code=403, detail=decision.reason)

    with governed_write(body.path, ident.agent, ident.task_id):
        try:
            note = await backend.read_note(body.path)             # OCC read
            current_version = hashlib.sha256((note.get("content") or "").encode("utf-8")).hexdigest()
            check_occ(current_version, body.expected_version)
            scrubbed_content = DLPFilter.scrub(body.content)
            await backend.patch(body.path, "heading", body.target, scrubbed_content,
                                reject_if_preexists=True)         # idempotent write
            notify_audit(ident.agent, ident.task_id, "log_decision", True, f"{body.path}#{body.target}")
            meter_record(ident.agent, ident.task_id, "log_decision")
            return {"ok": True}
        except HTTPException:
            raise
        except Exception as e:
            notify_audit(ident.agent, ident.task_id, "log_decision", False, str(e))
            raise HTTPException(status_code=502, detail="Obsidian backend error")

@app.post("/mcp/delegate_task")
async def delegate_task_ep(body: DelegateBody, ident: AgentIdentity = Depends(require_identity)):
    result = await _delegate_task(ident.agent, ident.task_id, body.target_agent, body.prompt)
    return {"ok": result.ok, "agent": result.agent, "output": result.output,
            "tokens_in": result.tokens_in, "tokens_out": result.tokens_out}

@app.post("/mcp/search_okf")
async def search_okf(body: SearchBody, ident: AgentIdentity = Depends(require_identity)):
    results = okf_search(body.query)
    notify_audit(ident.agent, ident.task_id, "search_okf", True, f"{len(results)} hits")
    meter_record(ident.agent, ident.task_id, "search_okf")
    return {"results": results}

@app.get("/mcp/get_concept")
async def get_concept_ep(concept_id: str, bundle: str | None = None, ident: AgentIdentity = Depends(require_identity)):
    concept = okf_get_concept(concept_id, bundle)
    if not concept:
        raise HTTPException(status_code=404, detail=f"Concept '{concept_id}' not found")
    concept["body"] = DLPFilter.scrub(concept.get("body", ""))
    notify_audit(ident.agent, ident.task_id, "get_concept", True, concept_id)
    meter_record(ident.agent, ident.task_id, "get_concept")
    return concept

@app.get("/mcp/search_tools")
async def search_tools_ep(query: str | None = None, ident: AgentIdentity = Depends(require_identity)):
    tool_schemas = [
        {"tool_id": "search_tools", "description": "Search available MCP tools by description or name", "readOnlyHint": True},
        {"tool_id": "load_tool_schema", "description": "Load full input/output schema for one tool", "readOnlyHint": True},
        {"tool_id": "search_notes", "description": "Search Obsidian vault notes by query", "readOnlyHint": True},
        {"tool_id": "read_note", "description": "Read a single Obsidian note by path", "readOnlyHint": True},
        {"tool_id": "search_okf", "description": "Search OKF bundles for structured concepts", "readOnlyHint": True},
        {"tool_id": "get_concept", "description": "Get one OKF concept by concept-id", "readOnlyHint": True},
        {"tool_id": "lookup_agent", "description": "Look up a registered agent by id", "readOnlyHint": True},
        {"tool_id": "find_capability", "description": "Find agents providing a capability", "readOnlyHint": True},
        {"tool_id": "append_implement", "description": "Append to IMPLEMENT.md under a heading", "destructiveHint": True},
        {"tool_id": "log_decision", "description": "Log a decision to a log.md heading", "destructiveHint": True},
        {"tool_id": "delegate_task", "description": "Delegate a sub-task to another agent", "destructiveHint": True},
        {"tool_id": "request_credentials", "description": "Request scoped ephemeral credentials", "destructiveHint": False},
        {"tool_id": "request_clarification", "description": "Pause and request human input", "destructiveHint": False},
        {"tool_id": "reindex", "description": "Re-index the codebase graph", "destructiveHint": False},
        {"tool_id": "compress", "description": "Compress context to a token budget", "readOnlyHint": False},
    ]
    if query:
        q = query.lower()
        tool_schemas = [t for t in tool_schemas if q in t["tool_id"].lower() or q in t["description"].lower()]
    notify_audit(ident.agent, ident.task_id, "search_tools", True, f"{len(tool_schemas)} results")
    return {"tools": tool_schemas}

@app.get("/mcp/load_tool_schema")
async def load_tool_schema_ep(tool_id: str, ident: AgentIdentity = Depends(require_identity)):
    schemas = {
        "search_notes": {"input": {"query": "str"}, "output": {"results": "list[NoteMatch]"}},
        "read_note": {"input": {"path": "str"}, "output": "NoteContent", "headers": ["X-Version"]},
        "search_okf": {"input": {"query": "str", "bundle?": "str"}, "output": {"results": "list[ConceptMatch]"}},
        "get_concept": {"input": {"concept_id": "str", "bundle?": "str"}, "output": "ConceptContent", "headers": ["X-Version"]},
        "lookup_agent": {"input": {"agent_id": "str"}, "output": "AgentEntry"},
        "find_capability": {"input": {"capability": "str"}, "output": {"agents": "list[str]"}},
        "append_implement": {"input": {"path": "str", "target": "str", "content": "str", "expected_version?": "str"}, "output": {"ok": "bool"}},
        "log_decision": {"input": {"path": "str", "target": "str", "content": "str", "expected_version?": "str"}, "output": {"ok": "bool"}},
        "delegate_task": {"input": {"target_agent": "str", "prompt": "str"}, "output": {"ok": "bool", "agent": "str", "output": "str"}},
        "request_credentials": {"input": {"service": "str", "sandbox_id?": "str"}, "output": {"ok": "bool", "env_injected": "list[str]"}},
        "request_clarification": {"input": {"question": "str"}, "output": {"paused": "bool", "hitl_item": "int"}},
        "reindex": {"input": {}, "output": {"added": "int", "skipped": "int"}},
        "compress": {"input": {"budget_tokens": "int"}, "output": {"kept": "list[str]", "collapsed_nodes": "int"}},
    }
    schema = schemas.get(tool_id)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Unknown tool '{tool_id}'")
    notify_audit(ident.agent, ident.task_id, "load_tool_schema", True, tool_id)
    return {"tool_id": tool_id, "schema": schema}

@app.post("/mcp/acquire_lock")
async def acquire_lock_ep(resource: str, ttl_s: int = 120, ident: AgentIdentity = Depends(require_identity)):
    from .governance.locks import acquire_lock
    try:
        acquire_lock(resource, ident.agent, ident.task_id)
        notify_audit(ident.agent, ident.task_id, "acquire_lock", True, f"acquired {resource}")
        return {"ok": True, "resource": resource, "lease_expires_at": None}
    except HTTPException:
        raise
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "acquire_lock", False, str(e))
        raise HTTPException(status_code=409, detail=str(e))

@app.post("/mcp/request_snapshot")
async def request_snapshot_ep(label: str | None = None, ident: AgentIdentity = Depends(require_identity)):
    from .governance.snapshot import create_snapshot
    try:
        create_snapshot(ident.task_id)
        notify_audit(ident.agent, ident.task_id, "request_snapshot", True, f"snapshot {ident.task_id}")
        return {"ok": True, "snapshot_id": ident.task_id}
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "request_snapshot", False, str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mcp/request_credentials")
async def request_credentials(body: CredentialsBody, ident: AgentIdentity = Depends(require_identity)):
    try:
        result = secrets_bridge.request_credentials(body.service, body.sandbox_id, body.scope)
        notify_audit(ident.agent, ident.task_id, "request_credentials", True,
                     f"service={body.service} sandbox={body.sandbox_id}")
        meter_record(ident.agent, ident.task_id, "request_credentials")
        return result
    except ValueError as e:
        notify_audit(ident.agent, ident.task_id, "request_credentials", False, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        notify_audit(ident.agent, ident.task_id, "request_credentials", False, str(e))
        raise HTTPException(status_code=500, detail="Secrets bridge error")

@app.post("/mcp/rotate_credentials")
async def rotate_credentials(service: str, ident: AgentIdentity = Depends(require_identity)):
    try:
        result = secrets_bridge.rotate_credential(service)
        notify_audit(ident.agent, ident.task_id, "rotate_credentials", True, f"service={service}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/dashboard/secrets")
async def dashboard_secrets():
    return {"services": secrets_bridge.list_services()}

@app.post("/mcp/accept_implement")
async def accept_implement(body: AcceptBody, ident: AgentIdentity = Depends(require_identity)):
    if ident.agent != orchestrator_id():
        raise HTTPException(status_code=403, detail="Only the orchestrator may accept IMPLEMENT rows")
    mark_accepted(body.task_id)

    # Phase 6.3: physically append the accepted row to IMPLEMENT.md
    import datetime
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    plan_path = os.path.join(root, "PLAN.md")
    title = body.row_id
    agent = ident.agent
    phase = body.row_id.split("-")[0].replace("P", "") if "-" in body.row_id else "?"
    if os.path.exists(plan_path):
        for line in open(plan_path, encoding="utf-8"):
            m = _PLAN_ROW.match(line.strip())
            if m and m.group("id") == body.row_id:
                title = m.group("title")
                agent = m.group("agent")
                break

    impl_path = os.path.join(root, body.path)
    if os.path.exists(impl_path):
        with open(impl_path, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
        out_lines = []
        inserted = False
        new_row = f"| {phase} | {body.row_id} | {title} | {agent} | true | {datetime.datetime.now().strftime('%Y-%m-%d')} |"
        for line in lines:
            if line.startswith("---") and not inserted and any("| phase |" in line_ for line_ in out_lines):
                out_lines.append(new_row)
                inserted = True
            out_lines.append(line)
        if not inserted:
            out_lines.append(new_row)
        with open(impl_path, "w", encoding="utf-8") as f:
            f.write("\n".join(out_lines))

    notify_audit(ident.agent, ident.task_id, "accept_implement", True, f"{body.path}#{body.row_id}")
    return {"ok": True, "accepted": body.row_id}

@app.post("/mcp/request_clarification")
async def request_clarification(body: ClarifyBody, ident: AgentIdentity = Depends(require_identity)):
    hibernate(ident.task_id, ident.agent, reason="awaiting-hitl",
              frozen_state={"question": body.question, "diff": body.proposed_diff})
    item_id = enqueue(ident.task_id, ident.agent, body.question, body.proposed_diff)
    notify_audit(ident.agent, ident.task_id, "request_clarification", True, f"queued #{item_id}")

    # Route to orchestrator in the background (Phase 6.5)
    import asyncio

    from .adapters import adapter_for
    from .registry import lookup_agent, orchestrator_id
    orch_meta = lookup_agent(orchestrator_id())
    if orch_meta:
        async def _notify():
            try:
                await adapter_for(orch_meta).run(ident.task_id, f"HITL Clarification from {ident.agent}: {body.question}", orch_meta)
            except Exception:
                pass
        asyncio.create_task(_notify())

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

@app.get("/dashboard/task/{task_id}")
async def dashboard_task(task_id: str):
    with connect(CONTROL_DB) as c:
        spans = c.execute("SELECT id, ts, agent, tool, ok, detail FROM audit_log WHERE task_id=? ORDER BY ts", (task_id,)).fetchall()
        hitl = c.execute("SELECT id, status, resolution, ts FROM hitl_queue WHERE task_id=? ORDER BY ts", (task_id,)).fetchall()
        crashes = c.execute("SELECT reason, frozen_state, created_at FROM hibernation WHERE task_id=?", (task_id,)).fetchall()

    from .db import TOKEN_DB
    with connect(TOKEN_DB) as tc:
        tokens = tc.execute("SELECT agent, input_tokens, output_tokens, model, cost_usd FROM token_ledger WHERE task_id=?", (task_id,)).fetchall()

    return {
        "task_id": task_id,
        "spans": spans,
        "hitl": hitl,
        "crashes": crashes,
        "tokens": tokens
    }

@app.post("/dashboard/crashes/{task_id}/rerun")
async def dashboard_crashes_rerun(task_id: str):
    thaw(task_id)
    return {"ok": True, "task_id": task_id, "status": "thawed"}

# ---------- Phase 7: FinOps ----------

@app.get("/dashboard/tokens")
async def dashboard_tokens():
    return {"by_task": totals_by_task(), "heatmap": heatmap()}

@app.get("/dashboard/tokens/raw")
async def dashboard_tokens_raw(start_date: str | None = None, end_date: str | None = None):
    return {"rows": raw_ledger(start_date, end_date)}

@app.get("/dashboard/capo")
async def dashboard_capo():
    return {"summary": capo(), "trend": capo_trend()}

@app.post("/mcp/post_standup")
async def post_standup_ep(ident: AgentIdentity = Depends(require_identity)):
    result = await post_standup()
    audit(ident.agent, ident.task_id, "post_standup", True, result["path"])
    meter_record(ident.agent, ident.task_id, "post_standup")
    return result

@app.websocket("/dashboard/tokens/ws")
async def tokens_ws(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_json({"by_task": totals_by_task(), "capo": capo()})
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("[tokens_ws] error:", e)
        await ws.close()

# ---------- Phase 5: indexing + generation endpoints ----------

@app.post("/mcp/reindex")
async def reindex(ident: AgentIdentity = Depends(require_identity)):
    stats = graphify()
    audit(ident.agent, ident.task_id, "reindex", True, str(stats))
    meter_record(ident.agent, ident.task_id, "reindex")
    return stats


@app.post("/mcp/compress")
async def compress(budget_tokens: int = 4000, ident: AgentIdentity = Depends(require_identity)):
    result = compact(budget_tokens)
    audit(ident.agent, ident.task_id, "compress", True,
          f"kept={len(result['kept'])} collapsed={result['collapsed_nodes']}")
    meter_record(ident.agent, ident.task_id, "compress")
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
    if result["ok"]:
        meter_record(ident.agent, ident.task_id, "run_dream_cycle")
    return result


if __name__ == "__main__":
    uvicorn.run(app, host=settings.context_server_host, port=settings.context_server_port)
