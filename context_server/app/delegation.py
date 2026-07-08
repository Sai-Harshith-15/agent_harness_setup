"""delegate_task control plane (Phase 3.3)."""
from fastapi import HTTPException

from .adapters import TaskResult, adapter_for
from .db import TOKEN_DB, audit, connect
from .registry import lookup_agent, orchestrator_id


async def delegate_task(caller: str, task_id: str, target_agent: str, prompt: str) -> TaskResult:
    if caller != orchestrator_id():
        raise HTTPException(status_code=403, detail="Only the orchestrator may delegate_task")

    meta = lookup_agent(target_agent)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{target_agent}'")
    if meta.get("role") == "orchestrator":
        raise HTTPException(status_code=400, detail="Cannot delegate to the orchestrator itself")

    # Enforce max_tokens budget (Phase 8 gap)
    max_tokens = meta.get("cost_defaults", {}).get("max_tokens", 0)
    if max_tokens > 0:
        with connect(TOKEN_DB) as c:
            row = c.execute(
                "SELECT SUM(tokens_in + tokens_out) as total FROM token_ledger WHERE task_id=?",
                (task_id,)
            ).fetchone()
            used = row["total"] or 0
            if used >= max_tokens:
                audit(caller, task_id, "delegate_task", False, f"DENY: Budget exceeded ({used}/{max_tokens})")
                raise HTTPException(status_code=403, detail=f"Task token budget exceeded ({used} >= {max_tokens})")

    result = await adapter_for(meta).run(task_id, prompt, meta)

    with connect(TOKEN_DB) as c:
        c.execute(
            "INSERT INTO token_ledger (agent, task_id, tool, tokens_in, tokens_out, accepted) "
            "VALUES (?,?,?,?,?,0)",
            (result.agent, task_id, "delegate_task", result.tokens_in, result.tokens_out),
        )
    audit(caller, task_id, "delegate_task", result.ok, f"-> {target_agent}")
    return result
