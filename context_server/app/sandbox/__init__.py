from typing import Protocol, TypedDict


class ExecResult(TypedDict):
    stdout: str
    stderr: str
    code: int

class SandboxDriver(Protocol):
    async def spawn(self, bounds: dict) -> str:
        """Starts a new sandbox with the given resource boundaries, returning its unique identifier."""
        ...

    async def exec(self, id: str, cmd: str) -> ExecResult:
        """Executes a command in the sandbox and returns its standard output/error/code."""
        ...

    async def terminate(self, id: str) -> None:
        """Forcefully shuts down the sandbox and frees resources."""
        ...

    async def snapshot(self, id: str) -> str:
        """Captures the file system and runtime state of the sandbox to a path on the host."""
        ...
