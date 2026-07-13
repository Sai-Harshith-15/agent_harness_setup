"""Episodic memory subsystem (Gate 1 — same-context memory).

Provides shared, task-scoped episodic memory so context accumulates across
agent runs. Every agent turn (including delegated sub-agents) reads from and
writes to the same task-scoped memory store.

Table: episodic_memory in control_plane.db
- append-only, keyed by task_id
- DLP-scrubbed on write
- budgeted through headroom + compactor on read
"""
import hashlib
from datetime import datetime, timezone

from .db import CONTROL_DB, connect

MAX_RECALL_ROWS = 50


def persist_episodic(task_id: str, agent: str, role: str, content: str) -> None:
    """Append a row to the episodic memory for a task. DLP-scrubs content."""
    from .middlewares import DLPFilter
    scrubbed = DLPFilter.scrub(content, source=f"agent:{agent}", agent=agent, task_id=task_id)
    with connect(CONTROL_DB) as c:
        c.execute(
            "INSERT INTO episodic_memory (task_id, seq, agent, role, content, ts) "
            "VALUES (?, (SELECT COALESCE(MAX(seq),0)+1 FROM episodic_memory WHERE task_id=?), ?, ?, ?, ?)",
            (task_id, task_id, agent, role, scrubbed, datetime.now(timezone.utc).isoformat()),
        )


def hydrate_context(task_id: str, limit: int = MAX_RECALL_ROWS) -> str:
    """Build a context bundle from recent episodic rows for the given task.

    Returns a formatted string suitable for injection into the agent prompt.
    """
    with connect(CONTROL_DB) as c:
        rows = c.execute(
            "SELECT seq, agent, role, content, ts FROM episodic_memory "
            "WHERE task_id=? ORDER BY seq DESC LIMIT ?",
            (task_id, limit),
        ).fetchall()

    if not rows:
        return ""

    bundle_lines = ["<episodic_context>"]
    for row in reversed(rows):
        bundle_lines.append(
            f"[{row['seq']}] {row['agent']} ({row['role']}): {row['content']}"
        )
    bundle_lines.append("</episodic_context>")
    return "\n".join(bundle_lines)


def recall_episodic(task_id: str, limit: int = MAX_RECALL_ROWS) -> list[dict]:
    """Return recent episodic rows for a task (structured, for API response)."""
    with connect(CONTROL_DB) as c:
        rows = c.execute(
            "SELECT seq, agent, role, content, ts FROM episodic_memory "
            "WHERE task_id=? ORDER BY seq DESC LIMIT ?",
            (task_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
