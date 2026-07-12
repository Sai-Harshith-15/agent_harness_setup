# Contract: Optimistic Concurrency Control (OCC)

> Phase 2.10 · Read-modify-write protection against lost updates across multi-turn agent loops.
> Complementary to the Phase 2.6 lock manager: locks serialize writes; OCC guarantees freshness.

## 1. Version Hash Computation

| Resource Type | Hash Method | Example |
|---------------|------------|---------|
| Git-tracked files (`*.py`, `*.ts`, `*.tsx`, etc.) | `git hash-object` → blob SHA | `3c4e9a...` |
| Untracked mutable files (`log.md` outside repos, Obsidian notes) | xxhash64 | `a1b2c3d4e5f6` |
| Append-only ledgers (`IMPLEMENT.md`, `okf/log.md`) | **Position offset**, not content hash | See §3 |

## 2. Read Path

Every read tool (`read_note`, `get_concept`, `search_okf`, `search_notes`) returns:

```
X-Version: <hash_or_offset>
```

The agent MUST store this version alongside its read of the resource.
The version is opaque to the agent — it simply echoes it back on write.

## 3. Write Path — Mutable Resources

For mutable files and OKF concepts:

1. Agent sends `X-Expected-Version: <hash_from_read>` with the write request.
2. Server recomputes the current hash of the target resource.
3. **If `current_hash == X-Expected-Version`:** Write proceeds. Server returns new `X-Version`.
4. **If `current_hash != X-Expected-Version`:** Server rejects with:
   ```
   HTTP 412 Precondition Failed
   X-Error-Code: state_changed
   X-Current-Version: <new_hash>
   ```
5. Agent protocol on `state_changed`:
   - Re-read the resource (acquire new `X-Version`).
   - Re-apply modifications locally against the fresh content.
   - Re-attempt the write with the updated `X-Expected-Version`.

## 4. Write Path — Append-Only Ledgers

For `IMPLEMENT.md`, `okf/log.md`, and other append-only ledgers:

- Content hashing would yield false `state_changed` rejections on concurrent appends.
- Instead, the version is a **byte-offset position** of the ledger tail.
- Write tool sends `X-Expected-Version: <position_from_read>` (the file length in bytes).
- Server checks: `current_position == X-Expected-Version`.
  - **Match:** Append proceeds. Returns new position as `X-Version`.
  - **Mismatch:** Another agent appended. Reject with `state_changed`.
- The agent re-reads the ledger tail, merges its append, and retries.

## 5. Hibernation Interaction (Phase 6.6)

When a task is hibernated:

- The **hibernation record** stores `{resource_path: version_hash}` for every resource the task
  has read but not yet written to.
- On **thaw**, the server performs a staleness check:
  - For each watched resource, compare the stored version against the current version.
  - If any resource has changed, the agent receives a `state_changed` banner in the thaw response
    with the list of stale resources and their new versions.
- This unifies hibernation staleness detection under the same OCC primitive — no separate
  drift-detection mechanism is needed.

## 6. Interaction With the Lock Manager

OCC and the Phase 2.6 lock manager are **complementary**:

| Scenario | Lock | OCC | Outcome |
|----------|------|-----|---------|
| No concurrent access | Not needed | Passes (fresh) | Write succeeds. |
| Concurrent write attempt | Contention → one waits, one holds | N/A | Serialized by lock. |
| Agent A reads, waits 5 turns, acquires lock, writes | Held at write time | Fails if B wrote in between | `state_changed` — A must re-read. |
| Append to `log.md` | Not needed (append is safe without lock) | Position check | Concurrent appends serialized by position. |

## 7. Example Flow

```
Agent reads script.py          → X-Version: abc123
Agent spends 3 turns reasoning
Agent B reads script.py        → X-Version: abc123
Agent B edits and writes        → X-Expected-Version: abc123 → OK → new X-Version: def456
Agent attempts write            → X-Expected-Version: abc123
                                → 412 state_changed (current: def456)
Agent re-reads script.py        → X-Version: def456
Agent re-applies changes
Agent attempts write            → X-Expected-Version: def456 → OK → new X-Version: 789ghi
```
