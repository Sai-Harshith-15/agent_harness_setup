# Contract: Rate Limiting

> Phase 2.11 · Token-bucket rate limiter with per-tool cost weighting and compute quota.

## 1. Token-Bucket Per (agent, task_id)

- Token-bucket algorithm with configurable refill rate.
- Default: 10 requests per 10-second window per agent.
- On burst over the limit: server returns `429 Too Many Requests` with `Retry-After` header.
- The refused call is traced as `rate_limited` in the Phase 2.5 trace.

## 2. Per-Tool Cost Weighting

Different tools have different compute costs:

| Tool | Weight |
|------|--------|
| `search_notes` | 1 |
| `read_note` | 1 |
| `search_okf` | 2 |
| `get_concept` | 1 |
| `lookup_agent` | 1 |
| `find_capability` | 1 |
| `append_implement` | 2 |
| `log_decision` | 2 |
| `delegate_task` | 3 |
| `reindex` | 5 |
| `compress` | 3 |

Weighted cost applies per call; the token bucket is consumed accordingly.

## 3. Per-Task Compute Quota

Beyond RPM, a hard per-task compute-quota ceiling (token-equivalent units):
- Derived from the task's `bounds` field in `PLAN.md`.
- Default: unlimited unless `max_tokens` is set on the adapter.
- An agent that burns its quota mid-task is auto-paused into the Phase 6.6 hibernation flow for human review.

## 4. Distinguishing Rate-Limit from Circuit-Breaker

- **Circuit breaker (Phase 2.9):** catches *repetition* (same call, likely a stuck loop -> HITL).
- **Rate limiter (Phase 2.11):** catches *volume* (many distinct calls, possibly legitimate -> throttle and let it proceed slower).

Both feed the same Phase 7.3 token accounting.

## 5. Interaction With Other Subsystems

- **Circuit Breaker (Phase 2.9):** Complementary triggering.
- **Hibernation (Phase 6.6):** Quota exhaustion auto-hibernates.
- **Token Accounting (Phase 7.3):** All calls (accepted and rate-limited) are tracked.
