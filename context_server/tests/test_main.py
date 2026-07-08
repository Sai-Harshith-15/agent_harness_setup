import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ok", "degraded"]


def test_dashboard_state():
    with TestClient(app) as client:
        response = client.get("/dashboard/state")
        assert response.status_code == 200
        data = response.json()
        assert "locks" in data
        assert "recent_activity" in data
        assert isinstance(data["locks"], list)


def test_identity_rejected():
    with TestClient(app) as client:
        response = client.post("/mcp/search_notes", json={"query": "hello"})
        assert response.status_code == 401


def test_identity_accepted():
    with TestClient(app) as client:
        response = client.post("/mcp/search_notes", json={"query": "hello"}, headers={"X-Agent-Identity": "opencode:task-123:86f24b46f9aeeaff3bd79de5548999585a71532c939985baca78afaf25cc6a71"})
        assert response.status_code in [200, 502]
