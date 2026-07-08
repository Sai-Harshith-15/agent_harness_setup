"""Daily standup writer (Phase 7.1). Builds a summary from the ledger + audit log and
appends it to the daily note's 'Agent Updates' heading via the Obsidian backend.

Uses the periodic-note path from the plugin, then the same governed write path as
everything else: lock + idempotent patch (rejectIfContentPreexists) so re-running the
standup twice in a day cannot double-append.
"""
from datetime import date

from ..governance.locks import acquire_lock, release_lock
from ..obsidian_backend import backend
from .rollups import capo, totals_by_task


def build_standup_markdown() -> str:
    c = capo()
    top = totals_by_task(limit=5)
    lines = [f"### Standup {date.today().isoformat()}",
             f"- CAPO: {c['capo']} tokens/accepted ({c['accepted_tasks']} accepted, "
             f"{c['total_tokens']} total tokens)",
             "- Top tasks by spend:"]
    for t in top:
        flag = "✓" if t["accepted"] else "…"
        lines.append(f"  - {flag} {t['task_id']}: {t['total_tokens']} tokens")
    return "\n".join(lines) + "\n"


async def post_standup() -> dict:
    # periodic_note path for today's daily note (plugin exposes this).
    resp = await backend.periodic_daily()
    daily_path = resp.get("path") if isinstance(resp, dict) else None
    daily_path = daily_path or "Daily Notes/" + date.today().isoformat() + ".md"

    md = build_standup_markdown()
    acquire_lock(daily_path, "system", "standup")
    try:
        await backend.patch(daily_path, "heading", "Agent Updates", md, reject_if_preexists=True)
    finally:
        release_lock(daily_path, "standup")
    return {"posted": True, "path": daily_path}
