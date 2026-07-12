import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from context_server.app.governance.secrets_bridge import SecretsBridge
from context_server.app.identity import sign_identity


class TestSecretsBridge:
    def setup_method(self):
        self.sb = SecretsBridge()
        self.sb.register_service("test_svc", key="test-master-key", ttl_seconds=60, rotation_ttl=300)

    def test_register_and_list_services(self):
        services = self.sb.list_services()
        assert len(services) == 1
        assert services[0]["name"] == "test_svc"
        assert services[0]["ttl_seconds"] == 60

    def test_request_credentials_returns_structured_response(self):
        result = self.sb.request_credentials("test_svc", sandbox_id="sbx-01", scope="read")
        assert result["ok"] is True
        assert result["service"] == "test_svc"
        assert result["credential"].startswith("ephemeral-")
        assert len(result["env_injected"]) >= 1
        assert "expires_at" in result

    def test_request_credentials_per_sandbox_unique(self):
        res1 = self.sb.request_credentials("test_svc", sandbox_id="sbx-a", scope="read")
        res2 = self.sb.request_credentials("test_svc", sandbox_id="sbx-b", scope="read")
        assert res1["credential"] != res2["credential"]

    def test_request_credentials_unknown_service_raises(self):
        with pytest.raises(ValueError, match="Unknown service"):
            self.sb.request_credentials("nonexistent")

    def test_validate_and_revoke_expired(self):
        result = self.sb.request_credentials("test_svc", sandbox_id="sbx-01")
        credential = result["credential"]
        assert self.sb.validate_credential("test_svc", credential) is True

        self.sb._issued.clear()
        assert self.sb.validate_credential("test_svc", credential) is False

    def test_rotate_credential_changes_key(self):
        result = self.sb.rotate_credential("test_svc")
        assert result["ok"] is True
        assert result["rotated"] is True

    def test_rotation_check(self):
        self.sb._store["test_svc"]["last_rotated"] = 0
        assert self.sb.check_rotation_needed("test_svc") is True

        self.sb._store["test_svc"]["last_rotated"] = float("inf")
        assert self.sb.check_rotation_needed("test_svc") is False

    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("SECRETS_AWS_KEY", "aws-test-key")
        monkeypatch.setenv("SECRETS_AWS_TTL", "7200")
        sb2 = SecretsBridge()
        sb2.load_from_env()
        services = sb2.list_services()
        assert any(s["name"] == "aws" for s in services)

    def test_endpoint_request_credentials(self, monkeypatch):
        monkeypatch.setenv("ENABLE_OTEL", "false")
        monkeypatch.setenv("ENABLE_WATCHER", "false")

        from context_server.app.main import app

        ident = sign_identity("opencode", "task-13")
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.post(
                "/mcp/request_credentials",
                json={"service": "obsidian", "sandbox_id": "sbx-test", "scope": "sandbox"},
                headers={"X-Agent-Identity": ident},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["ok"] is True
            assert data["service"] == "obsidian"
            assert "credential" in data

    def test_endpoint_unknown_service_400(self, monkeypatch):
        monkeypatch.setenv("ENABLE_OTEL", "false")
        monkeypatch.setenv("ENABLE_WATCHER", "false")

        from context_server.app.main import app

        ident = sign_identity("opencode", "task-13")
        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.post(
                "/mcp/request_credentials",
                json={"service": "nonexistent"},
                headers={"X-Agent-Identity": ident},
            )
            assert res.status_code == 400

    def test_endpoint_dashboard_secrets(self, monkeypatch):
        monkeypatch.setenv("ENABLE_OTEL", "false")
        monkeypatch.setenv("ENABLE_WATCHER", "false")

        from context_server.app.main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            res = client.get("/dashboard/secrets")
            assert res.status_code == 200
            data = res.json()
            assert "services" in data
            assert any(s["name"] == "obsidian" for s in data["services"])
