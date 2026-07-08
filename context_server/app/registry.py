"""Loads registry/agents/*.md, parses YAML frontmatter, exposes lookup + capability search."""
import os
import glob
import yaml

REGISTRY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "registry", "agents")

def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) >= 3:
        fm = parts[1]
        return yaml.safe_load(fm) if yaml else {}
    return {}

def load_agents() -> dict[str, dict]:
    agents: dict[str, dict] = {}
    for path in glob.glob(os.path.join(REGISTRY_DIR, "*.md")):
        with open(path, encoding="utf-8") as f:
            meta = _parse_frontmatter(f.read())
        if meta and meta.get("id"):
            agents[meta["id"]] = meta
    return agents

def lookup_agent(agent_id: str) -> dict | None:
    return load_agents().get(agent_id)

def find_capability(capability: str) -> list[str]:
    return [
        aid for aid, meta in load_agents().items()
        if capability in (meta.get("capabilities") or [])
    ]

def orchestrator_id() -> str | None:
    for aid, meta in load_agents().items():
        if meta.get("role") == "orchestrator":
            return aid
    return None
