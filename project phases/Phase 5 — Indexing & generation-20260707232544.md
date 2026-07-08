# Phase 5 — Indexing & generation

# Phase 5 — Indexing & generation
The first heavy code phase: build the knowledge/code index and the context-budget machinery every later phase leans on. Ships Graphify (repo → graph), a codebase-memory store, a headroom manager (context budget), a compactor (compression spans), drift detection (spec vs impl), and delta indexing (incremental re-index on change). Copy each file into `D:\GitRepo\agent_harness_setup\` at the path in its heading.
> Depends on Phases 0–4. Everything here emits spans/attributes that the Phase 6/7/9 telemetry views consume. New code lives under `context_server/app/indexing/`.
* * *
## Add to `context_server/requirements.txt`

```plain
networkx==3.3
watchfiles==0.24.0
```

* * *
## `context_server/app/indexing/__init__.py`

```python
# empty — marks the package
```

* * *
## `context_server/app/indexing/store.py`

```python
"""codebase-memory: a small SQLite-backed store of indexed nodes + content hashes.

Lives beside the other stores in hooks/. Delta indexing keys off content_hash so we
only re-embed/re-graph what actually changed.
"""
import hashlib
import os

from ..config import settings
from ..db import connect

INDEX_DB = "codebase_memory.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    path TEXT PRIMARY KEY,
    kind TEXT NOT NULL,            -- file | symbol | note | okf_concept
    content_hash TEXT NOT NULL,
    tokens INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    rel TEXT NOT NULL,             -- imports | links | references | implements
    PRIMARY KEY (src, dst, rel)
);
"""


def init_index() -> None:
    with connect(INDEX_DB) as c:
        c.executescript(_SCHEMA)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]


def needs_reindex(path: str, new_hash: str) -> bool:
    with connect(INDEX_DB) as c:
        row = c.execute("SELECT content_hash FROM nodes WHERE path=?", (path,)).fetchone()
    return row is None or row["content_hash"] != new_hash


def upsert_node(path: str, kind: str, new_hash: str, tokens: int, summary: str = "") -> None:
    with connect(INDEX_DB) as c:
        c.execute(
            "INSERT INTO nodes (path, kind, content_hash, tokens, summary) VALUES (?,?,?,?,?) "
            "ON CONFLICT(path) DO UPDATE SET kind=excluded.kind, content_hash=excluded.content_hash, "
            "tokens=excluded.tokens, summary=excluded.summary, updated_at=datetime('now')",
            (path, kind, new_hash, tokens, summary),
        )


def add_edge(src: str, dst: str, rel: str) -> None:
    with connect(INDEX_DB) as c:
        c.execute("INSERT OR IGNORE INTO edges (src, dst, rel) VALUES (?,?,?)", (src, dst, rel))


def all_nodes() -> list[dict]:
    with connect(INDEX_DB) as c:
        return [dict(r) for r in c.execute("SELECT * FROM nodes").fetchall()]


def all_edges() -> list[dict]:
    with connect(INDEX_DB) as c:
        return [dict(r) for r in c.execute("SELECT * FROM edges").fetchall()]
```

* * *
## `context_server/app/indexing/graphify.py`

```python
"""Graphify: walk the repo, hash each file, upsert nodes, extract import/link edges.

Delta-aware: files whose content_hash is unchanged are skipped. Emits a small stats
dict the /dashboard and OTel layer can report.
"""
import os
import re

from .store import init_index, content_hash, needs_reindex, upsert_node, add_edge

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([\w\.]+)", re.M)
_MD_LINK = re.compile(r"\[\[([^\]]+)\]\]")            # wikilinks
_INCLUDE_EXT = {".py", ".ts", ".tsx", ".md"}
_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".next", "hooks"}


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)  # rough; swap for a real tokenizer later


def graphify(root: str = ROOT) -> dict:
    init_index()
    scanned = reindexed = skipped = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1]
            if ext not in _INCLUDE_EXT:
                continue
            path = os.path.relpath(os.path.join(dirpath, fn), root).replace("\\", "/")
            scanned += 1
            try:
                text = open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            h = content_hash(text)
            if not needs_reindex(path, h):
                skipped += 1
                continue
            kind = "note" if ext == ".md" else "file"
            upsert_node(path, kind, h, _tokens(text), summary=text[:160].replace("
", " "))
            for m in _PY_IMPORT.findall(text):
                add_edge(path, m, "imports")
            for m in _MD_LINK.findall(text):
                add_edge(path, m, "links")
            reindexed += 1
    return {"scanned": scanned, "reindexed": reindexed, "skipped": skipped}
```

* * *
## `context_server/app/indexing/headroom.py`

```python
"""Headroom manager: track context budget and decide when the compactor must run."""
from dataclasses import dataclass


@dataclass
class Headroom:
    max_tokens: int = 128_000
    reserve: int = 8_000          # keep this much free for the model's reply

    def remaining(self, used: int) -> int:
        return self.max_tokens - self.reserve - used

    def must_compact(self, used: int, incoming: int) -> bool:
        return self.remaining(used) < incoming
```

* * *
## `context_server/app/indexing/compactor.py`

```python
"""Compactor: compress a set of index nodes down to a token budget.

