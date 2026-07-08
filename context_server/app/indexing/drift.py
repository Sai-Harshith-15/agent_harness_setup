"""Drift detection: flag spec (contracts/*, PLAN.md) nodes whose implementation
counterpart changed without the spec being touched, and vice versa.

Stub heuristic: a code node that references a contract concept but whose contract
node is older is 'impl-ahead'; the reverse is 'spec-ahead'. Real impl can diff
git history — the shape stays the same.
"""
from .store import all_nodes


def detect_drift() -> list[dict]:
    nodes = {n["path"]: n for n in all_nodes()}
    banners: list[dict] = []
    contracts = [p for p in nodes if p.startswith("contracts/") or p == "PLAN.md"]
    code = [p for p in nodes if p.endswith((".py", ".ts", ".tsx"))]
    for c in contracts:
        newer_code = [p for p in code if nodes[p]["updated_at"] > nodes[c]["updated_at"]]
        if len(newer_code) >= 3:
            banners.append({"kind": "impl-ahead", "spec": c, "changed_code": newer_code[:5]})
    return banners
