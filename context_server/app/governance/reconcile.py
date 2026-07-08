"""Crash reconciliation (Phase 6.7). On startup (or on demand): reap expired lock
leases as crash_recovery, surface orphaned in-flight tasks, and expose a re-run hook.
"""
from datetime import datetime, timezone

from ..db import CONTROL_DB, audit, connect
from .hibernation import thaw


def reconcile() -> dict:
    now = datetime.now(timezone.utc)
    reaped = []
    rejected_hitl = []
    with connect(CONTROL_DB) as c:
        for row in c.execute("SELECT * FROM locks").fetchall():
            if datetime.fromisoformat(row["lease_expires_at"]) <= now:
                reaped.append({"resource": row["resource"], "was": f"{row['agent']}:{row['task_id']}"})
                c.execute("DELETE FROM locks WHERE resource=?", (row["resource"],))

        try:
            # Table might not have expires_at if it's an old DB without migrations
            for row in c.execute("SELECT * FROM hitl_queue WHERE status='open' AND expires_at IS NOT NULL").fetchall():
                if datetime.fromisoformat(row["expires_at"]) <= now:
                    c.execute("UPDATE hitl_queue SET status='rejected', resolution='auto-expired' WHERE id=?", (row["id"],))
                    thaw(row["task_id"])
                    rejected_hitl.append(row["id"])
        except Exception:
            pass # ignore schema errors if not migrated

        orphans = [dict(r) for r in c.execute("SELECT * FROM hibernation").fetchall()]
    for r in reaped:
        audit("system", "crash-reconcile", "release_lock", True, f"{r['resource']} released:crash_recovery")
    for r_id in rejected_hitl:
        audit("system", "crash-reconcile", "hitl_expire", True, f"hitl item {r_id} auto-expired")
    return {"released_locks": reaped, "hibernated_orphans": orphans, "rejected_hitl": rejected_hitl}
