---
type: Agent
title: antigravity
description: UI and End-to-End browser testing delegate.
tags: [browser, e2e, ui]
bindings: [okf/log.md, IMPLEMENT.md]
id: antigravity
role: delegate
adapter: http
capabilities: [browser, e2e, ui]
---
# antigravity

UI and End-to-End browser testing delegate.

## Native Config
- **Config file:** `.gemini/config` (or context equivalent)

## AGENTS.md Source
- Repo root (`./AGENTS.md`)

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `IMPLEMENT.md` (per repo), `log.md` (per bundle)

## Removal Condition
Remove when UI manipulation and E2E testing are handled by the native orchestrator.
