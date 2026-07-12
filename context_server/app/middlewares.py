"""Context Server policy middlewares (Phases 2.9 - 2.13).

Circuit breaker: args-hash replay detection (Phase 2.9).
Rate limiter: token-bucket with per-tool cost weighting (Phase 2.11).
Identity spoof: compares body identity to transport identity (Phase 2.8).
Chaperon: untrusted-provenance write block + read-side macro-span collapsing (Phase 2.13).
"""
import hashlib
import json
import math
import re
import time
from collections import Counter, defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from .db import CONTROL_DB, audit, connect

# Per-tool cost weights for rate limiting (Phase 2.11)
TOOL_WEIGHTS: dict[str, int] = defaultdict(lambda: 1, **{
    "search_notes": 1,
    "read_note": 1,
    "search_okf": 2,
    "get_concept": 1,
    "lookup_agent": 1,
    "find_capability": 1,
    "search_tools": 1,
    "load_tool_schema": 1,
    "append_implement": 2,
    "log_decision": 2,
    "delegate_task": 3,
    "reindex": 5,
    "compress": 3,
    "request_credentials": 2,
    "request_clarification": 2,
    "acquire_lock": 1,
    "request_snapshot": 2,
})

# In-memory chaperon state per task_id
_chaperon_branches: dict[str, dict] = {}


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    length = len(text)
    return -sum((c / length) * math.log2(c / length) for c in counts.values())


def _redact_token(kind: str, original: str) -> str:
    h = hashlib.sha256(original.encode()).hexdigest()[:6]
    return f"[REDACTED:{kind}:{h}]"


def _args_hash(request: Request) -> str:
    """Compute a stable hash of the request arguments for breaker replay detection."""
    try:
        qp = sorted(request.query_params.items())
        qp_str = json.dumps(qp)
    except Exception:
        qp_str = ""
    return hashlib.sha256(qp_str.encode()).hexdigest()[:12]


def _chaperon_flush(task_id: str, agent: str) -> None:
    """Flush a closed chaperoned branch: write one summary line to IMPLEMENT.md."""
    branch = _chaperon_branches.pop(task_id, None)
    if not branch:
        return
    count = branch.get("count", 0)
    source = branch.get("source", "unknown")
    if count > 0:
        audit(agent, task_id, "chaperon_flush", True,
              f"agent processed untrusted source {source}, made {count} read calls")


class PolicyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        agent_id = request.headers.get("X-Agent-Identity", "unknown:unknown")
        parts = agent_id.split(":")
        agent = parts[0] if parts else "unknown"

        path = request.url.path
        if not path.startswith("/mcp/"):
            return await call_next(request)

        tool = path.split("/")[-1]
        arg_hash = _args_hash(request)
        now = time.time()
        task_id = parts[1] if len(parts) > 1 else "unknown"

        # 1. Identity Spoof Detection (Phase 2.8)
        # Check query params for injected agent/task_id claims
        qp = request.query_params
        body_agent = qp.get("agent")
        body_task_id = qp.get("task_id")
        if body_agent and body_agent != agent:
            audit(agent, task_id, tool, False,
                  f"identity_spoof: body claims '{body_agent}', transport proves '{agent}'")
        if body_task_id and body_task_id != task_id:
            audit(agent, task_id, tool, False,
                  f"identity_spoof: body task_id '{body_task_id}' mismatch")

        # 2. Circuit Breaker — args-hash replay (Phase 2.9)
        with connect(CONTROL_DB) as c:
            row = c.execute(
                "SELECT trip_count, last_trip_time, is_half_open FROM breaker_state WHERE agent=? AND tool=? AND arg_hash=?",
                (agent, tool, arg_hash)
            ).fetchone()
            if row:
                trip_count = row["trip_count"]
                last_trip_time = row["last_trip_time"]
                is_half_open = row["is_half_open"]
            else:
                trip_count = 0
                last_trip_time = 0
                is_half_open = 0

        # If breaker is tripped (>=3 identical calls in 60s window)
        if trip_count >= 3 and now - last_trip_time < 60 and not is_half_open:
            audit(agent, "system", tool, False,
                  f"circuit_breaker_tripped: {trip_count} identical calls, args_hash={arg_hash}")
            raise HTTPException(status_code=503,
                              detail=f"circuit_breaker_tripped: {trip_count} identical calls detected")

        # Half-open probe: allow through, but if it matches same hash, re-trip
        if is_half_open and trip_count >= 3:
            pass  # Allow probe through; result determines if breaker resets

        # 3. Rate Limiter — token-bucket with per-tool weighting (Phase 2.11)
        weight = TOOL_WEIGHTS.get(tool, 1)
        bucket_window = 10  # seconds
        with connect(CONTROL_DB) as c:
            c.execute("DELETE FROM rate_limits WHERE agent=? AND timestamp < ?", (agent, now - bucket_window))
            count = c.execute(
                "SELECT SUM(weight) as total FROM rate_limits WHERE agent=?",
                (agent,)
            ).fetchone()["total"] or 0
            if count + weight > 20:  # max 20 weighted units per window
                audit(agent, "system", tool, False,
                      f"rate_limited: bucket={count}+{weight} > 20")
                raise HTTPException(status_code=429, detail="rate_limited: exceeded")
            c.execute("INSERT INTO rate_limits (agent, tool, timestamp, weight) VALUES (?, ?, ?, ?)",
                      (agent, tool, now, weight))

        # 4. Chaperon (Phase 2.13) — untrusted provenance
        provenance = request.headers.get("X-Provenance", "trusted")

        if provenance == "untrusted" and tool in ["append_implement", "log_decision"]:
            audit(agent, task_id, tool, False, "chaperon: untrusted write blocked")
            raise HTTPException(status_code=403, detail="chaperon: untrusted data write blocked")

        # Read-side chaperon: start/continue untrusted branch for read tools
        read_tools = {"search_notes", "read_note", "search_okf", "get_concept", "lookup_agent", "find_capability"}
        if provenance == "untrusted" and tool in read_tools:
            if task_id not in _chaperon_branches:
                _chaperon_branches[task_id] = {"count": 0, "source": provenance}
            _chaperon_branches[task_id]["count"] += 1
        else:
            # Exiting untrusted processing: flush the branch
            if task_id in _chaperon_branches and tool not in read_tools:
                _chaperon_flush(task_id, agent)

        response = await call_next(request)

        # Post-response: track breaker state
        with connect(CONTROL_DB) as c:
            if response.status_code >= 500:
                c.execute(
                    "INSERT INTO breaker_state (agent, tool, arg_hash, trip_count, last_trip_time, is_half_open) "
                    "VALUES (?, ?, ?, 1, ?, 0) "
                    "ON CONFLICT(agent, tool, arg_hash) "
                    "DO UPDATE SET trip_count = trip_count + 1, last_trip_time = ?",
                    (agent, tool, arg_hash, now, now)
                )
            elif response.status_code == 503 and "circuit_breaker" in str(response.headers.get("detail", "")):
                c.execute(
                    "INSERT INTO breaker_state (agent, tool, arg_hash, trip_count, last_trip_time, is_half_open) "
                    "VALUES (?, ?, ?, ?, ?, 1) "
                    "ON CONFLICT(agent, tool, arg_hash) "
                    "DO UPDATE SET trip_count = trip_count + 1, is_half_open = 1",
                    (agent, tool, arg_hash, 3, now)
                )
            else:
                c.execute(
                    "INSERT INTO breaker_state (agent, tool, arg_hash, trip_count, last_trip_time, is_half_open) "
                    "VALUES (?, ?, ?, 0, 0, 0) "
                    "ON CONFLICT(agent, tool, arg_hash) "
                    "DO UPDATE SET trip_count = 0, is_half_open = 0",
                    (agent, tool, arg_hash)
                )

        return response


