# Agentic OS — Runnable Starter Code (Phases 0–2)

# Agentic OS — Runnable Starter (Phases 0–2)
Copy each file below into `D:\GitRepo\agent_harness_setup\` at the path shown in its heading. This is the runnable backbone: a FastAPI **Context Server** that wraps the `obsidian-local-rest-api` MCP, holds the secrets bridge + transport identity + the two SQLite stores, and exposes `/health`, `/mcp/*`, and `/dashboard/*`. A separate page holds the **Next.js Mission Control** shell.
> Full run instructions are in the README file below. Later phases (3–9) slot into the same structure — see the tasks in 901615745748 ([https://app.clickup.com/90161687318/v/li/901615745748](https://app.clickup.com/90161687318/v/li/901615745748)).
* * *
## `README.md`

```markdown
# Agentic OS — runnable starter (Phases 0–2)

## Prerequisites
1. Obsidian running with the **Local REST API with MCP** plugin. Copy the API key from settings.
   HTTPS on https://127.0.0.1:27124 (self-signed cert), HTTP on http://127.0.0.1:27123.
2. Python 3.11+ and Node 18+.

## Setup
    # Backend
    cd context_server
    python -m venv .venv
    # Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env      # paste your OBSIDIAN_REST_API_KEY
    python -m app.main        # http://127.0.0.1:27180

    # Frontend (new terminal)
    cd frontend
    npm install
    npm run dev               # http://127.0.0.1:3000

Open http://127.0.0.1:3000 — green when the Context Server + Obsidian backend are reachable.

## Sanity checks
    curl http://127.0.0.1:27180/health
    curl -X POST http://127.0.0.1:27180/mcp/search_notes \
      -H "X-Agent-Identity: opencode:task-0" -H "Content-Type: application/json" \
      -d '{"query": "hello"}'
```

* * *
## `context_server/requirements.txt`

```plain
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
pydantic==2.9.2
pydantic-settings==2.5.2
python-dotenv==1.0.1
```

* * *
## `context_server/.env.example`

```plain
# --- Obsidian backend (obsidian-local-rest-api) ---
OBSIDIAN_REST_API_KEY=paste-your-key-here
OBSIDIAN_HTTPS_URL=https://127.0.0.1:27124
OBSIDIAN_HTTP_URL=http://127.0.0.1:27123
# Trust the plugin's self-signed cert instead of disabling verification globally.
# Export it from the plugin (or fetch /obsidian-local-rest-api.crt) and point here:
OBSIDIAN_CERT_PATH=./obsidian-local-rest-api.crt
# Dev-only: allow falling back to plain HTTP 27123 if HTTPS cert can't be trusted.
ALLOW_HTTP_FALLBACK=true

# --- Context Server ---
CONTEXT_SERVER_HOST=127.0.0.1
CONTEXT_SERVER_PORT=27180
HOOKS_DIR=../hooks
```

* * *
## `context_server/app/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    obsidian_rest_api_key: str = ""
    obsidian_https_url: str = "https://127.0.0.1:27124"
    obsidian_http_url: str = "http://127.0.0.1:27123"
    obsidian_cert_path: str | None = None
    allow_http_fallback: bool = True

    context_server_host: str = "127.0.0.1"
    context_server_port: int = 27180
    hooks_dir: str = "../hooks"


settings = Settings()
```

* * *
## `context_server/app/db.py`

```python
"""The two SQLite stores. WAL mode so the frontend can read while the server writes."""
import os
import sqlite3
from contextlib import contextmanager

from .config import settings

TOKEN_DB = "token_usage.db"
CONTROL_DB = "control_plane.db"

_SCHEMA_TOKEN = """
CREATE TABLE IF NOT EXISTS token_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    agent TEXT NOT NULL,
    task_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    accepted INTEGER NOT NULL DEFAULT 0
);
"""

_SCHEMA_CONTROL = """
CREATE TABLE IF NOT EXISTS locks (
    resource TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    task_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL DEFAULT (datetime('now')),
    lease_expires_at TEXT
);
CREATE TABLE IF NOT EXISTS hibernation (
    task_id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    reason TEXT,
    frozen_state TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    agent TEXT NOT NULL,
    task_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    ok INTEGER NOT NULL,
    detail TEXT
);
"""


def _path(name: str) -> str:
    os.makedirs(settings.hooks_dir, exist_ok=True)
    return os.path.join(settings.hooks_dir, name)


@contextmanager
def connect(name: str):
    conn = sqlite3.connect(_path(name))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect(TOKEN_DB) as c:
        c.executescript(_SCHEMA_TOKEN)
    with connect(CONTROL_DB) as c:
        c.executescript(_SCHEMA_CONTROL)


def audit(agent: str, task_id: str, tool: str, ok: bool, detail: str = "") -> None:
    with connect(CONTROL_DB) as c:
        c.execute(
            "INSERT INTO audit_log (agent, task_id, tool, ok, detail) VALUES (?,?,?,?,?)",
            (agent, task_id, tool, 1 if ok else 0, detail),
        )
```

* * *
## `context_server/app/identity.py`

```python
"""Transport identity (Phase 2.8). Every tool call carries (agent, task_id)."""
from dataclasses import dataclass
from fastapi import Header, HTTPException


@dataclass
class AgentIdentity:
    agent: str
    task_id: str


async def require_identity(
    x_agent_identity: str | None = Header(default=None),
) -> AgentIdentity:
    # Format: "<agent>:<task_id>", e.g. "opencode:task-42".
    # TODO(phase-2.8): verify a signed token instead of trusting the header.
    if not x_agent_identity or ":" not in x_agent_identity:
        raise HTTPException(status_code=401, detail="Missing or malformed X-Agent-Identity header")
    agent, task_id = x_agent_identity.split(":", 1)
    if not agent or not task_id:
        raise HTTPException(status_code=401, detail="X-Agent-Identity must be '<agent>:<task_id>'")
    return AgentIdentity(agent=agent, task_id=task_id)
```

* * *
## `context_server/app/obsidian_backend.py`

```python
"""Thin proxy to obsidian-local-rest-api. We NEVER reimplement its tools; we add policy.

Handles the self-signed cert (trust the plugin's cert, do not disable verification globally)
with a documented HTTP fallback for dev.
"""
import ssl
import httpx

from .config import settings


def _build_client() -> httpx.AsyncClient:
    headers = {"Authorization": f"Bearer {settings.obsidian_rest_api_key}"}

    # Preferred: HTTPS with the plugin's pinned self-signed cert.
    if settings.obsidian_cert_path:
        try:
            ctx = ssl.create_default_context(cafile=settings.obsidian_cert_path)
            ctx.check_hostname = False  # cert CN is for 127.0.0.1 loopback
            return httpx.AsyncClient(
                base_url=settings.obsidian_https_url, headers=headers, verify=ctx, timeout=15.0
            )
        except (FileNotFoundError, ssl.SSLError):
            pass  # fall through to HTTP fallback

    if settings.allow_http_fallback:
        # Dev-only plain HTTP on 27123.
        return httpx.AsyncClient(
            base_url=settings.obsidian_http_url, headers=headers, timeout=15.0
        )

    raise RuntimeError(
        "No trusted Obsidian transport: set OBSIDIAN_CERT_PATH or ALLOW_HTTP_FALLBACK=true"
    )


class ObsidianBackend:
    def __init__(self) -> None:
        self._client = _build_client()

    async def health(self) -> bool:
        try:
            r = await self._client.get("/")
            return r.status_code < 500
        except httpx.HTTPError:
            return False

    async def search_simple(self, query: str) -> list[dict]:
        r = await self._client.post("/search/simple/", params={"query": query})
        r.raise_for_status()
        return r.json()

    async def read_note(self, path: str) -> dict:
        # Returns content + a version signal we use for OCC (Phase 2.10).
        r = await self._client.get(f"/vault/{path}", headers={"Accept": "application/vnd.olrapi.note+json"})
        r.raise_for_status()
        return r.json()

    async def append(self, path: str, content: str) -> None:
        # Append-only writes to designated log.md targets.
        r = await self._client.post(f"/vault/{path}", content=content,
                                    headers={"Content-Type": "text/markdown"})
        r.raise_for_status()

    async def patch(self, path: str, target_type: str, target: str, content: str,
                    reject_if_preexists: bool = True) -> None:
        # rejectIfContentPreexists = our idempotency / retry guard (Phase 2.3 / 6.6 / 6.7).
        headers = {
            "Operation": "append",
            "Target-Type": target_type,
            "Target": target,
            "Content-Type": "text/markdown",
        }
        if reject_if_preexists:
            headers["If-None-Match"] = "*"
        r = await self._client.patch(f"/vault/{path}", content=content, headers=headers)
        r.raise_for_status()

    async def aclose(self) -> None:
        await self._client.aclose()


backend = ObsidianBackend()
```

* * *
## `context_server/app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
import uvicorn

from .config import settings
from .db import init_db, audit, connect, CONTROL_DB
from .identity import require_identity, AgentIdentity
from .obsidian_backend import backend


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    await backend.aclose()


app = FastAPI(title="Agentic OS Context Server", version="0.2.0", lifespan=lifespan)


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
    return {"locks": locks, "recent_activity": recent}


# ---------- MCP tool surface (identity-bound) ----------
class SearchBody(BaseModel):
    query: str


class AppendBody(BaseModel):
    path: str          # e.g. "projects/agent-os/log.md"
    content: str


@app.post("/mcp/search_notes")
async def search_notes(body: SearchBody, ident: AgentIdentity = Depends(require_identity)):
    try:
        results = await backend.search_simple(body.query)
        audit(ident.agent, ident.task_id, "search_notes", True, f"{len(results)} hits")
        # TODO(phase-2.12): DLP-scrub results before returning.
        return {"results": results}
    except Exception as e:  # noqa: BLE001
        audit(ident.agent, ident.task_id, "search_notes", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")


@app.post("/mcp/read_note")
async def read_note(path: str, ident: AgentIdentity = Depends(require_identity)):
    try:
        note = await backend.read_note(path)
        audit(ident.agent, ident.task_id, "read_note", True, path)
        return note  # includes content + version signal for OCC
    except Exception as e:  # noqa: BLE001
        audit(ident.agent, ident.task_id, "read_note", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")


@app.post("/mcp/append_implement")
async def append_implement(body: AppendBody, ident: AgentIdentity = Depends(require_identity)):
    # TODO(phase-2.6): acquire_lock lease before write.
    # TODO(phase-6): permission-matrix check — only designated log.md headings are writable.
    try:
        await backend.append(body.path, body.content)
        audit(ident.agent, ident.task_id, "append_implement", True, body.path)
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        audit(ident.agent, ident.task_id, "append_implement", False, str(e))
        raise HTTPException(status_code=502, detail="Obsidian backend error")


if __name__ == "__main__":
    uvicorn.run(app, host=settings.context_server_host, port=settings.context_server_port)
```

* * *
## `context_server/app/__init__.py`

```python
# empty — marks the package
```

* * *
## `contracts/obsidian_backend.md`

```markdown
# Contract: Obsidian backend

- Endpoint: https://127.0.0.1:27124/mcp/  (HTTP fallback http://127.0.0.1:27123/mcp/)
- Auth: Authorization: Bearer <OBSIDIAN_REST_API_KEY> — held by the secrets bridge only.
  The Context Server's Obsidian client is the ONLY consumer of this key. Never in agent prompts.
- Direction rule: Obsidian → OKF is one-directional. Agents never write arbitrary human notes.
  Allowed writes: (a) designated agent-writable log.md headings, (b) the daily note's
  "Agent Updates" heading. Everything else is a permission-matrix DENY.
- Idempotency: every Obsidian-bound write wraps vault_patch with rejectIfContentPreexists=true
  so a thaw re-issue / breaker retry / crash-reconcile replay cannot double-append.
- OCC: read_note attaches a version hash; a human mid-flight edit surfaces as a state_changed
  rejection on the next agent write, never a silent overwrite.
```

The **Next.js Mission Control** frontend is on the next page of this doc.