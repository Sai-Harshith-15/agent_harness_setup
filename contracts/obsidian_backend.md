# Contract: Obsidian backend

- Endpoint: https://127.0.0.1:27124/mcp/  (HTTP fallback http://127.0.0.1:27123/mcp/)
- Auth: Authorization: Bearer <OBSIDIAN_REST_API_KEY> — held by the secrets bridge only.
  The Context Server's Obsidian client is the ONLY consumer of this key. Never in agent prompts.
- Direction rule: Obsidian → OKF is one-directional. Agents never write arbitrary human notes.
  Allowed writes: (a) designated agent-writable log.md headings, (b) the daily note's
  "Agent Updates" heading. Everything else is a permission-matrix DENY.
- Idempotency: every Obsidian-bound write wraps vault_patch with rejectIfContentPreexists=true
  so a thaw re-issue / breaker retry / crash-reconcile replay cannot double-append.
- OCC: read_note attaches a version hash; a human mid-flight edit surfaces as a state_changed
  rejection on the next agent write, never a silent overwrite.
