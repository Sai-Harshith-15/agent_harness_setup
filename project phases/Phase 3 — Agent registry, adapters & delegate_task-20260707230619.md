# Phase 3 — Agent registry, adapters & delegate_task

# Phase 3 — Agent registry, adapters & opencode orchestrator
Stands up the agent layer on top of the Phase 0–2 Context Server. opencode CLI is the **single orchestrator**; every other agent is a registered delegate reached only via `delegate_task`. Copy each file into `D:\GitRepo\agent_harness_setup\` at the path in its heading.
> Depends on the Phase 0–2 backbone (previous pages). New files live under `context_server/app/` plus a `registry/` folder at repo root.
* * *
## `registry/agents/opencode.md`

```markdown
---
id: opencode
role: orchestrator          # exactly ONE agent may carry this
adapter: filesystem
native_subagent_protocol: opencode-subagents   # opencode-internal parallelism ONLY
cross_agent_delegation: delegate_task          # never host another agent via native Task tool
cost_defaults:
  max_turns: 40
  orchestrator_overlay: true   # higher budget; heavy orchestrator turns are a CAPO smell
capabilities: [orchestrate, plan, route, accept_implement]
---
# opencode (orchestrator)
Owns the top-level loop. Only identity allowed to flip an IMPLEMENT.md `gate: passed`
row to `accepted: true`. Front-line HITL receiver for delegated children.
```

* * *
## `registry/agents/hermes.md`

```markdown
---
id: hermes
role: delegate
adapter: http
cost_defaults: { max_turns: 20 }
capabilities: [research, summarize, knowledge_lookup]
---
# hermes
Research + knowledge delegate. Reached only via delegate_task.
```

> Create `claude-code.md`, `antigravity.md`, `codex.md` the same way (role: delegate, capabilities per their strengths: `claude-code` → \[code, refactor, review\]; `antigravity` → \[browser, e2e, ui\]; `codex` → \[code, tests\]).
* * *
## `context_server/app/registry.py`

```python
"""Loads registry/agents/*.md, parses YAML frontmatter, exposes lookup + capability search."""
import os
import glob

try:
    import yaml  # add pyyaml to requirements.txt
except ImportError:  # pragma: no cover
    yaml = None

REGISTRY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "registry", "agents")


def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    _, fm, _body = text.split("---", 2)
    return yaml.safe_load(fm) if yaml else {}


def load_agents() -> dict[str, dict]:
    agents: dict[str, dict] = {}
    for path in glob.glob(os.path.join(REGISTRY_DIR, "*.md")):
        with open(path, encoding="utf-8") as f:
            meta = _parse_frontmatter(f.read())
        if meta and meta.get("id"):
            agents[meta["id"]] = meta
    return agents


def lookup_agent(agent_id: str) -> dict | None:
    return load_agents().get(agent_id)


def find_capability(capability: str) -> list[str]:
    return [
        aid for aid, meta in load_agents().items()
        if capability in (meta.get("capabilities") or [])
    ]


def orchestrator_id() -> str | None:
    for aid, meta in load_agents().items():
        if meta.get("role") == "orchestrator":
            return aid
    return None
```

* * *
## `context_server/app/adapters.py`

```python
"""Adapter layer. Each registered agent is invoked through a uniform interface.

Phase 3 ships a filesystem adapter (opencode-style) and an http adapter shell.
The real agent execution is process/HTTP-specific; here we define the contract and a
local echo runner so delegate_task is end-to-end testable without live agents.
"""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class TaskResult:
    agent: str
    task_id: str
    ok: bool
    output: str
    tokens_in: int = 0
    tokens_out: int = 0


class AgentAdapter(Protocol):
    async def run(self, task_id: str, prompt: str, meta: dict) -> TaskResult: ...


