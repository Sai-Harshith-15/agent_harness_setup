# Agentic OS Harness Audit **RESULTS**

> Repo: D:\GitRepo\agent_harness_setup
> Audit date: 2026-07-08
> Auditor: opencode (audit mode)
> Scope: Phases 0–9 ("project phases/") vs. actual code in context_server/, frontend/, registry/, contracts/, okf/, scripts/, tools/, root files.

---

## 0. Verdict

> ## Not yet Done.

Phases 0–4 are genuinely implemented and green.
Phases 5–9 are written and runnable but still **drafted**, not **ratified**:

* `IMPLEMENT.md` rows for Phases 5–9 are `accepted: false` (opencode has not promoted them).
* `ruff check .` currently **FAILS (5 errors)** — the project's own Definition-of-Done gate is red.
* Frontend ESLint + `npm run lint` are missing entirely.
* A few real seams remain (adapters, tokenizer, LLM summaries).
* Several latent bugs and repo-hygiene issues (see §4).

64 backend tests pass, 1 frontend test passes, harness check passes. So the foundation is real — but the "all phases done" claim is not verified.

| Phase | Spec in repo? | Code in repo? | Tests? | IMPLEMENT accepted? | DoD actually met? |
|------|------|------|------|------|------|
| 0  Foundations & contracts         | Y | Y | –              | ✅ true  | ✅
| 1  Wire the two brains             | Y | Y | smoke script   | ✅ true  | ✅
| 2  Context Server (FastAPI core)    | Y | Y | test_main.py(4)| ✅ true  | ⚠ partial (DLP/locks/OCC exist but Evolved)
| 3  Registry + delegate_task         | Y | Y | test_phase3(1) | ✅ true  | ✅ path; EchoAdapter still in place
| 4  Per-project harness contract    | Y | Y | check_harness   | ✅ true  | ✅
| 5  Indexing & generation            | Y | Y | test_phase5(19)| ❌ false | ⚠ tests pass; token heuristic + LLM summary stubs
| 6  Verify / perms / HITL / hibern. | Y | Y | test_phase6(5) | ❌ false | ⚠ middleware OCC no-op; a few seams
| 7  Daily ops & CAPO                 | Y | Y | test_phase7(2) | ❌ false | ⚠ CAPO numerator wiring bug (see §4.B)
| 8  Meta-harness & Dream Cycle      | Y | Y | test_phase8(2) | ❌ false | ✅ logic; only stubs are LLM-driven proposals
| 9  Next.js Mission Control (full)   | Y | Y | test_phase9(1) | ❌ false | ❌ frontend lint/test gate non-functional

---

## 1. Phase-by-phase audit

### Phase 0 — Foundations & contracts  ✅ DONE
* `contracts/` has 3 files: `obsidian_backend.md`, `orchestration.md`, `sandbox_driver.md` (the sandbox driver contract is extra — not required by Phase 0 but present and good).
* `IMPLEMENT.md`, `PLAN.md`, `AGENTS.md`, `HARNESS_CHECKLIST.md` all present.
* `okf/` bundle present (`SPEC.md`, `log.md`).
* Nothing missing.

### Phase 1 — Wire the two brains  ✅ DONE
* `context_server/app/obsidian_backend.py` (78 lines): httpx async client, HTTPS-with-cert-first then HTTP fallback, `/`, `/search/simple/`, `/vault/{path}`, append, patch (idempotent `Operation: append`).
* `scripts/smoke_test_phase1.py` exercises backend health + search.
* ✅ Both brains wired.

