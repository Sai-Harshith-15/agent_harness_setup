"""Lock manager (Phase 2.6, realized here) + OCC (Phase 2.10).

Locks are leased rows in control_plane.db so a crash leaves a reclaimable record
rather than an in-memory lock that vanishes. OCC compares a caller-supplied version
hash against the live note; a mismatch = state_changed (never a silent overwrite).
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from ..db import CONTROL_DB, connect

LEASE_SECONDS = 120

# In-memory map of task_id -> resource it is currently polling/waiting for.
_task_waiting_on = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def acquire_lock(resource: str, agent: str, task_id: str) -> None:
    # First, check if adding this dependency creates a deadlock
    visited = set()
    current_task = task_id
    current_resource = resource
    
    while current_resource:
        with connect(CONTROL_DB) as c:
            row = c.execute("SELECT task_id, lease_expires_at FROM locks WHERE resource=?", (current_resource,)).fetchone()
        if not row:
            break
        owner = row["task_id"]
        expires = datetime.fromisoformat(row["lease_expires_at"])
        if expires <= _now():
            break
        if owner == task_id:
            raise HTTPException(status_code=409, detail="deadlock_risk: cycle detected in lock DAG")
        if owner in visited:
            break
        visited.add(owner)
        current_resource = _task_waiting_on.get(owner)

    with connect(CONTROL_DB) as c:
        row = c.execute("SELECT agent, task_id, lease_expires_at FROM locks WHERE resource=?",
                        (resource,)).fetchone()
        if row:
            expires = datetime.fromisoformat(row["lease_expires_at"])
            held_by_other = row["task_id"] != task_id
            if held_by_other and expires > _now():
                _task_waiting_on[task_id] = resource
                raise HTTPException(status_code=409,
                                    detail=f"resource locked by {row['agent']}:{row['task_id']}")
        
        # Lock acquired, clear waiting state if any
        _task_waiting_on.pop(task_id, None)
        exp = (_now() + timedelta(seconds=LEASE_SECONDS)).isoformat()
        c.execute(
            "INSERT INTO locks (resource, agent, task_id, lease_expires_at) VALUES (?,?,?,?) "
            "ON CONFLICT(resource) DO UPDATE SET agent=excluded.agent, task_id=excluded.task_id, "
            "lease_expires_at=excluded.lease_expires_at",
            (resource, agent, task_id, exp),
        )


def release_lock(resource: str, task_id: str, reason: str = "released") -> None:
    with connect(CONTROL_DB) as c:
        c.execute("DELETE FROM locks WHERE resource=? AND task_id=?", (resource, task_id))


def check_occ(live_version: str, expected_version: str | None) -> None:
    # expected_version is what read_note handed the agent. If the live note moved, reject.
    if expected_version is not None and live_version != expected_version:
        raise HTTPException(status_code=409,
                            detail="state_changed: note was modified since it was read")


@contextmanager
def governed_write(resource: str, agent: str, task_id: str):
    acquire_lock(resource, agent, task_id)
    try:
        yield
    finally:
        release_lock(resource, task_id)
