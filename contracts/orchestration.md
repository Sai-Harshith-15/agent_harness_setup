# Contract: Orchestration

> Phase 3.3 · Cross-agent task delegation protocol.
> Defines the orchestrator's exclusive role and the delegation lifecycle.

## 1. Orchestrator Monopoly

- The `opencode` CLI holds the **sole orchestrator role** (`role: orchestrator` in registry).
- No other registered agent may serve as the orchestrator.
- The orchestrator MUST declare `forbid_native_cross_agent: true` in its registry entry.

## 2. Delegation Protocol

All cross-agent work flows through the Context Server's `delegate_task` tool:

1. Orchestrator calls `delegate_task(target_agent, task_spec, bounds?)`.
2. Context Server validates the caller's transport identity is the registered orchestrator.
3. Server creates a child task record, spawns a `delegation` OTel span nested under the caller's trace.
4. Target agent receives the task via its adapter → loop → tools.
5. Child task results are written via `append_implement` / `log_decision` back through the server.
6. Orchestrator polls child task status or receives a completion event.

**Forbidden:** The orchestrator's native subagent protocol (e.g., opencode's built-in subtask spawning)
MUST NOT be used to host another registered agent. All cross-agent work goes through
`delegate_task`. Hosting another agent natively is an audit failure tagged `native_bypass` in the
Phase 2.5 trace.

## 3. Accepted Flip Monopoly

Only the orchestrator's transport identity (verified by Phase 2.8 signed tokens) may write
`accepted: true` on an `IMPLEMENT.md` row. Other agents may append progress rows (via
`append_implement` with their own identity) but CANNOT self-certify task acceptance.

The acceptance write is checked in two places:
- **Middleware (Phase 6.2):** `can_write()` verifies the transport principal is the orchestrator
  when the tool is `append_implement` and the payload contains `accepted: true`.
- **OCC (Phase 2.10):** The `IMPLEMENT.md` version token is position-offset based; the server
  rejects an acceptance write if the row was already accepted (idempotency guard).

## 4. Task Lifecycle (Delegation → Completion)

```
[Orchestrator]                    [Target Agent]                    [Context Server]
    |                                  |                                  |
    |-- delegate_task(agent, spec) --> |                                  |
    |                                  |        [creates child span]      |
    |                                  | <-- task payload + bounds --     |
    |                                  |                                  |
    |                                  |-- search_tools() --------------->|
    |                                  |-- load_tool_schema() ----------->|
    |                                  |-- append_implement() ----------->|
    |                                  |                                  |
    | <-- IMPLEMENT.md row appended -- |                                  |
    |                                  |                                  |
    |-- append_implement(accepted) --> |                                  |
    |                                  |        [verifies orchestrator]   |
    | <-- accepted: true --------------|                                  |
```

## 5. Verification

Before any task is marked complete, the harness MUST pass:

- The orchestrator's identity is authenticated at the transport layer (Phase 2.8).
- The `delegate_task` edge is recorded in the task-dependency DAG (Phase 2.6).
- The child task's OTel spans are nested under the parent's trace (Phase 2.5).
- `accepted: true` write is only accepted from the orchestrator transport principal.
- `IMPLEMENT.md` is append-only (Phase 3.4 validator); the accepted row cannot be deleted.
