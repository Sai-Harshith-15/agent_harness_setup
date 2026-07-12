---
type: Agent
title: codex
description: Test writing and generation delegate.
tags: [code, tests]
bindings: [okf/log.md, IMPLEMENT.md]
id: codex
role: delegate
adapter: http
capabilities: [code, tests]
---
# codex

Test writing and generation delegate.

## Native Config
- **Config file:** `codex.json` (or context equivalent)

## AGENTS.md Source
- Repo root (`./AGENTS.md`)

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `IMPLEMENT.md` (per repo), `log.md` (per bundle)

## Removal Condition
Remove when test writing and generation can be reliably done without specialized sandboxing.