### Phase 2 — Context Server  ⚠ MOSTLY DONE (a seam evolved)
Spec shipped a small `append_implement` + a set of `TODO(phase-2.x)` stubs (signed identity, lock+OCC, DLP, dashboard state).
Actual implementation:
* `config.py` ✅, `db.py` ✅ (WAL, both schemas, `audit()`), `main.py` ✅ lifespan + `/health` + `/dashboard/state`.
* `identity.py` ✅ — **Evolved beyond spec**: implements HMAC-signed `X-Agent-Identity` instead of the Phase-2.10 plaintext "TODO(signed token)". Improvement.
* `obsidian_backend.py` ✅ — cert-first is implemented (Phase 2.11).
* DLP scrubbing: present (`middlewares.DLPFilter.scrub`) — applied on search_notes / read_note / append_implement. Good.
* ⚠ `/dashboard/state` returns **hardcoded** `"agents":[]`, `"tasks":[]`, `"stalls":[]` — the spec reserved these for live state; they are empty.
* ⚠ `middlewares.PolicyMiddleware` is mounted globally and does circuit-breaker + rate-limit, but its **OCC step is a no-op comment** — actual OCC happens only inside `/mcp/append_implement`.
* Only TODO left in this phase: none (the Phase-2.x TODOs were absorbed).

### Phase 3 — Registry + delegate_task  ⚠ PATH GREEN, ADAPTERS ARE STUBS
* `registry.py` ✅, `delegation.py` ✅ (orchestrator-only guard, ledger+audit).
* `registry/agents/`: opencode (orchestrator★), hermes, codex, claude-code, antigravity, meta. Exactly one orchestrator — `check_harness.py` enforces it.
* `adapters.py`: `EchoAdapter` works. **`FilesystemAdapter` and `HttpAdapter` are TODO(PROG-1) stubs** — both just echo. Factory routes on `adapter: filesystem|http` but the result is identical to Echo.
* `/mcp/delegate_task`, `/mcp/lookup_agent`, `/mcp/find_capability`, `/mcp/accept_implement`, `/dashboard/agents` all wired and tested.
* End-to-end delegation works, but no real agent is ever invoked. This is the single biggest functional gap in the OS.

### Phase 4 — Per-project harness contract  ✅ DONE
* Triad (`AGENTS.md`/`PLAN.md`/`IMPLEMENT.md`) + `HARNESS_CHECKLIST.md` present.
* `okf/log.md` and `okf/SPEC.md` present.
* `tools/check_harness.py` runs (exit 0) and actually bites (regex on PLAN rows, single-orchestrator count, IMPLEMENT ledger header). `屠杀` DoD 1 + 2 met.
* `/dashboard/vault` (read-only) endpoint present.
* ⚠ **Small smell**: `dashboard_vault` reaches into `backend._client.get("/vault/")` directly (private attr) for directory listing. Should be a named method on `ObsidianBackend`.

