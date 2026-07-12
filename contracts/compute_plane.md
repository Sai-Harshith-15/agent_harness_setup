# Contract: Compute Plane

> Phase 0.5 · Sandbox technology choice and resource-cap defaults.

## 1. Sandbox Technology

- **Default:** E2B-style Firecracker microVMs for kernel-level isolation.
- **Local fallback:** gVisor/Kata Containers when no cloud sandbox provider is available.
- **Current implementation:** `SandboxDriver` in `context_server/app/meta/sandbox.py` provides
  an in-process stub with per-sandbox ephemeral credential injection.

## 2. Isolation Requirements

- **Kernel-level isolation:** No workspace escape, no PII leakage to host.
- **Resource caps:** Per-tool CPU / wall-clock / memory / egress limits.
- **Lifecycle:** Sandbox spawned per task (or per destructive tool call).
  Torn down at task end. No long-lived state escapes the sandbox except via context-server write tools.

## 3. Resource Bounds

Per-task bounds derived from `PLAN.md` or adapter defaults:

| Bound | Default | Description |
|-------|---------|-------------|
| `max_tokens` | unlimited | Total token budget for the task |
| `max_turns` | 60 | Maximum tool-call turns |
| `max_depth` | 3 | Maximum delegation depth |
| `wall_clock_s` | 3600 | Maximum wall-clock duration |
| `cpu_cores` | 1 | CPU allocation |
| `memory_mb` | 512 | Memory allocation |

## 4. Secrets Injection

Per-sandbox ephemeral credentials are injected into the sandbox environment on spawn.
The agent never sees the raw secret; it sees only `{ ok: true, env_injected: [...] }`.

## 5. Interaction With Other Subsystems

- **Secrets Bridge (Phase 2.7):** Ephemeral credentials injected on spawn.
- **Hibernation (Phase 6.6):** Sandbox terminated on freeze, fresh sandbox provisioned on thaw.
- **Crash Recovery (Phase 6.7):** Orphaned sandboxes reaped on startup.
