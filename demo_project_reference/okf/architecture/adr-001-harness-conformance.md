---
type: ArchitectureDecision
title: Harness Contract Conformance
description: Decision to conform this project to the Agentic OS Phase 4 harness contract.
tags: [harness, conformance]
timestamp: 2026-07-12
---
# ADR-001: Harness Contract Conformance

**Status:** Accepted

**Context:** The Agentic OS Phase 4 plan requires one reference downstream project
brought into conformance with the per-project harness contract.

**Decision:** This `demo_project_reference` project conforms to the contract:
- Harness triad files at root (AGENTS.md, PLAN.md, IMPLEMENT.md)
- HARNESS_CHECKLIST.md for pre-merge verification
- okf/ bundle with architecture, runbooks, and domain directories

**Consequences:**
- All agents read from the shared Context Server
- All agent writes go through `append_implement` / `log_decision`
- Human promotes noteworthy entries from IMPLEMENT.md to Obsidian
