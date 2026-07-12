"""The two SQLite stores. WAL mode so the frontend can read while the server writes."""
import os
import sqlite3
import threading
from contextlib import contextmanager

from .config import settings

_lamport = 0
_lamport_lock = threading.Lock()

def _next_lamport() -> int:
    global _lamport
    with _lamport_lock:
        _lamport += 1
        return _lamport

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
    model TEXT NOT NULL DEFAULT '',
    cost_usd REAL NOT NULL DEFAULT 0.0,
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
CREATE TABLE IF NOT EXISTS breaker_state (
    agent TEXT NOT NULL,
    tool TEXT NOT NULL,
    arg_hash TEXT NOT NULL DEFAULT '',
    trip_count INTEGER NOT NULL DEFAULT 0,
    last_trip_time REAL NOT NULL DEFAULT 0,
    is_half_open INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (agent, tool, arg_hash)
);
CREATE TABLE IF NOT EXISTS rate_limits (
    agent TEXT NOT NULL,
    tool TEXT NOT NULL DEFAULT '',
    timestamp REAL NOT NULL,
    weight INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS dlp_quarantine (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    hash6 TEXT NOT NULL,
    original_text TEXT NOT NULL,
    source TEXT NOT NULL,
    agent TEXT NOT NULL,
    task_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    reviewed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS credential_leases (
    cred_id TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    sandbox_id TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
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
        from opentelemetry.trace.status import Status, StatusCode
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(tool) as span:
            span.set_attribute("agent", agent)
            span.set_attribute("task_id", task_id)
            span.set_attribute("ok", ok)
            span.set_attribute("detail", detail)
            span.set_attribute("lamport_seq", _next_lamport())
            if not ok:
                span.set_status(Status(StatusCode.ERROR))
                # Rich failure classification (Phase 2.5)
                if "identity_spoof" in detail:
                    fail_class = "identity_spoof_attempt"
                elif "circuit_breaker" in detail:
                    fail_class = "circuit_breaker"
                elif "rate_limited" in detail:
                    fail_class = "rate_limited"
                elif "state_changed" in detail:
                    fail_class = "state_changed"
                elif "deadlock" in detail:
                    fail_class = "planning"
                elif "DENY" in detail:
                    fail_class = "constraint"
                elif "dlp_blocked" in detail or "dlp_quarantined" in detail:
                    fail_class = "dlp_blocked" if "dlp_blocked" in detail else "dlp_quarantined"
                elif "secret_redacted" in detail or "pii_redacted" in detail:
                    fail_class = "secret_redacted" if "secret_redacted" in detail else "pii_redacted"
                elif "permission" in detail.lower():
                    fail_class = "constraint"
                elif "infrastructure_crash" in detail:
                    fail_class = "infrastructure_crash"
                elif "hibernation" in detail:
                    fail_class = "hibernation_thaw"
                elif "context" in detail.lower():
                    fail_class = "context"
                else:
                    fail_class = "system"
                span.set_attribute("failure_class", fail_class)
    except Exception:
        pass
