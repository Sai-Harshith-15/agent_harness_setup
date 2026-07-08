from datetime import datetime, timedelta, timezone
from context_server.app.config import settings
from context_server.app.db import connect, init_db, CONTROL_DB
import context_server.app.governance.locks as locks

def run():
    settings.hooks_dir = "test_hooks"
    init_db()
    
    def _past_now():
        return datetime.now(timezone.utc) + timedelta(seconds=-500)
    
    original_now = locks._now
    locks._now = _past_now
    
    locks.acquire_lock("some/expired.md", "hermes", "task-expired")
    
    locks._now = original_now
    locks.acquire_lock("some/active.md", "opencode", "task-active")
    
    with connect(CONTROL_DB) as c:
        rows = [dict(r) for r in c.execute("SELECT * FROM locks").fetchall()]
        print("ROWS:", rows)

if __name__ == "__main__":
    run()
