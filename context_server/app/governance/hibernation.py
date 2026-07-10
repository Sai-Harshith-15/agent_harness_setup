"""Hibernation (Phase 6.6): freeze a task's state on request_clarification, thaw later.

Thaw re-issues the paused write, but the Obsidian idempotency guard
(rejectIfContentPreexists) means a re-issued append can never double-write.
"""
import json

from ..db import CONTROL_DB, connect


def hibernate(task_id: str, agent: str, reason: str, frozen_state: dict) -> None:
    with connect(CONTROL_DB) as c:
        # P22: release locks on freeze
        locks = c.execute("SELECT resource FROM locks WHERE task_id=?", (task_id,)).fetchall()
        lock_resources = [row["resource"] for row in locks]
        for r in lock_resources:
            c.execute("DELETE FROM locks WHERE resource=? AND task_id=?", (r, task_id))
            
        frozen_state["_locks"] = lock_resources
        
        c.execute(
            "INSERT INTO hibernation (task_id, agent, reason, frozen_state) VALUES (?,?,?,?) "
            "ON CONFLICT(task_id) DO UPDATE SET reason=excluded.reason, "
            "frozen_state=excluded.frozen_state",
            (task_id, agent, reason, json.dumps(frozen_state)),
        )


def thaw(task_id: str) -> dict | None:
    with connect(CONTROL_DB) as c:
        row = c.execute("SELECT * FROM hibernation WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            return None
        c.execute("DELETE FROM hibernation WHERE task_id=?", (task_id,))
        
    frozen_state = json.loads(row["frozen_state"] or "{}")
    agent = row["agent"]
    
    # P22: re-acquire locks on thaw
    from .locks import acquire_lock
    for r in frozen_state.get("_locks", []):
        acquire_lock(r, agent, task_id)
        
    # P22: stale-on-thaw drift recheck
    from ..indexing.drift import detect_drift
    drift = detect_drift()
    if drift:
        frozen_state["_drift"] = drift
        
    return {"task_id": row["task_id"], "agent": agent,
            "reason": row["reason"], "frozen_state": frozen_state}
