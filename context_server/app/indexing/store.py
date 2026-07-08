"""codebase-memory: a small SQLite-backed store of indexed nodes + content hashes.

Lives beside the other stores in hooks/. Delta indexing keys off content_hash so we
only re-embed/re-graph what actually changed.
"""
import hashlib

from ..db import connect

INDEX_DB = "codebase_memory.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    path TEXT PRIMARY KEY,
    kind TEXT NOT NULL,            -- file | symbol | note | okf_concept
    content_hash TEXT NOT NULL,
    tokens INTEGER NOT NULL DEFAULT 0,
    summary TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    rel TEXT NOT NULL,             -- imports | links | references | implements
    PRIMARY KEY (src, dst, rel)
);
"""


def init_index() -> None:
    with connect(INDEX_DB) as c:
        c.executescript(_SCHEMA)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]


def needs_reindex(path: str, new_hash: str) -> bool:
    with connect(INDEX_DB) as c:
        row = c.execute("SELECT content_hash FROM nodes WHERE path=?", (path,)).fetchone()
    return row is None or row["content_hash"] != new_hash


def upsert_node(path: str, kind: str, new_hash: str, tokens: int, summary: str = "") -> None:
    with connect(INDEX_DB) as c:
        c.execute(
            "INSERT INTO nodes (path, kind, content_hash, tokens, summary) VALUES (?,?,?,?,?) "
            "ON CONFLICT(path) DO UPDATE SET kind=excluded.kind, content_hash=excluded.content_hash, "
            "tokens=excluded.tokens, summary=excluded.summary, updated_at=datetime('now')",
            (path, kind, new_hash, tokens, summary),
        )


def add_edge(src: str, dst: str, rel: str) -> None:
    with connect(INDEX_DB) as c:
        c.execute("INSERT OR IGNORE INTO edges (src, dst, rel) VALUES (?,?,?)", (src, dst, rel))


def all_nodes() -> list[dict]:
    with connect(INDEX_DB) as c:
        return [dict(r) for r in c.execute("SELECT * FROM nodes").fetchall()]


def all_edges() -> list[dict]:
    with connect(INDEX_DB) as c:
        return [dict(r) for r in c.execute("SELECT * FROM edges").fetchall()]
