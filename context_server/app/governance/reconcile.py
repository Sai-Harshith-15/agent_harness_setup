"""Crash reconciliation (Phase 6.7). On startup (or on demand): reap expired lock
leases as crash_recovery, surface orphaned in-flight tasks, and expose a re-run hook.
"""
from datetime import datetime, timezone

from ..db import connect, CONTROL_DB, audit


def reconcile() -> dict:
    now = datetime.now(timezone.utc)
    reaped = []
    with connect(CONTROL_DB) as c:
        for row in c.execute("SELECT * FROM locks").fetchall():
            if datetime.fromisoformat(row["lease_expires_at"]) <= now:
                reaped.append({"resource": row["resource"], "was": f"{row['agent']}:{row['task_id']}"})
                c.execute("DELETE FROM locks WHERE resource=?", (row["resource"],))
        orphans = [dict(r) for r in c.execute("SELECT * FROM hibernation").fetchall()]
    for r in reaped:
        audit("system", "crash-reconcile", "release_lock", True, f"{r['resource']} released:crash_recovery")
    return {"released_locks": reaped, "hibernated_orphans": orphans}
