import pytest
from conftest import make_identity
from fastapi.testclient import TestClient

from context_server.app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

@pytest.fixture(autouse=True)
def setup_data():
    pass

def test_phase8_meta_analyze(monkeypatch):
    import context_server.app.meta.dream_cycle as dream_cycle
    from context_server.app.meta.dream_cycle import analyze

    monkeypatch.setattr(dream_cycle, "detect_drift", lambda: [{"spec": "Spec A", "changed_code": ["file_a.py"]}])
    monkeypatch.setattr(dream_cycle, "capo", lambda: {"capo": 6000, "total_tokens": 6000, "accepted_tasks": 1})
    monkeypatch.setattr(dream_cycle, "totals_by_task", lambda limit=1: [{"task_id": "task-expensive", "total_tokens": 6000, "accepted": 1}])
    monkeypatch.setattr(dream_cycle, "_recent_denials", lambda limit=50: [{"tool": "write", "detail": "DENY", "n": 4}])

    proposals = analyze()
    assert len(proposals) == 3

    drift_p = next(p for p in proposals if p["kind"] == "drift")
    assert "file_a.py" in drift_p["proposal"]

    cost_p = next(p for p in proposals if p["kind"] == "cost")
    assert "task-expensive" in cost_p["proposal"]

    rel_p = next(p for p in proposals if p["kind"] == "reliability")
    assert "write" in rel_p["proposal"]

def test_phase8_endpoints(client, monkeypatch):
    import context_server.app.main as main_app

    monkeypatch.setattr(main_app, "analyze", lambda: [{"kind": "test", "proposal": "test proposal", "evidence": {}}])

    res = client.get("/dashboard/dream")
    assert res.status_code == 200
    assert len(res.json()["proposals"]) == 1

    codex_ident = make_identity("codex", "task-1")
    res = client.post("/mcp/run_dream_cycle", headers={"X-Agent-Identity": codex_ident})
    assert res.status_code == 403

    async def mock_run_dream_cycle():
        return {"ok": True, "proposals": [{"kind": "test"}], "written_to": "okf/log.md"}
    monkeypatch.setattr(main_app, "run_dream_cycle", mock_run_dream_cycle)

    meta_ident = make_identity("meta", "dream-1")
    res = client.post("/mcp/run_dream_cycle", headers={"X-Agent-Identity": meta_ident})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert len(res.json()["proposals"]) == 1
    assert res.json()["written_to"] == "okf/log.md"
