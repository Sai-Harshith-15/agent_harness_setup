import os
import uuid

from . import ExecResult


class E2BRunner:
    """The E2B cloud execution target, enabled by configuration."""

    def __init__(self):
        self.api_key = os.environ.get("E2B_API_KEY")
        self._sandboxes = {}

    async def spawn(self, bounds: dict) -> str:
        # Stub logic representing E2B sandbox creation
        if not self.api_key:
            print("Warning: E2B_API_KEY not set. Operating in stub mode.")

        sandbox_id = f"e2b-{uuid.uuid4().hex[:8]}"
        self._sandboxes[sandbox_id] = {"status": "running"}
        return sandbox_id

    async def exec(self, id: str, cmd: str) -> ExecResult:
        if id not in self._sandboxes:
            raise ValueError(f"Sandbox {id} not found or terminated.")

        return {
            "stdout": f"[E2B STUB] Executed {cmd}",
            "stderr": "",
            "code": 0
        }

    async def terminate(self, id: str) -> None:
        if id in self._sandboxes:
            del self._sandboxes[id]

    async def snapshot(self, id: str) -> str:
        if id not in self._sandboxes:
            raise ValueError(f"Sandbox {id} not found.")
        return f"e2b://snapshots/{id}"