class EchoAdapter:
    """Stand-in runner: proves the delegate path works before wiring real agents.
    TODO(phase-3): replace with real filesystem (opencode) + HTTP adapters."""
    async def run(self, task_id: str, prompt: str, meta: dict) -> TaskResult:
        out = f"[{meta.get('id')}] handled: {prompt[:120]}"
        return TaskResult(agent=meta.get("id", "?"), task_id=task_id, ok=True,
                          output=out, tokens_in=len(prompt) // 4, tokens_out=len(out) // 4)


def adapter_for(meta: dict) -> AgentAdapter:
    # TODO(phase-3): return FilesystemAdapter() / HttpAdapter() based on meta['adapter'].
    return EchoAdapter()
```

* * *
## `context_server/app/delegation.py`

```python
"""delegate_task control plane (Phase 3.3).

Rules enforced here:
  - Only the orchestrator may delegate.
  - Cross-agent work goes through this path, never a native subagent protocol.
  - Every delegated turn is logged to the token ledger + audit log.
  - Only the orchestrator identity may flip an IMPLEMENT.md acceptance row (see main.py).
"""
from fastapi import HTTPException

from .registry import lookup_agent, orchestrator_id
from .adapters import adapter_for, TaskResult
from .db import connect, TOKEN_DB, audit


async def delegate_task(caller: str, task_id: str, target_agent: str, prompt: str) -> TaskResult:
    if caller != orchestrator_id():
        raise HTTPException(status_code=403, detail="Only the orchestrator may delegate_task")

    meta = lookup_agent(target_agent)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{target_agent}'")
    if meta.get("role") == "orchestrator":
        raise HTTPException(status_code=400, detail="Cannot delegate to the orchestrator itself")

    result = await adapter_for(meta).run(task_id, prompt, meta)

    with connect(TOKEN_DB) as c:
        c.execute(
            "INSERT INTO token_ledger (agent, task_id, tool, tokens_in, tokens_out, accepted) "
            "VALUES (?,?,?,?,?,0)",
            (result.agent, task_id, "delegate_task", result.tokens_in, result.tokens_out),
        )
    audit(caller, task_id, "delegate_task", result.ok, f"-> {target_agent}")
    return result
```

* * *
## Add to `context_server/app/main.py`

```python
# --- imports (top of file) ---
from .registry import load_agents, lookup_agent, find_capability, orchestrator_id
from .delegation import delegate_task as _delegate_task


# --- new models ---
class DelegateBody(BaseModel):
    target_agent: str
    prompt: str


class AcceptBody(BaseModel):
    path: str      # IMPLEMENT.md location
    row_id: str    # the gate:passed row to accept


# --- registry endpoints ---
@app.get("/mcp/lookup_agent")
async def lookup_agent_ep(agent_id: str, ident: AgentIdentity = Depends(require_identity)):
    meta = lookup_agent(agent_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return meta


@app.get("/mcp/find_capability")
async def find_capability_ep(capability: str, ident: AgentIdentity = Depends(require_identity)):
    return {"capability": capability, "agents": find_capability(capability)}


@app.get("/dashboard/agents")
async def dashboard_agents():
    return {"agents": list(load_agents().values()), "orchestrator": orchestrator_id()}


# --- delegate_task ---
@app.post("/mcp/delegate_task")
async def delegate_task_ep(body: DelegateBody, ident: AgentIdentity = Depends(require_identity)):
    result = await _delegate_task(ident.agent, ident.task_id, body.target_agent, body.prompt)
    return {"ok": result.ok, "agent": result.agent, "output": result.output,
            "tokens_in": result.tokens_in, "tokens_out": result.tokens_out}


# --- acceptance gate: ONLY the orchestrator can flip a row to accepted ---
@app.post("/mcp/accept_implement")
async def accept_implement(body: AcceptBody, ident: AgentIdentity = Depends(require_identity)):
    if ident.agent != orchestrator_id():
        raise HTTPException(status_code=403, detail="Only the orchestrator may accept IMPLEMENT rows")
    with connect(TOKEN_DB) as c:
        c.execute("UPDATE token_ledger SET accepted=1 WHERE task_id=?", (body.row_id,))
    audit(ident.agent, ident.task_id, "accept_implement", True, f"{body.path}#{body.row_id}")
    # TODO(phase-6.3): also append the accepted row to IMPLEMENT.md via the Obsidian backend.
    return {"ok": True, "accepted": body.row_id}
```

* * *
## Add `pyyaml` to `context_server/requirements.txt`

```plain
pyyaml==6.0.2
```

* * *
## Smoke test (Definition of Done)

```bash
# 1. Orchestrator delegates to hermes
curl -X POST http://127.0.0.1:27180/mcp/delegate_task \
  -H "X-Agent-Identity: opencode:task-42" -H "Content-Type: application/json" \
  -d '{"target_agent": "hermes", "prompt": "summarize the obsidian backend contract"}'
# -> {"ok": true, "agent": "hermes", ...}

# 2. A NON-orchestrator delegating is rejected (403)
curl -X POST http://127.0.0.1:27180/mcp/delegate_task \
  -H "X-Agent-Identity: hermes:task-42" -H "Content-Type: application/json" \
  -d '{"target_agent": "codex", "prompt": "nope"}'
# -> 403 Only the orchestrator may delegate_task

# 3. Only orchestrator can accept an IMPLEMENT row
curl -X POST http://127.0.0.1:27180/mcp/accept_implement \
  -H "X-Agent-Identity: hermes:task-42" -H "Content-Type: application/json" \
  -d '{"path": "IMPLEMENT.md", "row_id": "task-42"}'
# -> 403

# 4. Capability discovery
curl "http://127.0.0.1:27180/mcp/find_capability?capability=research" \
  -H "X-Agent-Identity: opencode:task-42"
# -> {"capability": "research", "agents": ["hermes"]}
```

Green on all four = Phase 3 Definition of Done met: opencode delegates, delegates can't delegate, only the orchestrator accepts, and capability routing works. The `EchoAdapter` is the one seam to replace with real filesystem (opencode) + HTTP agent runners — everything else is production-shaped.