class DLPFilter:
    """Phase 2.12 DLP Scrubbing — regex patterns + Shannon entropy + hit policies."""

    PATTERNS: list[tuple[str, str, str]] = [
        ("aws_key",      r'AKIA[0-9A-Z]{16}', ''),
        ("token",        r'Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*', 'Bearer '),
        ("github_pat",   r'ghp_[0-9a-zA-Z]{36}', ''),
        ("slack",        r'xox[baprs]-[0-9a-zA-Z\-]+', ''),
        ("private_key",  r'-----BEGIN (?:PRIVATE|RSA|EC|OPENSSH|DSA) KEY-----.*?-----END (?:PRIVATE|RSA|EC|OPENSSH|DSA) KEY-----', ''),
        ("email",        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', ''),
        ("phone",        r'\+?1?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', ''),
        ("cc",           r'\b(?:\d[ -]*?){13,16}\b', ''),
    ]

    @staticmethod
    def scrub(text: str, source: str = "unknown", agent: str = "system", task_id: str = "system") -> str:
        if not isinstance(text, str):
            return text

        from .config import settings
        from .db import audit as _dlp_audit

        hit = False
        hit_kinds = set()
        for kind, pattern, prefix in DLPFilter.PATTERNS:
            flags = re.DOTALL if "PRIVATE" in pattern or "KEY" in pattern else 0

            def _replace(m, kind=kind):
                nonlocal hit
                hit = True
                hit_kinds.add(kind)
                full_match = m.group(0)
                token = _redact_token(kind, full_match)
                return prefix + token

            if re.search(pattern, text, flags):
                text = re.sub(pattern, _replace, text, flags=flags)

        text, hit_entropy = DLPFilter._entropy_scan(text)
        if hit_entropy:
            hit = True
            hit_kinds.add("high_entropy")

        if hit:
            for kind in hit_kinds:
                fail_class = "secret_redacted" if kind in ("aws_key", "github_pat", "slack", "token", "private_key") else "pii_redacted"
                try:
                    _dlp_audit(agent, task_id, "dlp_scrub", True,
                               f"redacted:{kind} from {source} (class={fail_class})")
                except Exception:
                    pass

            policy = getattr(settings, 'dlp_hit_policy', 'redact')
            if policy == "block":
                try:
                    _dlp_audit(agent, task_id, "dlp_scrub", False,
                               f"dlp_blocked:{','.join(hit_kinds)} from {source}")
                except Exception:
                    pass
                raise HTTPException(status_code=403, detail="dlp_violation: sensitive data blocked")
            elif policy == "quarantine":
                DLPFilter._quarantine(text, source, agent, task_id)
                try:
                    _dlp_audit(agent, task_id, "dlp_scrub", False,
                               f"dlp_quarantined:{','.join(hit_kinds)} from {source}")
                except Exception:
                    pass
                raise HTTPException(status_code=202, detail="dlp_violation: content quarantined for review")

        return text

    @staticmethod
    def _entropy_scan(text: str) -> tuple[str, bool]:
        changed = False
        window_size = 24
        i = 0
        result = list(text)
        while i < len(text):
            end = i + window_size
            if end > len(text):
                break
            candidate = text[i:end]
            if re.match(r'^[a-zA-Z0-9_\-\.\+\/\=]+$', candidate):
                entropy = _shannon_entropy(candidate)
                if entropy >= 4.5:
                    token = _redact_token("high_entropy", candidate)
                    result[i:end] = list(token)
                    changed = True
                    i += len(token)
                    continue
            i += 1
        return "".join(result), changed

    @staticmethod
    def _quarantine(text: str, source: str, agent: str, task_id: str):
        from .db import CONTROL_DB, connect
        with connect(CONTROL_DB) as c:
            c.execute(
                "INSERT INTO dlp_quarantine (kind, hash6, original_text, source, agent, task_id, created_at, reviewed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                ("dlp_hit", hashlib.sha256(text.encode()).hexdigest()[:6], text, source, agent, task_id, time.time())
            )
