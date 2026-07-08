"""Transport identity (Phase 2.8). Every tool call carries (agent, task_id)."""
from dataclasses import dataclass
from fastapi import Header, HTTPException


@dataclass
class AgentIdentity:
    agent: str
    task_id: str


async def require_identity(
    x_agent_identity: str | None = Header(default=None),
) -> AgentIdentity:
    # Format: "<agent>:<task_id>", e.g. "opencode:task-42".
    # TODO(phase-2.8): verify a signed token instead of trusting the header.
    if not x_agent_identity or ":" not in x_agent_identity:
        raise HTTPException(status_code=401, detail="Missing or malformed X-Agent-Identity header")
    agent, task_id = x_agent_identity.split(":", 1)
    if not agent or not task_id:
        raise HTTPException(status_code=401, detail="X-Agent-Identity must be '<agent>:<task_id>'")
    return AgentIdentity(agent=agent, task_id=task_id)
