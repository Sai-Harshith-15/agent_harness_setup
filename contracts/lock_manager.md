# Contract: Lock Manager

> Phase 2.6 · Distributed lock manager with deadlock detection and OCC integration.

## 1. Lease Semantics

- Locks are keyed by `(resource_path)`.
- Lease duration: **120 seconds** (default TTL, configurable via `LEASE_SECONDS`).
- On `acquire_lock(resource_path)`:
  - If the resource is free (or held by the same `task_id`), the lease is granted immediately.
  - If held by a different `task_id` with an unexpired lease, the request blocks or returns `409 conflict`.
  - Expired leases are treated as free (no deadlock on crashed agents).
- On `release_lock(resource_path, task_id)`:
  - The lease is cleared. The release reason is recorded: `released`, `released:hibernation`, or `released:crash_recovery`.
- All lock events are written to the append-only lock table in `control_plane.db`.

## 2. Task-Dependency DAG Deadlock Detector

Every `acquire_lock` and `delegate_task` instantiation is recorded as a directed edge in a
server-side task-dependency DAG:

- Edge `T_holder -> T_requester`: "task T_requester is blocked waiting for a resource held by T_holder."
- Delegation edges: `parent -> child`.

**Before granting a lease**, the server checks whether the new edge would create a **cycle**.
If a cycle is detected:
- The lease is instantly refused with `deadlock_risk` error (HTTP 409).
- The error carries the would-be cycle path.
- The requesting agent must yield its current locks, abort, or hibernate.

**Cycle-detection:** O(V+E) per request via incremental reachability against the live-task graph.

## 3. Interaction With Other Subsystems

- **OCC (Phase 2.10):** Locks serialize the write instant; OCC guarantees the write works from a current view. Both are required.
- **Hibernation (Phase 6.6):** On freeze, locks are released with reason `released:hibernation`; on thaw, locks are re-acquired.
- **Crash Recovery (Phase 6.7):** On startup, stale locks are cleared with reason `released:crash_recovery`.
- **delegate_task (Phase 3.3):** Delegation edges are added to the DAG for deadlock detection.
