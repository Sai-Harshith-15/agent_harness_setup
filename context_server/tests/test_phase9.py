import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from context_server.app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

def test_phase9_dashboard_plan(client, monkeypatch):
    # Create a temporary PLAN.md file
    fd, path = tempfile.mkstemp(text=True)
    with os.fdopen(fd, 'w') as f:
        f.write("# PLAN.md\n")
        f.write("- [in-progress] (P1) Task 1 | agent=opencode capo=5 tokens=100\n")
        f.write("- [done] (P2) Task 2 | agent=hermes\n")

    # dashboard_plan uses os.path.join(root, "PLAN.md")
    # we can mock os.path.exists and open for it, or just monkeypatch os.path.join
    original_join = os.path.join

    def mock_join(*args):
        if args and args[-1] == "PLAN.md":
            return path
        return original_join(*args)

    monkeypatch.setattr(os.path, "join", mock_join)

    res = client.get("/dashboard/plan")

    # cleanup temp file
    os.remove(path)

    assert res.status_code == 200
    data = res.json()
    assert "rows" in data
    rows = data["rows"]
    assert len(rows) == 2

    assert rows[0]["id"] == "P1"
    assert rows[0]["status"] == "in-progress"
    assert rows[0]["title"] == "Task 1"
    assert rows[0]["agent"] == "opencode"
    assert rows[0]["capo"] == 5
    assert rows[0]["tokens"] == 100

    assert rows[1]["id"] == "P2"
    assert rows[1]["status"] == "done"
    assert rows[1]["title"] == "Task 2"
    assert rows[1]["agent"] == "hermes"
    assert rows[1]["capo"] == 0
    assert rows[1]["tokens"] == 0
