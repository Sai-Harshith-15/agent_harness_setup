# Contract: Hibernation

> Phase 6.6 · Freeze/thaw protocol for long HITL pauses.

## 1. Freeze (on `request_clarification`)

1. **Serialize agent memory state:**
   - Active OKF concept pointers, lock set, accumulated trace/span id
   - Sandbox filesystem delta (diff against pre-task snapshot)
   - Open clarification prompt
   - Stored durably (not in sandbox) keyed by `task_id`

2. **Release all active locks** with reason `released:hibernation` (Phase 2.6).

3. **Terminate the sandbox** (Phase 0.5). No idle compute burn.

4. **Revoke the identity token** (Phase 2.8). Paused task holds no live credential.

5. **Mark task** `state: hibernated` in `PLAN.md`. Surfaced in Phase 7 evening review.

## 2. Thaw (on human answer)

1. **Provision fresh sandbox** (Phase 0.5) with same `bounds` as original.

2. **Re-acquire necessary locks** (Phase 2.6). If a lock is now held by another agent,
   thaw blocks on `acquire_lock` rather than silently overwriting.

3. **Re-issue fresh identity token** (Phase 2.8). New token's `task_id` matches hibernation record
   so OTel trace stays continuous.

4. **Hydrate state:**
   - Replay serialized memory pointers
   - Restore filesystem delta onto fresh sandbox
   - Resume agent loop at clarification prompt with human's answer injected

5. **Emit `thaw` span** (Phase 2.5) linking pre-hibernation to post-hibernation spans.

## 3. Stale-on-Thaw Drift Re-Check

Between freeze and thaw, the workspace may have moved (another agent edited a file).
On thaw:
- Phase 5.5 drift check is re-run against concepts/paths the task was working on.
- If drift is detected: agent is handed the drift banner *before* resuming.
- This binds hibernation directly to the drift-detection layer.

## 4. Forced Hibernation Cap

- Max hibernation TTL: **7 days** (configurable in `Program.md`).
- After TTL: task is auto-cancelled, hibernation record archived, human notified.
- Prevents infinite backlog of unanswered clarifications.

## 5. Interaction With Other Subsystems

- **Lock Manager (Phase 2.6):** Locks released on freeze, re-acquired on thaw.
- **Identity (Phase 2.8):** Token revoked on freeze, re-issued on thaw.
- **Drift Detection (Phase 5.5):** Stale-on-thaw re-check.
- **Crash Recovery (Phase 6.7):** Hibernation record integrity verified on startup.
