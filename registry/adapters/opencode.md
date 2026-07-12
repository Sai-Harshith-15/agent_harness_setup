---
type: AgentAdapter
title: opencode Adapter
tags: [mcp, filesystem, subagent]
---
# opencode Adapter

Maps the shared agent harness protocol to opencode's native configuration.
opencode is the **orchestrator** — the only identity allowed to flip `IMPLEMENT.md`
rows to `accepted: true` and the only caller of `delegate_task`.

## Native Config
- **Config file:** `opencode.json` / `opencode.jsonc`
- **Transport:** filesystem (CLI subprocess)
- **Role:** orchestrator

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `IMPLEMENT.md` (per repo), `registry/log.md`, `okf/log.md` (per bundle)

## AGENTS.md Source
- Repo root (`./AGENTS.md`)

## Orchestrator Privileges
- `accept_implement`: exclusive flip of `accepted: true` on `IMPLEMENT.md` rows
- `delegate_task`: exclusive right to spawn child tasks under other agents
- `forbid_native_cross_agent`: true (must use context-server `delegate_task`, not native subagents)

## Adapter Flags
- `filesystem-first`: true
- `subagent-support`: true

## Cost Defaults
```yaml
cost_defaults:
  max_turns: 40
  orchestrator_overlay: true
  hard_stop: true
  effort_level: off
  model_aux: cheaper-model
```

## Registration Step
1. Create `registry/agents/opencode.md` with `type: Agent`
2. Set `role: orchestrator` and `forbid_native_cross_agent: true`
3. Append to `registry/log.md`: `**Registration**: agent opencode added (adapter filesystem, role orchestrator)`

## Removal Condition
Remove when any registered agent can safely flip `IMPLEMENT.md` `accepted: true`
without an orchestrator-mediated consensus check. That implies a decentralized
acceptance protocol — not foreseen short-term.
