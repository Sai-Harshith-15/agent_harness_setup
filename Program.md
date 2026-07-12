# Program.md — top-level program ledger

> Drives what the orchestrator runs next. The Dream Cycle appends proposals here for
> human review; opencode reads the top unchecked item each loop.

## Metrics
- Active orphans: 0 (Target: 0)
- Average task token spend: 1500 (Target: < 5000)

## Audit Schedule
- Daily: Review open hitl_queue items.
- Weekly: Crash reconciliation snapshot review.
- **Quarterly:** Removal-condition audit — next: 2026-10-12 (see demo_project_reference/okf/architecture/adr-002-removal-audit.md)

## Now
- [ ] (PROG-1) Replace EchoAdapter with real filesystem + HTTP agent runners (Phase 3 seam)
- [ ] (PROG-2) Swap //4 token heuristic for a real tokenizer (Phase 5 seam)

## Proposed by Dream Cycle (human promotes ↑)
<!-- meta appends here nightly; never auto-executed -->
- [ ] (PROG-3) Upgrade token counter to tiktoken real encoding instead of heuristic.
