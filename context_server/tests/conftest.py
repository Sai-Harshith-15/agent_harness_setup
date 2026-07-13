import os

import pytest

os.environ.setdefault("ENABLE_OTEL", "false")
os.environ.setdefault("ENABLE_WATCHER", "false")
os.environ.setdefault("IDENTITY_SECRET", "test-identity-secret-for-harness-tests")


def make_identity(agent: str, task_id: str) -> str:
    import hashlib
    import hmac
    secret = os.environ["IDENTITY_SECRET"]
    msg = f"{agent}:{task_id}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{agent}:{task_id}:{sig}"


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
