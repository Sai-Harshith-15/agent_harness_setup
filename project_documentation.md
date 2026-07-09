# Agentic OS — Project Documentation & Re-Audit Report (v2)

> Repository: `D:\GitRepo\agent_harness_setup`
> Re-audit date: 2026-07-09 (after fixes applied per `project_gaps.md`)
> Scope: Entire codebase re-audited against `agent_os_project_architecture.md`, the 9 phase docs in
> `project phases/`, `AGENTS.md`, `PLAN.md`, `IMPLEMENT.md`, `project_gaps.md`, and the parent
> harness plan (`opencode_glm_implementation_plan.md`).
> Method: Direct file reads + live `pytest` / `ruff` / `check_harness.py` / `npm test` / `npm run
> lint` runs. Cross-checked `IMPLEMENT.md` "Deviations summary" claims against shipped code.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Changed Since v1 (fixes applied)](#2-what-changed-since-v1-fixes-applied)
3. [Critical Regression — Tests & Validator Now RED](#3-critical-regression--tests--validator-now-red)
4. [System Architecture (as designed)](#4-system-architecture-as-designed)
5. [Repository Layout (current)](#5-repository-layout-current)
6. [Phase-by-Phase Status (re-audited)](#6-phase-by-phase-status-re-audited)
7. [Gap Closure Scorecard — v1 → now](#7-gap-closure-scorecard--v1--now)
8. [Remaining Gaps](#8-remaining-gaps)
9. [Test, Lint & Harness Validator Status](#9-test-lint--harness-validator-status)
10. [What Else Needs to Be Added (re-prioritized)](#10-what-else-needs-to-be-added-re-prioritized)
11. [Final Readiness Verdict (v2)](#11-final-readiness-verdict-v2)

---

## 1. Executive Summary

The user applied the `project_gaps.md` remediation plan and **closed a meaningful slice of the v1
audit's gaps** — most of the cheap "spec-truth blockers" and several "robustness hardening" items
are now genuinely implemented in code. The backend moved from *partial* to *substantively better*:
`/mcp/log_decision` shipped, OCC switched to SHA-256 content hash, breaker/rate-limit became
SQLite-durable, a lock-DAG cycle detector was added, DLP widened to 5 patterns, the `forbid_native_
cross_agent` flag was fixed, OKF concepts got frontmatter, `check_harness.py` became a discipline
enforcer, the registry became an OKF bundle, the sandbox stub was removed (deviation recorded), and
real OpenTelemetry SDK wiring (TracerProvider + OTLP to Jaeger + Lamport counters + failure-class
tags) was added.

**However, the rerun introduced a CRITICAL regression**: the new OTel code imports
`opentelemetry.sdk.*` at module top-level in `main.py:11-16`, and the OTel packages were added to
`requirements.txt:12-15` but **NEVER actually installed** in either the system Python or
`context_server/.venv`. Result: **6 of 8 backend test modules ERROR during collection**
(`ModuleNotFoundError: No module named 'opentelemetry.sdk'`), `ruff` reports **12 violations**, and
`check_harness.py` — which now runs pytest as a gate — **FAILS** with "pytest suite failed". The
project was `48/48 green / ruff clean / check_harness exit 0` before this round; it is now **red
across the board** for the automated gates.

Per your instruction, **no packages were installed and no code was edited during this re-audit** —
the OTel regression, the ruff violations, and the broken validator are documented below as the
top-priority blockers to fix before the next commit.

The **Phase 9 frontend moved from ~25% to ~45%**: Tailwind configured, Zustand store with live
WebSocket to `/dashboard/events`, left-rail nav with framer-motion, auth middleware + `/login`,
Monaco editor imported, crash re-run button, ActivityStream with CSV export, Playwright package +
one e2e spec. But it introduced its own regression (`vitest.config.ts` doesn't exclude the Playwright
spec → `npm test` RED), and 6 of 10 DoD items remain missing/full-task-lifecycle, real tokens SQL
view + CSV, real monaco *diff*, PIN/signed-token auth, top-bar pill, shadcn/ui, TanStack Query
actually wired, Playwright config, Lighthouse.

| Layer | v1 verdict | v2 verdict | Net change |
|---|---|---|---|
| Backend (Phases 0–8) | Partial → leaning ready | **Partial, but automated gates RED** | Code improved; tests broken (regression) |
| Frontend (Phase 9) | NOT READY (~25%) | NOT READY (~45%) | +20 pts, but `npm test` now RED |
| Governance/Contracts/Registry/OKF | Partial | **Better** (4 new contracts, OKF bundle, frontmatter, enforcer) | Real improvement |
| Tests / Lint / Validator | GREEN (nominally) | **RED** (pytest 6 errors, ruff 12, check_harness FAIL) | **Regression** |

> **Honest headline:** The fixes are real and the code is closer to spec, but **the project is not
> usable as-is** because the OTel dependency wiring broke the entire automated gate. Fix the
> regression first (one pip install + a few ruff fixes + `vitest.config.ts` exclude), then the
> remaining behavioral gaps in §8.

---

## 2. What Changed Since v1 (fixes applied)

Verified by direct file reads + `git status`. ✅ = genuinely fixed; ⚠️ = partial; ❌ = attempted
but broke something; (unchanged) = gap remains from v1.

### P0 — Spec-truth blockers (from `project_gaps.md`)
- ✅ **`/mcp/log_decision` endpoint shipped** — `context_server/app/main.py:260-281`; same
  governed-write path as `append_implement` (permission → lock → OCC content-hash → DLP scrub →
  idempotent `vault_patch`).
- ✅ **`forbid_native_cross_agent: true` flag fixed** — `registry/agents/opencode.md:6` now carries
  the spec's key (in addition to `cross_agent_delegation`). `tools/check_harness.py:31-32` asserts it.
- ✅ **OKF concept frontmatter fixed** — all 3 `okf/concepts/*.md` now carry `id, title, tags,
  source` (verified `okf/concepts/capo.md:1-6`). `check_harness.py:37-45` enforces conformance.
- ✅ **Ledger corrected** — `IMPLEMENT.md:16` now reads "19/24 tests green" (numeric honesty);
  "Deviations summary" (`IMPLEMENT.md:165-169`) now lists 4 deviations (log_decision miss, flag
  miss, frontmatter miss, sandbox removal). The previously-empty table is populated.

### P1 — Robustness hardening
- ✅ **Durable breaker + rate-limit** — moved from in-memory to SQLite: `breaker_state` and
  `rate_limits` tables in `db.py:58-68`; `middlewares.py:29-84` reads/writes via
  `connect(CONTROL_DB)`. State now survives restart and works across workers.
- ✅ **OCC on content hash, not mtime** — `main.py:229,247,270` compute
  `hashlib.sha256(note_content).hexdigest()` as the version; `governance/locks.py:73` `check_occ`
  compares caller-supplied hash vs. live content hash. The "no silent overwrite" guarantee is now real.
- ✅ **DLP widened** — `middlewares.py:96-99` adds GitHub PAT (`ghp_…`), Slack token (`xox[baprs]-…`),
  private-key blocks, and a generic ≥40-char high-entropy pattern, on top of AWS keys + Bearer.
- ✅ **Sandbox stub removed** (documented deviation) — `context_server/app/sandbox/` deleted (git
  shows `D` for all 3 files); `IMPLEMENT.md:169` records "sandbox/ stub removed — Opted to not
  implement local containerization yet to reduce scope."
- ✅ **Lock DAG + cycle detection (P28)** — `governance/locks.py:24-44` walks the
  `_task_waiting_on` dependency chain before acquiring a lock; a cycle (owner == current task) raises
  `409 deadlock_risk: cycle detected in lock DAG`.

### P2 — Real observability
- ⚠️ **OTel SDK wiring added in code** — `main.py:11-16` imports `TracerProvider`,
  `BatchSpanProcessor`, `OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)`,
  `FastAPIInstrumentor.instrument_app(app)`; `db.py:104-118` emits real spans with `agent`,
  `task_id`, `ok`, `detail`, `lamport_seq` (via `_next_lamport()` `db.py:12-16`), and a `failure_class`
  attribute on error (`auth` vs `system` heuristic). `docker-compose.yml` adds a Jaeger
  all-in-one collector on :4317/:4318.
- ❌ **…but the deps are not installed** → **the OTel regression** — see §3.

### Highly-robust additions
- ✅ **4 new contracts** — `contracts/dlp.md`, `mcp_tools.md`, `observability.md`, `occ.md`
  (though each is only **3 lines** — present-but-thin).
- ✅ **`check_harness.py` is now a discipline enforcer** — `tools/check_harness.py` now asserts:
  (a) `forbid_native_cross_agent: true` on the orchestrator (`:31-32`), (b) OKF concept frontmatter
  keys (`:37-45`), (c) IMPLEMENT.md append-only vs `git show HEAD` (`:59-64`), (d) **test-green
  gate** running `pytest context_server/tests/` (`:67-70`).
- ✅ **Registry became an OKF bundle** — `registry/index.md` (9 lines), `registry/log.md`
  (3 lines), `registry/agents/index.md` (9 lines) added.
- ✅ **CI workflow** modified (`.github/workflows/ci.yml`).
- (unchanged) Secrets rotation + ephemeral injection (P11) — still not implemented.
- (unchanged) Per-sandbox ephemeral credential injection — n/a (sandbox removed).

### Frontend (Phase 9) — fixes applied
- ✅ **Tailwind configured** — `frontend/tailwind.config.ts`, `postcss.config.js`, `app/globals.css`.
- ✅ **Zustand store** — `frontend/lib/store.ts:22-46` opens WS to `/dashboard/events` +
  `/dashboard/tokens/ws`; `app/components/ActivityStream.tsx` is a real consumer.
- ✅ **Left-rail nav** — `app/nav.tsx:22-49` (`md:flex-col md:w-72`) with framer-motion active link.
- ✅ **Auth gate** — `frontend/middleware.ts:4-25` + `app/login/page.tsx` (cookie/Authorization check).
- ✅ **Monaco editor imported** — `app/hitl/page.tsx:3,38` (`@monaco-editor/react`).
- ✅ **Crash re-run button** — `app/crash/page.tsx:18-21,39` → `POST /dashboard/crashes/{taskId}/rerun`.
- ✅ **ActivityStream CSV export** — `app/components/ActivityStream.tsx:20-39` (note: lives on the
  home stream, NOT on `/tokens`).
- ⚠️ **Playwright package** — `@playwright/test` installed + `tests/e2e/dashboard.spec.ts` written,
  BUT no `playwright.config.ts` exists and `vitest.config.ts` doesn't exclude `tests/e2e/**` →
  `npm test` now runs the Playwright spec inside Vitest and **crashes** (regression).

---

## 3. Critical Regression — Tests & Validator Now RED

### The OTel dependency regression

`context_server/app/main.py:11-16`:
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
```

These are **top-level imports** — they fire at module import time (collection), so any test that
imports `app.main` fails before a single test runs.

`context_server/requirements.txt:12-15` declares:
```
opentelemetry-sdk==1.25.0
opentelemetry-api==1.25.0
opentelemetry-exporter-otlp==1.25.0
opentelemetry-instrumentation-fastapi==0.46b0
```
… **but none of these are installed** — verified in both the system Python (`Python313`) and the
project venv (`context_server/.venv/Scripts/python.exe` → `ModuleNotFoundError: No module named
'opentelemetry'` / `'opentelemetry.sdk'`).

### Live gate results (run this re-audit)

| Gate | Command | Result |
|---|---|---|
| Backend tests | `python -m pytest context_server/tests/ -q` | **6 ERRORS during collection** — `test_main.py`, `test_phase3.py`, `test_phase6.py`, `test_phase7.py`, `test_phase8.py`, `test_phase9.py` all fail to import `main`. 2 warnings, **0 tests run**. v1 was 48 passed. |
| Backend lint | `ruff check context_server` | **12 violations** (e.g. `I001` unsorted imports in `db.py`, `F841` unused `current_task` in `locks.py:27`, multiple `W293` trailing-whitespace in `locks.py` + `E501` line-length in `middlewares.py` SQL strings). v1 was clean. |
| Harness validator | `python tools/check_harness.py` | **HARNESS CHECK FAILED: FAIL pytest suite failed (all tests must be green)** exit 1. v1 was exit 0. |
| Frontend tests | `cd frontend && npm test` | **RED** — vitest tries to import the Playwright spec in `tests/e2e/dashboard.spec.ts` and crashes: *"Playwright Test did not expect test.describe() to be called here."* One vitest unit test still passes. |
| Frontend lint | `cd frontend && npm run lint` | GREEN, 1 warning (`react-hooks/exhaustive-deps` in `ActivityStream.tsx:16`). |

### Why this matters

`check_harness.py` was *upgraded* this round to enforce a `pytest`-green gate (`tools/check_harness.py:67-70`).
That improvement is correct, but it means the OTel regression now cascades: because pytest errors,
`check_harness.py` fails, which (per `AGENTS.md` Definition of Done) blocks every commit. The repo
was `green / clean / exit 0` before this round; it is now **red across all three backend gates**.

### Fix order (cheap, unblocks everything)
1. `context_server/.venv/Scripts/python.exe -m pip install -r context_server/requirements.txt`
   (installs the 4 OTel packages — **restricted action per `AGENTS.md`; needs your approval**).
2. `ruff check context_server --fix` then `ruff check context_server` (resolves the 5 auto-fixable
   violations; the other 7 (line-length, the unused `current_task`) need a quick manual edit).
3. Delete the unused `current_task` in `governance/locks.py:27`.
4. Add `exclude: ['tests/e2e/**']` to `frontend/vitest.config.ts` + add a `frontend/playwright.config.ts`.
5. Re-run gates: `pytest -q` (expect 48 green), `ruff .`, `check_harness.py` (expect exit 0),
   `npm test` (expect green).

After these gates are green again, the genuine quality gains from this round can be trusted.

---

## 4. System Architecture (as designed)

(Unchanged from v1 — `agent_os_project_architecture.md` was not modified in this round.)
Three layers: Orchestrator (opencode CLI, sole) → Context Server (FastAPI, :27180) → Mission
Control (Next.js, :3000). Locked ports: Obsidian MCP 27124/27123, Context Server 27180,
Mission Control 3000, Jaeger 4317/4318 (new this round via `docker-compose.yml`), Langfuse 3001
(optional). Locked decisions D1–D8 unchanged. See `agent_os_project_architecture.md` §2 for the
full diagram.

---

## 5. Repository Layout (current)

```
context_server/
  app/
    main.py              App entry + OTel TracerProvider/instrumentation (NEW) + /mcp/log_decision (NEW)
    db.py                SQLite stores + audit() now emits OTel spans + Lamport counters (NEW)
    identity.py          HMAC-SHA256 signed transport identity (unchanged, real)
    obsidian_backend.py  httpx proxy to obsidian-local-rest-api
    registry.py          Loads registry/agents/*.md YAML
    adapters.py          Echo/Filesystem/Http adapters
    delegation.py        delegate_task: orchestrator-only, budget, ledger
    middlewares.py       PolicyMiddleware (SQLite-durable breaker/rate-limit NEW) + DLPFilter (5 patterns NEW)
    indexing/            store, graphify, headroom, compactor, drift, watcher
    governance/
      locks.py           Leased locks + DAG cycle detection (NEW) + OCC content-hash check
      permissions.py     Allow-list matrix (default DENY)
      hitl.py            Queue + 7-day expiry
      hibernation.py     INSERT/DELETE JSON (UNCHANGED — full lifecycle still missing)
      reconcile.py       Reaps TTL locks + auto-expires HITL (no crash-vs-TTL distinguish)
    finops/              meter, rollups, standup (per-tool metering STILL not wired)
    meta/                dream_cycle, runner
    sandbox/             DELETED (deviation recorded)
  tests/                 conftest + test_main/adapters/phase3/5/6/7/8/9 — collection ERRORs (regression)
  requirements.txt       Now declares 4 opentelemetry-* packages (NEW) — NOT INSTALLED
contracts/
  obsidian_backend.md, orchestration.md, sandbox_driver.md  (original 3)
  dlp.md, mcp_tools.md, observability.md, occ.md            (NEW — 3 lines each, thin)
registry/
  agents/*.md (6, opencode.md now has forbid_native_cross_agent NEW), adapters/
  index.md (NEW), log.md (NEW), agents/index.md (NEW)
okf/
  SPEC.md, log.md, concepts/{capo,delegate-task,dream-cycle}.md  (concepts now have frontmatter NEW)
docker-compose.yml       Jaeger OTel collector (NEW)
tools/check_harness.py   Discipline enforcer (NEW assertions + test-green gate)
hooks/                   control_plane.db, token_usage.db (runtime, gitignored)
frontend/                Next.js — Tailwind (NEW), Zustand store (NEW), left rail (NEW),
                        auth middleware.ts+login/ (NEW), Monaco import (NEW), crash rerun (NEW),
                        ActivityStream+CSV (NEW), Playwright pkg (NEW, broken config)
project phases/          9 phase spec docs (unchanged)
project_gaps.md          The remediation plan the user executed (NEW this round)
```

---

## 6. Phase-by-Phase Status (re-audited)

Status legend: ✅ FULLY ⚠️ PARTIAL ❌ MISSING/BROKEN. "Δ" marks a change from v1.

### Phase 0 — Foundations & Contracts — ✅ (was ✅)
- ✅ 3 original contracts present
- ✅ `check_harness.py` now a real enforcer (NEW)
- ⚠️ Contract set still incomplete — only 7 contracts exist (`obsidian_backend`, `orchestration`,
  `sandbox_driver` + new `dlp`, `mcp_tools`, `observability`, `occ`). The 4 new ones are 3-line
  stubs. Still missing: `identity`, `secrets_bridge`, `read_chaperon`, `circuit_breaker`,
  `rate_limit`, `project_contract`, `obsidian_export_hook`, `delta_indexing`, `permission_matrix`,
  `hibernation`, `crash_recovery`, `lock_manager`.

### Phase 1 — Wire the Two Brains — ✅ (was ⚠️ → upgraded)
- ✅ Obsidian backend proxy (`obsidian_backend.py`), adapter contract present
- ✅ opencode registered as sole orchestrator
- ✅ **OKF concepts now carry frontmatter** (Δ) — `okf/concepts/capo.md:1-6` verified
- ✅ **Registry is now an OKF bundle** (Δ) — `index.md`, `log.md`, `agents/index.md` added
- ⚠️ `bindings` field still missing on every agent markdown (unchanged gap)

### Phase 2 — Context Server — ⚠️ (was ⚠️ → improved but RED)
- ✅ FastAPI, `/health` (degraded, not 5xx)
- ✅ HMAC-SHA256 identity (`identity.py:11-34`) — unchanged, real
- ✅ **DLP widened** (Δ) — 5 patterns
- ✅ **OCC content-hash** (Δ) — `main.py:229,247,270`
- ✅ **Breaker + rate-limit now SQLite-durable** (Δ)
- ✅ **Lock DAG cycle detection** (Δ) — `governance/locks.py:24-44`
- ⚠️ **OTel/Lamport/failure-class now in code** (Δ) — but **broken by uninstalled deps**
- ⚠️ Chaperon still only blocks untrusted writes → 403 (no macro-span/sampled-args, P31 partial)
- ❌ **`/mcp/log_decision` endpoint FIXED** (Δ) — `main.py:260-281`
- ⚠️ Secrets bridge — still just env passthrough (no ephemeral injection, P11 partial)
- ⚠️ Lamport counters exist in code (`db.py:9-16`) but untested (tests can't import)

### Phase 3 — Agent Registry, Adapters & delegate_task — ✅ (was ⚠️ → upgraded)
- ✅ 6 agents + registry loader; `find_capability`, `accept_implement` orchestrator-only
- ✅ Real `Filesystem`/`Http` adapters
- ✅ **`forbid_native_cross_agent: true` flag fixed** (Δ) — `registry/agents/opencode.md:6`,
  asserted by `check_harness.py:31-32`
- ⚠️ `bindings` field still missing (unchanged)

### Phase 4 — Per-Project Harness Contract — ✅ (was ⚠️ → upgraded)
- ✅ Harness triad present; validator now enforces
- ✅ `/dashboard/vault`, `/dashboard/plan` parse
- ✅ **`check_harness.py` upgraded** (Δ) — flag, frontmatter, append-only, test-green
- ⚠️ `project_contract.md`, `obsidian_export_hook.md` still missing (unchanged)

### Phase 5 — Indexing & Generation — ⚠️ (unchanged structurally; now RED)
- ✅ Indexing module real (delta-aware, tiktoken, LLM-augmented compactor, watcher)
- ⚠️ Drift still a timestamp heuristic (not code-graph divergence, no vector/P30)
- ❌ `scripts/generate_agent_configs.py` still missing
- ❌ `contracts/delta_indexing.md` still missing
- ❌ Tests for this phase do not run (regression) — collection ERROR

### Phase 6 — Verification, Permissions, HITL, Hibernation, Crash Reconciliation — ⚠️ (was ❌ → improved)
- ✅ Permission matrix default-DENY; governed write path real; HITL queue + expiry
- ✅ **Lock DAG cycle detection added** (Δ) — addresses P28
- ✅ **Crash re-run endpoint added** (Δ) — `/dashboard/crashes/{task_id}/rerun` (`main.py:323-326`)
  calls `thaw()`. Frontend has a re-run button.
- ⚠️ `reconcile.py:10-35` still reaps locks whose `lease_expires_at <= now` — does NOT distinguish
  crash from normal TTL expiry, does NOT sweep sandboxes (sandbox removed), does NOT close spans as
  `infrastructure_crash`, does NOT finalize `in_progress` PLAN rows, does NOT roll back. (P26 still partial.)
- ⚠️ `hibernation.py` still just INSERT/DELETE a JSON blob — no token revoke, no sandbox terminate,
  no lock release/re-acquire, no stale-on-thaw drift re-check. (P22 still partial.)
- ⚠️ HITL still only enqueued for the UI — not routed to the orchestrator (unchanged)
- ❌ `accept_implement` still does NOT append the accepted row to `IMPLEMENT.md` file (unchanged) —
  `main.py:289-295` only flips the ledger flag
- ❌ Lethal-trifecta / instruction-provenance combinatorial rule (P13) — not implemented
- ❌ `contracts/{permission_matrix,hibernation,crash_recovery}.md` still missing

### Phase 7 — Daily Ops & Cost Discipline (CAPO) — ⚠️ (unchanged core gap)
- ✅ `finops/meter.py`, `rollups.py`, `standup.py`; `/dashboard/tokens`, `/dashboard/capo`, websockets
- ❌ **Per-tool token metering STILL not wired** (unchanged from v1) — `finops/meter.record()` is
  defined (`meter.py:7-14`) and `mark_accepted` exists, but **`meter.record` is never called at any
  MCP call site** (`search_notes`, `read_note`, `append_implement`, `log_decision`, `reindex`,
  `compress`, `post_standup`, `run_dream_cycle`). Only `delegate_task` writes `token_ledger`. → CAPO
  still measures "tokens-per-accepted-delegation," not "every tool call."
- ❌ `hooks/task_outcomes.db` (arch Phase 7 separate denominator) still absent — fold-in still
  undocumented as a deviation in `IMPLEMENT.md` (the deviations table mentions other items but NOT
  this one)
- ❌ Week rollup to `registry/log.md` — `registry/log.md` now exists (3 lines) but is empty of rollups

### Phase 8 — Meta-Harness & Dream Cycle — ✅ for phase-doc DoD (unchanged)
- ✅ `meta/dream_cycle.py` analyze + render; `/dashboard/dream`, `/mcp/run_dream_cycle` (403 for non-meta)
- ✅ `registry/agents/meta.md` registered
- ⚠️ `Program.md` still empty stub (P7 audit-schedule gap)
- ⚠️ No recorded accepted Dream-Cycle proposal (unchanged)

### Phase 9 — Next.js Mission Control — NOT READY, ~45% (was ~25%)

Phase 9 DoD checklist (re-audited):

| # | DoD item | v1 | v2 | Evidence (file:line) |
|---|---|---|---|---|
| 1 | Every page renders real data | FULLY | FULLY | all pages real `fetch` to `127.0.0.1:27180` |
| 2 | Full task lifecycle in `/task/[id]` | MISSING | **MISSING** | `task/[id]/page.tsx:4-15` still only filters `recent_activity` into spans — no PLAN/breaker/HITL/freeze/thaw/gate/CAPO |
| 3 | `/tokens` SQL views + time-range + CSV | MISSING | **MISSING** | `tokens/page.tsx:4-29` — no selector, no time-range, no CSV (CSV lives on `ActivityStream.tsx:20-39`, home page) |
| 4 | `/hitl` monaco DIFF modal approve/modify/reject | MISSING | **PARTIAL** | `hitl/page.tsx:3,38` imports `@monaco-editor/react` but renders a **readOnly single editor**, not a diff; `Modify` sends `status:"modified"` with no edit affordance (`:13-19`) |
| 5 | `/crash` one-click re-run from snapshot id | MISSING | **PARTIAL** | `crash/page.tsx:18-21,39` re-run button → `/dashboard/crashes/{taskId}/rerun`; keys off `task_id`, not a snapshot id |
| 6 | Playwright green; Lighthouse a11y ≥ 95 | MISSING | **MISSING** | `@playwright/test` installed + `tests/e2e/dashboard.spec.ts` written, but **no `playwright.config.ts`**; vitest mis-runs the spec → `npm test` RED. No Lighthouse config. |
| 7 | WebSocket `/dashboard/events` + 5s poll fallback | MISSING | **PARTIAL** | `lib/store.ts:22-46` opens WS to `/dashboard/events` + `/dashboard/tokens/ws`; ActivityStream consumes. **No 5s poll fallback anywhere;** no reconnect logic |
| 8 | Auth: local PIN + signed (ui, human) tokens | MISSING | **PARTIAL** | `middleware.ts:4-25` + `/login` — but literal-string compare `=== "admin-token-123"`; **no PIN, no HMAC signing, no ui/human split** |
| 9 | Left rail nav + top-bar global pill | MISSING | **PARTIAL** | `nav.tsx:22-49` left rail ✓; **no top bar**, status pill only on `/` (`page.tsx:37-52`) |
| 10 | Deps installed & USED | — | **PARTIAL** | Tailwind ✓, Zustand ✓, Monaco ✓ (installed), Playwright ✓ (installed, uninconfig'd), framer-motion ✓, lucide-react ✓. **`@tanstack/react-query` installed but NO `QueryClientProvider` anywhere → dead.** **`@shadcn/ui` NOT installed at all** (not in package.json, not in node_modules). `clsx`/`tailwind-merge` installed but unused. |

Frontend gates: `npm run lint` GREEN (1 warning); `npm test` **RED** (vitest–Playwright collision,
see §3 fix #4); no Lighthouse.

---

## 7. Gap Closure Scorecard — v1 → now

From `project_gaps.md` priority tiers, now with re-audit verdicts.

### P0 — Spec-truth blockers
| Gap | v1 | Now | Status |
|---|---|---|---|
| Ship `/mcp/log_decision` | MISSING | FULLY | ✅ CLOSED (`main.py:260-281`) |
| `forbid_native_cross_agent` flag | wrong key | correct + asserted | ✅ CLOSED (`opencode.md:6`, `check_harness.py:31`) |
| OKF concept frontmatter | MISSING | present | ✅ CLOSED (`okf/concepts/*.md:1-6`) |
| Correct the ledger (P5-1 "24/24" + deviations table) | OPTIMISTIC | honest | ✅ CLOSED (`IMPLEMENT.md:16,165-169`) |

### P1 — Robustness hardening
| Gap | v1 | Now | Status |
|---|---|---|---|
| Durable breaker + rate-limit | in-memory | SQLite-backed | ✅ CLOSED (`db.py:58-68`, `middlewares.py:29-84`) |
| OCC on content hash | mtime | SHA-256 | ✅ CLOSED (`main.py:229,247,270`) |
| Widen DLP | 2 patterns | 5 patterns | ✅ CLOSED (`middlewares.py:96-99`) |
| Wire/delete sandbox | dead code | deleted + deviation recorded | ✅ CLOSED (deviation accepted) |
| Lock DAG + cycle detection (P28) | single-row lease | cycle walk added | ✅ CLOSED (`locks.py:24-44`) |
| Secrets rotation + ephemeral injection (P11) | partial | unchanged | ❌ STILL OPEN |

### P2 — Real observability
| Gap | v1 | Now | Status |
|---|---|---|---|
| OTel collector + real spans + Lamport + failure-class tags | FAKED (audit_log rows) | **WIRED IN CODE** but **deps not installed → tests/validator RED** | ⚠️ ATTEMPTED — unblocks as §3 fix #1/#2 |

### P3 — Frontend (was 25%)
| Gap | v1 | Now | Status |
|---|---|---|---|
| WebSocket consumer for `/dashboard/events` | MISSING | Zustand store + ActivityStream | ✅ CLOSED (`lib/store.ts`, `ActivityStream.tsx`) |
| Monaco diff modal | `<pre>` JSON | Monaco imported, but **readOnly single editor not a diff** | ⚠️ PARTIAL |
| CSV export | MISSING | on ActivityStream (home), **not on `/tokens`** | ⚠️ PARTIAL |
| Crash re-run button | MISSING | present (keys off task_id, not snapshot id) | ⚠️ PARTIAL |
| Playwright | NONE | pkg + 1 spec, **no config → `npm test` RED** | ⚠️ PARTIAL/BROKEN |
| Auth (PIN + signed ui+human tokens) | NONE | hardcoded literal-token cookie gate | ⚠️ PARTIAL |
| Left rail + top-bar pill | horizontal nav | left rail ✓; no top bar pill | ⚠️ PARTIAL |
| Tailwind/Zustand/shadcn/TanStack(used)/Monaco/Playwright | missing | Tailwind✓ Zustand✓ Monaco✓ Playwright✓ (unconfigured) **shadcn✗ TanStack unused✗** | ⚠️ PARTIAL |
| Full task lifecycle in `/task/[id]` | MISSING | **still spans only** | ❌ STILL OPEN |
| `/tokens` time-range + SQL-view + CSV | MISSING | **unchanged** | ❌ STILL OPEN |
| 5s poll fallback on WS | NONE | **none** | ❌ STILL OPEN |

### "Highly-robust" additions
| Gap | v1 | Now | Status |
|---|---|---|---|
| Contract completeness (~80% missing) | 3 contracts | 7 contracts (4 new, 3-line stubs) | ⚠️ PARTIAL (12 still missing) |
| `check_harness.py` discipline enforcer | presence check | flag+frontmatter+append-only+test-green | ✅ CLOSED |
| Registry as OKF bundle | MISSING | `index.md`/`log.md`/`agents/index.md` added | ✅ CLOSED |
| CI | NONE | `.github/workflows/ci.yml` modified | ⚠️ EXISTS (content not deeply audited; will be RED until §3 fixed) |
| Secrets rotation + ephemeral injection | partial | unchanged | ❌ STILL OPEN |

### Gaps NOT from the plan that remain from v1
| Gap | Status |
|---|---|
| Per-tool token metering wired into every MCP call site (Phase 7 DoD) | ❌ UNCHANGED — `meter.record` never called; CAPO is delegation-only |
| `accept_implement` appends the row to `IMPLEMENT.md` file | ❌ UNCHANGED — only flips ledger flag |
| HITL routed to the orchestrator (not just the UI queue) | ❌ UNCHANGED |
| Full hibernation lifecycle P22 (token revoke / sandbox terminate / lock release-reacquire / drift recheck) | ❌ UNCHANGED — still INSERT/DELETE JSON |
| Real crash reconciliation P26 (crash-vs-TTL distinguish / span `infrastructure_crash` / task finalize / rollback) | ⚠️ PARTIAL — added HITL auto-expire + thaw + re-run endpoint, but not the distinguishing/finalize/rollback |
| Lethal-trifecta / instruction-provenance (P13) | ❌ UNCHANGED |
| Real drift (code-graph divergence + vector + `semantic_drift_detected` + Dream re-norm, P30) | ❌ UNCHANGED |
| `scripts/generate_agent_configs.py` | ❌ UNCHANGED |
| `Program.md` audit schedule (P7) | ❌ UNCHANGED (empty stub) |
| `bindings` field on every agent | ❌ UNCHANGED |

---

## 8. Remaining Gaps

Consolidated, de-duplicated list of gaps still open after this round.

### Blocker tier (must fix before any commit)
1. **OTel deps not installed** → `pytest` 6 collection errors, `ruff` 12 violations,
   `check_harness.py` FAIL. (§3 fix #1, #2, #3)
2. **`frontend/vitest.config.ts` missing `exclude: ['tests/e2e/**']`** + no
   `frontend/playwright.config.ts` → `npm test` RED. (§3 fix #4)

### Backend behavioral (still open from v1)
3. **Per-tool token metering not wired** — `finops/meter.record` not called at MCP call sites;
   CAPO is delegation-only.
4. **`accept_implement` doesn't write the IMPLEMENT.md file row** — only flips ledger flag.
5. **HITL not routed to orchestrator** — only the UI queue.
6. **Full hibernation lifecycle (P22)** — token revoke / sandbox terminate / lock release-reacquire
   / drift recheck on thaw. Currently INSERT/DELETE JSON.
7. **Real crash reconciliation (P26)** — distinguish crash from TTL expiry, close spans as
   `infrastructure_crash`, finalize `in_progress` PLAN rows, roll back. Re-run endpoint added; the
   rest is open.
8. **Lethal-trifecta / instruction-provenance permission rule (P13).**
9. **Real drift detection (P30)** — code-graph divergence + vector store +
   `semantic_drift_detected` + Dream-Cycle re-normalization.
10. **Secrets rotation + ephemeral sandbox-credential injection (P11)** — sandbox removed, but the
    rotation alerts / ephemeral injection still don't exist.
11. **`scripts/generate_agent_configs.py`** still missing (Phase 5 generator).
12. **`Program.md`** still empty stub; quarter audit not scheduled (P7).
13. **`bindings` field** still missing on every agent markdown (parent Phase 3 DoD).

### Frontend (Phase 9) — still missing
14. **`/task/[id]` full task lifecycle view** — PLAN row → spans → breaker → HITL → freeze → thaw →
    gate → CAPO (still spans only).
15. **`/tokens`** — SQL views layout, time-range selector, **CSV export on this page**.
16. **`/hitl` real Monaco *diff* (original ↔ modified)** with editable right pane; Modify must let
    the user edit content and re-run OCC.
17. **`/crash` re-run keyed on snapshot id**, not just task_id.
18. **`npm test` Playwright suite green** — add `playwright.config.ts`, fix vitest exclusion.
19. **Lighthouse a11y ≥ 95** — no config.
20. **5s poll fallback** on the WebSocket store (with reconnect).
21. **Real auth** — local PIN + HMAC-signed `(ui, human)` tokens, not a hardcoded literal cookie.
22. **Top-bar global status pill** (currently only on `/`).
23. **`@shadcn/ui` not installed** — install or drop from the spec; **`@tanstack/react-query`
    installed but never instantiated** — add `QueryClientProvider` in `layout.tsx` or remove it.
24. **`next.config.js` has no `/api` rewrite** but `lib/api.ts:1` (client branch) calls `/api/...`
    — client-side `api()` calls will 404 (verify and fix the rewrite or the base URL).
25. **Pages still use silent `.catch(() => fakeDefault)`** fallbacks that mask real backend failures
    (unchanged from v1).

### Contracts / governance
26. **12 contracts still missing** — `identity`, `secrets_bridge`, `read_chaperon`, `circuit_breaker`,
    `rate_limit`, `project_contract`, `obsidian_export_hook`, `delta_indexing`, `permission_matrix`,
    `hibernation`, `crash_recovery`, `lock_manager`. The 4 new contracts are 3-line stubs — should be
    fleshed out to be enforceable.
27. **`IMPLEMENT.md` "Deviations summary" still missing the `task_outcomes.db` fold-in** deviation
    (CAPO denominator lives in `token_ledger.accepted`, not a separate file per arch Phase 7 DoD).

---

## 9. Test, Lint & Harness Validator Status

| Gate | Command | v1 result | v2 result | Δ |
|---|---|---|---|---|
| Backend tests | `python -m pytest context_server/tests/ -q` | 48 passed | **6 collection ERRORS, 0 tests run** | 🔴 regression |
| Backend lint | `ruff check context_server` | clean | **12 violations** (`I001` db.py imports, `F841` `current_task` @ `locks.py:27`, multiple `W293`, `E501` in SQL strings) | 🔴 regression |
| Harness validator | `python tools/check_harness.py` | exit 0 | **exit 1 — FAIL pytest suite failed** | 🔴 regression |
| Frontend tests | `cd frontend && npm test` | 1 passed | **RED** (vitest runs Playwright spec, crashes) — 1 unit test still passes | 🔴 regression |
| Frontend lint | `cd frontend && npm run lint` | clean | GREEN, 1 warning (`ActivityStream.tsx:16` exhaustive-deps) | ✅ |
| Playwright | none | n/a | `@playwright/test` installed, 1 spec, **no config** — not runnable | ⚠️ partial |

**Note on the v1 test count:** `IMPLEMENT.md:16` was corrected this round to "19/24 tests green"
(reflecting the actual 19 functions in `test_phase5.py`), but the *total* backend suite was 48
passing before this round — that number is the relevant baseline for the regression.

---

## 10. What Else Needs to Be Added (re-prioritized)

### Tier 0 — Unblock the gates (do first, ~10 minutes)
1. `pip install -r context_server/requirements.txt` in the venv (installs the 4 OTel packages)
   — **restricted per `AGENTS.md`; needs your approval**.
2. `ruff check context_server --fix` + delete `current_task` in `governance/locks.py:27` + reflow
   the SQL strings in `middlewares.py` that exceed line length.
3. Add `exclude: ['tests/e2e/**']` to `frontend/vitest.config.ts`; add
   `frontend/playwright.config.ts` (e.g. `testDir: './tests/e2e'`).
4. Re-run: `pytest -q` (expect 48 green), `ruff .`, `check_harness.py` (expect exit 0),
   `npm test` (expect green). **Do not commit until all four are green** — `AGENTS.md` Definition of
   Done forbids it.

### Tier 1 — Close the remaining v1 backend gaps
5. Wire `finops/meter.record()` into every MCP tool call site (search_notes, read_note,
   append_implement, log_decision, reindex, compress, post_standup, run_dream_cycle).
6. Make `accept_implement` append the accepted row to `IMPLEMENT.md` (Phase 6.3).
7. Route HITL `request_clarification` to the orchestrator in addition to the UI queue.
8. Implement the full hibernation lifecycle (P22): token revoke + sandbox terminate + lock release
   on freeze; lock re-acquire + stale-on-thaw drift recheck on thaw.
9. Real crash reconciliation (P26): distinguish crash from TTL, close spans as
   `infrastructure_crash`, finalize `in_progress` PLAN rows, roll back to snapshot, wire the re-run
   endpoint to use the snapshot id.
10. Lethal-trifecta / instruction-provenance permission rule (P13).
11. Real drift detection + vector store + `semantic_drift_detected` + Dream re-norm (P30).
12. `scripts/generate_agent_configs.py` generator (Phase 5).
13. Fill `Program.md` with the optimization metric + quarterly audit schedule (P7); record one
    accepted Dream-Cycle proposal.
14. Add `bindings` to every agent markdown.
15. Document the `task_outcomes.db` fold-in as a deviation in `IMPLEMENT.md`, or create the separate
    `hooks/task_outcomes.db` per arch Phase 7.

### Tier 2 — Finish Phase 9 (current ~45% → target 100%)
16. Install `@shadcn/ui` (or formally drop it from the spec) and either wire
    `QueryClientProvider` for `@tanstack/react-query` or remove the dead dependency.
17. `/task/[id]` — render the full lifecycle (PLAN row, nested spans, breaker trip, HITL, freeze,
    thaw, gate, CAPO) as one replayable trajectory pointed at the now-real OTel spans (after Tier 0).
18. `/tokens` — SQL-view layout + time-range selector + CSV export on this page.
19. `/hitl` — real Monaco *diff* (original ↔ modified); Modify editable + OCC re-run on submit.
20. `/crash` — re-run keyed on snapshot id.
21. WebSocket store — add 5s poll fallback + reconnect.
22. Auth — replace the hardcoded `admin-token-123` literal with a real PIN + HMAC-signed
    `(ui, human)` tokens (depends on a backend signing endpoint).
23. Top-bar global status pill across all pages.
24. `next.config.js` — add the `/api` rewrite that `lib/api.ts:1` assumes (or fix `api.ts`).
25. Pages — stop using silent `.catch(() => fakeDefault)`; surface real failures.
26. Lighthouse a11y ≥ 95 config + assertion.

### Tier 3 — Governance / contracts
27. Author the 12 missing contracts (§8 #26), or formally mark them out-of-scope deviations.
28. Flesh out the 4 new 3-line contracts to be enforceable.
29. Strengthen `check_harness.py` further: assert `bindings` presence, append-only monotonicity
    beyond `len(lines)` (e.g. hash chain), and a `ruff .` gate alongside the pytest gate.
30. CI — `.github/workflows/ci.yml` exists; ensure it runs `pytest + ruff + check_harness.py + npm
    test + npm run lint` and fails the build on red (it must be RED right now until Tier 0 lands).

---

## 11. Final Readiness Verdict (v2)

| Question | v1 answer | v2 answer |
|---|---|---|
| Does the project boot and demonstrate the architecture? | Yes | **Unverified** — the OTel import at module top-level means `uvicorn context_server.app.main:app` will fail to start until the deps are installed. The app **does not currently boot** against a clean Python. |
| Are all 10 phase rows marked done? | Yes | Yes (ledger unchanged this round for phase status; only "Deviations summary" + the P5-1 numeric were corrected) |
| Do the shipped changes meet each phase doc's DoD? | Mixed | Phase 0 ✅, Phase 1 ✅ (upgraded), Phase 2 ⚠️ (improved but OTel-broken), Phase 3 ✅ (upgraded), Phase 4 ✅ (upgraded), Phase 5 ⚠️ (unchanged + RED), Phase 6 ⚠️ (improved but P22/P26 still partial), Phase 7 ⚠️ (metering still unwired), Phase 8 ✅, Phase 9 ❌ (now ~45%, gate broken) |
| Are tests / lint / validator green? | Yes (nominally) | **NO — regression across all three backend gates + frontend `npm test` RED** |
| Is it ready to use as the spec defines? | No, not yet | **No — and currently less usable than v1 because the gates are red.** |

### Summary verdict (v2)

- **Backend code is meaningfully better than v1**: log_decision, content-hash OCC, durable
  breaker/rate-limit, lock-DAG cycle detection, widened DLP, real (in-code) OTel/Lamport/failure-class,
  a crash re-run endpoint, a strengthened `check_harness.py`, OKF bundle structure, OKF frontmatter,
  the corrected flag and ledger. Most P0 + P1 items from `project_gaps.md` are genuinely closed.

- **BUT the repo is currently RED and unbootable** because the OTel packages were added to
  `requirements.txt` but never installed, breaking `pytest`, `ruff` (cascading), `check_harness.py`,
  and the app's own `uvicorn` start. The frontend `npm test` is also RED due to a missing
  Playwright config + a vitest exclusion. These are **cheap blocker fixes** (Tier 0 above) — none
  require reverting the good work.

- **Phase 9 frontend moved ~20 percentage points (25% → ~45%)** — real Tailwind, real Zustand+WS,
  left rail, auth skeleton, Monaco import, CSV export, crash re-run, Playwright package. Still missing
  the heavy items: full task lifecycle, real monaco **diff**, `/tokens` SQL+CSV+time-range, PIN/signed
  auth, top-bar pill, shadcn, configured Playwright, Lighthouse, poll fallback.

- **Several v1 behavioral gaps were NOT touched** by the `project_gaps.md` round and remain open:
  per-tool metering (the heart of accurate CAPO), `accept_implement` writing the IMPLEMENT.md file,
  HITL→orchestrator routing, full P22 hibernation lifecycle, full P26 crash reconciliation (re-run
  endpoint excepted), P13 lethal-trifecta, P30 real drift, the Phase 5 generator, `Program.md`, and
  `bindings`.

### Honest headline (v2)

> The fixes are real and the code is closer to spec on every dimension the `project_gaps.md` plan
> targeted. But the round shipped a **dependency-install regression** that made the project **less
> verifiable than before**: pytest errors, ruff violations, `check_harness.py` fails, and `uvicorn`
> won't start without the OTel packages. **Run Tier 0 (~10 min) to restore green gates**, then the
> genuinely improved codebase can be trusted and the remaining Tier 1/2/3 gaps (§8) can be closed
> next. Do **not** commit until Tier 0 is green — `AGENTS.md` Definition of Done requires it.