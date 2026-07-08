"""Adapter layer. Each registered agent is invoked through a uniform interface."""
from dataclasses import dataclass
from typing import Protocol

@dataclass
class TaskResult:
    agent: str
    task_id: str
    ok: bool
    output: str
    tokens_in: int = 0
    tokens_out: int = 0

class AgentAdapter(Protocol):
    async def run(self, task_id: str, prompt: str, meta: dict) -> TaskResult: ...

class EchoAdapter:
    """Stand-in runner: proves the delegate path works before wiring real agents."""
    async def run(self, task_id: str, prompt: str, meta: dict) -> TaskResult:
        out = f"[{meta.get('id')}] handled: {prompt[:120]}"
        return TaskResult(agent=meta.get("id", "?"), task_id=task_id, ok=True,
                          output=out, tokens_in=len(prompt) // 4, tokens_out=len(out) // 4)

class FilesystemAdapter:
    """Filesystem runner (e.g. opencode CLI)"""
    async def run(self, task_id: str, prompt: str, meta: dict) -> TaskResult:
        # TODO(PROG-1): Wire real subprocess call to agent binary
        out = f"[{meta.get('id')}] (FilesystemAdapter) handled: {prompt[:120]}"
        return TaskResult(agent=meta.get("id", "?"), task_id=task_id, ok=True,
                          output=out, tokens_in=len(prompt) // 4, tokens_out=len(out) // 4)

class HttpAdapter:
    """HTTP runner (e.g. delegate endpoint)"""
    async def run(self, task_id: str, prompt: str, meta: dict) -> TaskResult:
        # TODO(PROG-1): Wire real httpx call to agent service
        out = f"[{meta.get('id')}] (HttpAdapter) handled: {prompt[:120]}"
        return TaskResult(agent=meta.get("id", "?"), task_id=task_id, ok=True,
                          output=out, tokens_in=len(prompt) // 4, tokens_out=len(out) // 4)

def adapter_for(meta: dict) -> AgentAdapter:
    adapter_type = meta.get("adapter")
    if adapter_type == "filesystem":
        return FilesystemAdapter()
    elif adapter_type == "http":
        return HttpAdapter()
    return EchoAdapter()
