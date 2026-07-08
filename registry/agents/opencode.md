---
id: opencode
role: orchestrator
adapter: filesystem
native_subagent_protocol: opencode-subagents
cross_agent_delegation: delegate_task
cost_defaults:
  max_turns: 40
  orchestrator_overlay: true
capabilities: [orchestrate, plan, route, accept_implement]
---
# opencode (orchestrator)
Owns the top-level loop. Only identity allowed to flip an IMPLEMENT.md `gate: passed`
row to `accepted: true`. Front-line HITL receiver for delegated children.
