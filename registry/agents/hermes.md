---
type: Agent
title: hermes
description: Research + knowledge delegate. Reached only via delegate_task.
tags: [research, summarize, knowledge_lookup]
bindings: [okf/log.md, IMPLEMENT.md]
id: hermes
role: delegate
adapter: http
capabilities: [research, summarize, knowledge_lookup]
---
# hermes

Research + knowledge delegate. Reached only via delegate_task.

## Native Config
- **Config file:** Hermes `config.yaml`

## AGENTS.md Source
- Repo root (`./AGENTS.md`)

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `IMPLEMENT.md` (per repo), `log.md` (per bundle)

## Removal Condition
Remove when the research + summarize + knowledge_lookup capabilities are absorbed
by the orchestrator's native model without requiring a separate agent process.
