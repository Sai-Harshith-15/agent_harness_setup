"""Adapter layer. Each registered agent is invoked through a uniform interface."""
import asyncio
import json
from dataclasses import dataclass
from typing import Protocol

import httpx


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
        agent_id = meta.get("id", "?")
        max_turns = meta.get("cost_defaults", {}).get("max_turns", 10)
        try:
            proc = await asyncio.create_subprocess_exec(
                "opencode", "--prompt", prompt, "--agent-id", agent_id, "--task-id", task_id, "--max-turns", str(max_turns),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                return TaskResult(agent=agent_id, task_id=task_id, ok=False, output=stderr.decode() or "Error", tokens_in=len(prompt)//4, tokens_out=0)

            lines = stdout.decode().strip().split('\n')
            if lines and lines[-1].startswith("{"):
                envelope = json.loads(lines[-1])
                return TaskResult(
                    agent=agent_id, task_id=task_id, ok=envelope.get("ok", True),
                    output=envelope.get("output", ""),
                    tokens_in=envelope.get("tokens_in", len(prompt)//4),
                    tokens_out=envelope.get("tokens_out", len(stdout)//4)
                )
            return TaskResult(agent=agent_id, task_id=task_id, ok=True, output=stdout.decode(), tokens_in=len(prompt)//4, tokens_out=len(stdout)//4)
        except Exception as e:
            return TaskResult(agent=agent_id, task_id=task_id, ok=False, output=str(e), tokens_in=len(prompt)//4, tokens_out=0)

class HttpAdapter:
    """HTTP runner (e.g. delegate endpoint)"""
    async def run(self, task_id: str, prompt: str, meta: dict) -> TaskResult:
        agent_id = meta.get("id", "?")
        endpoint = meta.get("endpoint", "http://127.0.0.1:8000/run")
        max_turns = meta.get("cost_defaults", {}).get("max_turns", 10)
        try:
            async with httpx.AsyncClient(timeout=30.0 * max_turns) as client:
                resp = await client.post(endpoint, json={"task_id": task_id, "prompt": prompt, "agent_id": agent_id})
                resp.raise_for_status()
                envelope = resp.json()
                return TaskResult(
                    agent=agent_id, task_id=task_id, ok=envelope.get("ok", True),
                    output=envelope.get("output", ""),
                    tokens_in=envelope.get("tokens_in", len(prompt)//4),
                    tokens_out=envelope.get("tokens_out", 0)
                )
        except Exception as e:
            return TaskResult(agent=agent_id, task_id=task_id, ok=False, output=str(e), tokens_in=len(prompt)//4, tokens_out=0)

def adapter_for(meta: dict) -> AgentAdapter:
    adapter_type = meta.get("adapter")
    if adapter_type == "filesystem":
        return FilesystemAdapter()
    elif adapter_type == "http":
        return HttpAdapter()
    return EchoAdapter()
