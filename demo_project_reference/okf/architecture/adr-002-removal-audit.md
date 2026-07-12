---
type: ArchitectureDecision
title: Removal-Condition Audit
description: Schedule the quarterly removal-condition audit for all harness components.
tags: [meta-harness, audit, removal-condition]
timestamp: 2026-07-12
---
# ADR-002: Removal-Condition Audit Schedule

**Status:** Accepted

**Context:** Phase 8 requires quarterly re-walk of HARNESS_CHECKLIST.md "When this
harness component should be removed" rows for every registered component. Anything
the model can now do alone gets retired.

**Decision:** First audit scheduled for **2026-10-12** (Q4 2026). Subsequent audits
quarterly thereafter (Jan, Apr, Jul, Oct).

**Audit scope:**
- Every `registry/agents/*.md` — is the agent still needed or has the model absorbed its capabilities?
- Every `registry/adapters/*.md` — can the adapter be removed?
- Every `contracts/*.md` — is the contract still binding?
- Every tool in the context-server tool surface — can any be deprecated?

**Consequences:**
- Audit results must be logged to `IMPLEMENT.md`
- Retired components are archived, not deleted
- The audit itself may propose registry changes via `append_implement`
