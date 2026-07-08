"""HITL clarification queue (Phase 6, D8). A child calls request_clarification; the
Context Server pauses it (hibernation) and enqueues a prompt routed to BOTH the
orchestrator and Mission Control's /hitl page. A pending write carries a diff preview
for the diff-modal.
"""
import json
from datetime import datetime, timedelta, timezone

from ..db import CONTROL_DB, connect

_SCHEMA = """
CREATE TABLE IF NOT EXISTS hitl_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    question TEXT NOT NULL,
    proposed_diff TEXT,           -- JSON: {path, target, before, after}
    status TEXT NOT NULL DEFAULT 'open',   -- open | approved | modified | rejected
    resolution TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT
);
"""


def init_hitl() -> None:
    with connect(CONTROL_DB) as c:
        c.executescript(_SCHEMA)


def enqueue(task_id: str, agent: str, question: str, proposed_diff: dict | None = None) -> int:
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    with connect(CONTROL_DB) as c:
        cur = c.execute(
            "INSERT INTO hitl_queue (task_id, agent, question, proposed_diff, expires_at) VALUES (?,?,?,?,?)",
            (task_id, agent, question, json.dumps(proposed_diff) if proposed_diff else None, expires_at),
        )
        return cur.lastrowid


def open_items() -> list[dict]:
    with connect(CONTROL_DB) as c:
        rows = c.execute("SELECT * FROM hitl_queue WHERE status='open' ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def resolve(item_id: int, status: str, resolution: str) -> None:
    with connect(CONTROL_DB) as c:
        c.execute("UPDATE hitl_queue SET status=?, resolution=? WHERE id=?",
                  (status, resolution, item_id))
