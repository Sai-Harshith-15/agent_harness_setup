---
type: AgentAdapter
title: Claude Code Adapter
tags: [mcp, filesystem, subagent]
---
# Claude Code Adapter

Maps the shared agent harness protocol to claude-code's native configuration.

## Native Config
- **Config file:** `CLAUDE.md` (generated from `AGENTS.md` template — just a rename)
- **State dir:** `.claude/`
- **Transport:** HTTP (contacted via context server's adapter layer)

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `IMPLEMENT.md` (per repo), `log.md` (per bundle)

## AGENTS.md Source
- `CLAUDE.md` at repo root, auto-generated from `AGENTS.md` template
- The adapter maps `CLAUDE.md` → `AGENTS.md` (they are identical by convention)

## Adapter Flags
- `subagent-support`: true (claude-code Task tool)
- `mcp-support`: true
- `forbid_native_cross_agent`: true (must use context-server `delegate_task`, not native Task tool for cross-agent delegation)

## Cost Defaults
```yaml
cost_defaults:
  max_turns: 20
  hard_stop: true
  effort_level: off
  model_aux: cheaper-model
  compression_threshold: below-default
```

## Registration Step
1. Create `registry/agents/claude-code.md` with `type: Agent`
2. Run the Phase 5 config generator to produce `CLAUDE.md` from `AGENTS.md`
3. Append to `registry/log.md`: `**Registration**: agent claude-code added (adapter http)`

## Removal Condition
Remove when the code + refactor + review capabilities are handled by a single
agent that also natively speaks the context-server MCP without an adapter layer.
