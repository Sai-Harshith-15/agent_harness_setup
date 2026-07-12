# Contract: Delegation

> Phase 3.3 · Inter-agent delegation via `delegate_task` tool.

## 1. Tool Payload

```
delegate_task(
  delegate_to: str,      # Registered agent id from registry/agents/
  task_spec: str,        # Self-contained scope string written into PLAN.md
  input_bindings?: list,  # Which OKF concepts/files/locks child can touch
  expected_output?: str,  # Contract the child must satisfy
  bounds?: {              # CPU/wall-clock/token budget for child
    max_tokens?: int,
    max_depth?: int
  }
)
```

- `delegate_to`: Validated against transport-authenticated caller (Phase 2.8). Caller cannot delegate *as* someone else.
- `bounds`: <= parent's remaining budget.

## 2. Server-Side Actions

1. **Write child task row** into project's `PLAN.md`, parented to caller's `task_id`. Delegation is visible in the plan.
2. **Provision new sandbox** (Phase 0.5) for the child with narrowed `input_bindings`.
3. **Issue child agent its own signed identity token** (Phase 2.8). Child's writes attributed to the child, not the parent.
4. **Nest OTel spans:** Every child tool call becomes a child span under the parent's task trace.
5. **Apply Permission Matrix** (Phase 6.2) to the child independently — delegation never widens privilege.

## 3. Completion Contract

- When the child's Phase 6.3 gate passes: result is returned to the parent's context as the tool's return value.
- `PLAN.md` child row is marked done.
- If the child fails or hits the Phase 2.9 circuit breaker: failure class propagates up the span tree.
  Parent can retry, re-delegate, or call `request_clarification`.

## 4. Recursion Guard

- `delegate_task` depth is capped (default 3).
- Counted toward the parent's `max_turns` budget.
- Each hop is visible as its own span subtree.

## 5. Interaction With Other Subsystems

- **Identity (Phase 2.8):** Child's writes attributed to child principal.
- **Permission Matrix (Phase 6.2):** Delegation never widens privilege.
- **Lock Manager (Phase 2.6):** Delegation edges added to DAG for deadlock detection.
- **Observability (Phase 2.5):** Full span nesting from parent through child.
