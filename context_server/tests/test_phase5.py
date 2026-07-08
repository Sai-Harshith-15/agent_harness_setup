"""Phase 5 tests — indexing & generation.

All store operations run against an isolated tmp-dir SQLite so the production
hooks/ directory is never touched during CI.
"""
import os
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def isolate_hooks(tmp_path, monkeypatch):
    """Redirect the hooks directory so every test writes to a throwaway path."""
    monkeypatch.setenv("HOOKS_DIR", str(tmp_path))
    # Re-apply the env var to settings (pydantic-settings reads at import time,
    # but the db helper calls _path() lazily so patching settings.hooks_dir works).
    from context_server.app.config import settings
    monkeypatch.setattr(settings, "hooks_dir", str(tmp_path))
    yield


@pytest.fixture()
def client(isolate_hooks):
    """TestClient — watcher is patched out by conftest._no_watcher."""
    from context_server.app.main import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


AGENT_HDR = {"X-Agent-Identity": "opencode:task-5"}


# ---------------------------------------------------------------------------
# Unit: store
# ---------------------------------------------------------------------------

class TestStore:
    def test_content_hash_deterministic(self):
        from context_server.app.indexing.store import content_hash
        assert content_hash("hello") == content_hash("hello")
        assert content_hash("hello") != content_hash("world")
        assert len(content_hash("x")) == 16

    def test_needs_reindex_first_call(self, isolate_hooks):
        from context_server.app.indexing.store import init_index, needs_reindex, content_hash
        init_index()
        h = content_hash("data")
        assert needs_reindex("some/path.py", h) is True

    def test_needs_reindex_after_upsert(self, isolate_hooks):
        from context_server.app.indexing.store import (
            init_index, needs_reindex, upsert_node, content_hash,
        )
        init_index()
        h = content_hash("data")
        upsert_node("some/path.py", "file", h, 10, "summary")
        assert needs_reindex("some/path.py", h) is False

    def test_needs_reindex_hash_change(self, isolate_hooks):
        from context_server.app.indexing.store import (
            init_index, needs_reindex, upsert_node, content_hash,
        )
        init_index()
        h1 = content_hash("v1")
        h2 = content_hash("v2")
        upsert_node("p.py", "file", h1, 5, "")
        assert needs_reindex("p.py", h2) is True


# ---------------------------------------------------------------------------
# Unit: graphify
# ---------------------------------------------------------------------------

class TestGraphify:
    def test_first_run_indexes_files(self, isolate_hooks, tmp_path):
        # Create a tiny synthetic repo in tmp_path
        py_file = tmp_path / "hello.py"
        py_file.write_text("import os\n")
        md_file = tmp_path / "README.md"
        md_file.write_text("# hello\n")

        from context_server.app.indexing.graphify import graphify
        stats = graphify(root=str(tmp_path))

        assert stats["scanned"] >= 2
        assert stats["reindexed"] >= 2
        assert stats["skipped"] == 0

    def test_second_run_skips_unchanged(self, isolate_hooks, tmp_path):
        py_file = tmp_path / "mod.py"
        py_file.write_text("x = 1\n")

        from context_server.app.indexing.graphify import graphify
        graphify(root=str(tmp_path))
        stats2 = graphify(root=str(tmp_path))

        assert stats2["reindexed"] == 0
        assert stats2["skipped"] >= 1

    def test_delta_on_change(self, isolate_hooks, tmp_path):
        py_file = tmp_path / "mod.py"
        py_file.write_text("x = 1\n")

        from context_server.app.indexing.graphify import graphify
        graphify(root=str(tmp_path))

        py_file.write_text("x = 2\n")
        stats2 = graphify(root=str(tmp_path))

        assert stats2["reindexed"] == 1
        assert stats2["skipped"] == 0


# ---------------------------------------------------------------------------
# Unit: compactor
# ---------------------------------------------------------------------------

class TestCompactor:
    def _seed(self, isolate_hooks, n=5):
        from context_server.app.indexing.store import init_index, upsert_node, content_hash
        init_index()
        for i in range(n):
            upsert_node(f"file{i}.py", "file", content_hash(f"v{i}"), 200, f"summary {i}")

    def test_compact_respects_budget(self, isolate_hooks):
        self._seed(isolate_hooks)
        from context_server.app.indexing.compactor import compact
        result = compact(budget_tokens=400)
        assert result["kept_tokens"] <= 400
        assert "span" in result
        assert result["span"]["budget"] == 400

    def test_compact_empty_store(self, isolate_hooks):
        from context_server.app.indexing.store import init_index
        from context_server.app.indexing.compactor import compact
        init_index()
        result = compact(budget_tokens=1000)
        assert result["kept"] == []
        assert result["kept_tokens"] == 0
        assert result["collapsed_nodes"] == 0


# ---------------------------------------------------------------------------
# Unit: headroom
# ---------------------------------------------------------------------------

class TestHeadroom:
    def test_remaining(self):
        from context_server.app.indexing.headroom import Headroom
        h = Headroom(max_tokens=10_000, reserve=1_000)
        assert h.remaining(2_000) == 7_000

    def test_must_compact_true(self):
        from context_server.app.indexing.headroom import Headroom
        h = Headroom(max_tokens=10_000, reserve=1_000)
        assert h.must_compact(used=9_500, incoming=1_000) is True

    def test_must_compact_false(self):
        from context_server.app.indexing.headroom import Headroom
        h = Headroom(max_tokens=10_000, reserve=1_000)
        assert h.must_compact(used=1_000, incoming=100) is False


# ---------------------------------------------------------------------------
# Unit: drift
# ---------------------------------------------------------------------------

class TestDrift:
    def test_detect_drift_returns_list(self, isolate_hooks):
        from context_server.app.indexing.store import init_index
        from context_server.app.indexing.drift import detect_drift
        init_index()
        result = detect_drift()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# API: Phase 5 endpoints
# ---------------------------------------------------------------------------

class TestPhase5API:
    def test_reindex_returns_stats(self, client, isolate_hooks, tmp_path, monkeypatch):
        # Patch the graphify that the endpoint calls so it scans tmp_path (fast)
        import context_server.app.main as main_mod
        from context_server.app.indexing.graphify import graphify as _real_gfy

        def _fast_graphify():
            return _real_gfy(root=str(tmp_path))

        monkeypatch.setattr(main_mod, "graphify", _fast_graphify)
        r = client.post("/mcp/reindex", headers=AGENT_HDR)
        assert r.status_code == 200
        body = r.json()
        assert "scanned" in body and "reindexed" in body and "skipped" in body

    def test_compress_respects_budget(self, client):
        r = client.post("/mcp/compress?budget_tokens=2000", headers=AGENT_HDR)
        assert r.status_code == 200
        body = r.json()
        assert body["kept_tokens"] <= 2000
        assert "span" in body

    def test_dashboard_graph(self, client):
        r = client.get("/dashboard/graph")
        assert r.status_code == 200
        body = r.json()
        assert "nodes" in body and "edges" in body

    def test_dashboard_drift(self, client):
        r = client.get("/dashboard/drift")
        assert r.status_code == 200
        assert "banners" in r.json()

    def test_dashboard_headroom_defaults(self, client):
        r = client.get("/dashboard/headroom")
        assert r.status_code == 200
        body = r.json()
        assert "remaining" in body and "must_compact" in body

    def test_dashboard_headroom_custom(self, client):
        r = client.get("/dashboard/headroom?used=120000&incoming=5000")
        assert r.status_code == 200
        body = r.json()
        assert body["must_compact"] is True
