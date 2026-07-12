# Context Server

> type: ContextServer
> title: Agentic OS Context Server
> description: Single delivery surface for the Agentic OS — the ONE place agents go to
>   ask "what do I need to know?" and to write back "here's what I decided."
> tags: [mcp, context, memory, tools]

## Connection

- **Transport:** HTTP MCP (FastAPI)
- **Host:** localhost:27180
- **Identity:** `X-Agent-Identity` header (HMAC-SHA256 signed token)

## Tool Surface

### Read Tools (readOnlyHint: true)

| Tool | Description |
|------|-------------|
| `search_notes` | Search Obsidian vault notes by query |
| `read_note` | Read a single Obsidian note by path |
| `search_okf` | Search OKF bundles for structured concepts |
| `get_concept` | Get one OKF concept by concept-id |
| `lookup_agent` | Look up a registered agent by id |
| `find_capability` | Find agents providing a capability |
| `search_tools` | Search available tools by description |
| `load_tool_schema` | Load full schema for one tool |

### Write Tools (destructiveHint: true)

| Tool | Description |
|------|-------------|
| `append_implement` | Append to IMPLEMENT.md under a heading |
| `log_decision` | Log a decision to a log.md heading |
| `acquire_lock` | Acquire a lease on a resource path |
| `request_snapshot` | Create a named restore point |

### Orchestration Tools

| Tool | Description |
|------|-------------|
| `delegate_task` | Delegate a sub-task to another agent |
| `request_clarification` | Pause and request human input |
| `request_credentials` | Request scoped ephemeral credentials |
| `compress` | Compress context to a token budget |
| `reindex` | Re-index the codebase graph |

## Backends

- **Obsidian backend:** `obsidian-local-rest-api` MCP proxy (primary brain).
- **OKF backend:** Local `okf/` bundle reader (secondary brain).
- **Graph backend:** `codebase_memory.db` with nodes + edges.
- **Compression backend:** headroom token-budget compactor.
- **Lock backend:** SQLite lease table in `control_plane.db`.
- **Secrets backend:** In-memory HMAC-derived ephemeral credentials.

## Progressive Disclosure

Agents start with only `search_tools` loaded. Full tool schemas are loaded on demand
via `load_tool_schema`. This prevents context bloat.

## Removal Condition

This component should be removed when all agents natively support a shared
memory + context pipeline without a central proxy server.
