"""Shared test fixtures for the context_server test suite.

pytest_configure runs before any test module is imported, so setting
ENABLE_WATCHER=false here guarantees the background watcher is never
started by the server lifespan during any test.
"""
import os


def pytest_configure(config):
    """Disable the file watcher before any module is imported by tests."""
    os.environ["ENABLE_WATCHER"] = "false"


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _init_test_db(tmp_path, monkeypatch):
    """Per-test: redirect hooks to a fresh tmp dir and initialise both DBs."""
    monkeypatch.setenv("HOOKS_DIR", str(tmp_path))

    from context_server.app.config import settings
    monkeypatch.setattr(settings, "hooks_dir", str(tmp_path))

    from context_server.app.db import init_db
    init_db()

    # Also initialise the codebase-memory index DB so all_nodes/all_edges work
    from context_server.app.indexing.store import init_index
    init_index()

    yield
