"""Runs the Dream Cycle and persists proposals via the GOVERNED write path only.

Writes go to okf/log.md ('Agent Updates' heading) — the same permission-matrix-approved
target every other agent uses. Never to Obsidian human notes.
"""
from ..governance.locks import acquire_lock, release_lock
from ..governance.permissions import can_write
from ..obsidian_backend import backend
from .dream_cycle import analyze, render_markdown

OKF_LOG = "okf/log.md"
HEADING = "Agent Updates"


async def run_dream_cycle() -> dict:
    proposals = analyze()
    md = render_markdown(proposals)

    decision = can_write(OKF_LOG, "heading", HEADING)   # must pass the matrix
    if not decision.allowed:
        return {"ok": False, "reason": decision.reason}

    acquire_lock(OKF_LOG, "meta", "dream-cycle")
    try:
        # idempotent: re-running the same night won't double-append the same section.
        await backend.patch(OKF_LOG, "heading", HEADING, md, reject_if_preexists=True)
    finally:
        release_lock(OKF_LOG, "dream-cycle")

    return {"ok": True, "proposals": proposals, "written_to": OKF_LOG}
