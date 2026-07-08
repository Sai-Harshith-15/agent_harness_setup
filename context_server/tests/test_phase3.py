import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app


def test_phase3_dod():
    with TestClient(app) as client:
        # 1. Orchestrator delegates to hermes
        res1 = client.post("/mcp/delegate_task",
                           json={"target_agent": "hermes", "prompt": "summarize the obsidian backend contract"},
                           headers={"X-Agent-Identity": "opencode:task-42:e3070606312c058178873e641213b9f5c6c77d115342b472a7ed1eab8e1b2739"})
        assert res1.status_code == 200
        assert res1.json()["ok"] is True
        assert res1.json()["agent"] == "hermes"

        # 2. A NON-orchestrator delegating is rejected (403)
        res2 = client.post("/mcp/delegate_task",
                           json={"target_agent": "codex", "prompt": "nope"},
                           headers={"X-Agent-Identity": "hermes:task-42:81e6f935bc2577e5e43022dc35d4ba61303a04e71ce4a398b1ba185ec4bf7c53"})
        assert res2.status_code == 403
        assert "Only the orchestrator may delegate" in res2.json()["detail"]

        # 3. Only orchestrator can accept an IMPLEMENT row (hermes fails)
        res3 = client.post("/mcp/accept_implement",
                           json={"path": "IMPLEMENT.md", "row_id": "task-42"},
                           headers={"X-Agent-Identity": "hermes:task-42:81e6f935bc2577e5e43022dc35d4ba61303a04e71ce4a398b1ba185ec4bf7c53"})
        assert res3.status_code == 403

        # 4. Capability discovery
        res4 = client.get("/mcp/find_capability?capability=research",
                          headers={"X-Agent-Identity": "opencode:task-42:e3070606312c058178873e641213b9f5c6c77d115342b472a7ed1eab8e1b2739"})
        assert res4.status_code == 200
        assert "hermes" in res4.json()["agents"]
