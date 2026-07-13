"""delegate_task control plane (Phase 3.3 + Gate 1 episodic context).

Depth-capped, plan-recorded, span-nested delegation.
Hydrates shared episodic context before dispatch and persists results after.
"""
import os

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from .adapters import TaskResult, adapter_for
from .db import TOKEN_DB, audit, connect
from .episodic import hydrate_context, persist_episodic
from .registry import lookup_agent, orchestrator_id

MAX_DEPTH = 3


async def delegate_task(caller: str, task_id: str, target_agent: str, prompt: str,
                        depth: int = 0) -> TaskResult:
    if caller != orchestrator_id():
        raise HTTPException(status_code=403, detail="Only the orchestrator may delegate_task")

    if depth >= MAX_DEPTH:
        raise HTTPException(status_code=400, detail=f"Delegation depth cap ({MAX_DEPTH}) exceeded")

    meta = lookup_agent(target_agent)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Unknown agent '{target_agent}'")
    if meta.get("role") == "orchestrator":
        raise HTTPException(status_code=400, detail="Cannot delegate to the orchestrator itself")

    max_tokens = meta.get("cost_defaults", {}).get("max_tokens", 0)
    if max_tokens > 0:
        def _check_budget():
            with connect(TOKEN_DB) as c:
                row = c.execute(
                    "SELECT SUM(tokens_in + tokens_out) as total FROM token_ledger WHERE task_id=?",
                    (task_id,)
                ).fetchone()
                return row["total"] or 0
        used = await run_in_threadpool(_check_budget)
        if used >= max_tokens:
            await run_in_threadpool(audit, caller, task_id, "delegate_task", False,
                  f"DENY: Budget exceeded ({used}/{max_tokens})")
            raise HTTPException(status_code=403,
                                detail=f"Task token budget exceeded ({used} >= {max_tokens})")

    # Hydrate shared episodic context into the prompt
    context_bundle = await run_in_threadpool(hydrate_context, task_id)
    hydrated_prompt = prompt
    if context_bundle:
        hydrated_prompt = f"{context_bundle}\n\n{prompt}"

    # Persist the incoming prompt as episodic input
    await run_in_threadpool(persist_episodic, task_id, caller, "input", prompt)

    # Write child task row to PLAN.md (Phase 3.3)
    child_task_id = f"{task_id}.{target_agent}.{depth + 1}"
    try:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        plan_path = os.path.join(root, "PLAN.md")
        if os.path.exists(plan_path):
            child_row = f"- [delegated] ({child_task_id}) delegate:{target_agent} | agent={target_agent}\n"
            with open(plan_path, "r", encoding="utf-8") as f:
                content = f.read()
            if child_row.strip() not in content:
                with open(plan_path, "a", encoding="utf-8") as f:
                    f.write(child_row)
    except OSError:
        pass

    # Nest OTel span for delegation (Phase 2.5)
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("delegate_task") as span:
            span.set_attribute("delegate_to", target_agent)
            span.set_attribute("parent_task_id", task_id)
            span.set_attribute("child_task_id", child_task_id)
            span.set_attribute("depth", depth + 1)
    except ImportError:
        pass

    result = await adapter_for(meta).run(task_id, hydrated_prompt, meta)

    # Persist the result as episodic output
    await run_in_threadpool(persist_episodic, task_id, result.agent, "output", result.output)

    def _record_ledger():
        with connect(TOKEN_DB) as c:
            c.execute(
                "INSERT INTO token_ledger (agent, task_id, tool, tokens_in, tokens_out, accepted) "
                "VALUES (?,?,?,?,?,0)",
                (result.agent, task_id, "delegate_task", result.tokens_in, result.tokens_out),
            )
    await run_in_threadpool(_record_ledger)
    await run_in_threadpool(audit, caller, task_id, "delegate_task", result.ok, f"-> {target_agent} (child={child_task_id})")
    return result
