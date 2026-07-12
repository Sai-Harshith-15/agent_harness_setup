---
type: AgentAdapter
title: Hermes Adapter
tags: [mcp, http, research]
---
# Hermes Adapter

Maps the shared agent harness protocol to Hermes' native configuration.

## Native Config
- **Config file:** Hermes `config.yaml`
- **Endpoint:** `http://127.0.0.1:8001/run` (FastAPI runner at `registry/agents/hermes/run.py`)
- **Identity:** HMAC-signed `X-Agent-Identity` header

## Memory Surfaces
- **Reads:** Obsidian (via context server), OKF bundle (per repo)
- **Writes:** `IMPLEMENT.md` (per repo), `log.md` (per bundle)

## AGENTS.md Source
- Repo root (`./AGENTS.md`), generated from harness template

## Adapter Flags
- `needs-ephemeral-prompt`: true (cost-control from Hermes transcript)
- `auto-memory-off`: true (disable unless team-context needed)
- `compression-threshold`: below-default
- `target-ratio`: low
- `tool-output-limits`: low (with headroom `compress` as escape valve)
- `undo-over-reprompt`: true

## Cost Defaults
```yaml
cost_defaults:
  max_turns: 20
  max_tokens: 50000
  effort_level: off
  hard_stop: true
  model_aux: cheaper-model
  model_subagent: cheaper-model
```

## Registration Step
1. Create `registry/agents/hermes.md` with `type: Agent`
2. Ensure `registry/agents/hermes/run.py` is at the configured endpoint
3. Append to `registry/log.md`: `**Registration**: agent hermes added (adapter http)`

## Removal Condition
Remove when the research + summarize + knowledge_lookup capabilities are absorbed
by the orchestrator's native model without requiring a separate agent process.
