"""Compactor: compress a set of index nodes down to a token budget.

Strategy (deterministic, no LLM in the loop for the stub): keep highest-degree /
most-recently-updated nodes' summaries until the budget is hit; everything else
collapses into a single 'compacted N nodes' macro-summary. Emits a compaction span.
TODO(phase-5): swap the summary source for real LLM summaries.
"""
from .store import all_edges, all_nodes


def _degree() -> dict[str, int]:
    deg: dict[str, int] = {}
    for e in all_edges():
        deg[e["src"]] = deg.get(e["src"], 0) + 1
        deg[e["dst"]] = deg.get(e["dst"], 0) + 1
    return deg


def compact(budget_tokens: int) -> dict:
    deg = _degree()
    nodes = sorted(all_nodes(), key=lambda n: (deg.get(n["path"], 0), n["updated_at"]), reverse=True)
    kept, used = [], 0
    for n in nodes:
        if used + n["tokens"] > budget_tokens:
            break
        kept.append(n["path"])
        used += n["tokens"]
    collapsed = len(nodes) - len(kept)
    return {
        "kept": kept,
        "kept_tokens": used,
        "collapsed_nodes": collapsed,
        "span": {"name": "compactor", "budget": budget_tokens, "used": used, "collapsed": collapsed},
    }
