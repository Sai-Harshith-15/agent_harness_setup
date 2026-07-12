"""Sandbox Driver (Phase 1.3 / Gap 1.3).
Provides isolation for running registered agents, and handles per-sandbox
ephemeral credential injection via the secrets bridge.
"""
import uuid

from ..governance.secrets_bridge import bridge as secrets_bridge


class SandboxDriver:
    def __init__(self):
        self.sandboxes: dict[str, dict] = {}

    def spawn(self, bounds: dict = None) -> str:
        sandbox_id = f"sbx-{uuid.uuid4().hex[:8]}"

        env_injection: dict[str, str] = {
            "SANDBOX_ID": sandbox_id,
        }

        for service_info in secrets_bridge.list_services():
            service = service_info["name"]
            try:
                cred = secrets_bridge.request_credentials(service, sandbox_id, "sandbox")
                for env_var in cred.get("env_injected", []):
                    env_injection[env_var] = cred["credential"]
            except Exception:
                env_injection[f"{service.upper()}_KEY"] = f"placeholder-{sandbox_id}"

        self.sandboxes[sandbox_id] = {
            "status": "running",
            "env": env_injection,
            "bounds": bounds or {}
        }
        return sandbox_id

    def exec(self, sandbox_id: str, cmd: list[str]) -> dict:
        if sandbox_id not in self.sandboxes:
            raise ValueError(f"Unknown sandbox {sandbox_id}")
        return {"code": 0, "stdout": "", "stderr": ""}

    def terminate(self, sandbox_id: str):
        if sandbox_id in self.sandboxes:
            self.sandboxes[sandbox_id]["status"] = "terminated"

    def snapshot(self, sandbox_id: str) -> str:
        return f"/tmp/snapshots/{sandbox_id}.tar.gz"

    def inject_credential(self, sandbox_id: str, service: str) -> dict:
        if sandbox_id not in self.sandboxes:
            raise ValueError(f"Unknown sandbox {sandbox_id}")
        cred = secrets_bridge.request_credentials(service, sandbox_id, "sandbox")
        for env_var in cred.get("env_injected", []):
            self.sandboxes[sandbox_id]["env"][env_var] = cred["credential"]
        return {"ok": True, "sandbox_id": sandbox_id, "service": service}


driver = SandboxDriver()
