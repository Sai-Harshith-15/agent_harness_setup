"""OKF backend: read from registered okf/ bundles (Phase 2.3).

Provides search_okf and get_concept — the structured-fact retrieval surface
for the Secondary Brain. Reads from every registered */okf/ bundle discovered
from registry/agents/<agent>.md's bindings field, plus the local okf/ bundle.
"""
import re
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

def _okf_bundles() -> list[Path]:
    """Discover all registered OKF bundle roots."""
    root = Path(__file__).resolve().parent.parent.parent
    bundles = [root / "okf"]
    for agent_file in (root / "registry" / "agents").glob("*.md"):
        try:
            content = agent_file.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if line.startswith("bindings:"):
                    for binding in line.split(":", 1)[1].strip().strip("[]").split(","):
                        b = binding.strip().strip('"').strip("'")
                        if b.endswith("/okf"):
                            bundles.append(root / b)
        except Exception:
            pass
    return [b for b in bundles if b.exists()]


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(content)
    if not m:
        return {}, content
    fm_text = m.group(1)
    body = content[m.end():]
    fm = {}
    current_key = None
    for line in fm_text.split("\n"):
        kv = line.split(":", 1)
        if len(kv) == 2:
            fm[kv[0].strip()] = kv[1].strip()
            current_key = kv[0].strip()
        elif line.startswith("  ") and current_key:
            fm[current_key] += " " + line.strip()
    return fm, body.strip()


def _all_concepts() -> list[dict]:
    results = []
    repo_root = Path(__file__).resolve().parent.parent.parent
    for bundle in _okf_bundles():
        for md_file in bundle.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                fm, body = _parse_frontmatter(content)
                rel_path = str(md_file.relative_to(repo_root))
                results.append({
                    "path": rel_path.replace("\\", "/"),
                    "concept_id": md_file.stem,
                    "type": fm.get("type", "unknown"),
                    "title": fm.get("title", md_file.stem),
                    "description": fm.get("description", ""),
                    "tags": fm.get("tags", ""),
                    "frontmatter": fm,
                    "body": body,
                    "bundle": str(bundle.name),
                })
            except Exception:
                pass
    return results


def search_okf(query: str, bundle: str | None = None, max_results: int = 10) -> list[dict]:
    query_lower = query.lower()
    scored = []
    for concept in _all_concepts():
        if bundle and concept["bundle"] != bundle:
            continue
        score = 0
        if query_lower in concept["title"].lower():
            score += 10
        if query_lower in concept["description"].lower():
            score += 5
        if query_lower in concept["body"].lower():
            score += 2
        if query_lower in concept.get("tags", "").lower():
            score += 3
        if score > 0:
            scored.append((score, concept))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:max_results]]


def get_concept(concept_id: str, bundle: str | None = None) -> dict | None:
    for concept in _all_concepts():
        if concept["concept_id"] == concept_id:
            if bundle and concept["bundle"] != bundle:
                continue
            import hashlib
            content_str = concept.get("body", "")
            concept["version_hash"] = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
            return concept
    return None
