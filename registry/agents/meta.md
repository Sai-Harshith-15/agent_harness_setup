---
type: Agent
title: meta
description: The reflection agent for OS improvement.
tags: [reflect, propose_improvement, review_trajectory]
bindings: [okf/log.md, Program.md]
id: meta
role: delegate
adapter: http
capabilities: [reflect, propose_improvement, review_trajectory]
---
# meta

The reflection agent. Reads drift + CAPO + audit trails and proposes harness/prompt
improvements. Writes proposals ONLY to okf/log.md and Program.md via append_implement.
Never edits Obsidian human notes. Never flips an IMPLEMENT row to accepted.

## Native Config
- **Config file:** Configured internally as a background process.

## AGENTS.md Source
- Runs against `Program.md` instead of a project `AGENTS.md`.

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `Program.md`, `log.md` (per bundle)

## Removal Condition
Remove when the models can reliably self-optimize their own defaults dynamically.
