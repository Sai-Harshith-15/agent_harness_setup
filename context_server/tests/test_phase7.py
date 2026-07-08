import pytest
from fastapi.testclient import TestClient

from context_server.app.finops.meter import mark_accepted, record
from context_server.app.finops.rollups import capo, capo_trend, heatmap, totals_by_task
from context_server.app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

@pytest.mark.asyncio
async def test_phase7_finops_metering_and_rollups():
    # 1. Insert some spend
    record("hermes", "task-1", "search", 100, 50, accepted=False)
    record("hermes", "task-1", "read", 20, 10, accepted=False)
    record("opencode", "task-2", "write", 200, 100, accepted=False)

    # 2. Verify totals_by_task
    totals = totals_by_task()
    t1 = next(t for t in totals if t["task_id"] == "task-1")
    t2 = next(t for t in totals if t["task_id"] == "task-2")
    assert t1["total_tokens"] == 180
    assert t1["accepted"] == 0
    assert t2["total_tokens"] == 300
    assert t2["accepted"] == 0

    # 3. Accept task-1
    mark_accepted("task-1")
    totals = totals_by_task()
    t1 = next(t for t in totals if t["task_id"] == "task-1")
    assert t1["accepted"] == 1

    # 4. CAPO rollups
    c = capo()
    assert c["total_tokens"] == 480
    assert c["accepted_tasks"] == 1
    assert c["capo"] == 480.0

    hm = heatmap()
    h_search = next(h for h in hm if h["agent"] == "hermes" and h["tool"] == "search")
    assert h_search["tokens"] == 150

    trend = capo_trend(days=1)
    assert len(trend) > 0
    assert trend[-1]["accepted"] == 1


def test_phase7_finops_endpoints(client, monkeypatch):
    from context_server.app.obsidian_backend import backend

    # Insert spend
    record("hermes", "task-3", "search", 1000, 500, accepted=True)

    res = client.get("/dashboard/tokens")
    assert res.status_code == 200
    assert "by_task" in res.json()
    assert "heatmap" in res.json()

    res = client.get("/dashboard/capo")
    assert res.status_code == 200
    assert "summary" in res.json()
    assert "trend" in res.json()

    async def mock_periodic_daily():
        return {"path": "Daily Notes/2026-07-08.md"}

    monkeypatch.setattr(backend, "periodic_daily", mock_periodic_daily)

    # Needs to bypass or handle actual backend patch
    async def mock_patch(*args, **kwargs):
        pass
    monkeypatch.setattr(backend, "patch", mock_patch)

    res = client.post("/mcp/post_standup", headers={"X-Agent-Identity": "opencode:task-3:623834a916491e667f9a8ef0ec361be33569f1c2786aa0691ed8c11cc375fdc7"})
    assert res.status_code == 200
    assert res.json()["posted"] is True