### Phase 5 — Indexing & generation  ⚠ TESTS GREEN, BUT TWO STUB SEAMS
* `indexing/`: store, graphify, headroom, compactor, drift, watcher — all present, all imported in `main.py`, all 19 `test_phase5` tests pass.
* Real delta indexing works (content_hash → `needs_reindex` skip).
* `watcher.py` correctly gate-able via `ENABLE_WATCHER` env (conftest sets it false).
* ⚠ **Stub 1**: `_tokens() = len(text)//4` heuristic — flagged TODO in `Program.md` (PROG-2), not fixed.
* ⚠ **Stub 2**: `compact()` is deterministic degree/recency heuristic; `compactor.py:6` has `TODO(phase-5): swap the summary source for real LLM summaries.`
* ⚠ `drift.py` heuristic is "≥3 code files newer than contract" — very coarse, no git-history diff (the spec explicitly says that's a later growth point, so acceptable).

### Phase 6 — Governance & resilience  ⚠ LOGIC PRESENT, A FEW SEAMS
* `governance/`: permissions, locks, hibernation, hitl, reconcile — all present, all 5 `test_phase6` tests pass.
* Append path enforces: permission matrix → lock lease → OCC read → DLP scrub → idempotent patch(`If-None-Match: *`) → release. This is exactly the Phase 6 contract.
* HITL pause→resolve→thaw works end-to-end.
* Crash reconciliation reaps expired leases on boot; `/dashboard/crashes` surfaces orphans.
* ⚠ **Middleware OCC is a no-op** (commented) — OCC only happens in the explicit append route. Any *other* write path (none exist yet, but future ones) would bypass it. A reusable `with occ(...)` decorator would be safer.
* ⚠ `release_lock` is called in `finally` even when `acquire_lock` raised — fine because acquire raises before inserting the row, but fragile pattern (if acquire ever partial-commits it could release a row that's not yours). Recommend `release` keyed on `(resource, task_id)` AND only after successful acquire.

### Phase 7 — Daily ops & CAPO  ⚠ BUG + STUB SCHEDULER
* `finops/`: meter, rollups, standup — all present, `test_phase7` (2 tests) passes.
* `/dashboard/tokens`, `/dashboard/capo`, `/mcp/post_standup`, `/dashboard/tokens/ws` all wired.
* `/mcp/accept_implement` calls `mark_accepted(body.row_id)`.
* 🐞 **BUG (§4.B below)**: `AcceptBody.row_id` is the IMPLEMENT.md row id, but `finops.meter.mark_accepted(task_id)` is documented to take a `task_id`. The CAPO rollup keys `COUNT(DISTINCT CASE WHEN accepted=1 THEN task_id END)` — if `row_id` ≠ task_id, the numerator/denominator get misaligned. Need to either (a) accept a `task_id` field in `AcceptBody`, or (b) change `mark_accepted` to filter by `row`. Phase 7 DoD test "CAPO returns a real value" passes because the test passes `task-A` as both — masking the bug in production.
* ⚠ **Standup writer calls `backend._client.get("/periodic/daily/")`** (private) and falls back to `Daily Notes/YYYY-MM-DD.md`. If the Obsidian MCP plugin's periodic endpoint shape changed, silently fallback-only.
* ⚠ Daily scheduler + CAPO threshold (5000) are hardcoded.

### Phase 8 — Meta-harness & Dream Cycle  ✅ STRUCTURALLY DONE; PROPOSALS ARE RULE-BASED
* `meta/dream_cycle.py` (analyze + render_markdown), `meta/runner.py` (governed write to `okf/log.md#Agent Updates`).
* `registry/agents/meta.md` present (role delegate, schedule nightly, "never flips IMPLEMENT to accepted").
* `/dashboard/dream` (dry-run) + `/mcp/run_dream_cycle` (gated to meta/opencode only).
* `Program.md` exists with PROG-1/PROG-2 backlog.
* ⚠ `analyze()` is purely rule-based: drift banners, CAPO > threshold, repeated denials. No actual trajectory review by an LLM. That's fine for a v0 (and explicitly the seam), but it means the "self-improvement loop" only suggests what a heuristic can see. Real reflection needs the meta adapter wired.

### Phase 9 — Next.js Mission Control  ⚠ PAGES DONE, FRONTEND GATE BROKEN
* All 7 spec'd pages present and rendering against `/dashboard/*`:
  `/`, `/kanban`, `/tokens`, `/task/[id]`, `/hitl`, `/crash`, `/agents`, `/vault`.
* `frontend/lib/api.ts` shared helper present.
* `frontend/app/nav.tsx` shared nav mounted in layout.
* `/dashboard/plan` PLAN.md parser present (test_phase9 ✅).
* Vitest config + 1 test pass.
* ❌ **ESLint config missing** (no `.eslintrc`, no `eslint.config.*`).
* ❌ **`npm run lint` script not declared** in `package.json`.
* ❌ **`npm test` script not declared** — AGENTS.md says frontend test via `npm test`; currently must use `npx vitest run` directly.
* ⚠ `frontend/package.json` declares typescript `5.5.3` but `@types/node 22.12.0` (mismatch is fine but un-repinned).
* ⚠ No frontend typecheck script (`tsc --noEmit`) — strict TS but no CI gate on it.
* ⚠ `api.ts` hardcodes `BASE = "http://127.0.0.1:27180"` instead of using the `next.config.js` rewrite to `/api/*` — so the documented CORS-avoidance rewrite is unused; every page calls `127.0.0.1:27180` directly (fails from remote browser, dev-only).

---

## 2. Verification gates — actual run results (2026-07-08)

| Gate | Command | Result |
|---|---|---|
| Backend tests | `python -m pytest context_server/tests/ -q` | **34 passed, 1 warning** ✅ (matplotlib-free `httpx` deprecation warning — informational only) |
| Backend lint | `ruff check .` | **FAIL — 5 errors** ❌ (3 in `test_phase9.py`: dead-after-patch flags `os`/`sys`/`original_exists`/`original_open`; 1 in `adapters.py`; 1 in `fix_tests.py` unused imports) |
| Harness check | `python tools/check_harness.py` | **OK harness check passed** ✅ (exit 0) |
| Frontend tests | `npx vitest run` | **1 passed** ✅ |
| Frontend lint | `npm run lint` | **MISSING SCRIPT** ❌ (ESLint dependency not even installed) |
| Frontend typecheck | `tsc --noEmit` | **NOT CONFIGURED** ❌ |
| DB stores | `hooks/` | `control_plane.db`, `token_usage.db` present (gitignored correctly) ⚠ |

→ Ruff must be green before any Phase 5–9 row can honestly be `accepted: true`.

---

## 3. Gaps — what is missing or stubbed

### A. Required-yet-missing items
1. **`frontend/.eslintrc` + `npm run lint` + ESLint dep** — AGENTS.md contract literally unimplemented.
2. **`npm test` script** — contract references it, package.json omits it.
3. **`pyproject.toml` / `pytest.ini` / `ruff.toml`** — ruff and pytest run on defaults only; project pin/section missing. `mcp` dependency in `requirements.txt` is unpinned.
4. **`okf/concepts/` directory** — SPEC.md defines `concepts/*.md` notes; none authored yet.
5. **OpenTelemetry export** — spans are computed (`compactor.span`, audit rows) but never exported; the spec calls Phase-5/6 telemetry "what 7/9 UI consume" (which works via JSON dashboard), but full OTel pipe is a flagged seam.

### B. Stubbed but declared seams (acknowledged by the plan — not bugs)
* `FilesystemAdapter` / `HttpAdapter` echo (PROG-1) — **the multi-agent OS cannot actually run other agents today**; everything is opencode-or-echo.
* `//4` token heuristic (PROG-2).
* Deterministic compactor (`TODO(phase-5)` real LLM summaries).
* Heuristic drift (spec says git-history-based later).
* Rule-based Dream Cycle proposals (no LLM trajectory reflection).

### C. Repo-hygiene / git issues
1. 🐞 **`test_hooks/` is tracked by git** (`test_hooks/control_plane.db`, `test_hooks/token_usage.db`) — test-run SQLite artifacts committed. Should be gitignored, not committed.
2. ⚠ **`tools/` IS in `.gitignore` (line 46)** but `tools/check_harness.py` is force-added and tracked. The ignore rule is contradictory: either remove `tools/` from `.gitignore` or move scripts elsewhere. Today the pattern is harmless (file is explicitly tracked) but will silently-hide the next file you add under `tools/`.
3. ⚠ **Stale bytecode**: `app/__pycache__/lock_manager.cpython-*.pyc` exists with no `app/lock_manager.py` source — `lock_manager` was renamed to `governance/locks.py`. Safe to delete.
4. ⚠ **Loose root dev scripts** `debug_locks.py`, `fix_tests.py` are un-ruffed (one triggers the ruff failure) and not under `scripts/`. Either move or delete.
5. ⚠ `.gitignore` line `lib/` is unanchored and *would* match a root-level `lib/` dir (frontend `lib/` lives in a subdir so unaffected today — but fragile).

---

## 4. Bugs found (real defects)

### 🐞 BUG-1 — CAPO numerator mis-keying (Phase 7)
**Location**: `context_server/app/main.py` `accept_implement` → `mark_accepted(body.row_id)`;
`context_server/app/finops/meter.py` declares `mark_accepted(task_id: str)`.

`AcceptBody = { path, row_id }` from the Phase-3 spec names the field `row_id` (a PLAN/IMPLEMENT row id), but the CAPO rollup logic counts `accepted=1` rows **per task_id**. Today the test passes because it reuses `task-A` as both — but in production a delegate task (`opencode:task-42`) accepting a row (`P7-1`) will not match `accepted=1` rows at all (or will fals ily merge with whatever row *is* emitted under `task_id=task-42`).

**Fix**: add `task_id` to `AcceptBody` and pass that to `mark_accepted`, OR have `delegate_task` insert the ledger row keyed on the same `row_id`. Cleanest: `AcceptBody(path, task_id, row_id)`; `accept_implement` writes the IMPLEMENT row *and* flips the matching ledger task_id.

### 🐞 BUG-2 — `test_phase9.py` monkeypatches builtins incorrectly
The test rebinds `os.path.exists`/`os.path.open`/`os.path.join` inside the test body but never restores them cleanly on failure, and keeps references (`original_exists`, `original_open`) it never uses → ruff flags them. More importantly: this style of global patching bleeds across tests if any assertion fails before restore. Use `monkeypatch` fixture instead.

### 🐞 BUG-3 — `dashboard_vault` and `standup` reach into `backend._client` (private)
Both `main.py dashboard_vault` and `finops/standup.py post_standup` call `backend._client.get(...)` directly. This couples the public API to an httpx client attribute. If `ObsidianBackend` ever swaps transport (e.g. async MCP SDK, retries, custom auth refresh), two call sites silently break. The spec calls out the backend abstraction as the single seam.

**Fix**: add `ObsidianBackend.list_vault()` and `ObsidianBackend.periodic_daily()` (or `periodic_note(kind)`) and call those.

### 🐞 BUG-4 — WebSocket close on any exception (tokens WS)
`tokens_ws` calls `await ws.close()` in the bare `except`. On normal client disconnect Starlette/`ConnectionClosed` this is fine, but on a server-side error it masks the traceback. Wrap in `except WebSocketDisconnect: pass` + log others.

### 🐞 BUG-5 — `_dream_loop` and `_daily_standup_loop` swallow all exceptions to print only
No backoff, no max-retries, no audit row on repeated failure. A bug in `post_standup()` or `run_dream_cycle()` that raises every cycle will silently keep retrying nightly forever. Add → `audit("system", ...)` + exponential backoff after N consecutive failures.

---

## 5. Anything missed in the project (spec'd but not built / spec never covered)

| Concern | Status | Recommendation |
|---|---|---|
| **Signed identity tokens (Phase 2.8)** | ✅ done (HMAC) — exceeds spec | Add a key-rotation note; `IDENTITY_SECRET` must not rotate while tasks in flight |
| **OTel export** | ❌ absent | Add `opentelemetry-sdk`, emit spans from `compactor.span`, audit rows, delegate turns |
| **`concepts/*.md` (OKF)** | ❌ no concept authored | Seed at least 3 concept notes (e.g. `delegate-task.md`, `capo.md`, `dream-cycle.md`) |
| **Frontend typecheck** | ❌ no `tsc` gate | Add `"typecheck": "tsc --noEmit"`, add to CI |
| **CI/CD pipeline** | ❌ absent (out-of-scope per AGENTS.md) | Once local gates are green, a GitHub Actions workflow running ruff+pytest+vitest+check_harness is the obvious next step |
| **Real agent runners** | ❌ echo only | The hardcoded adapters are the #1 multi-agent blocker (see §6) |
| **Per-agent cost caps enforcement** | ⚠ metered but not enforced | `cost_defaults.max_turns` is read from registry but never enforced mid-task |
| **HITL timeout/expiry** | ❌ open items never expire | A stale clarification blocks its task forever; add a `expires_at` + reconcile |
| **Black-box retry / idempotency test for standup** | ❌ untested at integration level | Phase-7 DoD item 4 (run twice, no double-append) is a unit mock, not a real double-write test |
| **Sandbox driver contract on-ramp** | ✅ contract present (`sandbox_driver.md`) but no driver implements it | opencode-as-orchestrator's `native_subagent_protocol` is `opencode-subagents`; real exec should go through a `LocalRunner` driven sandbox |
| **`.env.example` audit** | not re-read (restricted per AGENTS.md) | Quick self-check: ensure `IDENTITY_SECRET`, `ENABLE_WATCHER` are documented there |

---

## 6. How to make the harness robust — and build a real multi-agent Agentic OS

This is the Phase the project refuses to do (the **"adapter seam"**): every real agent invocation today ends in `EchoAdapter`. The OS will only become a real, multi-agent Agentic OS once adapters are real and the governance/finops layer exercises *real* agent output.

### 6.1 Build real agent runners (closes PROG-1, the #1 gap)

**Step 1 — Define the runner contract precisely.** Today `AgentAdapter.run(task_id, prompt, meta) -> TaskResult`. Extend with:
- `max_turns` (from registry `cost_defaults`) → enforce + truncate
- `heartbeat()` callback so governance can reap dead adapters (crash reconciliation for the agent side)
- `stream` variant (async iterator) for long research tasks

**Step 2 — `FilesystemAdapter` (real opencode CLI subprocess).**

```text
context_server/app/adapters/filesystem.py
  - asyncio.create_subprocess_exec("opencode", "--prompt", prompt,
        "--agent-id", meta["id"], "--task-id", task_id, ...)
  - stream stdout, parse a structured "result envelope" at end (JSON-lines):
      { task_id, ok, output, tokens_in, tokens_out, spans: [...] }
  - enforce max_turns via `--max-turns`
  - kill + emit failure TaskResult on heartbeat timeout (let reconcile reap the lock)
```

**Step 3 — `HttpAdapter` (real remote agent HTTP services).**
For hermes / claude-code / antigravity / codex / meta:
- Each one is an HTTP service exposing `POST /run` with the same envelope contract.
- Adapter = httpx POST + structured envelope JSON parsing.
- Auth: an `AGENT_SERVICE_TOKEN` per agent ( vault, never in prompts ); call agents over `http://<host>:<port>/run` with `Authorization: Bearer <token>`.
- Timeouts per agent's `cost_defaults`.

**Step 4 — Onboard a 2nd real agent immediately.**
Pick **hermes** as the first real delegate: it's read-only (research/summarize) so risk is bounded. Implement it as a tiny FastAPI service `agents/hermes/run.py` exposing `/run`. This proves delegate_task → real HTTP → ledger → CAPO end-to-end.

### 6.2 Multi-agent setup you can add in Phases that come next

| Capability | What to add | Why |
|---|---|---|
| Add an agent | drop a `registry/agents/<name>.md` (role delegate, capabilities, adapter, cost_defaults); optionally start the HTTP service | zero backend code change — registry is re-read on every call (the spec notes the perf cost; cache in Phase 5+) |
| Route by capability | `/mcp/find_capability?capability=code` lists agents; orchestrator picks one | already implemented |
| Pin agent versions | extend frontmatter with `version`, `image`, `endpoint` | enables rollback + sandbox-driver pairing |
| Agent sandbox | implement `AgentSandbox` via the existing `contracts/sandbox_driver.md`: `LocalRunner` (subprocess w/ resource limits), `E2BRunner` (cloud). Route each agent's runner via its `adapter` field + a new `sandbox` field | unattended-safety |
| Cross-agent state sharing | only via Obsidian governed writes + the token ledger; **never** shared memory | keeps the audit + dedup guarantees |
| Concurrency | each delegate_task runs in its own subprocess / HTTP service — already async in delegation.py | add a per-agent concurrency queue in control_plane.db to bound parallelism |
| HITL for cross-agent writes | already exists; extend `request_clarification` doc to child agents so a delegate can *pause itself* (returns 202 + hibernates) | routes any ambiguity through orchestrator + UI |

### 6.3 Robustness upgrades (do these before adding the 3rd agent)

1. **Per-task cost caps enforced**: read `meta["cost_defaults"]["max_turns"]` and `max_tokens` in the adapter; abort + audit when exceeded. Flip the task to `rejected` in PLAN.md.
2. **HITL expiry**: add `hitl_queue.expires_at`; `reconcile()` auto-rejects expired open items and `reject`(s) the paused task (writes a denial to okf/log.md).
3. **Middleware OCC actually used**: implement the commented step in `PolicyMiddleware` so *any* write route gets OCC, not just the explicit append.
4. **Lock release only-after-acquire**: wrap acquire/release so release is a no-op when acquire raised.
5. **Fix the 5 ruff errors**, then add a pre-commit hook running `ruff check . && pytest -q && python tools/check_harness.py`.
6. **`.gitignore`** — un-ignore `tools/`, move `test_hooks/` into it, delete tracked `test_hooks/*.db`.
7. **Frontend gate**: add `lint` (eslint + prettier), `typecheck` (tsc), `test` (vitest) scripts; add ESLint+Prettier devDeps; wire `next.config.js` rewrite into `api.ts` so it's not dev-localhost-bound.
8. **CI**: a single GitHub Actions job running: `ruff check .`, `pytest context_server/tests/`, `tools/check_harness.py`, `npm run lint && npm run typecheck && npm test`.
9. **`pyproject.toml`**: pin ruff, pytest, pytest-asyncio (or anyio), add `[tool.ruff]` + `[tool.pytest.ini_options]`; pin `mcp` in requirements.txt.
10. **Telemetry**: emit `audit_log` rows as OTel spans (a single `OtelExporter` listening on `audit()` in `db.py`).

### 6.4 Make the Dream Cycle do real work

The meta agent is registered but unwired (PROG-1). Once `HttpAdapter` exists:
- meta = a service that ingests `analyze()` outputs + the last N audit trajectories + drift + CAPO and asks an LLM to *propose* harness/prompt edits.
- Human promotes in `Program.md`. That's the self-improvement loop the spec promises.
- Until then, `analyze()` is a useful deterministic triage but not "reflection."

### 6.5 Suggested build order (what to do next, in order)

1. **Fix ruff + repo hygiene** (test_hooks, tools gitignore, loose scripts) — unblocks the green-commit gate.
2. **Fix BUG-1 (CAPO keying)** + add an integration test for delegate→accept→capo with *different* task_id and row_id.
3. **Add frontend lint/typecheck/test npm scripts + ESLint config** — makes the Phase 9 contract honest.
4. **Implement `HttpAdapter` for real + build `agents/hermes`** — proves multi-agent works.
5. **`FilesystemAdapter` real subprocess for opencode** (so the orchestrator can spawn itself with limits).
6. **Add HITL expiry + per-task cost cap enforcement** — unattended safety.
7. **Promote IMPLEMENT rows P5–P9 to `accepted: true`** after 1–3 are green — closes Phase 5–9 honestly.
8. **CI pipeline**, then **OTel export**, then **sandbox driver** (`E2BRunner`) for cloud-safe agents.

---

## 7. Summary

* Phases 0–9 are **written** in the codebase and their tests pass — this is real progress.
* The honest status: **Phases 0–4 are ratified (accepted:true), Phases 5–9 are drafted (accepted:false)** — matching `IMPLEMENT.md`.
* The Definition-of-Done gate is currently **red** because `ruff check .` fails (5 trivial errors).
* The frontend DoD gate is **non-functional** (no lint / typecheck npm scripts, ESLint not installed) — this is the most-violated contract clause.
* The deepest functional gap is **adapters are echo-stubs**: the OS orchestrates, audits, meters, governs, and dreams — but it does not actually *run* any other agent yet. That is what "robust agentic OS" requires next, and §6.1 + §6.5 give the concrete path.
* Several latent bugs (CAPO keying, private-attr coupling, WS close handling, scheduler backoff) are listed in §4; none are severe, but fix BUG-1 before promoting Phase 7.

**Bottom line**: The skeleton is sound and remarkably complete for a Phase 0–9 scaffold. Close the ruff/hygiene gate first, then make adapters real — that single change converts this from a well-governed demo into an actual multi-agent Agentic OS.