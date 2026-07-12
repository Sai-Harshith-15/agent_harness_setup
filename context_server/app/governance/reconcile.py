"""Crash reconciliation (Phase 6.7). On startup (or on demand): reap expired lock
leases as crash_recovery, surface orphaned in-flight tasks, and expose a re-run hook.
"""
from datetime import datetime, timezone

from ..db import CONTROL_DB, audit, connect
from .hibernation import thaw


def reconcile(startup: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    reaped = []
    crashes = []
    rejected_hitl = []
    with connect(CONTROL_DB) as c:
        for row in c.execute("SELECT * FROM locks").fetchall():
            is_expired = datetime.fromisoformat(row["lease_expires_at"]) <= now
            if startup or is_expired:
                if startup:
                    crashes.append({"resource": row["resource"], "was": f"{row['agent']}:{row['task_id']}"})
                else:
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
        audit("system", "crash-reconcile", "release_lock", True, f"{r['resource']} released:ttl_expiry")
    for r in crashes:
        audit("system", "crash-reconcile", "release_lock", False, f"{r['resource']} released:infrastructure_crash")
        try:
            from opentelemetry import trace
            from opentelemetry.trace.status import Status, StatusCode

            from .snapshot import restore_snapshot
            tracer = trace.get_tracer(__name__)
            agent, task_id = r["was"].split(":", 1)
            with tracer.start_as_current_span("crash_reconcile") as span:
                span.set_attribute("resource", r["resource"])
                span.set_attribute("task_id", task_id)
                span.set_attribute("agent", agent)
                span.set_status(Status(StatusCode.ERROR, "infrastructure_crash"))
            restore_snapshot(task_id)
        except Exception as e:
            print("[reconcile] Failed to rollback/span for crash:", e)
    for r_id in rejected_hitl:
        audit("system", "crash-reconcile", "hitl_expire", True, f"hitl item {r_id} auto-expired")

    if startup and crashes:
        import os
        import re
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        plan_path = os.path.join(root, "PLAN.md")
        if os.path.exists(plan_path):
            with open(plan_path, "r", encoding="utf-8") as f:
                content = f.read()
            # finalize in-progress rows
            content = re.sub(r"- \[in-progress\]", "- [crash]", content)
            content = re.sub(r"- \[delegated\]", "- [crash]", content)
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write(content)

    return {"released_locks": reaped, "crashes": crashes, "hibernated_orphans": orphans, "rejected_hitl": rejected_hitl}
