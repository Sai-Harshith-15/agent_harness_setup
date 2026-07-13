import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.main import app
from conftest import make_identity


def test_phase3_dod(monkeypatch):
    import httpx

    class MockResponse:
        def raise_for_status(self): pass
        def json(self):
            return {"ok": True, "output": "mock", "tokens_in": 10, "tokens_out": 10}

    async def mock_post(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    with TestClient(app) as client:
        opencode_ident = make_identity("opencode", "task-42")
        hermes_ident = make_identity("hermes", "task-42")

        res1 = client.post("/mcp/delegate_task",
                           json={"target_agent": "hermes", "prompt": "summarize the obsidian backend contract"},
                           headers={"X-Agent-Identity": opencode_ident})
        assert res1.status_code == 200
        assert res1.json()["ok"] is True
        assert res1.json()["agent"] == "hermes"

        res2 = client.post("/mcp/delegate_task",
                           json={"target_agent": "codex", "prompt": "nope"},
                           headers={"X-Agent-Identity": hermes_ident})
        assert res2.status_code == 403
        assert "Only the orchestrator may delegate" in res2.json()["detail"]

        res3 = client.post("/mcp/accept_implement",
                           json={"path": "IMPLEMENT.md", "task_id": "task-42", "row_id": "P4-1"},
                           headers={"X-Agent-Identity": hermes_ident})
        assert res3.status_code == 403

        res4 = client.get("/mcp/find_capability?capability=research",
                          headers={"X-Agent-Identity": opencode_ident})
        assert res4.status_code == 200
        assert "hermes" in res4.json()["agents"]
