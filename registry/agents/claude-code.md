---
type: Agent
title: claude-code
description: Coding and refactoring delegate.
tags: [code, refactor, review]
bindings: [okf/log.md, IMPLEMENT.md]
id: claude-code
role: delegate
adapter: http
capabilities: [code, refactor, review]
---
# claude-code

Coding and refactoring delegate.

## Native Config
- **Config file:** `CLAUDE.md`

## AGENTS.md Source
- `CLAUDE.md` at repo root, auto-generated from `AGENTS.md` template

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `IMPLEMENT.md` (per repo), `log.md` (per bundle)

## Removal Condition
Remove when the code + refactor + review capabilities are handled by a single
agent that also natively speaks the context-server MCP without an adapter layer.
