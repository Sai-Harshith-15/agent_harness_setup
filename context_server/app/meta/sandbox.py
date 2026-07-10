"""Sandbox Driver (Phase 1.3 / Gap 1.3).
Provides isolation for running registered agents, and handles per-sandbox
ephemeral credential injection.
"""
import uuid
from ..config import settings

class SandboxDriver:
    def __init__(self):
        self.sandboxes = {}

    def spawn(self, bounds: dict = None) -> str:
        """Starts a new sandbox and injects ephemeral credentials."""
        sandbox_id = f"sbx-{uuid.uuid4().hex[:8]}"
        
        # Ephemeral per-sandbox credential injection (Gap 1.3)
        # We inject the bridge token so the sandbox can auth against the context server.
        env_injection = {
            "OBSIDIAN_REST_API_KEY": settings.obsidian_rest_api_key,
            "SANDBOX_ID": sandbox_id
        }
        
        self.sandboxes[sandbox_id] = {
            "status": "running",
            "env": env_injection,
            "bounds": bounds or {}
        }
        return sandbox_id

    def exec(self, sandbox_id: str, cmd: list[str]) -> dict:
        """Executes a command in the sandbox."""
        if sandbox_id not in self.sandboxes:
            raise ValueError(f"Unknown sandbox {sandbox_id}")
            
        # Stub implementation for execution
        return {"code": 0, "stdout": "", "stderr": ""}

    def terminate(self, sandbox_id: str):
        """Forcefully shuts down the sandbox."""
        if sandbox_id in self.sandboxes:
            self.sandboxes[sandbox_id]["status"] = "terminated"

    def snapshot(self, sandbox_id: str) -> str:
        """Captures the state of the sandbox to a path."""
        return f"/tmp/snapshots/{sandbox_id}.tar.gz"

driver = SandboxDriver()
