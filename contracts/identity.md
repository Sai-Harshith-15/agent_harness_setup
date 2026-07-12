# Contract: Identity

> Phase 2.8 · Zero-trust transport-layer identity with Lamport-step expiry.

## 1. Token Issuance

At task startup, the Context Server issues a unique, short-lived, signed identity token:

```
HMAC-SHA256({agent_id}:{task_id}:{issued_at}:{lamport_seq})
```

Format: `{agent_id}:{task_id}:{signature}`

The token is delivered out-of-band to the agent process (env var / startup handshake), **never via the LLM prompt**.

## 2. Transport Binding

- **HTTP MCP server:** Agent presents token in `X-Agent-Identity` header on every request.
  The Context Server extracts identity strictly from the authenticated connection.
- **stdio/socket MCP:** Server validates peer PID/socket credential (`SO_PEERCRED` on Linux, named-pipe ACL on Windows).

## 3. Payload Identity Override Rule

Any `agent` / `task_id` field the LLM places in the JSON body is treated as **untrusted hint text only**.
The server overwrites it with the transport-derived principal.

A mismatch (payload claims a different agent than the transport proves) is:
- Logged as `identity_spoof_attempt` failure class in the OTel trace.
- Counted toward the Phase 2.9 circuit breaker.
- The request **proceeds** with the transport principal (not rejected — we don't want prompt-injected payloads to cause denial-of-service).

## 4. Token Rotation on Hibernation

On Phase 6.6 thaw, a fresh identity token is issued so a resumed task is not bound to a stale credential.
The new token carries the same `task_id` so the OTel trace stays continuous.

## 5. Lamport-Step Expiry

The signed token payload carries a **monotonically increasing logical sequence step** (Lamport timestamp).
Expiry and freshness are validated against the server's logical sequence counter, **not** the host wall-clock.
Wall-clock `issued_at`/`exp` fields are kept only as human-readable hints.

## 6. Token Revocation

Tokens are task-scoped and expire with the task's `bounds` window.
The Phase 6.6 Hibernation Protocol re-issues a fresh token on state hydration.

## 7. Interaction With Other Subsystems

- **Permission Matrix (Phase 6.2):** Evaluated against the transport principal, not the body.
- **Circuit Breaker (Phase 2.9):** `identity_spoof_attempt` events increment the breaker counter.
- **Hibernation (Phase 6.6):** Fresh token issued on thaw.
