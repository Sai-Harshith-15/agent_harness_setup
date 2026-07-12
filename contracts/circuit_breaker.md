# Contract: Circuit Breaker

> Phase 2.9 · Args-hash replay detection and auto-HITL escalation.

## 1. Args-Hash Replay Window

The Context Server maintains a sliding window per `(agent, task_id, tool)` of the last N `args-hash` values.

**Trip condition:** If the exact same `(tool, args-hash)` combination is observed >= N times within a short window:
- Defaults: N=3, window=60s.
- Tunable from Phase 2.5 trace stats.

## 2. On Trip

1. The repeated call is refused with a structured `circuit_breaker_tripped` error (HTTP 503) carrying the repeated hash and trip count.
2. The event is tagged `circuit_breaker` in the Phase 2.5 trace.
3. A summary is written to `IMPLEMENT.md` by the context server (not the agent).
4. The Phase 6.5 `request_clarification` HITL handoff is **auto-triggered** — the loop is escalated to a human.

## 3. Half-Open Probe Recovery

After a trip, the breaker stays open for a cool-down interval (default: 60s).
The next call is allowed through as a **probe**:
- A probe that succeeds with a **different** `args-hash` resets the window.
- A probe that repeats the **same** hash re-trips immediately and re-escalates HITL.

## 4. Scope

Per `(agent, task_id, tool)` — a healthy agent calling with varied queries is unaffected.
Only identical, rapid, repeated calls trip. This prevents false-positives on legitimate retry-with-backoff patterns.

## 5. Interaction With Other Subsystems

- **Rate Limiter (Phase 2.11):** Complementary — circuit breaker catches repetition; rate limiter catches volume.
- **HITL (Phase 6.5):** Auto-triggered on trip.
- **Observability (Phase 2.5):** `circuit_breaker` failure class on trip events.
