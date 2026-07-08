"""Transport identity (Phase 2.8). Every tool call carries (agent, task_id)."""
import hashlib
import hmac
from dataclasses import dataclass

from fastapi import Header, HTTPException

from .config import settings


def sign_identity(agent: str, task_id: str) -> str:
    msg = f"{agent}:{task_id}".encode("utf-8")
    sig = hmac.new(settings.identity_secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{agent}:{task_id}:{sig}"

@dataclass
class AgentIdentity:
    agent: str
    task_id: str

async def require_identity(
    x_agent_identity: str | None = Header(default=None),
) -> AgentIdentity:
    # Format: "<agent>:<task_id>:<signature>"
    if not x_agent_identity:
        raise HTTPException(status_code=401, detail="Missing X-Agent-Identity header")
    parts = x_agent_identity.split(":")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="X-Agent-Identity must be '<agent>:<task_id>:<signature>'")
    agent, task_id, sig = parts

    expected_sig = hmac.new(settings.identity_secret.encode("utf-8"), f"{agent}:{task_id}".encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid identity signature")

    return AgentIdentity(agent=agent, task_id=task_id)
