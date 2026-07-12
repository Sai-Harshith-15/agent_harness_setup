# Contract: Observability

> Phase 2.5 · Trajectory-level tracing with logical-clock ordering.
> Every reasoning step and tool call must be auditable and replayable.

## 1. Span Schema (OTel)

Every tool call and internal operation emits a span with these attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `agent` | str | Registered agent id (from transport identity, not payload). |
| `task_id` | str | Current task identifier. |
| `tool` | str | Tool name or operation name. |
| `args_hash` | str | SHA256 of serialized tool arguments (first 16 hex chars). |
| `in_tokens` | int | Estimated input tokens for this call. |
| `out_tokens` | int | Estimated output tokens for this call. |
| `latency_ms` | float | Wall-clock duration (for human display only). |
| `status` | str | `ok` or `error`. |
| `lamport_seq` | int | Monotonically increasing logical sequence counter. |
| `failure_class` | str | One of the classes below, or `none`. |
| `span_kind` | str | `tool_call`, `delegation`, `compaction`, `dream_cycle`, `crash_reconcile`, `hibernation`. |

Parent span per task; child spans for each tool call. Delegation edges nest under caller's trace.

## 2. Failure Classification Tags

Every non-ok span carries exactly one `failure_class`:

| Tag | Triggered By |
|-----|-------------|
| `context` | Stale OKF concept, missing Obsidian note, wrong version. |
| `constraint` | Permission denied, DLP block, chaperon violation, sandbox resource cap. |
| `planning` | Deadlock risk, invalid delegation target, malformed tool args. |
| `identity_spoof_attempt` | Transport identity ≠ payload identity (Phase 2.8). |
| `circuit_breaker` | Args-hash replay trip (Phase 2.9). |
| `rate_limited` | Token-bucket exhaustion (Phase 2.11). |
| `infrastructure_crash` | Task died without releasing locks; reconciliation span (Phase 2.6). |
| `secret_redacted` | Known secret shape matched and redacted (Phase 2.12). |
| `pii_redacted` | PII pattern matched and redacted (Phase 2.12). |
| `dlp_blocked` | Write blocked by DLP hit policy (Phase 2.12). |
| `dlp_quarantined` | Content diverted to quarantine table (Phase 2.12). |
| `state_changed` | OCC version mismatch (Phase 2.10). |
| `hibernation_thaw` | Task resumed from hibernation with stale-state warnings (Phase 6.6). |

## 3. Logical Sequence Counter (Lamport Timestamps)

To neutralize cross-sandbox clock drift (e.g., E2B microVM vs. local host):

- The Context Server maintains a **monotonically increasing logical sequence counter**,
  incremented atomically per-span.
- Every span carries `lamport_seq` (the counter value at span start).
- Every identity token (Phase 2.8) carries `lamport_seq` for expiry validation.
- Spans are ordered and nested by `lamport_seq` position, **not** by `start_at`/`end_at` timestamps.
- Wall-clock timestamps are kept only as human-readable hints; they do not govern ordering,
  expiry, or nesting.
- Client sends `X-Lamport-Seq` header; server merges with its own counter via `max(client_seq, server_seq) + 1`.

## 4. Export Pipeline

- **OTel exporter:** `OTLPSpanExporter` to `localhost:4317` (Jaeger). Gated by `ENABLE_OTEL=true`.
  When `ENABLE_OTEL=false` (or unset), a no-op exporter is used to silence test noise.
- **Langfuse exporter:** LLM-call-level traces via langfuse SDK. Requires `LANGFUSE_PUBLIC_KEY`
  and `LANGFUSE_SECRET_KEY`. Gated by `ENABLE_LANGFUSE=true`.
- **BatchSpanProcessor** with configurable batch size and schedule delay.

## 5. Macro-Span Collapsing (Chaperoned Branches)

When an agent processes untrusted-provenance content (Phase 2.13):

- Individual tool-call spans are **collapsed** into a single `span_kind=chaperoned_read` macro-span.
- The macro-span records: `total_calls`, `first_args_hash`, `last_args_hash`, `duration_ms`.
- Individual call arguments are dropped from permanent trace storage.
- On branch exit, a single `IMPLEMENT.md` summary line is written: "agent processed untrusted source X, made N read calls".
- The Phase 5.4 compactor skips chaperoned branches (they are already summarized).

## 6. Retention

- Raw OTel spans retained for 7 days (configurable via `OTEL_SPAN_RETENTION_DAYS`).
- Rollups to `IMPLEMENT.md` and `okf/log.md` occur daily at standup (9am local).
- Langfuse traces retained per Langfuse project configuration.
- Quarantine entries (Phase 2.12) retained until manually reviewed.

## 7. Interaction With Other Subsystems

- **Phase 2.8 identity:** Mismatched identity triggers `identity_spoof_attempt` failure class.
- **Phase 2.9 breaker:** Trip events emit `circuit_breaker` failure class.
- **Phase 2.11 rate limiter:** `429` responses emit `rate_limited` failure class.
- **Phase 2.12 DLP:** Redaction/block/quarantine events emit corresponding failure classes.
- **Phase 6.6 hibernation:** Freeze/thaw events emit `hibernation` spans with `hibernation_thaw` failure class.
- **Phase 8 dream cycle:** Meta-analysis spans emit `dream_cycle` spans.
