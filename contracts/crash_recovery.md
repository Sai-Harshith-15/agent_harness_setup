# Contract: Crash Recovery

> Phase 6.7 · Startup reconciliation hook for orphaned state after infrastructure crashes.

## 1. Startup Reconciliation Hook

On boot, before the Context Server serves any agent request:

### 1.1 Orphaned Sandbox Sweep
- Query the host for any sandbox whose `task_id` is not present in the active-connections table.
- Terminate them. Each kill is logged with the orphaned `task_id`.

### 1.2 Stale-Lock Clearance
- Clear all lock-lease entries whose owning `(agent, task_id)` is not backed by a live connection.
- Mark them `released:crash_recovery` in the append-only lock table.
- Done immediately, not via TTL expiry.

### 1.3 Open-Span Closure
- For every task whose span tree is still `open` and owning connection is gone:
  - Emit terminal `crash_recovery` span (Phase 2.5) closing the subtree.
  - Failure class: `infrastructure_crash`.

### 1.4 Task-State Finalization
- Mark every `in_progress` `PLAN.md` task not backed by a live connection as `failed:infrastructure_crash`.
- Append entry to `IMPLEMENT.md` with last-known span id for replay.
- Trigger Phase 6.4 rollback to task's pre-execution snapshot.

### 1.5 Hibernation-Record Integrity Check
- Verify Phase 6.6 hibernation store is intact (no partial writes from the crash).
- Corrupted records are quarantined and surfaced in Phase 7 evening review.

## 2. Idempotency

The reconciliation pass is idempotent — running it twice yields the same state.
A crash during recovery itself is safe (next boot re-runs cleanly).

## 3. Crash Root-Cause Capture

Where the host exposes it (systemd journal, container exit code, FastAPI startup error):
- Capture crash cause into first `IMPLEMENT.md` entry after boot.

## 4. Quota Interaction

Reaped tasks' compute spend up to the crash instant is still attributed to their `task_id` in the
Phase 7.3 token ledger. CAPO (Phase 7.4) correctly counts a crashed task as a rejected outcome.

## 5. Interaction With Other Subsystems

- **Lock Manager (Phase 2.6):** Stale locks cleared as `released:crash_recovery`.
- **Observability (Phase 2.5):** Open spans closed as `infrastructure_crash`.
- **Hibernation (Phase 6.6):** Record integrity verified on startup.
- **Snapshot/Rollback (Phase 6.4):** Rollback triggered for crashed tasks.
