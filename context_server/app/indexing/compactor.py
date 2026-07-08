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

    summary = "Compacted nodes by degree and recency."
    if collapsed > 0:
        try:
            import os

            from litellm import completion
            if os.environ.get("OPENAI_API_KEY") or os.environ.get("LITELLM_API_KEY"):
                prompt = (
                    f"Summarize the following {collapsed} discarded nodes into a single brief paragraph:\n"
                    + "\n".join([f"{n['path']}: {n['summary']}" for n in nodes[len(kept):len(kept)+10]])
                )
                resp = completion(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
                summary = resp.choices[0].message.content
        except Exception:
            pass

    try:
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("compactor") as span:
            span.set_attribute("budget", budget_tokens)
            span.set_attribute("used", used)
            span.set_attribute("collapsed", collapsed)
            span.set_attribute("summary_len", len(summary))
    except Exception:
        pass

    return {
        "kept": kept,
        "kept_tokens": used,
        "collapsed_nodes": collapsed,
        "summary": summary,
        "span": {"name": "compactor", "budget": budget_tokens, "used": used, "collapsed": collapsed},
    }
