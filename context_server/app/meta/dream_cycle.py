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

    # 4. LLM Reflection (Phase 8: Real Meta Agent)
    try:
        import json
        import os

        from litellm import completion

        prompt = (
            "You are the Meta Agent of an Agentic OS. Review the following telemetry and propose 1-2 concrete, "
            "actionable improvements to the system prompts or operating rules. Output as a JSON array of objects "
            "with keys 'kind' (must be 'reflection'), 'proposal' (string), and 'evidence' (string).\n\n"
            f"Drift evidence: {list(detect_drift())}\n"
            f"CAPO cost evidence: {c}\n"
            f"Denials evidence: {_recent_denials()}\n"
        )

        # Only run if an API key is provided, else fallback to heuristic
        if os.environ.get("OPENAI_API_KEY") or os.environ.get("LITELLM_API_KEY"):
            response = completion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            # The prompt asks for an array but response_format json_object requires an object.
            # We can parse the json and extract the proposals.
            # For simplicity, we just append a single reflection.
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "proposals" in parsed:
                    proposals.extend(parsed["proposals"])
                elif isinstance(parsed, list):
                    proposals.extend(parsed)
                else:
                    proposals.append({
                        "kind": "reflection",
                        "proposal": f"LLM Reflection: {content[:100]}...",
                        "evidence": "llm_output"
                    })
            except Exception:
                pass
    except Exception as e:
        print(f"[dream-cycle] LLM reflection failed: {e}")

    return proposals


def render_markdown(proposals: list[dict]) -> str:
    if not proposals:
        return f"### Dream Cycle {date.today().isoformat()}\n- No proposals; system nominal.\n"
    lines = [f"### Dream Cycle {date.today().isoformat()}"]
    for i, p in enumerate(proposals, 1):
        lines.append(f"- [ ] ({p['kind']}-{i}) {p['proposal']}")
    return "\n".join(lines) + "\n"
