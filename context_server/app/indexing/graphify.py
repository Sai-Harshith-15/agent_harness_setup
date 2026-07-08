"""Graphify: walk the repo, hash each file, upsert nodes, extract import/link edges.

Delta-aware: files whose content_hash is unchanged are skipped. Emits a small stats
dict the /dashboard and OTel layer can report.
"""
import os
import re

from .store import add_edge, content_hash, init_index, needs_reindex, upsert_node

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_PY_IMPORT = re.compile(r"^\s*(?:from|import)\s+([\w\.]+)", re.M)
_MD_LINK = re.compile(r"\[\[([^\]]+)\]\]")            # wikilinks
_INCLUDE_EXT = {".py", ".ts", ".tsx", ".md"}
_SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".next", "hooks"}


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)  # rough; swap for a real tokenizer later


def graphify(root: str = ROOT) -> dict:
    init_index()
    scanned = reindexed = skipped = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1]
            if ext not in _INCLUDE_EXT:
                continue
            path = os.path.relpath(os.path.join(dirpath, fn), root).replace("\\", "/")
            scanned += 1
            try:
                text = open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            h = content_hash(text)
            if not needs_reindex(path, h):
                skipped += 1
                continue
            kind = "note" if ext == ".md" else "file"
            upsert_node(path, kind, h, _tokens(text), summary=text[:160].replace("\n", " "))
            for m in _PY_IMPORT.findall(text):
                add_edge(path, m, "imports")
            for m in _MD_LINK.findall(text):
                add_edge(path, m, "links")
            reindexed += 1
    return {"scanned": scanned, "reindexed": reindexed, "skipped": skipped}
