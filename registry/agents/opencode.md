---
type: Agent
title: opencode
description: Orchestrator agent that owns the top-level loop.
tags: [orchestrate, plan, route, accept_implement]
bindings: [okf/log.md, registry/log.md, IMPLEMENT.md]
id: opencode
role: orchestrator
forbid_native_cross_agent: true
adapter: filesystem
capabilities: [orchestrate, plan, route, accept_implement]
---
# opencode (orchestrator)

Owns the top-level loop. Only identity allowed to flip an IMPLEMENT.md `gate: passed`
row to `accepted: true`. Front-line HITL receiver for delegated children.

## Native Config
- **Config file:** `opencode.json` / `opencode.jsonc`

## AGENTS.md Source
- Repo root (`./AGENTS.md`)

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `IMPLEMENT.md` (per repo), `log.md` (per bundle)

## Removal Condition
Remove when the orchestrator is no longer needed to route tasks between specialized delegates.
