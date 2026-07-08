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

def adapter_for(meta: dict) -> AgentAdapter:
    # Phase 3 returns EchoAdapter to prove the control plane
    return EchoAdapter()