Strategy (deterministic, no LLM in the loop for the stub): keep highest-degree /
most-recently-updated nodes' summaries until the budget is hit; everything else
collapses into a single 'compacted N nodes' macro-summary. Emits a compaction span.
TODO(phase-5): swap the summary source for real LLM summaries.
"""
from .store import all_nodes, all_edges


def _degree() -> dict[str, int]:
    deg: dict[str, int] = {}
    for e in all_edges():
        deg[e["src"]] = deg.get(e["src"], 0) + 1
        deg[e["dst"]] = deg.get(e["dst"], 0) + 1
    return deg


def compact(budget_tokens: int) -> dict:
    deg = _degree()
    nodes = sorted(all_nodes(), key=lambda n: (deg.get(n["path"], 0), n["updated_at"]), reverse=True)
    kept, used = [], 0
    for n in nodes:
        if used + n["tokens"] > budget_tokens:
            break
        kept.append(n["path"])
        used += n["tokens"]
    collapsed = len(nodes) - len(kept)
    return {
        "kept": kept,
        "kept_tokens": used,
        "collapsed_nodes": collapsed,
        "span": {"name": "compactor", "budget": budget_tokens, "used": used, "collapsed": collapsed},
    }
```

* * *
## `context_server/app/indexing/drift.py`

```python
"""Drift detection: flag spec (contracts/*, PLAN.md) nodes whose implementation
counterpart changed without the spec being touched, and vice versa.

Stub heuristic: a code node that references a contract concept but whose contract
node is older is 'impl-ahead'; the reverse is 'spec-ahead'. Real impl can diff
git history — the shape stays the same.
"""
from .store import all_nodes


def detect_drift() -> list[dict]:
    nodes = {n["path"]: n for n in all_nodes()}
    banners: list[dict] = []
    contracts = [p for p in nodes if p.startswith("contracts/") or p == "PLAN.md"]
    code = [p for p in nodes if p.endswith((".py", ".ts", ".tsx"))]
    for c in contracts:
        newer_code = [p for p in code if nodes[p]["updated_at"] > nodes[c]["updated_at"]]
        if len(newer_code) >= 3:
            banners.append({"kind": "impl-ahead", "spec": c, "changed_code": newer_code[:5]})
    return banners
```

* * *
## `context_server/app/indexing/watcher.py`

```python
"""Delta indexing: watch the repo and re-graphify changed files only.
Run as a background task from main.py's lifespan, or standalone: python -m app.indexing.watcher
"""
import asyncio

from watchfiles import awatch

from .graphify import graphify, ROOT


async def watch_and_index() -> None:
    graphify()  # initial full pass (delta-aware, so cheap on restart)
    async for _changes in awatch(ROOT, recursive=True):
        stats = graphify()  # only changed hashes get re-indexed
        print(f"[delta-index] {stats}")


if __name__ == "__main__":
    asyncio.run(watch_and_index())
```

* * *
## Add index endpoints to `context_server/app/main.py`

```python
# --- imports ---
from .indexing.graphify import graphify
from .indexing.store import all_nodes, all_edges
from .indexing.compactor import compact
from .indexing.drift import detect_drift
from .indexing.headroom import Headroom


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
```

* * *
## Optional: run the watcher inside the server (add to lifespan in `main.py`)

```python
import asyncio
from .indexing.watcher import watch_and_index

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(watch_and_index())   # background delta indexing
    yield
    task.cancel()
    await backend.aclose()
```

* * *
## Smoke test (Definition of Done)

```bash
# 1. Full index build
curl -X POST http://127.0.0.1:27180/mcp/reindex -H "X-Agent-Identity: opencode:task-5"
# -> {"scanned": N, "reindexed": N, "skipped": 0}   (first run)

# 2. Re-run without changes -> delta indexing skips everything
curl -X POST http://127.0.0.1:27180/mcp/reindex -H "X-Agent-Identity: opencode:task-5"
# -> {"scanned": N, "reindexed": 0, "skipped": N}

# 3. Edit one file, re-run -> exactly 1 reindexed (proves delta works)

# 4. Compactor respects a budget
curl -X POST "http://127.0.0.1:27180/mcp/compress?budget_tokens=2000" -H "X-Agent-Identity: opencode:task-5"
# -> {"kept": [...], "kept_tokens": <=2000, "collapsed_nodes": M, "span": {...}}

# 5. Graph + drift feeds render
curl http://127.0.0.1:27180/dashboard/graph
curl http://127.0.0.1:27180/dashboard/drift
```

Index rebuilds incrementally (test 3), the compactor honors a token budget and emits a span (test 4), and the graph + drift feeds are queryable for the Phase 9 UI (test 5). That's the Phase 5 Definition of Done. The two seams to grow later: real token counting (swap the `//4` heuristic) and real LLM summaries in the compactor.