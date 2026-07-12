# PLAN.md — agent_harness_setup

<!-- Kanban row format:
     [status] (id) title | agent=<id> capo=<n> tokens=<n>
     status values: backlog | in-progress | delegated | awaiting-hitl | hibernated | done | rejected -->

## Phase 0 — Foundations & contracts
- [done] (P0-1) Scaffold contracts/ + IMPLEMENT.md seed | agent=opencode capo=0 tokens=0

## Phase 1 — Wire the two brains
- [done] (P1-1) Obsidian backend proxy binding | agent=opencode capo=0 tokens=0
- [done] (P1-2) OKF bundle scaffold | agent=opencode capo=0 tokens=0

## Phase 2 — Context Server
- [done] (P2-1) FastAPI MCP + health + dashboard | agent=opencode capo=0 tokens=0
- [done] (P2-2) Lock manager + OCC + DLP | agent=opencode capo=0 tokens=0

## Phase 3 — Agent registry + delegate_task
- [done] (P3-1) Registry loader + adapters + delegate_task | agent=opencode capo=0 tokens=0

## Phase 4 — Per-project harness contract
- [done] (P4-1) Harness triad + checklist validator | agent=opencode capo=0 tokens=0
- [done] (P4-2) Read-only /vault browse path | agent=opencode capo=0 tokens=0

## Phase 5 — Indexing & generation
- [done] (P5-1) Indexing + generation | agent=antigravity capo=0 tokens=0

## Phase 6 — Verification, permissions, HITL, hibernation & crash reconciliation
- [done] (P6-1) Permission matrix + HITL gate | agent=opencode capo=0 tokens=0
- [done] (P6-2) Hibernation + crash reconciliation | agent=opencode capo=0 tokens=0

## Phase 7 — Daily ops & cost discipline (CAPO)
- [done] (P7-1) CAPO cost controller | agent=opencode capo=0 tokens=0

## Phase 8 — Meta-harness & Dream Cycle
- [done] (P8-1) Meta-harness loop | agent=opencode capo=0 tokens=0

## Phase 9 — Next.js Mission Control (full pages)
- [done] (P9-1) Full Mission Control UI pages | agent=opencode capo=0 tokens=0
- [delegated] (task-42.hermes.1) delegate:hermes | agent=hermes
