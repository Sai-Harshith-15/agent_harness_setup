# Secrets Bridge Contract

> Gap 1.3 / Phase 2.7 — Credential resolution, injection, rotation, and audit.

## Tools

| Tool | Method | Payload | Returns |
|------|--------|---------|---------|
| `request_credentials` | POST `/mcp/request_credentials` | `{ service, sandbox_id, scope }` | `{ ok, service, credential, env_injected[], expires_at }` |
| `rotate_credentials` | POST `/mcp/rotate_credentials` | `?service=<name>` | `{ ok, service, rotated, old_hash }` |
| List services | GET `/dashboard/secrets` | — | `{ services: [{ name, ttl_seconds, rotation_ttl, last_rotated }] }` |

## Design Rules

1. **Agent never sees the raw secret.** The return payload includes `{ ok: true, env_injected: ["SERVICE_KEY"] }` — the credential value is injected into the sandbox environment only, never returned in the agent-visible response body.
2. **Per-sandbox ephemeral credentials.** Each `spawn()` derives a unique ephemeral key per `(service, sandbox_id, scope)` via HMAC-SHA256 of the master key, ensuring no two sandboxes share the same credential.
3. **TTL-bound.** Every issued credential carries a configurable TTL (default 3600s). Expired credentials are rejected on validation and cleaned up.
4. **Proactive rotation.** A background loop checks every hour for services past their `rotation_ttl` (default 86400s). On rotation, the master key is replaced and all prior ephemeral derivations are invalidated.
5. **Rotation callbacks.** Services can register callbacks via `on_rotation(service, callback)` to rebuild clients (e.g., the Obsidian backend reconnects with the new token).
6. **DLP coordination.** When the DLP middleware redacts a value matching a registered service's key pattern, the secrets bridge is alerted and a rotation event is triggered.
7. **Audit trail.** All credential requests and rotations are audited with service name and sandbox_id — never the secret value.

## Credential Derivation

```
ephemeral_key = HMAC-SHA256(master_key, "service|sandbox_id|scope|expiry_window")[:32]
prefix = "ephemeral-"
```

## Env Var Loading

All env vars matching `SECRETS_<SERVICE>_KEY` are auto-loaded on startup. Optional overrides:
- `SECRETS_<SERVICE>_TTL` — credential TTL in seconds (default 3600)
- `SECRETS_<SERVICE>_ROTATION_TTL` — rotation interval (default 86400)

## Database

Table `credential_leases` in `control_plane.db`:
| Column | Type | Description |
|--------|------|-------------|
| cred_id | TEXT PK | `{service}:{sandbox_id}:{issued_timestamp}` |
| service | TEXT | Service name |
| sandbox_id | TEXT | Target sandbox |
| issued_at | TEXT | ISO-8601 |
| expires_at | TEXT | ISO-8601 |

## Sandbox Integration

The `SandboxDriver.spawn()` method queries the secrets bridge for all registered services and injects per-service ephemeral credentials into the sandbox environment. Each sandbox receives unique credentials, never the master key.

## Interaction with OTel

Every `request_credentials` call emits an OTel span with attributes `service`, `sandbox_id`, and `scope` — but never the `credential` value.

## Compliance

- [ ] No raw API key in any agent-readable response or OTel span attribute.
- [ ] Per-sandbox unique credential generation verified.
- [ ] Rotation loop runs and replaces master keys on schedule.
- [ ] Expired credentials are rejected and cleaned up.
- [ ] DLP coordination fires rotation on leak detection.
