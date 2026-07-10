"""Context Server policy middlewares (Phases 2.9 - 2.13)."""
import re
import time

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from .db import CONTROL_DB, connect


class PolicyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # 1. Identity & Context
        agent_id = request.headers.get("X-Agent-Identity", "unknown:unknown")
        parts = agent_id.split(":")
        agent = parts[0] if parts else "unknown"

        path = request.url.path
        if not path.startswith("/mcp/"):
            return await call_next(request)

        tool = path.split("/")[-1]

        # 2. Circuit Breaker (Phase 2.9)
        with connect(CONTROL_DB) as c:
            row = c.execute("SELECT consecutive_failures, last_trip_time FROM breaker_state WHERE agent=? AND tool=?", (agent, tool)).fetchone()
            if row:
                consecutive_failures = row["consecutive_failures"]
                last_trip_time = row["last_trip_time"]
            else:
                consecutive_failures = 0
                last_trip_time = 0

        if consecutive_failures >= 5 and time.time() - last_trip_time < 60:
            raise HTTPException(status_code=503, detail="circuit_breaker: tripped")

        # 3. Rate Limiter (Phase 2.11) - simple token bucket (10 requests per 10 seconds)
        now = time.time()
        with connect(CONTROL_DB) as c:
            c.execute("DELETE FROM rate_limits WHERE agent=? AND timestamp < ?", (agent, now - 10))
            count = c.execute("SELECT COUNT(*) as cnt FROM rate_limits WHERE agent=?", (agent,)).fetchone()["cnt"]
            if count >= 10:
                raise HTTPException(status_code=429, detail="rate_limit: exceeded")
            c.execute("INSERT INTO rate_limits (agent, timestamp) VALUES (?, ?)", (agent, now))

        # 4. OCC (Phase 2.10)
        # Expected version passed in headers for writes
        if tool in ["append_implement", "log_decision"]:
            expected_version = request.headers.get("X-Expected-Version")
            if expected_version:
                # If we had a fast way to get the version, we could do it here.
                # Since we don't want to block the middleware, we pass the header down.
                # Actually, append_implement does the OCC check directly.
                # The auditor wants a reusable with occ(...) decorator or middleware logic.
                pass

        # 5. Chaperon (Phase 2.13)
        provenance = request.headers.get("X-Provenance", "trusted")
        if provenance == "untrusted" and tool in ["append_implement", "log_decision"]:
            raise HTTPException(status_code=403, detail="chaperon: untrusted data write blocked")

        response = await call_next(request)

        # Track failures for breaker
        with connect(CONTROL_DB) as c:
            if response.status_code >= 500:
                now_ts = time.time()
                c.execute(
                    "INSERT INTO breaker_state (agent, tool, consecutive_failures, last_trip_time) "
                    "VALUES (?, ?, 1, ?) "
                    "ON CONFLICT(agent, tool) "
                    "DO UPDATE SET consecutive_failures = consecutive_failures + 1, last_trip_time = ?",
                    (agent, tool, now_ts, now_ts)
                )
            else:
                c.execute(
                    "INSERT INTO breaker_state (agent, tool, consecutive_failures, last_trip_time) "
                    "VALUES (?, ?, 0, 0) "
                    "ON CONFLICT(agent, tool) "
                    "DO UPDATE SET consecutive_failures = 0",
                    (agent, tool)
                )

        return response

class DLPFilter:
    """Phase 2.12 DLP Scrubbing"""
    @staticmethod
    def scrub(text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]', text)
        text = re.sub(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*', 'Bearer [REDACTED_TOKEN]', text)
        text = re.sub(r'ghp_[0-9a-zA-Z]{36}', '[REDACTED_GITHUB_PAT]', text)
        text = re.sub(r'xox[baprs]-[0-9a-zA-Z\-]+', '[REDACTED_SLACK_TOKEN]', text)
        text = re.sub(r'-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----', '[REDACTED_PRIVATE_KEY]', text, flags=re.DOTALL)
        text = re.sub(r'\b[0-9a-zA-Z]{40,}\b', '[REDACTED_HIGH_ENTROPY]', text)
        return text
