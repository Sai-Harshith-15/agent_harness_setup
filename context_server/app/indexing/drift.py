"""Drift detection: flag spec (contracts/*, PLAN.md) nodes whose implementation
counterpart changed without the spec being touched, and vice versa.

Stub heuristic: a code node that references a contract concept but whose contract
node is older is 'impl-ahead'; the reverse is 'spec-ahead'. Real impl can diff
git history — the shape stays the same.
"""
import os
from functools import lru_cache
from .store import all_nodes

@lru_cache(maxsize=1000)
def get_embedding(text: str) -> list[float]:
    if not text.strip():
        return []
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("LITELLM_API_KEY"):
        return []
    try:
        from litellm import embedding
        response = embedding(model="text-embedding-3-small", input=[text])
        return response.data[0]["embedding"]
    except Exception:
        return []

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def semantic_drift_detected(spec_text: str, impl_text: str) -> bool:
    # 1. Real vector embeddings via litellm (Phase 0.1 / P30)
    v1 = get_embedding(spec_text)
    v2 = get_embedding(impl_text)
    if v1 and v2:
        sim = cosine_similarity(v1, v2)
        return sim < 0.7  # Semantic drift threshold

    # 2. Fallback to Jaccard token overlap
    spec_tokens = set(spec_text.lower().split())
    impl_tokens = set(impl_text.lower().split())
    if not spec_tokens or not impl_tokens:
        return False
    overlap = len(spec_tokens.intersection(impl_tokens))
    jaccard = overlap / len(spec_tokens.union(impl_tokens))
    return jaccard < 0.1


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
