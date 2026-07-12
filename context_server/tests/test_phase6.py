import pytest
from fastapi.testclient import TestClient

from context_server.app.db import CONTROL_DB, connect
from context_server.app.governance.locks import acquire_lock
from context_server.app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_phase6_out_of_matrix_write_denied(client):
    # 1. Out-of-matrix write is DENIED
    res = client.post(
        "/mcp/append_implement",
        json={"path": "People/Alice.md", "target": "Notes", "content": "nope"},
        headers={"X-Agent-Identity": "hermes:task-6:cababbc77d7b77c66d010f147df06c57ba005b403895166ba8cb3d9006f5893a"}
    )
    assert res.status_code == 403
    assert "is not an agent-writable log target" in res.json()["detail"]


def test_phase6_allowed_write_succeeds(client, monkeypatch):
    # Mock backend to simulate OCC pass
    import context_server.app.main as main_mod

    class DummyBackend:
        async def read_note(self, path):
            return {"content": ""}

        async def patch(self, path, target_type, target, content, reject_if_preexists):
            pass

        async def aclose(self):
            pass

    monkeypatch.setattr(main_mod, "backend", DummyBackend())

    # 2. Allowed write succeeds (designated log heading)
    res = client.post(
        "/mcp/append_implement",
        json={"path": "okf/log.md", "target": "Agent Updates", "content": "- did the thing", "expected_version": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
        headers={"X-Agent-Identity": "opencode:task-6:9b9f441bdd1578ac0104b0589073d38a666c76130b9430f173d9b919623a8ae5"}
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_phase6_lock_contention(client):
    # Acquire a lock manually first
    acquire_lock("okf/log.md", "hermes", "task-99")

    # 3. Lock contention: two different tasks, same resource -> second gets 409
    res = client.post(
        "/mcp/append_implement",
        json={"path": "okf/log.md", "target": "Agent Updates", "content": "- did the thing"},
        headers={"X-Agent-Identity": "opencode:task-6:9b9f441bdd1578ac0104b0589073d38a666c76130b9430f173d9b919623a8ae5"}
    )
    assert res.status_code == 409
    assert "resource locked by hermes:task-99" in res.json()["detail"]


def test_phase6_hitl_pause_and_resolve(client):
    # 4. HITL pause
    res = client.post(
        "/mcp/request_clarification",
        json={"question": "overwrite config?", "proposed_diff": {"path": "x", "before": "a", "after": "b"}},
        headers={"X-Agent-Identity": "codex:task-99:982a73795578386cabc3eca10f1684f3218f4c5220345a09e32b9af877745c22"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["paused"] is True
    item_id = data["hitl_item"]

    # Verify in dashboard
    res_dash = client.get("/dashboard/hitl")
    assert res_dash.status_code == 200
    items = res_dash.json()["open"]
    assert len(items) == 1
    assert items[0]["id"] == item_id
    assert items[0]["task_id"] == "task-99"

    # Verify it is hibernated in db
    with connect(CONTROL_DB) as c:
        hib = c.execute("SELECT * FROM hibernation WHERE task_id='task-99'").fetchone()
        assert hib is not None

    # Resolve it
    res_patch = client.patch(
        "/dashboard/hitl",
        json={"item_id": item_id, "status": "approved", "resolution": "go ahead"}
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "approved"

    # Verify thawed (removed from hibernation)
    with connect(CONTROL_DB) as c:
        hib_after = c.execute("SELECT * FROM hibernation WHERE task_id='task-99'").fetchone()
        assert hib_after is None


def test_phase6_crash_reconciliation(client, monkeypatch):
    from datetime import datetime, timedelta, timezone

    import context_server.app.governance.locks as locks

    def _past_now():
        return datetime.now(timezone.utc) + timedelta(seconds=-500)

    monkeypatch.setattr(locks, "_now", _past_now)
    acquire_lock("some/expired.md", "hermes", "task-expired")

    with connect(CONTROL_DB) as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM locks").fetchall()]
        print(f"DEBUG LOCKS AFTER EXPIRED: {rows}")

    def _normal_now():
        return datetime.now(timezone.utc)
    monkeypatch.setattr(locks, "_now", _normal_now)
    acquire_lock("some/active.md", "opencode", "task-active")

    with connect(CONTROL_DB) as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM locks").fetchall()]
        print(f"DEBUG LOCKS AFTER ACTIVE: {rows}")

    with connect(CONTROL_DB) as c:
        c.execute("INSERT OR REPLACE INTO hibernation (task_id, agent, reason, frozen_state) VALUES ('orphan-99', 'codex', 'crash', '{}')")

    res = client.get("/dashboard/crashes")
    assert res.status_code == 200
    data = res.json()
    print("Dashboard crashes response:", data)

    reaped = [r["resource"] for r in data["released_locks"]]
    assert "some/expired.md" in reaped, f"Data was: {data}"
    assert "some/active.md" not in reaped

    orphans = [r["task_id"] for r in data["hibernated_orphans"]]
    assert "orphan-99" in orphans


def test_phase6_crash_reconcile_span_and_snapshot(monkeypatch):
    """Gap 1.1: verify startup reconciliation emits OTel span (infrastructure_crash)
    and calls restore_snapshot for crashed locks."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    from context_server.app.db import CONTROL_DB, connect, init_db
    from context_server.app.governance.reconcile import reconcile

    init_db()

    # Insert an expired lock that simulates a crash-orphaned lease
    with connect(CONTROL_DB) as c:
        c.execute("DELETE FROM locks")
        expired_at = (datetime.now(timezone.utc) - timedelta(seconds=300)).isoformat()
        c.execute(
            "INSERT INTO locks (resource, agent, task_id, lease_expires_at) VALUES (?, ?, ?, ?)",
            ("crash/test.md", "hermes", "task-crash-span", expired_at),
        )

    # Mock restore_snapshot to verify it gets called
    with patch("context_server.app.governance.snapshot.restore_snapshot") as mock_restore:
        result = reconcile(startup=True)

    # Verify the crash was detected
    assert len(result["crashes"]) >= 1
    crash_resources = [c["resource"] for c in result["crashes"]]
    assert "crash/test.md" in crash_resources

    # Verify restore_snapshot was called with the crashed task_id
    mock_restore.assert_called_with("task-crash-span")
