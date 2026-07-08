"""Lock manager and DAG deadlock check (Phase 2.6)."""
import time
from fastapi import HTTPException
from .db import connect, CONTROL_DB

class LockManager:
    # Uses SQLite for leases, in-memory graph for deadlock detection
    _dag = {} # node -> list of dependencies

    @classmethod
    def acquire(cls, resource: str, agent: str, task_id: str, ttl_seconds: int = 600):
        # 1. Deadlock check (simple cycle detection)
        # Assuming task_id is waiting on resource, and resource is held by holding_task
        with connect(CONTROL_DB) as c:
            row = c.execute("SELECT task_id, lease_expires_at FROM locks WHERE resource = ?", (resource,)).fetchone()
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            
            if row:
                holding_task = row["task_id"]
                expires = row["lease_expires_at"]
                if expires and expires > now and holding_task != task_id:
                    # Check cycle
                    cls._dag[task_id] = [holding_task]
                    if cls._has_cycle(task_id):
                        cls._dag[task_id] = []
                        raise HTTPException(status_code=409, detail="deadlock_risk: cycle detected")
                    raise HTTPException(status_code=423, detail="Resource locked")

            # Acquire lock
            expires_at = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() + ttl_seconds))
            c.execute("""
                INSERT INTO locks (resource, agent, task_id, lease_expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(resource) DO UPDATE SET
                    agent = excluded.agent,
                    task_id = excluded.task_id,
                    acquired_at = datetime('now'),
                    lease_expires_at = excluded.lease_expires_at
            """, (resource, agent, task_id, expires_at))

    @classmethod
    def release(cls, resource: str, task_id: str):
        with connect(CONTROL_DB) as c:
            c.execute("DELETE FROM locks WHERE resource = ? AND task_id = ?", (resource, task_id))
            if task_id in cls._dag:
                del cls._dag[task_id]

    @classmethod
    def _has_cycle(cls, start_node: str) -> bool:
        visited = set()
        stack = [start_node]
        path = set()

        while stack:
            node = stack[-1]
            if node not in visited:
                visited.add(node)
                path.add(node)
                for neighbor in cls._dag.get(node, []):
                    if neighbor in path:
                        return True
                    stack.append(neighbor)
            else:
                path.discard(node)
                stack.pop()
        return False
