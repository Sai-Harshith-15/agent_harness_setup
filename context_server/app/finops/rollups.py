"""SQL rollups for the dashboard. CAPO = total tokens / accepted outcomes.

The frontend /tokens page reads these directly.
"""
from ..db import TOKEN_DB, connect


def totals_by_task(limit: int = 20) -> list[dict]:
    sql = """
        SELECT task_id,
               SUM(tokens_in + tokens_out) AS total_tokens,
               MAX(accepted)               AS accepted
        FROM token_ledger
        GROUP BY task_id
        ORDER BY total_tokens DESC
        LIMIT ?
    """
    with connect(TOKEN_DB) as c:
        return [dict(r) for r in c.execute(sql, (limit,)).fetchall()]


def heatmap() -> list[dict]:
    # (agent x tool) token spend, for the analytics heatmap.
    sql = """
        SELECT agent, tool, SUM(tokens_in + tokens_out) AS tokens
        FROM token_ledger GROUP BY agent, tool ORDER BY tokens DESC
    """
    with connect(TOKEN_DB) as c:
        return [dict(r) for r in c.execute(sql).fetchall()]


def capo() -> dict:
    """Cost per accepted outcome. Numerator = all tokens; denominator = # accepted tasks."""
    sql = """
        SELECT
            SUM(tokens_in + tokens_out) AS total_tokens,
            COUNT(DISTINCT CASE WHEN accepted=1 THEN task_id END) AS accepted_tasks
        FROM token_ledger
    """
    with connect(TOKEN_DB) as c:
        row = dict(c.execute(sql).fetchone())
    total = row["total_tokens"] or 0
    accepted = row["accepted_tasks"] or 0
    return {
        "total_tokens": total,
        "accepted_tasks": accepted,
        "capo": round(total / accepted, 1) if accepted else None,   # None = no accepted outcome yet
    }


def capo_trend(days: int = 14) -> list[dict]:
    sql = """
        SELECT date(ts) AS day,
               SUM(tokens_in + tokens_out) AS tokens,
               COUNT(DISTINCT CASE WHEN accepted=1 THEN task_id END) AS accepted
        FROM token_ledger
        WHERE ts >= date('now', ?)
        GROUP BY day ORDER BY day
    """
    with connect(TOKEN_DB) as c:
        rows = [dict(r) for r in c.execute(sql, (f"-{days} days",)).fetchall()]
    for r in rows:
        r["capo"] = round(r["tokens"] / r["accepted"], 1) if r["accepted"] else None
    return rows


def raw_ledger(start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    """Raw ledger rows for the SQL-view / CSV export."""
    sql = "SELECT * FROM token_ledger"
    params = []
    conditions = []
    if start_date:
        conditions.append("ts >= datetime(?)")
        params.append(start_date)
    if end_date:
        conditions.append("ts <= datetime(?)")
        params.append(end_date)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY ts DESC LIMIT 1000"
    with connect(TOKEN_DB) as c:
        return [dict(r) for r in c.execute(sql, tuple(params)).fetchall()]
