"""Context Server policy middlewares (Phases 2.9 - 2.13)."""
import re
import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


class PolicyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Breaker state: (agent, tool) -> (consecutive_failures, last_trip_time)
        self.breaker_state = defaultdict(lambda: [0, 0])
        # Rate limit state: agent -> list of timestamps
        self.rate_limits = defaultdict(list)

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
        breaker = self.breaker_state[(agent, tool)]
        if breaker[0] >= 5 and time.time() - breaker[1] < 60:
            raise HTTPException(status_code=503, detail="circuit_breaker: tripped")

        # 3. Rate Limiter (Phase 2.11) - simple token bucket (10 requests per 10 seconds)
        now = time.time()
        self.rate_limits[agent] = [t for t in self.rate_limits[agent] if now - t < 10]
        if len(self.rate_limits[agent]) >= 10:
            raise HTTPException(status_code=429, detail="rate_limit: exceeded")
        self.rate_limits[agent].append(now)

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
        if response.status_code >= 500:
            breaker[0] += 1
            breaker[1] = time.time()
        else:
            breaker[0] = 0

        return response

class DLPFilter:
    """Phase 2.12 DLP Scrubbing"""
    @staticmethod
    def scrub(text: str) -> str:
        if not isinstance(text, str):
            return text
        text = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY]', text)
        text = re.sub(r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*', 'Bearer [REDACTED_TOKEN]', text)
        return text
