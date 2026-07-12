---
id: registry
title: Agent Registry
tags: [okf-bundle]
source: setup
---
# Agent Registry

This is the OKF bundle root for the Agent Registry. The registry is the OS's single source of truth for:
- Which agents exist in the system
- How they are configured and reached (adapters)
- What capabilities they provide
- The orchestrator monopoly

## Registered Agents

| Agent | Role | Adapter | Capabilities |
|-------|------|---------|-------------|
| [opencode](./agents/opencode.md) | orchestrator | filesystem | orchestrate, plan, route, accept_implement |
| [hermes](./agents/hermes.md) | delegate | http | research, summarize, knowledge_lookup |
| [claude-code](./agents/claude-code.md) | delegate | http | code, refactor, review |
| [codex](./agents/codex.md) | delegate | http | code, tests |
| [antigravity](./agents/antigravity.md) | delegate | http | browser, e2e, ui |
| [meta](./agents/meta.md) | delegate | http | reflect, propose_improvement, review_trajectory |

## Context Server
- **Connection:** `http://127.0.0.1:27180` (HTTP MCP, FastAPI)
- **Identity:** `X-Agent-Identity` header (HMAC-SHA256 signed token)
- **Adapter:** [context-server.md](./adapters/context-server.md)

## Adapters
- [Index](./adapters/index.md) — Registration ritual and adapter catalog
- [opencode](./adapters/opencode.md) — opencode orchestrator adapter
- [hermes](./adapters/hermes.md) — Hermes research delegate adapter
- [claude-code](./adapters/claude-code.md) — Claude Code coding delegate adapter
- [context-server](./adapters/context-server.md) — Context Server itself
- [obsidian-local-rest-api](./adapters/obsidian-local-rest-api.md) — Obsidian MCP backend

## Capabilities
- [Index](./capabilities/index.md)
- [orchestrate](./capabilities/orchestrate.md)
- [code](./capabilities/code.md)
- [browser](./capabilities/browser.md)
- [research](./capabilities/research.md)
- [reflect](./capabilities/reflect.md)

## Log
- [log.md](./log.md) — Append-only audit ledger of agent registrations and changes.
