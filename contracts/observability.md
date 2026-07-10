# Contract: Observability

This contract defines the tracing and observability guidelines for the Agentic OS (Phase 5).

## 1. OpenTelemetry (OTel)
The context server uses `opentelemetry-instrumentation-fastapi`.
- All HTTP requests are traced.
- Critical background jobs (like `dream_cycle`) span explicit `tracer.start_as_current_span` blocks.
- Spans are exported to an OTLP endpoint on `localhost:4317`. If `ENABLE_OTEL=false`, a no-op exporter is used.

## 2. Langfuse Tracing
For LLM telemetry, the system integrates with Langfuse.
- `litellm.success_callback = ["langfuse"]`
- Each generation includes token counts, model details, and latency.

## 3. Crash Reconciliation
When a task dies unexpectedly:
- The `snapshot` subsystem restores the environment.
- The `reconcile.py` daemon explicitly closes dangling OTel spans with a status of `infrastructure_crash`.
