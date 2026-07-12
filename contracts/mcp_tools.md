# Contract: MCP Tools

> Phase 2.2 · Full tool surface contract.
> Every agent sees the same tool set; progressive disclosure keeps context lean.

## 1. Read Tools (readOnlyHint: true)

| Tool | Signature | Returns |
|------|-----------|---------|
| `search_notes` | `(query: str, max_results?: int, para_folder?: str)` → `list[NoteMatch]` | Matching notes from Obsidian vault, scored by relevance. |
| `read_note` | `(path: str)` → `NoteContent` | Full content + frontmatter of one Obsidian `.md` file. Includes `X-Version` header for OCC. |
| `search_okf` | `(query: str, bundle?: str, max_results?: int)` → `list[ConceptMatch]` | Matching concepts from all registered OKF bundles. |
| `get_concept` | `(concept_id: str, bundle?: str)` → `ConceptContent` | Full OKF concept document. Includes `X-Version` header for OCC. |
| `lookup_agent` | `(agent_id: str)` → `AgentEntry` | Agent registration from `registry/agents/<id>.md`. |
| `find_capability` | `(capability: str)` → `list[CapabilityEntry]` | Which agents provide a given capability. |
| `search_tools` | `(query?: str)` → `list[ToolSchema]` | Registered tools matching query. First step in progressive disclosure. |
| `load_tool_schema` | `(tool_id: str)` → `ToolSchema` | Full input/output schema for one tool. Second step in progressive disclosure. |

## 2. Write Tools (destructiveHint: true)

| Tool | Signature | OCC | DLP | Permissions |
|------|-----------|-----|-----|-------------|
| `append_implement` | `(phase: str, agent: str, task?: str)` → `{ok, version}` | Position-check on tail offset | Full DLP scrub | Orchestrator only |
| `log_decision` | `(section: str, decision: str, rationale?: str)` → `{ok, version}` | Position-check on tail offset | Full DLP scrub | Any agent |
| `acquire_lock` | `(resource_path: str, ttl_s?: int = 120)` → `{lease_id, expires_at}` | N/A (lock itself) | N/A | Any agent |
| `request_snapshot` | `(label?: str)` → `{snapshot_id, path}` | N/A | N/A | Any agent |

## 3. Orchestration Tools

| Tool | Signature | Notes |
|------|-----------|-------|
| `delegate_task` | `(target_agent: str, task_spec: str, bounds?: Bounds)` → `{task_id, spans}` | Orchestrator only. Spawns child task. Span nests under caller's OTel trace. |
| `request_clarification` | `(question: str, options?: list[str])` → `{hitl_id, status}` | Pauses loop, serializes state, pushes HITL prompt. |
| `request_credentials` | `(service: str, scope?: str)` → `{ok, env_injected: list[str]}` | Resolves scoped ephemeral credentials, injects into sandbox env. Agent never sees raw secret. |
| `compress` | `(content: str, budget?: int)` → `{compressed, hash, tokens_saved}` | Delegates to headroom for token reduction. |

## 4. Progressive Disclosure

Agents start with only `search_tools` loaded. The disclosure protocol:

1. Agent calls `search_tools(query)` to discover relevant tools.
2. Agent calls `load_tool_schema(tool_id)` to get the full input/output schema for a specific tool.
3. Agent uses the loaded schema to call the tool with correct arguments.

This prevents context bloat — the full 16-tool schema is never loaded into the system prompt.

## 5. Request Headers (All Calls)

| Header | Required | Value |
|--------|----------|-------|
| `X-Agent-Identity` | Yes | `{agent_id}:{task_id}` — transport-layer authenticated (Phase 2.8). Body claims are ignored. |
| `X-Expected-Version` | Writes only | Git blob SHA (tracked) or xxhash (untracked). `log.md` / `IMPLEMENT.md` use position offset. |
| `X-Provenance` | Yes | `trusted` or `untrusted`. Controls chaperon behavior (Phase 2.13). |
| `X-Lamport-Seq` | Yes | Monotonically increasing logical sequence number (Phase 2.5). |

## 6. Response Headers (All Calls)

| Header | Always | Notes |
|--------|--------|-------|
| `X-Version` | Yes | Content version hash for OCC on next write. |
| `X-Lamport-Seq` | Yes | Server's logical sequence counter after processing. |
| `Retry-After` | On 429 | Seconds until rate limit resets. |

## 7. Error Responses

| Status | Error Code | Meaning |
|--------|-----------|---------|
| 403 | `permission_denied` | Agent lacks write permission for target. |
| 403 | `dlp_violation` | Content matched a DLP pattern (block mode). |
| 412 | `state_changed` | OCC version mismatch — must re-read before re-writing. |
| 429 | `rate_limited` | Token-bucket exhausted. |
| 503 | `circuit_breaker_tripped` | Repeated identical call detected. |
| 409 | `deadlock_risk` | Lock acquisition would create a dependency cycle. |
| 422 | `identity_spoof_attempt` | Transport identity ≠ payload identity. |

## 8. Interaction With Other Subsystems

- **OCC (Phase 2.10):** Every read returns `X-Version`; every write requires `X-Expected-Version`.
  Append-only tools use position-offset checks, not content hashes.
- **DLP (Phase 2.12):** All write payloads pass through `DLPFilter.scrub()` before persistence.
  Read-tool *return* payloads are also scrubbed before reaching agent context.
- **Rate Limiter (Phase 2.11):** Token-bucket enforcement per `(agent, task_id)`. Weighted by tool cost.
- **Circuit Breaker (Phase 2.9):** Args-hash replay window per `(agent, task_id, tool)`.
- **Chaperon (Phase 2.13):** `X-Provenance: untrusted` gates write-tool access and triggers macro-span collapsing on reads.
