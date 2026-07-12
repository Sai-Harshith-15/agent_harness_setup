import os

import pytest

# Suppress OTel export noise in tests (no Jaeger running) and disable file watcher
os.environ.setdefault("ENABLE_OTEL", "false")
os.environ.setdefault("ENABLE_WATCHER", "false")


@pytest.fixture(autouse=True, scope="session")
def clean_hooks_db():
    hooks_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "hooks")
    for db_file in ["control_plane.db", "token_usage.db"]:
        path = os.path.join(hooks_dir, db_file)
        if os.path.exists(path):
            os.remove(path)
    yield
    for db_file in ["control_plane.db", "token_usage.db"]:
        path = os.path.join(hooks_dir, db_file)
        if os.path.exists(path):
            os.remove(path)

