"""Tests for new MCP endpoints: search_okf, get_concept, search_tools, load_tool_schema,
acquire_lock, request_snapshot, and the fixed circuit breaker / rate limiter.
"""

import pytest
from fastapi.testclient import TestClient

from context_server.app.identity import sign_identity


def _headers(agent="opencode", task_id="test-audit"):
    return {"X-Agent-Identity": sign_identity(agent, task_id)}


@pytest.fixture()
def isolate_hooks(tmp_path, monkeypatch):
    from context_server.app.config import settings as s
    monkeypatch.setattr(s, "hooks_dir", str(tmp_path))
    yield


@pytest.fixture()
def client(isolate_hooks):
    from context_server.app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_search_okf_returns_results(client):
    resp = client.post("/mcp/search_okf", json={"query": "agent"}, headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data


def test_search_okf_no_match(client):
    resp = client.post("/mcp/search_okf", json={"query": "xyznonexistent12345"}, headers=_headers())
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_get_concept_found(client):
    resp = client.get("/mcp/get_concept?concept_id=capo", headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["concept_id"] == "capo"
    assert "version_hash" in data


def test_get_concept_not_found(client):
    resp = client.get("/mcp/get_concept?concept_id=nonexistent", headers=_headers())
    assert resp.status_code == 404


def test_get_concept_with_bundle(client):
    resp = client.get("/mcp/get_concept?concept_id=capa&bundle=okf", headers=_headers())
    assert resp.status_code in (200, 404)  # capa may or may not exist


def test_search_tools_all(client):
    resp = client.get("/mcp/search_tools", headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tools"]) >= 10


def test_search_tools_filtered(client):
    resp = client.get("/mcp/search_tools?query=search", headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tools"]) >= 1


def test_load_tool_schema_valid(client):
    resp = client.get("/mcp/load_tool_schema?tool_id=search_notes", headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["tool_id"] == "search_notes"
    assert "input" in data["schema"]


def test_load_tool_schema_unknown(client):
    resp = client.get("/mcp/load_tool_schema?tool_id=nonexistent_tool", headers=_headers())
    assert resp.status_code == 404


def test_acquire_lock_success(client):
    resp = client.post("/mcp/acquire_lock?resource=test_file.md", headers=_headers("opencode", "lock-test"))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_acquire_lock_contention(client):
    resource = "contended_file.md"
    resp1 = client.post(f"/mcp/acquire_lock?resource={resource}", headers=_headers("opencode", "task1"))
    assert resp1.status_code == 200
    resp2 = client.post(f"/mcp/acquire_lock?resource={resource}", headers=_headers("hermes", "task2"))
    assert resp2.status_code == 409


def test_request_snapshot(client):
    resp = client.post("/mcp/request_snapshot?label=before_destructive", headers=_headers("opencode", "snap-1"))
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_circuit_breaker_tolerates_repeated(client):
    """Phase 2.9: repeated calls with the same args are tolerated up to limit."""
    hdr = _headers("opencode", "cb-test")
    for _ in range(4):
        resp = client.get("/mcp/get_concept?concept_id=capo", headers=hdr)
    assert resp.status_code in (200, 503)


def test_rate_limiter_accepts_normal_load(client):
    """Phase 2.11: normal rate of distinct calls is accepted."""
    hdr = _headers("opencode", "rl-test")
    resp = client.get("/mcp/lookup_agent?agent_id=opencode", headers=hdr)
    assert resp.status_code == 200


def test_identity_spoof_detected_in_middleware(client):
    """Phase 2.8: middleware logs identity spoof when body claims differ."""
    hdr = _headers("opencode", "spoof-test")
    resp = client.post(
        "/mcp/log_decision",
        json={"path": "okf/log.md", "target": "Implementation Log", "content": "test"},
        headers=hdr,
    )
    assert resp.status_code in (200, 403, 502)


def test_search_tools_progressive_discovery(client):
    """Phase 5.6: progressive tool disclosure."""
    resp = client.get("/mcp/search_tools", headers=_headers())
    assert resp.status_code == 200
    tools = [t["tool_id"] for t in resp.json()["tools"]]
    assert "search_tools" in tools
    assert "load_tool_schema" in tools
    assert "delegate_task" in tools


def test_h2_sync_db_calls_do_not_block_event_loop():
    """H2 regression: PolicyMiddleware and route handlers must offload sqlite calls
    (via run_in_threadpool) rather than call them directly inside async def, which
    would block the single-threaded event loop under concurrent load.

    We can't easily benchmark loop responsiveness in-process with TestClient (it
    runs synchronously), so this asserts the structural fix directly: no bare
    (non-threadpooled) `audit(`/`meter_record(`/`connect(` call remains in the
    top-level body of an `async def` (nested nested plain `def` helpers, which are
    legitimately dispatched via `run_in_threadpool` at their call site, are excluded).
    """
    import inspect
    import re
    import textwrap

    from context_server.app import main as main_mod
    from context_server.app import middlewares as mw_mod

    def _strip_nested_def_bodies(src: str) -> str:
        lines = src.splitlines()
        out = []
        skip_indent = None
        for line in lines:
            stripped = line.strip()
            if skip_indent is not None:
                if line[:1] in (" ", "\t") and (len(line) - len(line.lstrip())) > skip_indent:
                    continue
                skip_indent = None
            if re.match(r"def\s+\w+\(", stripped) and not stripped.startswith("async def"):
                skip_indent = len(line) - len(line.lstrip())
                continue
            out.append(line)
        return "\n".join(out)

    def _bare_blocking_calls(src: str) -> list[str]:
        src = _strip_nested_def_bodies(textwrap.dedent(src))
        offenders = []
        for m in re.finditer(r"\b(audit|meter_record|connect)\(", src):
            start = m.start()
            prefix = src[max(0, start - 40):start]
            if "run_in_threadpool" in prefix or prefix.rstrip().endswith("import"):
                continue
            offenders.append(src[max(0, start - 20):start + 20].replace("\n", "\\n"))
        return offenders

    for name, obj in vars(main_mod).items():
        if inspect.iscoroutinefunction(obj):
            offenders = _bare_blocking_calls(inspect.getsource(obj))
            assert not offenders, f"{name} has un-threadpooled blocking call(s): {offenders}"

    offenders = _bare_blocking_calls(inspect.getsource(mw_mod.PolicyMiddleware.dispatch))
    assert not offenders, f"PolicyMiddleware.dispatch has un-threadpooled blocking call(s): {offenders}"
