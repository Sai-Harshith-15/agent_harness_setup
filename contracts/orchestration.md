# Contract: Orchestration

- The `opencode` CLI holds the orchestrator role.
- No other registered agent serves as the orchestrator.
- **Rule on cross-agent delegation**: All cross-agent work must go through the Context Server's `delegate_task` tool. opencode's native subagent tool cannot be used to host another registered agent. Hosting another agent natively instead of through `delegate_task` is an audit failure.
- **Accepted flip monopoly**: Only the `opencode` transport identity can write the `accepted: true` state on an `IMPLEMENT.md` row. Other agents can append progress (via `append_implement`), but cannot self-certify acceptance.
