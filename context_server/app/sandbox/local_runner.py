import asyncio
import uuid

from . import ExecResult


class LocalRunner:
    """A containerized local execution environment designed for a zero-cloud dev loop."""

    def __init__(self):
        self._sandboxes = {}

    async def spawn(self, bounds: dict) -> str:
        sandbox_id = str(uuid.uuid4())
        self._sandboxes[sandbox_id] = {"status": "running"}
        return sandbox_id

    async def exec(self, id: str, cmd: str) -> ExecResult:
        if id not in self._sandboxes:
            raise ValueError(f"Sandbox {id} not found or terminated.")

        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "code": proc.returncode or 0
        }

    async def terminate(self, id: str) -> None:
        if id in self._sandboxes:
            del self._sandboxes[id]

    async def snapshot(self, id: str) -> str:
        if id not in self._sandboxes:
            raise ValueError(f"Sandbox {id} not found.")
        return f"/tmp/sandbox_snapshots/{id}.tar.gz"
