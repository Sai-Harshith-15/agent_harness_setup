"""Dream Cycle (Phase 8): nightly self-improvement pass.

Inputs (all already produced by earlier phases):
  - drift banners       (Phase 5)  -> spec/impl divergence
  - CAPO summary/trend   (Phase 7)  -> cost efficiency signal
  - audit log            (Phase 2/6) -> failure/denial patterns

Output: a list of reviewable improvement PROPOSALS. It does NOT execute them and does
NOT touch Obsidian human notes. Proposals are appended to Program.md's 'Proposed'
section and okf/log.md via the governed write path.
"""
from datetime import date

from ..db import CONTROL_DB, connect
from ..finops.rollups import capo, totals_by_task
from ..indexing.drift import detect_drift


def _recent_denials(limit: int = 50) -> list[dict]:
    with connect(CONTROL_DB) as c:
        rows = c.execute(
            "SELECT tool, detail, COUNT(*) AS n FROM audit_log "
            "WHERE ok=0 GROUP BY tool, detail ORDER BY n DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def analyze() -> list[dict]:
    proposals: list[dict] = []

    # 1. Drift -> propose reconciling spec vs impl.
    for b in detect_drift():
        proposals.append({
            "kind": "drift",
            "proposal": f"Reconcile {b['spec']} with impl-ahead files {b.get('changed_code')}",
            "evidence": b,
        })

    # 2. CAPO regression -> propose cost review on the priciest task.
    c = capo()
    if c["capo"] and c["capo"] > 5000:   # tune threshold to your budget
        top = totals_by_task(limit=1)
        proposals.append({
            "kind": "cost",
            "proposal": f"CAPO is {c['capo']} tokens/accepted; investigate top task "
                        f"{top[0]['task_id'] if top else 'n/a'} for wasted turns",
            "evidence": c,
        })

    # 3. Repeated denials/failures -> propose a harness or prompt fix.
    for d in _recent_denials():
        if d["n"] >= 3:
            proposals.append({
                "kind": "reliability",
                "proposal": f"{d['tool']} failed {d['n']}x with '{d['detail']}' — "
                            f"add a guard or clarify the contract",
                "evidence": d,
            })

    return proposals


def render_markdown(proposals: list[dict]) -> str:
    if not proposals:
        return f"### Dream Cycle {date.today().isoformat()}\n- No proposals; system nominal.\n"
    lines = [f"### Dream Cycle {date.today().isoformat()}"]
    for i, p in enumerate(proposals, 1):
        lines.append(f"- [ ] ({p['kind']}-{i}) {p['proposal']}")
    return "\n".join(lines) + "\n"
