# Agent Harness Setup — Project Documentation

## Overview
This is **Phase 9** of the Agent Harness Engineering project. A multi-phase orchestration platform that integrates Claude Code agents with Obsidian (knowledge backend), control plane governance, and a Mission Control frontend (Next.js).

**Current Status:** Phase 9 nearly complete (P9-2 Audit in progress)

## Key Architecture

### Three Pillars
1. **Registry** (`registry/`) — Agent definitions + adapters (opencode, hermes, claude-code, antigravity, codex)
2. **Context Server** (`context_server/app/`) — FastAPI control plane with:
   - Lock manager (SQLite leases + in-memory DAG)
   - Indexing/graphification (file system + drift detection)
   - Governance (permissions matrix, OCC, DLP, rate-limiter)
   - HITL hibernation queue
   - Crash reconciliation
   - FinOps metering & rollups
3. **Mission Control Frontend** (`frontend/`) — Next.js dashboard + plan parser

### Contracts
- `contracts/obsidian_backend.md` — Obsidian local REST API binding
- `contracts/orchestration.md` — Agent delegation + isolation rules
- `contracts/sandbox_driver.md` — Capability routing & sandboxing

## Implementation Phases (Completed ✅)
- **P0** — Foundations & contracts
- **P1** — Registry + Obsidian binding
- **P2** — Context server core (locks, identity, dashboards)
- **P3** — Agent registry + delegation + DoD test
- **P4** — Harness triad + check_harness.py
- **P5** — Indexing & reindex/compact/drift endpoints
- **P6** — Governance & resilience (permissions, OCC, HITL, reconciliation)
- **P7** — FinOps metering + standup
- **P8** — Dream Cycle analysis + nightly runner
- **P9** — Mission Control Next.js frontend + Playwright audit (P9-2 in progress)

## Critical Files
- `IMPLEMENT.md` — append-only ledger of completed work + deviations
- `PLAN.md` — original task roadmap
- `project_documentation.md` — detailed architecture specs
- `AGENTS.md` — agent capability definitions
- `HARNESS_CHECKLIST.md` — QA checklist
- `check_harness.py` — smoke test runner

## Known Deviations from Plan
1. `forbid_native_cross_agent` flag naming (uses `cross_agent_delegation` instead)
2. OKF concept frontmatter incomplete (strict SPEC requirement)

## MCP & Tools Available
- **headroom** — Context compression (headroom_compress, headroom_retrieve, headroom_stats)
- **graphify** — Knowledge graph generation over codebases
- **Explore** — Code search agent
- **Workflow** — Multi-agent orchestration

## Next Immediate Steps
1. **Resolve P9-2 Audit** — Fix Playwright tests (NextJS backend fetch issue)
2. **Complete Phase 9** — Dashboard/plan parser integration
3. **Post-Phase 9** — Schedule post-implementation reviews + FinOps tuning

## Memory System
Project context is persisted in `.claude/memory/` with MEMORY.md index. Use `[[memory-name]]` to link related facts.
