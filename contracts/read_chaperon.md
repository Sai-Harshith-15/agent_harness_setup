# Contract: Read-Edge Context Chaperoning

> Phase 2.13 · Denial-of-context defense for untrusted-provenance read loops.

## 1. Untrusted-Provenance Read Isolation

When an agent reads data flagged with an untrusted provenance tag (`X-Provenance: untrusted`):
- The Context Server **isolates that task's telemetry stream** into a chaperoned branch.
- Reads are still allowed (the open loop must process the untrusted content).
- The branch is marked `untrusted_processing`.

## 2. Macro-Span Collapsing

While the chaperoned branch is open:
- Duplicate or high-frequency read spans are **collapsed** into a single aggregated macro-span.
- Individual high-entropy arguments are dropped from permanent trace storage.
- A count + the first/last args are retained as samples.
- Trace growth is bounded to O(1) per branch, not O(calls).

## 3. Branch-Exit Flush

When the agent exits the untrusted processing branch:
- The macro-span is sealed.
- A single summary entry is written to `IMPLEMENT.md`: "agent processed untrusted source X, made N read calls."
- The human review pipeline sees one line, not a flooded log.

## 4. Compactor Protection

The Phase 5.4 compactor treats chaperoned branches as already-summarized and **skips them**.
This prevents the compactor from being throttled re-summarizing injected trash.

## 5. Limiter-Coupled HITL Escalation

When the Phase 2.11 rate limiter trips inside a chaperoned branch:
- Auto-escalates to Phase 6.5 HITL.
- An untrusted-source-driven burst is the highest-risk read pattern.

## 6. Write-Side Gate

The chaperon also gates **writes**: `X-Provenance: untrusted` blocks `append_implement` and `log_decision` calls.
This prevents untrusted content from being persisted into the OS's durable stores.

## 7. Interaction With Other Subsystems

- **Permission Matrix (Phase 6.2):** Provenance tag is the single primitive gating both read and write edges.
- **Rate Limiter (Phase 2.11):** Limiter trips inside chaperoned branches auto-escalate HITL.
- **Compactor (Phase 5.4):** Skips chaperoned branches.
- **HITL (Phase 6.5):** Auto-triggered on limiter-coupled escalation.
