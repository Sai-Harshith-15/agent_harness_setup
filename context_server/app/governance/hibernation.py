"""Hibernation (Phase 6.6): freeze a task's state on request_clarification, thaw later.

Thaw re-issues the paused write, but the Obsidian idempotency guard
(rejectIfContentPreexists) means a re-issued append can never double-write.
"""
import json

from ..db import CONTROL_DB, connect


def hibernate(task_id: str, agent: str, reason: str, frozen_state: dict) -> None:
    with connect(CONTROL_DB) as c:
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
    return {"task_id": row["task_id"], "agent": row["agent"],
            "reason": row["reason"], "frozen_state": json.loads(row["frozen_state"] or "{}")}
