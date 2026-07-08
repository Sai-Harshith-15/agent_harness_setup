import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.adapters import (
    EchoAdapter,
    FilesystemAdapter,
    HttpAdapter,
    TaskResult,
    adapter_for,
)

HERMES_META = {
    "id": "hermes",
    "role": "delegate",
    "adapter": "http",
    "endpoint": "http://127.0.0.1:8001/run",
    "cost_defaults": {"max_turns": 20, "max_tokens": 50000},
    "capabilities": ["research", "summarize"],
}

CODEX_META = {
    "id": "codex",
    "role": "delegate",
    "adapter": "http",
    "cost_defaults": {"max_turns": 20},
    "capabilities": ["code", "tests"],
}

FILESYSTEM_META = {
    "id": "opencode",
    "role": "orchestrator",
    "adapter": "filesystem",
    "cost_defaults": {"max_turns": 10},
    "capabilities": ["orchestration"],
}


class TestEchoAdapter:
    """Baseline — echo adapter always returns ok=True and echoes the prompt."""

    def test_run_returns_ok(self):
        adapter = EchoAdapter()
        result = asyncio.run(adapter.run("task-1", "hello world", HERMES_META))
        assert isinstance(result, TaskResult)
        assert result.ok is True
        assert result.agent == "hermes"
        assert "hello world" in result.output
        assert result.tokens_in > 0

    def test_tokens_heuristic(self):
        adapter = EchoAdapter()
        result = asyncio.run(adapter.run("t42", "A" * 400, {"id": "x"}))
        assert result.tokens_in == 100
        assert result.tokens_out > 0
        assert result.tokens_out == len(result.output) // 4


class TestFilesystemAdapter:
    """Exercises the real FilesystemAdapter via the bundled mock_opencode.py."""

    def test_success_with_mock_script(self):
        adapter = FilesystemAdapter()
        meta = dict(FILESYSTEM_META)
        result = asyncio.run(adapter.run("task-fs-1", "summarise code", meta))
        assert result.ok is True
        assert result.agent == "opencode"
        assert "Mock output" in result.output
        assert result.tokens_out > 0

    def test_error_on_missing_script(self, monkeypatch):
        async def mock_exec(*args, **kwargs):
            raise FileNotFoundError("no such script")

        monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)
        adapter = FilesystemAdapter()
        result = asyncio.run(adapter.run("task-fs-2", "anything", FILESYSTEM_META))
        assert result.ok is False
        assert "no such script" in result.output

    def test_nonzero_exit(self, monkeypatch):
        class MockProc:
            returncode = 1

            async def communicate(self):
                return b"", b"fatal error"

        async def mock_exec(*args, **kwargs):
            return MockProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)
        adapter = FilesystemAdapter()
        result = asyncio.run(adapter.run("task-fs-3", "anything", FILESYSTEM_META))
        assert result.ok is False
        assert "fatal error" in result.output
        assert result.tokens_out == 0

    def test_stdout_without_envelope(self, monkeypatch):
        class MockProc:
            returncode = 0

            async def communicate(self):
                return b"plain text output\nno json here\n", b""

        async def mock_exec(*args, **kwargs):
            return MockProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)
        adapter = FilesystemAdapter()
        result = asyncio.run(adapter.run("task-fs-4", "anything", FILESYSTEM_META))
        assert result.ok is True
        assert "plain text output" in result.output

    def test_envelope_with_false_ok(self, monkeypatch):
        class MockProc:
            returncode = 0

            async def communicate(self):
                envelope = json.dumps({"task_id": "t", "ok": False, "output": "failed",
                                        "tokens_in": 5, "tokens_out": 2})
                return envelope.encode(), b""

        async def mock_exec(*args, **kwargs):
            return MockProc()

        monkeypatch.setattr(asyncio, "create_subprocess_exec", mock_exec)
        adapter = FilesystemAdapter()
        result = asyncio.run(adapter.run("task-fs-5", "anything", FILESYSTEM_META))
        assert result.ok is False
        assert result.output == "failed"
        assert result.tokens_in == 5
        assert result.tokens_out == 2


class TestHttpAdapter:
    """Exercises the HttpAdapter via mocked httpx."""

    def test_success(self, monkeypatch):
        import httpx

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"ok": True, "output": "hermes researched x", "tokens_in": 42, "tokens_out": 12}

        async def mock_post(*args, **kwargs):
            return MockResponse()

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        adapter = HttpAdapter()
        result = asyncio.run(adapter.run("task-h-1", "research the contract", HERMES_META))
        assert result.ok is True
        assert result.agent == "hermes"
        assert "researched" in result.output
        assert result.tokens_in == 42
        assert result.tokens_out == 12

    def test_http_error(self, monkeypatch):
        import httpx

        async def mock_post(*args, **kwargs):
            raise httpx.HTTPError("connection refused")

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        adapter = HttpAdapter()
        result = asyncio.run(adapter.run("task-h-2", "anything", HERMES_META))
        assert result.ok is False
        assert "connection refused" in result.output

    def test_endpoint_from_meta(self, monkeypatch):
        import httpx

        captured_endpoint = None

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"ok": True, "output": "ok", "tokens_in": 0, "tokens_out": 0}

        async def mock_post(self_mock, url, **kwargs):
            nonlocal captured_endpoint
            captured_endpoint = url
            return MockResponse()

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        adapter = HttpAdapter()
        codex_meta = dict(CODEX_META)
        codex_meta["endpoint"] = "http://127.0.0.1:9000/run"
        asyncio.run(adapter.run("task-h-3", "test endpoint", codex_meta))
        assert captured_endpoint == "http://127.0.0.1:9000/run"

    def test_default_endpoint(self, monkeypatch):
        import httpx

        captured_endpoint = None

        class MockResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"ok": True, "output": "ok", "tokens_in": 0, "tokens_out": 0}

        async def mock_post(self_mock, url, **kwargs):
            nonlocal captured_endpoint
            captured_endpoint = url
            return MockResponse()

        monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
        adapter = HttpAdapter()
        meta_no_endpoint = {"id": "agent-x", "cost_defaults": {}}
        asyncio.run(adapter.run("task-h-4", "no endpoint in meta", meta_no_endpoint))
        assert captured_endpoint == "http://127.0.0.1:8000/run"


class TestAdapterFor:
    """Tests the adapter factory routing."""

    def test_echo_fallback(self):
        adapter = adapter_for({"id": "unknown"})
        assert isinstance(adapter, EchoAdapter)

    def test_filesystem_route(self):
        adapter = adapter_for({"adapter": "filesystem"})
        assert isinstance(adapter, FilesystemAdapter)

    def test_http_route(self):
        adapter = adapter_for(HERMES_META)
        assert isinstance(adapter, HttpAdapter)
