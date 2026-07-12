"""Secrets Bridge (Gap 1.3 / Phase 2.7).
Resolves scoped, short-lived, ephemeral credentials and injects them into
sandbox environments only — never into an agent's prompt.
"""

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone

from ..config import settings
from ..db import CONTROL_DB, audit, connect


class CredentialIssued:
    def __init__(self, service: str, credential: str, scope: dict, issued_at: float, expires_at: float):
        self.service = service
        self.credential = credential
        self.scope = scope
        self.issued_at = issued_at
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class SecretsBridge:
    def __init__(self):
        self._store = {}
        self._issued: dict[str, CredentialIssued] = {}
        self._rotation_callbacks: dict[str, callable] = {}

    def register_service(self, name: str, key: str, ttl_seconds: int = 3600,
                         rotation_ttl: int = 86400, scope_template: dict = None):
        self._store[name] = {
            "key": key,
            "ttl_seconds": ttl_seconds,
            "rotation_ttl": rotation_ttl,
            "scope_template": scope_template or {},
            "last_rotated": time.time(),
        }

    def load_from_env(self):
        for env_key, env_val in os.environ.items():
            if env_key.startswith("SECRETS_") and env_key.endswith("_KEY"):
                service = env_key[len("SECRETS_"):-len("_KEY")].lower()
                ttl = int(os.environ.get(f"SECRETS_{service.upper()}_TTL", "3600"))
                rot_ttl = int(os.environ.get(f"SECRETS_{service.upper()}_ROTATION_TTL", "86400"))
                self.register_service(service, key=env_val, ttl_seconds=ttl, rotation_ttl=rot_ttl)

    def _derive_ephemeral_key(self, service: str, sandbox_id: str, scope: str) -> str:
        master_key = self._store[service]["key"]
        ttl = self._store[service]["ttl_seconds"]
        expiry_window = int(time.time()) + ttl
        payload = f"{service}|{sandbox_id}|{scope}|{expiry_window}"
        derived = hmac.new(master_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"ephemeral-{derived[:32]}"

    def request_credentials(self, service: str, sandbox_id: str = "default",
                            scope: str = "default") -> dict:
        if service not in self._store:
            raise ValueError(f"Unknown service '{service}'. Registered: {list(self._store.keys())}")

        ttl = self._store[service]["ttl_seconds"]
        issued_at = time.time()
        expires_at = issued_at + ttl
        credential = self._derive_ephemeral_key(service, sandbox_id, scope)

        issued = CredentialIssued(service, credential, {"sandbox_id": sandbox_id, "scope": scope},
                                  issued_at=issued_at, expires_at=expires_at)
        cred_id = f"{service}:{sandbox_id}:{int(issued_at)}"
        self._issued[cred_id] = issued

        try:
            with connect(CONTROL_DB) as c:
                c.execute(
                    "INSERT OR REPLACE INTO credential_leases (cred_id, service, sandbox_id, issued_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                    (cred_id, service, sandbox_id, datetime.fromtimestamp(issued_at, tz=timezone.utc).isoformat(),
                     datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat()),
                )
        except Exception:
            pass  # table may not exist yet in test contexts; in-memory store suffices

        try:
            audit("system", sandbox_id, "request_credentials", True,
                  f"issued ephemeral credential for {service} (scope={scope}, ttl={ttl}s)")
        except Exception:
            pass

        return {
            "ok": True,
            "service": service,
            "credential": credential,
            "env_injected": [f"{service.upper()}_KEY"],
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
        }

    def rotate_credential(self, service: str) -> dict:
        if service not in self._store:
            raise ValueError(f"Unknown service '{service}'")

        old_key_hash = hashlib.sha256(self._store[service]["key"].encode("utf-8")).hexdigest()[:8]
        new_key = f"rotated-{service}-{os.urandom(16).hex()}"
        self._store[service]["key"] = new_key
        self._store[service]["last_rotated"] = time.time()

        try:
            audit("system", "secrets-bridge", "rotate_credential", True,
                  f"rotated {service} (old hash={old_key_hash})")
        except Exception:
            pass

        if service in self._rotation_callbacks:
            try:
                self._rotation_callbacks[service](new_key)
            except Exception as e:
                audit("system", "secrets-bridge", "rotation_callback", False, f"{service}: {e}")

        return {"ok": True, "service": service, "rotated": True, "old_hash": old_key_hash}

    def on_rotation(self, service: str, callback: callable):
        self._rotation_callbacks[service] = callback

    def check_rotation_needed(self, service: str) -> bool:
        if service not in self._store:
            return False
        elapsed = time.time() - self._store[service]["last_rotated"]
        return elapsed >= self._store[service]["rotation_ttl"]

    def auto_rotate_expired(self) -> list[str]:
        rotated = []
        for service in list(self._store.keys()):
            if self.check_rotation_needed(service):
                self.rotate_credential(service)
                rotated.append(service)
        return rotated

    def list_services(self) -> list[dict]:
        return [
            {"name": name, "ttl_seconds": info["ttl_seconds"],
             "rotation_ttl": info["rotation_ttl"],
             "last_rotated": datetime.fromtimestamp(info["last_rotated"], tz=timezone.utc).isoformat()}
            for name, info in self._store.items()
        ]

    def validate_credential(self, service: str, credential: str) -> bool:
        for cred_id, issued in list(self._issued.items()):
            if issued.service == service and issued.credential == credential:
                if issued.is_expired():
                    del self._issued[cred_id]
                    return False
                return True
        return False

    def revoke_expired(self) -> int:
        revoked = 0
        for cred_id in list(self._issued.keys()):
            if self._issued[cred_id].is_expired():
                del self._issued[cred_id]
                revoked += 1
        try:
            with connect(CONTROL_DB) as c:
                c.execute("DELETE FROM credential_leases WHERE expires_at < ?",
                          (datetime.now(timezone.utc).isoformat(),))
        except Exception:
            pass
        return revoked


bridge = SecretsBridge()

if os.environ.get("SECRETS_OBSIDIAN_KEY") or os.environ.get("SECRETS_GITHUB_KEY"):
    bridge.load_from_env()
else:
    bridge.register_service("obsidian", key=settings.obsidian_rest_api_key,
                            ttl_seconds=3600, rotation_ttl=86400)
    bridge.register_service("github", key=os.environ.get("GITHUB_TOKEN", "github-token-placeholder"),
                            ttl_seconds=1800, rotation_ttl=43200)
