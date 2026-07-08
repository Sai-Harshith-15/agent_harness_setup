"""Token metering. Every tool call records a ledger row. accepted=1 is set later,
only by the orchestrator via accept_implement (Phase 3), which is the CAPO numerator.
"""
from ..db import connect, TOKEN_DB


def record(agent: str, task_id: str, tool: str, tokens_in: int, tokens_out: int,
           accepted: bool = False) -> None:
    with connect(TOKEN_DB) as c:
        c.execute(
            "INSERT INTO token_ledger (agent, task_id, tool, tokens_in, tokens_out, accepted) "
            "VALUES (?,?,?,?,?,?)",
            (agent, task_id, tool, tokens_in, tokens_out, 1 if accepted else 0),
        )


def mark_accepted(task_id: str) -> int:
    with connect(TOKEN_DB) as c:
        cur = c.execute("UPDATE token_ledger SET accepted=1 WHERE task_id=?", (task_id,))
        return cur.rowcount
