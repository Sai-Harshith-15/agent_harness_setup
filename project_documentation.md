# Agentic OS — Project Documentation & Audit Report (v3)

> Repository: `D:\GitRepo\agent_harness_setup`
> Audit date: 2026-07-10 (re-audit after Tier 0 + Tier 1 remediation from `project_gaps.md`)
> Scope: Entire codebase audited against `agent_os_project_architecture.md`, the 9 phase docs
> in `project phases/`, `AGENTS.md`, `PLAN.md`, `IMPLEMENT.md`, `project_gaps.md`, and the
> parent harness plan (`opencode_glm_implementation_plan.md`).
> Method: Direct file reads + live `pytest` / `ruff` / `check_harness.py` / `npm test` /
> `npm run lint` runs. Cross-checked every `project_gaps.md` item against shipped code.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Changed Since v2 (fixes applied this round)](#2-what-changed-since-v2-fixes-applied-this-round)
3. [Gate Status (live results)](#3-gate-status-live-results)
4. [System Architecture](#4-system-architecture)
5. [Repository Layout (current)](#5-repository-layout-current)
6. [Complete Feature Inventory — What the Code Actually Does](#6-complete-feature-inventory--what-the-code-actually-does)
7. [Phase-by-Phase Status (re-audited v3)](#7-phase-by-phase-status-re-audited-v3)
8. [Gap Closure Scorecard — v2 → v3](#8-gap-closure-scorecard--v2--v3)
9. [Remaining Gaps](#9-remaining-gaps)
10. [Final Readiness Verdict (v3)](#10-final-readiness-verdict-v3)

---

## 1. Executive Summary

Between v2 and v3, the user executed the **Tier 0 and Tier 1 remediation** from the v2 audit.
The result is a **dramatic improvement**: the v2 critical OTel dependency regression is fixed
(packages installed → pytest 48 green, app boots), the frontend `npm test` regression is fixed
(vitest excludes e2e + `playwright.config.ts` added), and **10 of the 13 v1/v2 backend behavioral
gaps are now genuinely closed in code** — including the three hardest ones: per-tool token
metering wired into every MCP call site, `accept_implement` physically appending the row to
`IMPLEMENT.md`, and the full P22 hibernation lifecycle (lock release on freeze, lock re-acquire
+ drift recheck on thaw).

**One gate remains RED**: `ruff check context_server` reports **23 violations** (16 whitespace,
3 import-sort, 2 trailing-whitespace, 1 multi-import, 1 ambiguous-variable-name). 22 of 23 are
auto-fixable with `ruff check --fix`; the E741 needs a one-character rename. This is a **cheap,
~2-minute fix** and the only thing blocking a fully-green gate set.

The **frontend moved from ~45% to ~50%**: the `next.config.js` `/api` rewrite was added (closing
the client-side 404 risk), but the heavy Phase 9 items remain: full task lifecycle view, Monaco
*diff*, `/tokens` SQL+CSV+time-range, PIN/signed-token auth, top-bar pill, shadcn, TanStack
Query wiring, 5s poll fallback, Lighthouse, and removing silent `.catch()` fallbacks.

| Layer | v2 verdict | v3 verdict | Net change |
|---|---|---|---|
| Backend (Phases 0–8) | Partial, gates RED (regression) | **Substantially complete, gates GREEN except ruff** | Major improvement — 10 behavioral gaps closed |
| Frontend (Phase 9) | NOT READY (~45%) | NOT READY (~50%) | +5 pts (api rewrite); heavy items still open |
| Governance/Contracts/Registry/OKF | Better | **Better + more** (bindings on all agents, Program.md filled, generator script) | Real improvement |
| Tests / Lint / Validator | RED (regression) | **GREEN except ruff** (pytest 48✅, check_harness✅, npm test✅, npm lint✅) | Regression fixed |

> **Honest headline:** The backend is now **the strongest it has ever been** — per-tool CAPO
> metering, real hibernation lifecycle, real crash reconciliation with PLAN finalization,
> lethal-trifecta enforcement, semantic drift detection, and the IMPLEMENT.md file-write are all
> genuinely shipped. The **only blocker is 23 ruff violations** (22 auto-fixable). Fix ruff,
> then the remaining work is frontend Phase 9 + contract authoring + secrets rotation.

---

## 2. What Changed Since v2 (fixes applied this round)

Verified by direct file reads + `git diff --stat HEAD`. ✅ = genuinely fixed; ⚠️ = partial;
(unchanged) = gap remains from v2.

### Tier 0 — Unblock the gates (v2 §10 Tier 0)
- ✅ **OTel deps installed** — `opentelemetry-sdk/api/exporter-otlp/instrumentation-fastapi`
  now installed in system Python. `pytest` 48 passed, app boots. v2's critical regression FIXED.
- ✅ **`vitest.config.ts` excludes e2e** — `frontend/vitest.config.ts:8` adds
  `exclude: [..., 'tests/e2e/**']`. `npm test` GREEN.
- ✅ **`playwright.config.ts` added** — `frontend/playwright.config.ts` with `testDir: './tests/e2e'`.
- ✅ **`next.config.js` `/api` rewrite added** — `frontend/next.config.js` proxies `/api/:path*`
  → `http://127.0.0.1:27180/:path*`. Client-side `api()` calls (`lib/api.ts:1` BASE=`/api`) now
  resolve correctly. v2 gap #24 CLOSED.
- ❌ **ruff NOT fixed** — 23 violations remain (was 12 in v2; new code added whitespace issues).
  22 auto-fixable. **This is the sole RED gate.**

### Tier 1 — Close the remaining v1/v2 backend gaps
- ✅ **Per-tool token metering NOW WIRED** (v2 §8 #3 — was the #1 open behavioral gap) —
  `meter_record()` is called at **every** MCP tool call site: `search_notes` (main.py:217),
  `read_note` (:231), `append_implement` (:253), `log_decision` (:277), `post_standup` (:391),
  `reindex` (:413), `compress` (:422), `run_dream_cycle` (:479). CAPO now measures every tool
  call, not just delegations. **MAJOR gap CLOSED.**
- ✅ **`accept_implement` now writes the IMPLEMENT.md file row** (v2 §8 #4) — `main.py:297-327`
  physically appends `| {phase} | {row_id} | {title} | {agent} | true | {date} |` to the file,
  looking up the title/agent from `PLAN.md`. **Gap CLOSED.**
- ✅ **HITL routed to orchestrator** (v2 §8 #5) — `main.py:339-350` creates a background
  `asyncio.create_task` that calls `adapter_for(orch_meta).run(...)` with the clarification
  question, in addition to the UI queue. **Gap CLOSED.**
- ✅ **Full hibernation lifecycle P22** (v2 §8 #6) — `hibernation.py:13-17` releases locks on
  freeze (stores them in `frozen_state["_locks"]`); `thaw()` :40-42 re-acquires locks via
  `acquire_lock`; `thaw()` :44-48 does stale-on-thaw drift recheck via `detect_drift()` and
  stores result in `frozen_state["_drift"]`. **MAJOR gap CLOSED.**
- ✅ **Real crash reconciliation P26** (v2 §8 #7) — `reconcile.py` now:
  (a) distinguishes crash from TTL: `startup=True` → `crashes` list + audit
  `released:infrastructure_crash` (line 39, `ok=False`); on-demand → `reaped` + audit
  `released:ttl_expiry` (line 37, `ok=True`). **Distinction is now real.**
  (b) finalizes `in_progress`/`delegated` PLAN rows → `[crash]` on startup (:50-54).
  (c) auto-expires open HITL items past `expires_at` + thaws their tasks (:25-31).
  Still missing: closing OTel spans as `infrastructure_crash`, rollback to snapshot. **Gap
  substantially CLOSED (2 of 4 sub-items remain).**
- ✅ **Lethal-trifecta / instruction-provenance P13** (v2 §8 #8) — `permissions.py:30-36`
  queries `audit_log` for the task's tool set; if both `read_private` and `read_untrusted`
  appear, returns `Decision(False, "lethal-trifecta: ...")`. **Gap CLOSED.**
- ⚠️ **Real drift detection P30** (v2 §8 #9) — `drift.py` now has:
  (a) code-graph temporal divergence: flags contracts with ≥3 newer code files (:28-37);
  (b) `semantic_drift_detected()` via Jaccard token-overlap similarity (:11-19, threshold <0.1);
  (c) `semantic_drift_detected` banner kind + `trigger_dream_renorm` action (:39-52).
  **Partial** — uses token overlap, not a real vector store/embeddings. Shape and banners are
  correct; the similarity engine is a placeholder for real embeddings. **Gap PARTIALLY CLOSED.**
- ✅ **`scripts/generate_agent_configs.py`** (v2 §8 #11) — NEW file, loads `registry/agents/*.md`
  via `load_agents()` and dumps YAML to `agent_configs.yaml`. **Gap CLOSED.**
- ✅ **`Program.md` filled** (v2 §8 #12) — now has Metrics (active orphans, avg token spend),
  Audit Schedule (daily HITL review, weekly crash snapshot), Now items, and a Dream-Cycle
  proposal section. **P7 gap CLOSED.**
- ✅ **`bindings` field on all agents** (v2 §8 #13) — `bindings: []` now present on all 6 agent
  markdown files (opencode, hermes, claude-code, codex, antigravity, meta). **Gap CLOSED.**
- (unchanged) **Secrets rotation + ephemeral injection P11** — still not implemented.

### Other changes
- ✅ **`requirements.txt`** — OTel pinned to `>=1.25.0` (was `==1.25.0`); added
  `pytest-asyncio>=0.21.1`.
- ✅ **`db.py`** — audit() OTel span emission unchanged from v2 (now actually works since deps
  installed).
- ✅ **`meter.py`** — `record()` signature unchanged; now *called* everywhere.
- ✅ **`locks.py`** — unused `current_task` variable from v2 appears cleaned up in the cycle
  walk (now uses `current_resource`).
- ✅ **Registry** — `registry/agents/index.md` updated; all agents carry `bindings: []`.

---

## 3. Gate Status (live results)

| Gate | Command | v2 result | v3 result | Δ |
|---|---|---|---|---|
| Backend tests | `python -m pytest context_server/tests/ -q` | 6 ERRORS, 0 run | **48 passed** (2 warnings) | ✅ FIXED |
| Backend lint | `ruff check context_server` | 12 violations | **23 violations** (16 W293, 3 I001, 2 W291, 1 E401, 1 E741) | 🔴 still RED (22 auto-fixable) |
| Harness validator | `python tools/check_harness.py` | exit 1 (pytest fail) | **exit 0 — OK harness check passed** | ✅ FIXED |
| Frontend tests | `cd frontend && npm test` | RED (vitest–Playwright collision) | **1 passed** (vitest green; e2e excluded) | ✅ FIXED |
| Frontend lint | `cd frontend && npm run lint` | GREEN, 1 warning | **GREEN, 1 warning** (`ActivityStream.tsx:16` exhaustive-deps) | ✅ same |
| Playwright | no config | not runnable | **`playwright.config.ts` added**; spec exists; not run in `npm test` | ⚠️ config'd, not verified green |
| CI workflow | RED | `.github/workflows/ci.yml` runs pytest+ruff+check_harness+npm test+npm lint+typecheck+Playwright | ⚠️ will be RED until ruff fixed |

### ruff violation breakdown (23 total)
| Code | Count | Fixable | Location |
|---|---|---|---|
| W293 | 16 | ✅ `--fix` | blank-line-with-whitespace in hibernation.py, permissions.py, reconcile.py, main.py |
| I001 | 3 | ✅ `--fix` | unsorted imports in main.py:340, reconcile.py:44 |
| W291 | 2 | ✅ `--fix` | trailing whitespace |
| E401 | 1 | ✅ `--fix` | `import os, re` on one line in reconcile.py:44 |
| E741 | 1 | ❌ manual | ambiguous variable `l` in main.py:320 list comprehension |

**Fix command:** `ruff check context_server --fix` (resolves 22), then rename `l` → `line_` at
`main.py:320`.

### Note on OTel trace export
When Jaeger is not running (no `docker-compose up`), the OTel `BatchSpanProcessor` logs
`Failed to export traces to localhost:4317` after tests complete. This does **not** fail pytest
(exit 0) but adds ~5s of retry delay and noise. For CI, either start Jaeger or configure a
no-op exporter in test mode. This is a **robustness nit**, not a gate failure.

---

## 4. System Architecture

Three layers, unchanged in topology from v1/v2:

```
┌─────────────────────────────────────────────────────────────┐
│  Orchestrator: opencode CLI (sole, forbid_native_cross_agent)│
│  Reads PLAN.md top unchecked item → delegates via MCP        │
└──────────────────┬──────────────────────────────────────────┘
                   │ HMAC-signed X-Agent-Identity header
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Context Server (FastAPI, :27180)                            │
│  ├── Identity (HMAC-SHA256)  ├── Policy MW (breaker/rate/DLP)│
│  ├── Governance (locks+OCC, permissions, HITL, hibernation)  │
│  ├── FinOps (meter, rollups, standup)  ├── Indexing (5 mods) │
│  ├── Meta (dream_cycle, runner)  ├── Obsidian backend proxy  │
│  ├── 2 SQLite stores (control_plane.db, token_usage.db)      │
│  └── OTel TracerProvider → OTLP :4317 (Jaeger)               │
└──────────────────┬──────────────────────────────────────────┘
                   │ WebSocket + REST
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Mission Control (Next.js 14, :3000)                         │
│  Pages: /, /kanban, /tokens, /hitl, /crash, /agents, /vault  │
│  Zustand store + WS  │  Tailwind  │  Monaco  │  Playwright   │
└─────────────────────────────────────────────────────────────┘
```

**Locked ports:** Obsidian MCP 27124/27123, Context Server 27180, Mission Control 3000,
Jaeger 4317/4318, Langfuse 3001 (optional).

**Locked decisions D1–D8:** unchanged from architecture doc.

---

## 5. Repository Layout (current)

```
context_server/
  app/
    main.py              App entry + OTel TracerProvider + all MCP endpoints + accept_implement file-write (NEW)
    config.py            Settings (env-driven)
    db.py                2 SQLite stores + audit() with OTel spans + Lamport counters
    identity.py          HMAC-SHA256 signed transport identity
    obsidian_backend.py  httpx proxy to obsidian-local-rest-api
    registry.py          Loads registry/agents/*.md YAML
    adapters.py          Echo/Filesystem/Http adapters
    delegation.py        delegate_task: orchestrator-only, budget, ledger
    middlewares.py       PolicyMiddleware (SQLite-durable breaker/rate-limit) + DLPFilter (5 patterns) + Chaperon
    indexing/
      store.py           Graph node/edge store
      graphify.py        File → graph walker
      headroom.py        Budget arithmetic
      compactor.py       LLM-augmented deterministic compaction (litellm)
      drift.py           Temporal + semantic drift detection (NEW: Jaccard + banners)
      watcher.py         watchfiles background indexer
    governance/
      locks.py           Leased locks + DAG cycle detection + OCC content-hash check
      permissions.py     Allow-list matrix (default DENY) + lethal-trifecta P13 (NEW)
      hitl.py            Queue + 7-day expiry
      hibernation.py     INSERT/DELETE + lock release/re-acquire + drift recheck (NEW: full P22)
      reconcile.py       Crash reconcile: distinguish crash/TTL + PLAN finalize + HITL expire (NEW)
    finops/
      meter.py           record() + mark_accepted() — NOW CALLED at every MCP site (NEW)
      rollups.py         CAPO, trend, heatmap, totals_by_task
      standup.py         Daily standup generator
    meta/
      dream_cycle.py     Analyze proposals + render
      runner.py          run_dream_cycle orchestrator
  tests/                 conftest + test_main/adapters/phase3/5/6/7/8/9 — 48 passed
  requirements.txt       fastapi, uvicorn, httpx, pydantic, mcp, pyyaml, watchfiles,
                         tiktoken, litellm, opentelemetry-* (4), pytest-asyncio
contracts/
  obsidian_backend.md, orchestration.md, sandbox_driver.md   (original 3 — real)
  dlp.md, mcp_tools.md, observability.md, occ.md             (new 4 — 2-3 line stubs)
registry/
  agents/*.md (6, all with bindings: [] NEW), adapters/
  index.md, log.md, agents/index.md                          (OKF bundle structure)
okf/
  SPEC.md, log.md, concepts/{capo,delegate-task,dream-cycle}.md  (frontmatter present)
docker-compose.yml       Jaeger OTel collector
tools/check_harness.py   Discipline enforcer (flag + frontmatter + append-only + test-green gate)
scripts/
  generate_agent_configs.py  NEW — dumps registry to YAML (Phase 5 generator)
  smoke_test_phase1.py
hooks/                   control_plane.db, token_usage.db (runtime, gitignored)
frontend/                Next.js 14 — see §7 Phase 9 for detail
  app/                   layout.tsx, nav.tsx (left rail), page.tsx (home + status pill)
    components/          ActivityStream.tsx (WS consumer + CSV export)
    task/[id]/           spans-only trajectory (no full lifecycle)
    tokens/              table + heatmap (no SQL-view/CSV/time-range)
    hitl/                Monaco readOnly editor (not a diff)
    crash/               re-run button (keys off task_id)
    kanban/, agents/, vault/, login/
  lib/                   api.ts (/api rewrite now works), store.ts (Zustand + WS)
  next.config.js         /api → :27180 rewrite (NEW)
  vitest.config.ts       excludes tests/e2e/** (NEW)
  playwright.config.ts   NEW — testDir: ./tests/e2e
  tests/e2e/             dashboard.spec.ts
Program.md               Metrics + Audit Schedule + Now + Dream proposals (NEW — filled)
project phases/          9 phase spec docs
project_gaps.md          The remediation plan
project_documentation.md This file
```

---

## 6. Complete Feature Inventory — What the Code Actually Does

This section documents **every functional capability** the codebase currently ships, so the
documentation covers the entire project.

### 6.1 Context Server (FastAPI :27180)

#### Health & Dashboard
| Endpoint | Method | Function |
|---|---|---|
| `/health` | GET | Returns `ok` or `degraded` based on Obsidian backend reachability (never 5xx) |
| `/dashboard/state` | GET | Locks + recent 25 audit rows + open HITL + recent 50 tasks + agent list |
| `/dashboard/agents` | GET | All registered agents + orchestrator id |
| `/dashboard/vault` | GET | Read-only Obsidian vault browse/read (list or read by path) |
| `/dashboard/events` | WS | Broadcasts audit events to connected dashboard clients |
| `/dashboard/plan` | GET | Parses PLAN.md kanban rows → structured JSON |
| `/dashboard/graph` | GET | All graph nodes + edges |
| `/dashboard/drift` | GET | Drift banners (impl-ahead + semantic_drift_detected) |
| `/dashboard/headroom` | GET | Context budget remaining + must_compact flag |
| `/dashboard/dream` | GET | Dream-Cycle proposals preview (dry run, no write) |

#### MCP Tool Surface (identity-bound via `X-Agent-Identity` HMAC header)
| Endpoint | Method | Function | Metered? |
|---|---|---|---|
| `/mcp/lookup_agent` | GET | Look up agent by id | — |
| `/mcp/find_capability` | GET | Find agents by capability | — |
| `/mcp/search_notes` | POST | Obsidian simple search + DLP scrub | ✅ |
| `/mcp/read_note` | POST | Read note + compute version_hash + DLP scrub | ✅ |
| `/mcp/append_implement` | POST | Governed write (permission → lock → OCC → DLP → idempotent patch) | ✅ |
| `/mcp/log_decision` | POST | Same governed-write path as append_implement | ✅ |
| `/mcp/delegate_task` | POST | Orchestrator-only delegation via adapters + token ledger | — (own path) |
| `/mcp/accept_implement` | POST | Orchestrator-only: mark_accepted + **append row to IMPLEMENT.md file** | — |
| `/mcp/request_clarification` | POST | Hibernate task + enqueue HITL + **route to orchestrator** | — |
| `/mcp/post_standup` | POST | Generate daily standup | ✅ |
| `/mcp/reindex` | POST | Run graphify indexer | ✅ |
| `/mcp/compress` | POST | Run compactor within token budget | ✅ |
| `/mcp/run_dream_cycle` | POST | Meta/orchestrator-only: run dream cycle | ✅ |

#### HITL & Crash endpoints
| Endpoint | Method | Function |
|---|---|---|
| `/dashboard/hitl` | GET | Open HITL items |
| `/dashboard/hitl` | PATCH | Resolve HITL item (approved/modified/rejected) → thaw task |
| `/dashboard/crashes` | GET | Run on-demand reconcile (reaped locks + hibernated orphans) |
| `/dashboard/crashes/{task_id}/rerun` | POST | Thaw a hibernated task |

#### FinOps endpoints
| Endpoint | Method | Function |
|---|---|---|
| `/dashboard/tokens` | GET | by_task totals + heatmap |
| `/dashboard/capo` | GET | CAPO summary + trend |
| `/dashboard/tokens/ws` | WS | Pushes token totals + CAPO every 3s |

#### Background loops (lifespan)
- **Daily standup loop** — fires at 9am local, calls `post_standup()`, retries with backoff.
- **Dream cycle loop** — fires at 3am local, calls `run_dream_cycle()`, retries with backoff.
- **Crash reconciliation** — runs once on startup (`reconcile(startup=True)`).
- **File watcher** — `watch_and_index()` via watchfiles (disabled in tests via `ENABLE_WATCHER=false`).

### 6.2 Governance Subsystem

| Module | Function |
|---|---|
| `identity.py` | HMAC-SHA256 signed `agent:task_id` tokens; `require_identity` dependency |
| `locks.py` | SQLite-leased locks (120s TTL) + in-memory task-waiting DAG with O(V+E) cycle detection + OCC content-hash check (`check_occ`) |
| `permissions.py` | Allow-list matrix: only `*/log.md` + `okf/log.md` paths, only `Agent Updates`/`Decisions`/`Implementation Log` headings. Default DENY. **P13 lethal-trifecta**: blocks tasks mixing `read_private` + `read_untrusted` |
| `hitl.py` | SQLite queue with 7-day expiry; enqueue/open_items/resolve |
| `hibernation.py` | **Full P22 lifecycle**: freeze releases locks → stores in frozen_state; thaw re-acquires locks + runs drift recheck → stores drift in frozen_state |
| `reconcile.py` | **P26 crash reconciliation**: startup reaps all locks as `infrastructure_crash`; on-demand reaps expired as `ttl_expiry`; finalizes `[in-progress]`/`[delegated]` PLAN rows → `[crash]`; auto-expires HITL + thaws |

### 6.3 Policy Middleware (per `/mcp/` request)
1. **Circuit breaker** — SQLite-durable; 5 consecutive 5xx → 60s trip (503).
2. **Rate limiter** — SQLite token bucket; 10 requests per 10s per agent (429).
3. **OCC** — passes `X-Expected-Version` header through (actual check in endpoint).
4. **Chaperon** — blocks untrusted-provenance writes to append_implement/log_decision (403).

### 6.4 DLP Filter (5 patterns)
AWS keys (`AKIA…`), Bearer tokens, GitHub PATs (`ghp_…`), Slack tokens (`xox…`), private-key
blocks, generic ≥40-char high-entropy strings. Applied to all read/write content.

### 6.5 Indexing Subsystem
| Module | Function |
|---|---|
| `store.py` | In-memory graph store (nodes + edges) with SQLite persistence |
| `graphify.py` | Walks repo files → builds graph nodes/edges |
| `headroom.py` | Context budget: `remaining(used)`, `must_compact(used, incoming)` |
| `compactor.py` | Deterministic + LLM-augmented (litellm) compaction within token budget; uses tiktoken |
| `drift.py` | **Temporal divergence** (≥3 newer code files vs contract) + **semantic drift** (Jaccard token overlap < 0.1) → banners with `trigger_dream_renorm` action |
| `watcher.py` | Background `watchfiles` indexer that calls `graphify()` on file changes |

### 6.6 FinOps Subsystem
| Module | Function |
|---|---|
| `meter.py` | `record()` — inserts token_ledger row per tool call (NOW CALLED at every MCP site); `mark_accepted()` — flips accepted=1 for a task |
| `rollups.py` | `capo()` (tokens/accepted-task), `capo_trend()`, `heatmap()` (agent×tool), `totals_by_task()` |
| `standup.py` | Daily standup generator |

### 6.7 Meta Subsystem
| Module | Function |
|---|---|
| `dream_cycle.py` | `analyze()` — generates optimization proposals; `render()` — formats for Program.md |
| `runner.py` | `run_dream_cycle()` — orchestrates analyze + write to Program.md proposals section |

### 6.8 SQLite Stores
**control_plane.db**: `locks`, `hibernation`, `audit_log`, `breaker_state`, `rate_limits`,
`hitl_queue` — all WAL mode.
**token_usage.db**: `token_ledger` (agent, task_id, tool, tokens_in, tokens_out, accepted).

### 6.9 Observability
- **OpenTelemetry SDK** wired: `TracerProvider` + `BatchSpanProcessor` + `OTLPSpanExporter`
  → `localhost:4317` (Jaeger). `FastAPIInstrumentor` instruments the app.
- **`audit()`** emits real spans with attributes: `agent`, `task_id`, `ok`, `detail`,
  `lamport_seq` (monotonic counter), `failure_class` (`auth` if DENY in detail, else `system`).
- **Jaeger** via `docker-compose.yml` (all-in-one collector on :4317/:4318).

### 6.10 Registry & OKF
- **6 agents**: opencode (orchestrator), hermes, claude-code, codex, antigravity, meta —
  all with `bindings: []`, capabilities, role, adapter fields.
- **OKF bundle**: `okf/SPEC.md`, `okf/log.md`, `okf/concepts/{capo,delegate-task,dream-cycle}.md`
  (all with `id, title, tags, source` frontmatter).
- **Registry bundle**: `registry/index.md`, `registry/log.md`, `registry/agents/index.md`.

### 6.11 Frontend (Next.js 14 :3000)
| Page | Status | What it does |
|---|---|---|
| `/` (home) | ✅ Real | Health status pill + active locks + ActivityStream (WS consumer + CSV export) |
| `/kanban` | ✅ Real | Fetches `/dashboard/plan`, renders PLAN.md rows |
| `/tokens` | ⚠️ Partial | by_task table + heatmap; no SQL-view layout, no time-range, no CSV on page |
| `/hitl` | ⚠️ Partial | Monaco editor (readOnly, not a diff); Approve/Modify/Reject buttons |
| `/crash` | ⚠️ Partial | Released locks + hibernated orphans + re-run button (keys off task_id) |
| `/agents` | ✅ Real | Fetches `/dashboard/agents` |
| `/vault` | ✅ Real | Fetches `/dashboard/vault`, browse/read notes |
| `/task/[id]` | ⚠️ Partial | Filters audit_log spans by task_id (no full lifecycle) |
| `/login` | ⚠️ Partial | Hardcoded `admin-token-123` cookie check |

**Frontend infrastructure**: Tailwind ✅, Zustand store + WS ✅, left-rail nav + framer-motion ✅,
Monaco imported ✅, Playwright package + config ✅, `/api` rewrite ✅, auth middleware ✅ (skeleton).
**Dead/missing deps**: `@tanstack/react-query` installed but no `QueryClientProvider`;
`@shadcn/ui` not installed.

---

## 7. Phase-by-Phase Status (re-audited v3)

Status legend: ✅ FULLY ⚠️ PARTIAL ❌ MISSING/BROKEN. "Δ" marks a change from v2.

### Phase 0 — Foundations & Contracts — ✅ (was ✅)
- ✅ 3 original contracts + 4 new (stub) contracts
- ✅ `check_harness.py` discipline enforcer (flag, frontmatter, append-only, test-green gate)
- ⚠️ 12 contracts still missing; 4 new contracts are 2-3 line stubs

### Phase 1 — Wire the Two Brains — ✅ (was ✅)
- ✅ Obsidian backend proxy, opencode sole orchestrator, OKF frontmatter, OKF bundle structure
- ✅ **`bindings` field now on all 6 agents** (Δ)

### Phase 2 — Context Server — ✅ (was ⚠️ → upgraded to GREEN)
- ✅ FastAPI, `/health`, HMAC identity, DLP (5 patterns), OCC content-hash, SQLite-durable breaker/rate-limit, lock DAG cycle detection
- ✅ **OTel/Lamport/failure-class now WORKING** (Δ — deps installed, tests green, app boots)
- ✅ **Chaperon** blocks untrusted writes (403)
- ⚠️ Secrets bridge still env passthrough (no ephemeral injection, P11)

### Phase 3 — Agent Registry, Adapters & delegate_task — ✅ (was ✅)
- ✅ 6 agents + registry loader; `forbid_native_cross_agent: true` asserted; `bindings` on all
- ✅ Real Filesystem/Http adapters; orchestrator-only delegation

### Phase 4 — Per-Project Harness Contract — ✅ (was ✅)
- ✅ Harness triad; `check_harness.py` enforcer; `/dashboard/vault`, `/dashboard/plan` parse
- ⚠️ `project_contract.md`, `obsidian_export_hook.md` still missing

### Phase 5 — Indexing & Generation — ✅ (was ⚠️ → upgraded)
- ✅ Indexing module real (delta-aware, tiktoken, litellm compactor, watcher)
- ✅ **`scripts/generate_agent_configs.py` added** (Δ)
- ⚠️ Drift now has temporal + semantic (Jaccard) detection (Δ) — but not real vector embeddings
- ⚠️ `contracts/delta_indexing.md` still missing

### Phase 6 — Verification, Permissions, HITL, Hibernation, Crash Reconciliation — ✅ (was ⚠️ → upgraded)
- ✅ Permission matrix default-DENY + **P13 lethal-trifecta** (Δ)
- ✅ Lock DAG cycle detection; HITL queue + 7-day expiry + **routed to orchestrator** (Δ)
- ✅ **Full P22 hibernation lifecycle** — lock release/re-acquire + drift recheck (Δ)
- ✅ **P26 crash reconciliation** — crash-vs-TTL distinguish + PLAN finalize + HITL auto-expire (Δ)
- ✅ `accept_implement` now **writes the IMPLEMENT.md file row** (Δ)
- ✅ Crash re-run endpoint + frontend re-run button
- ⚠️ Still missing: close OTel spans as `infrastructure_crash`, rollback to snapshot
- ❌ `contracts/{permission_matrix,hibernation,crash_recovery}.md` still missing

### Phase 7 — Daily Ops & Cost Discipline (CAPO) — ✅ (was ⚠️ → upgraded)
- ✅ **Per-tool token metering NOW WIRED** — `meter.record()` called at every MCP call site (Δ)
- ✅ CAPO, trend, heatmap, totals, standup, websockets
- ⚠️ `hooks/task_outcomes.db` still absent (fold-in not documented as deviation)
- ⚠️ Week rollup to `registry/log.md` — file exists but empty of rollups

### Phase 8 — Meta-Harness & Dream Cycle — ✅ (was ✅)
- ✅ `meta/dream_cycle.py` analyze + render; endpoints; meta agent registered
- ✅ **`Program.md` now filled** with metrics + audit schedule + proposals (Δ)
- ⚠️ No recorded accepted Dream-Cycle proposal (unchanged)

### Phase 9 — Next.js Mission Control — NOT READY, ~50% (was ~45%)

| # | DoD item | v2 | v3 | Evidence |
|---|---|---|---|---|
| 1 | Every page renders real data | FULLY | FULLY | all pages fetch from :27180 or /api |
| 2 | Full task lifecycle in `/task/[id]` | MISSING | **MISSING** | `task/[id]/page.tsx` still spans-only |
| 3 | `/tokens` SQL views + time-range + CSV | MISSING | **MISSING** | table + heatmap only |
| 4 | `/hitl` Monaco DIFF modal | PARTIAL | **PARTIAL** | readOnly single editor, not a diff; Modify has no edit affordance |
| 5 | `/crash` re-run from snapshot id | PARTIAL | **PARTIAL** | keys off task_id, not snapshot id |
| 6 | Playwright green; Lighthouse a11y ≥ 95 | MISSING | **PARTIAL** | config added (Δ); no Lighthouse |
| 7 | WS + 5s poll fallback | PARTIAL | **PARTIAL** | WS works; no poll fallback, no reconnect |
| 8 | Auth: PIN + signed tokens | PARTIAL | **PARTIAL** | hardcoded `admin-token-123` literal |
| 9 | Left rail + top-bar pill | PARTIAL | **PARTIAL** | left rail ✓; no top bar; pill only on `/` |
| 10 | Deps installed & USED | PARTIAL | **PARTIAL** | `/api` rewrite fixed (Δ); TanStack unused; shadcn not installed |

---

## 8. Gap Closure Scorecard — v2 → v3

### Tier 0 — Gate unblockers
| Gap | v2 | v3 | Status |
|---|---|---|---|
| OTel deps not installed → pytest/ruff/check_harness RED | RED | **GREEN** | ✅ CLOSED |
| `vitest.config.ts` missing e2e exclude + no playwright config | RED | **GREEN** | ✅ CLOSED |
| `next.config.js` missing `/api` rewrite | OPEN | **CLOSED** | ✅ CLOSED |
| ruff violations | 12 | 23 | ❌ STILL RED (22 auto-fixable) |

### Tier 1 — Backend behavioral gaps
| Gap | v2 | v3 | Status |
|---|---|---|---|
| Per-tool token metering wired (Phase 7 DoD) | OPEN | **CLOSED** | ✅ `meter_record()` at all 8 MCP sites |
| `accept_implement` writes IMPLEMENT.md file row | OPEN | **CLOSED** | ✅ `main.py:297-327` |
| HITL routed to orchestrator | OPEN | **CLOSED** | ✅ `main.py:339-350` |
| Full hibernation lifecycle P22 | OPEN | **CLOSED** | ✅ `hibernation.py:13-48` |
| Real crash reconciliation P26 | PARTIAL | **SUBSTANTIALLY CLOSED** | ⚠️ crash/TTL distinguish + PLAN finalize done; span-close + rollback remain |
| Lethal-trifecta / instruction-provenance P13 | OPEN | **CLOSED** | ✅ `permissions.py:30-36` |
| Real drift detection P30 | OPEN | **PARTIAL** | ⚠️ temporal + Jaccard semantic; no real vector store |
| `scripts/generate_agent_configs.py` | OPEN | **CLOSED** | ✅ new file |
| `Program.md` audit schedule P7 | OPEN | **CLOSED** | ✅ metrics + schedule + proposals |
| `bindings` field on all agents | OPEN | **CLOSED** | ✅ all 6 agents |
| Secrets rotation + ephemeral injection P11 | OPEN | **OPEN** | ❌ unchanged |

### Tier 2 — Frontend (Phase 9)
| Gap | v2 | v3 | Status |
|---|---|---|---|
| `/api` rewrite for client-side fetch | OPEN | **CLOSED** | ✅ `next.config.js` |
| `/task/[id]` full lifecycle | MISSING | **MISSING** | ❌ still spans-only |
| `/tokens` SQL+CSV+time-range | MISSING | **MISSING** | ❌ unchanged |
| `/hitl` Monaco diff | PARTIAL | **PARTIAL** | ⚠️ still readOnly single editor |
| `/crash` snapshot-id re-run | PARTIAL | **PARTIAL** | ⚠️ still task_id |
| Playwright config | MISSING | **CLOSED** | ✅ `playwright.config.ts` |
| 5s poll fallback | MISSING | **MISSING** | ❌ unchanged |
| Real auth (PIN + signed tokens) | PARTIAL | **PARTIAL** | ⚠️ still hardcoded literal |
| Top-bar global pill | PARTIAL | **PARTIAL** | ⚠️ still only on `/` |
| shadcn/ui | MISSING | **MISSING** | ❌ not installed |
| TanStack Query used | DEAD | **DEAD** | ❌ no QueryClientProvider |
| Lighthouse a11y ≥ 95 | MISSING | **MISSING** | ❌ no config |
| Silent `.catch()` fallbacks | OPEN | **OPEN** | ❌ unchanged |

### Tier 3 — Governance / contracts
| Gap | v2 | v3 | Status |
|---|---|---|---|
| 12 missing contracts | OPEN | **OPEN** | ❌ unchanged |
| 4 new contracts fleshed out | STUBS | **STUBS** | ❌ still 2-3 lines |
| IMPLEMENT.md deviations table current | PARTIAL | **STALE** | ⚠️ doesn't reflect v3 work (P13/P22/P26/metering/etc.) |
| `task_outcomes.db` fold-in deviation | OPEN | **OPEN** | ❌ not documented |

---

## 9. Remaining Gaps

Consolidated, de-duplicated list of gaps still open after v3.

### Blocker tier (must fix before commit)
1. **ruff: 23 violations** — `ruff check context_server --fix` (resolves 22) + rename `l` →
   `line_` at `main.py:320` (E741). **~2 minutes. This is the only RED gate.**

### Backend behavioral (still open)
2. **Real drift detection (P30)** — temporal + Jaccard token-overlap is present but not a real
   vector store with embeddings. Upgrade to real embeddings for production-grade drift.
3. **P26 crash reconciliation — remaining 2 sub-items**: close OTel spans as
   `infrastructure_crash`; rollback to snapshot (currently only finalizes PLAN rows + reaps locks).
4. **Secrets rotation + ephemeral credential injection (P11)** — still env passthrough only.
5. **Dream-Cycle**: no recorded accepted proposal in `Program.md` (the proposal section exists
   but has no promoted/accepted items).
6. **`hooks/task_outcomes.db`** — arch Phase 7 calls for a separate denominator file; currently
   CAPO denominator lives in `token_ledger.accepted`. Either create the file or document the
   fold-in as a deviation in `IMPLEMENT.md`.
7. **`registry/log.md` week rollup** — file exists (3 lines) but contains no rollup data.

### Frontend (Phase 9) — still missing
8. **`/task/[id]` full task lifecycle view** — PLAN row → spans → breaker → HITL → freeze → thaw
   → gate → CAPO. Currently spans-only.
9. **`/tokens`** — SQL-view layout, time-range selector, CSV export on this page.
10. **`/hitl` real Monaco *diff*** (original ↔ modified) with editable right pane; Modify must
    let the user edit content and re-run OCC.
11. **`/crash` re-run keyed on snapshot id**, not just task_id.
12. **5s poll fallback** on the WebSocket store (with reconnect logic).
13. **Real auth** — local PIN + HMAC-signed `(ui, human)` tokens, not hardcoded literal.
14. **Top-bar global status pill** across all pages (currently only on `/`).
15. **`@shadcn/ui`** — install or formally drop from spec.
16. **`@tanstack/react-query`** — add `QueryClientProvider` in `layout.tsx` or remove the dead dep.
17. **Lighthouse a11y ≥ 95** — no config or assertion.
18. **Silent `.catch(() => fakeDefault)` fallbacks** — pages mask real backend failures; should
    surface errors.

### Contracts / governance
19. **12 contracts still missing** — `identity`, `secrets_bridge`, `read_chaperon`,
    `circuit_breaker`, `rate_limit`, `project_contract`, `obsidian_export_hook`,
    `delta_indexing`, `permission_matrix`, `hibernation`, `crash_recovery`, `lock_manager`.
20. **4 new contracts are 2-3 line stubs** — `dlp.md`, `mcp_tools.md`, `observability.md`,
    `occ.md` need fleshing out to be enforceable.
21. **`IMPLEMENT.md` deviations table is stale** — doesn't reflect the v3 work (P13, P22, P26,
    metering, accept_implement file-write, HITL routing, bindings, Program.md, generator script).
    The ledger rows also still show the old dates; the new work is unlogged.
22. **`check_harness.py` could be stronger** — add a `ruff .` gate alongside the pytest gate;
    assert `bindings` presence; hash-chain append-only monotonicity.

---

## 10. Final Readiness Verdict (v3)

| Question | v1 | v2 | v3 |
|---|---|---|---|
| Does the project boot? | Yes | No (OTel import crash) | **Yes** — deps installed, `uvicorn` starts |
| Are all 10 phase rows marked done? | Yes | Yes | Yes (but ledger rows are stale — v3 work unlogged) |
| Do shipped changes meet each phase DoD? | Mixed | Mixed | **Phases 0–8 ✅; Phase 9 ❌ (~50%)** |
| Are tests/lint/validator green? | Yes (nominal) | **NO — regression** | **3 of 4 GREEN** (pytest✅, check_harness✅, npm test✅, npm lint✅); **ruff RED** |
| Is per-tool CAPO metering real? | No | No | **Yes** — `meter_record()` at all 8 MCP sites |
| Is the hibernation lifecycle real? | No | No | **Yes** — lock release/re-acquire + drift recheck |
| Is crash reconciliation real? | No | Partial | **Yes** — crash/TTL distinguish + PLAN finalize |
| Is it ready to use as the spec defines? | No | No (less usable than v1) | **Backend: yes (after ruff fix). Frontend: no (~50%).** |

### Summary verdict (v3)

- **The backend is the strongest it has ever been.** The v2 OTel regression is fixed. 10 of 13
  v1/v2 behavioral gaps are genuinely closed in code: per-tool metering (the heart of CAPO),
  `accept_implement` file-write, HITL→orchestrator routing, full P22 hibernation lifecycle, P26
  crash reconciliation with PLAN finalization, P13 lethal-trifecta, P30 drift (temporal + semantic),
  the Phase 5 generator, `Program.md` audit schedule, and `bindings` on all agents.

- **The only RED gate is ruff (23 violations, 22 auto-fixable).** Run `ruff check context_server
  --fix` + rename one variable. ~2 minutes to fully green.

- **The frontend is ~50%** — the `/api` rewrite was fixed, Playwright is configured, but the
  heavy items remain: full task lifecycle, Monaco *diff*, `/tokens` SQL+CSV, PIN/signed auth,
  top-bar pill, shadcn, TanStack wiring, poll fallback, Lighthouse, and removing silent catch
  fallbacks.

- **Governance needs attention**: 12 contracts missing, 4 new contracts are stubs, and the
  `IMPLEMENT.md` ledger/deviations table is stale (doesn't reflect the v3 work).

### Honest headline (v3)

> The backend has crossed the threshold from "partially working" to "substantively complete
> against its own spec" — real per-tool CAPO metering, real hibernation lifecycle, real crash
> reconciliation, lethal-trifecta enforcement, and a real IMPLEMENT.md file-write are all
> shipped and tested. **Fix the 23 ruff violations (22 auto-fixable, ~2 min) to restore a fully
> green gate set.** Then the remaining work is: frontend Phase 9 (the largest gap at ~50%),
> contract authoring (12 missing + 4 stubs), secrets rotation (P11), and updating the
> `IMPLEMENT.md` ledger to reflect the v3 work. The project is **usable for backend development
> today** and **ready for a focused frontend sprint** to reach spec-complete.
