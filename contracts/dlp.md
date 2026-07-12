# Contract: Data Loss Prevention (DLP)

> Phase 2.12 · Combined read-edge + write-edge + export-hook pipeline.
> Prevents secrets, PII, and high-entropy tokens from landing in durable stores.

## 1. Pattern Matching

The `DLPFilter` scrubs text via regular expressions **and** entropy analysis.
The following patterns are mandatory:

| Priority | Pattern | Replacement Token |
|----------|---------|-------------------|
| 1 | AWS keys: `AKIA[0-9A-Z]{16}` | `[REDACTED:aws_key:<hash6>]` |
| 1 | Bearer tokens: `Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*` | `Bearer [REDACTED:token:<hash6>]` |
| 1 | GitHub PATs: `ghp_[0-9a-zA-Z]{36}` | `[REDACTED:github_pat:<hash6>]` |
| 1 | Slack tokens: `xox[baprs]-[0-9a-zA-Z\-]+` | `[REDACTED:slack:<hash6>]` |
| 1 | PEM private keys: `-----BEGIN (PRIVATE\|RSA\|EC\|OPENSSH\|DSA) KEY-----.*?-----END \1 KEY-----` | `[REDACTED:private_key:<hash6>]` |
| 2 | PII emails: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` | `[REDACTED:email:<hash6>]` |
| 2 | Phone numbers: `\+?1?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}` | `[REDACTED:phone:<hash6>]` |
| 2 | Credit cards: `\b(?:\d[ -]*?){13,16}\b` (with Luhn validation) | `[REDACTED:cc:<hash6>]` |
| 3 | High-entropy strings: Shannon entropy ≥ 4.5 over candidate runs ≥ 24 chars | `[REDACTED:high_entropy:<hash6>]` |

**Redaction token format:** `[REDACTED:<kind>:<hash6>]` where `<hash6>` is the first 6 hex chars
of `sha256(original_value)`. The hash lets a human with the vault re-identify *which* secret
without the secret appearing in traces or logs.

**Entropy detection (Gap 3.2):** A sliding-window Shannon entropy scan runs over tokenized
input. Any run ≥ 24 characters with entropy ≥ 4.5 bits/char is treated as a candidate
high-entropy string and redacted. This catches secrets not matching known brand patterns.

## 2. Hit Policies

Administrators configure `DLP_HIT_POLICY` (env var, default `redact`). On any pattern match:

### `redact` (default)
- Replaces matched substrings with `[REDACTED:<kind>:<hash6>]` placeholders.
- Emits a `secret_redacted` or `pii_redacted` event to the trace pipeline (Phase 2.5).
- Allows the request to proceed with scrubbed content.
- Logs to `audit_log` with `tool="dlp"`, `detail="<kind>:<hash6>"`, `ok=true`.

### `block`
- Immediately raises `HTTPException(403)` with `detail="dlp_violation: <kind>"`.
- Emits `dlp_blocked` failure-class trace event.
- The secret is **never persisted** — the write is fully aborted.

### `quarantine`
- Persists the *original unredacted payload* to the `dlp_quarantine` table.
- Table schema: `(id, kind, hash6, original_text, source, created_at, reviewed)`.
- Returns `202 Accepted` to the agent (not 403) so the agent's loop does not stall.
- The write to the target resource **is not performed** — the content is held.
- Emits `dlp_quarantined` failure-class trace event.
- A human reviews quarantine entries via `/dashboard/dlp/quarantine` and may `release`
  (write proceeds with redacted text) or `reject` (permanently discard).

## 3. Coverage — Three Edges

DLP scrubbing runs on **three boundaries**:

| Edge | When | Action |
|------|------|--------|
| **Read edge** | `read_note`, `search_notes`, `search_okf`, `get_concept` return payloads | Scrub before returning to agent context. |
| **Write edge** | `append_implement`, `log_decision`, vault edits, OKF exports | Scrub before persisting to disk / DB. |
| **Export hook** | Obsidian → OKF bundle export pipeline (Phase 4.2) | Scrub during transformation. |

## 4. Secrets-Bridge Coordination

When a redaction matches a **registered** credential (known to the Phase 2.7 secrets bridge):
- The bridge is consulted: `lookup(hash6)` returns `service` and `last_rotated`.
- A **rotation alert** is raised: the human is notified that a registered secret leaked.
- The secret is immediately expired in the bridge and a new credential is issued.
- The event is tagged `secret_leaked_rotated` in the trace.

When a redaction matches **no** registered credential:
- It is surfaced as a "suspected leaked credential" candidate in the Phase 7 evening review.
- The redaction log entry carries `source` (which Obsidian note / OKF bundle / tool payload
  contained the match) so the human can root-cause and rotate if needed.

## 5. Interaction With Other Subsystems

- **Phase 2.5 traces:** Every redaction/block/quarantine event is traced with `args-hash`,
  `failure_class`, and the `kind` of secret detected.
- **Phase 2.9 circuit breaker:** Repeated DLP hits on the same `(agent, tool)` count toward
  the breaker's failure tally. A breaker trip on DLP auto-quarantines the agent's current task.
- **Phase 6.3 write pipeline:** `DLPFilter.scrub()` wraps every write via `governed_write`,
  ensuring no write path bypasses DLP.
- **Phase 7 evening review:** Quarantine items and suspected leaked candidates are included
  in the evening standup rollup.
