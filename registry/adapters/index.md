---
id: adapters
title: Adapters Index
tags: [okf-index]
source: setup
---
# Adapters

Every agent in the OS is paired with an **adapter** — a thin documentation + templating layer that maps the *shared* protocol (MCP tools, `AGENTS.md`/`PLAN.md`/`IMPLEMENT.md`, OKF bundles) to the agent's *native* configuration file(s). The adapter does NOT execute code; it is a documented mapping.

## Context Server Adapters
- [context-server.md](./context-server.md) — Context Server itself
- [obsidian-local-rest-api.md](./obsidian-local-rest-api.md) — Obsidian MCP backend

## Agent Adapters
- [opencode.md](./opencode.md) — opencode orchestrator (filesystem adapter)
- [hermes.md](./hermes.md) — Hermes research delegate (HTTP adapter)
- [claude-code.md](./claude-code.md) — Claude Code coding delegate (HTTP adapter)

## Registration Ritual

To add a new agent `X` to the OS:

1. **Create the agent concept:** `registry/agents/X.md` as OKF `type: Agent` with minimum fields:
   - `id`, `role` (delegate), `adapter` (http/filesystem)
   - `cost_defaults` (max_turns, max_tokens)
   - `bindings` (OKF bundle paths this agent can write to)
   - `capabilities` (list of capability ids from `registry/capabilities/`)

2. **Create or reuse an adapter:** If no existing adapter fits, create `registry/adapters/X.md` as OKF `type: AgentAdapter` documenting:
   - Native config file path
   - Memory surfaces (reads/writes)
   - AGENTS.md source
   - Adapter flags
   - Cost defaults
   - Removal condition

3. **Log the registration:** Append to `registry/log.md` under today's date:
   `**Registration**: agent X added (adapter Y).`

4. **Update the index:** Add X to `registry/index.md` under "Registered Agents."

5. **Regenerate configs:** (Phase 5) Run the config generator to produce each project's native agent config from the shared templates.
