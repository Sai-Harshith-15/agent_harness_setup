"""Drift detection: flag spec (contracts/*, PLAN.md) nodes whose implementation
counterpart changed without the spec being touched, and vice versa.

Stub heuristic: a code node that references a contract concept but whose contract
node is older is 'impl-ahead'; the reverse is 'spec-ahead'. Real impl can diff
git history — the shape stays the same.
"""
from .store import all_nodes


def semantic_drift_detected(spec_text: str, impl_text: str) -> bool:
    # A dummy vector-similarity heuristic using basic token overlap to simulate P30 vector store
    spec_tokens = set(spec_text.lower().split())
    impl_tokens = set(impl_text.lower().split())
    if not spec_tokens or not impl_tokens:
        return False
    overlap = len(spec_tokens.intersection(impl_tokens))
    jaccard = overlap / len(spec_tokens.union(impl_tokens))
    return jaccard < 0.1  # If similarity is very low, it drifted semantically


def detect_drift() -> list[dict]:
    nodes = {n["path"]: n for n in all_nodes()}
    banners: list[dict] = []
    contracts = [p for p in nodes if p.startswith("contracts/") or p == "PLAN.md"]
    code = [p for p in nodes if p.endswith((".py", ".ts", ".tsx"))]
    
    # 1. code-graph divergence (temporal)
    for c in contracts:
        newer_code = [p for p in code if nodes[p]["updated_at"] > nodes[c]["updated_at"]]
        if len(newer_code) >= 3:
            banners.append({
                "kind": "impl-ahead", 
                "spec": c, 
                "changed_code": newer_code[:5],
                "action": "trigger_dream_renorm"
            })
            
    # 2. vector store semantic drift (simulated via summary token overlap)
    for c in contracts:
        spec_summary = nodes[c].get("summary", "")
        spec_basename = c.split("/")[-1].replace(".md", "")
        for p in code:
            impl_summary = nodes[p].get("summary", "")
            if spec_basename in impl_summary:
                if semantic_drift_detected(spec_summary, impl_summary):
                    banners.append({
                        "kind": "semantic_drift_detected",
                        "spec": c,
                        "impl": p,
                        "action": "trigger_dream_renorm"
                    })
    return banners
