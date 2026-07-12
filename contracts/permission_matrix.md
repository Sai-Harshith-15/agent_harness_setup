# Contract: Permission Matrix

> Phase 6.2 · Write permission matrix with combinatorial lethal-trifecta rule.

## 1. Default DENY

All Obsidian writes are denied by default. Only two write shapes are allowed:
1. Append to a designated agent-writable `log.md` heading (`Agent Updates`, `Decisions`, `Implementation Log`).
2. Append to the daily note's `Agent Updates` heading.

## 2. Write Table (agents x targets)

| Agent | Can Write To | Heading |
|-------|-------------|---------|
| opencode | `okf/log.md`, `IMPLEMENT.md`, `registry/log.md` | Agent Updates, Implementation Log |
| hermes | `okf/log.md` | Agent Updates, Decisions |
| claude-code | `okf/log.md`, `IMPLEMENT.md` | Agent Updates, Implementation Log |
| antigravity | `okf/log.md` | Agent Updates |
| codex | `okf/log.md` | Agent Updates |
| meta | `okf/log.md` | Agent Updates |

Any write outside this table is denied with `permission_denied`.

## 3. Combinatorial Lethal-Trifecta Rule

An agent with simultaneous access to:
- (a) private data (`read_private` provenance)
- (b) untrusted external content (`X-Provenance: untrusted`)
- (c) external-communication tools

Cannot pair (b) with (a) or (c) in the same session unless a human explicitly elevates.

**Instruction provenance rule:** A tool call whose trigger content came from an untrusted source
cannot pair with private-data or external-egress tools in the same session.

This is a **server-side control**, not a prompt-level hint — it survives prompt injection.

## 4. Read-Side Mirror

The provenance tag that drives the lethal-trifecta write gate also drives read-edge context chaperoning
(Phase 2.13). Untrusted-provenance reads branch the task's telemetry into an isolated, macro-span-collapsed
stream.

## 5. Interaction With Other Subsystems

- **Identity (Phase 2.8):** Matrix evaluated against transport principal, not body claims.
- **Read Chaperon (Phase 2.13):** Provenance tag shared between write-gate and read-isolation.
- **HITL (Phase 6.5):** Human can elevate privilege for specific sessions.
