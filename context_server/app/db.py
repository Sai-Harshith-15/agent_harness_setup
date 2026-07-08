"""The two SQLite stores. WAL mode so the frontend can read while the server writes."""
import os
import sqlite3
from contextlib import contextmanager

from .config import settings

TOKEN_DB = "token_usage.db"
CONTROL_DB = "control_plane.db"

_SCHEMA_TOKEN = """
CREATE TABLE IF NOT EXISTS token_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    agent TEXT NOT NULL,
    task_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    accepted INTEGER NOT NULL DEFAULT 0
);
"""

_SCHEMA_CONTROL = """
CREATE TABLE IF NOT EXISTS locks (
    resource TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    task_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL DEFAULT (datetime('now')),
    lease_expires_at TEXT
);
CREATE TABLE IF NOT EXISTS hibernation (
    task_id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    reason TEXT,
    frozen_state TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL DEFAULT (datetime('now')),
    agent TEXT NOT NULL,
    task_id TEXT NOT NULL,
    tool TEXT NOT NULL,
    ok INTEGER NOT NULL,
    detail TEXT
);
"""


def _path(name: str) -> str:
    os.makedirs(settings.hooks_dir, exist_ok=True)
    return os.path.join(settings.hooks_dir, name)


@contextmanager
def connect(name: str):
    conn = sqlite3.connect(_path(name))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect(TOKEN_DB) as c:
        c.executescript(_SCHEMA_TOKEN)
    with connect(CONTROL_DB) as c:
        c.executescript(_SCHEMA_CONTROL)


def audit(agent: str, task_id: str, tool: str, ok: bool, detail: str = "") -> None:
    with connect(CONTROL_DB) as c:
        c.execute(
            "INSERT INTO audit_log (agent, task_id, tool, ok, detail) VALUES (?,?,?,?,?)",
            (agent, task_id, tool, 1 if ok else 0, detail),
        )
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(tool) as span:
            span.set_attribute("agent", agent)
            span.set_attribute("task_id", task_id)
            span.set_attribute("ok", ok)
            span.set_attribute("detail", detail)
    except Exception:
        pass
