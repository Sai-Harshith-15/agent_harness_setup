"""Permission matrix (Phase 6.1). Default DENY for Obsidian writes.

Only two write shapes are ever allowed:
  1. append to a designated agent-writable log.md heading
  2. append to the daily note's 'Agent Updates' heading
Everything else is denied — including any write to arbitrary human notes.
"""
import re
from dataclasses import dataclass

# Agent-writable targets. Extend via config; keep it an allow-list, never a deny-list.
_ALLOWED_LOG_PATHS = re.compile(r".*/log\.md$|^okf/log\.md$")
_ALLOWED_HEADING = {"Agent Updates", "Decisions", "Implementation Log"}


@dataclass
class Decision:
    allowed: bool
    reason: str


def can_write(path: str, target_type: str, target: str, agent: str = "", task_id: str = "") -> Decision:
    if target_type != "heading":
        return Decision(False, f"only heading-targeted appends allowed, got target_type={target_type}")
    if not _ALLOWED_LOG_PATHS.match(path):
        return Decision(False, f"path '{path}' is not an agent-writable log target")
    if target not in _ALLOWED_HEADING:
        return Decision(False, f"heading '{target}' is not in the writable allow-list")

    # Phase 6.2: Lethal-trifecta / instruction-provenance combinatorial rule (P13)
    if agent and task_id:
        from ..db import CONTROL_DB, connect
        with connect(CONTROL_DB) as c:
            tools = {r["tool"] for r in c.execute("SELECT DISTINCT tool FROM audit_log WHERE task_id=?", (task_id,)).fetchall()}
            if "read_private" in tools and "read_untrusted" in tools:
                return Decision(False, "lethal-trifecta: task has mixed private data with untrusted provenance")

    return Decision(True, "ok")
