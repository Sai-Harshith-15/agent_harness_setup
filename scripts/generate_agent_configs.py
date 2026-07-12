"""Script to generate YAML config for downstream integrators based on the agent registry."""
import os
import sys

import yaml

# Add context_server to path to import registry
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "context_server"))
from app.registry import load_agents


def main():
    agents = load_agents()
    out_path = os.path.join(os.path.dirname(__file__), "..", "agent_configs.yaml")
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(agents, f, default_flow_style=False)
    print(f"Generated {out_path} with {len(agents)} agents.")

if __name__ == "__main__":
    main()
