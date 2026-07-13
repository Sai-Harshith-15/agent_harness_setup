# Claude Code — Agentic OS Audit (Memory-Layer Focus)

> **Auditor:** Claude Code (robust agentic-OS audit pass)
> **Audit date:** 2026-07-12
> **Repo:** `D:\GitRepo\agent_harness_setup`
> **Scope:** Full codebase — control plane (`context_server/app/**`), memory layer (3 SQLite stores + OKF + Obsidian), registry, hooks, Next.js frontend, and all planning docs (`project phases/`, `opencode_glm_implementation_plan.md`, `IMPLEMENT.md`, `PLAN.md`, `Program.md`, `project_documentation.md`, `agent_os_project_architecture.md`).
> **Method:** Direct code reading of the memory subsystem + 3 parallel specialist sub-audits (phases-vs-implementation, frontend/UX, backend/security). Backend test suite: **76/76 pass** (from repo root only). `.venv`/`__pycache__` excluded.
> **Relationship to prior docs:** complements `audit results.md` (2026-07-12, doc-gap focus) and `project_gaps.md` (2026-07-10, v3). This audit supersedes both for code-level findings.

---

## 0. Bottom Line (read this first)

You asked one central question: *"I built an agent OS with **2 layers of memory**; every agent I run must pass its data into the **same-context memory**. Audit whether that actually works."*

**Verdict: It does not — and by the plan's own design, it was never built to.** The intended architecture (`opencode_glm_implementation_plan.md` §1.3, line 109) explicitly states:

> *"The Agentic OS unifies **semantic + procedural** memory. **Episodic stays per-agent on purpose**, because that is the layer where each agent's loop implementation differs."*

The code faithfully implements that decision. **There is no shared, same-context (episodic) memory that flows automatically from one agent run into the next.** Agents share only a `task_id` label for audit/token grouping; all memory is *pull-only*, and each agent must call MCP tools itself to fetch it. Delegation (`delegation.py:71`) and every adapter (`adapters.py`) hand a sub-agent **nothing but a raw `prompt` string** — no accumulated context, no prior outputs, no working memory.

So there is a **design-vs-intent gap**: your current goal (unified same-context memory across every agent) contradicts a deliberate architectural choice already baked into the plan and code. This is resolvable, but it is a *net-new subsystem*, not a bug fix. **Section 2 is the remediation design for it.**

Beyond that headline: the backend is feature-complete and tests are green, but carries **6 Critical** and **9 High** production-safety defects (forgeable identity, non-atomic locks, path-traversal write, destructive startup reconcile, unauthenticated state-mutation, event-loop-blocking SQLite, a 500-on-every-load task page). The frontend is a polished dashboard bolted onto six raw prototype pages (design score **5/10**).

**Overall readiness: strong prototype / demo-grade. NOT production-ready, and NOT yet ready to layer skills + MCPs on top** until the memory-handoff design (Section 2) and the Critical safety fixes (Section 7) are addressed — otherwise every skill you add inherits the forgeable-identity and no-shared-memory problems.

---

## 1. The Two-Layer Memory Model — What Was Actually Built

### 1.1 Intended design (from the plan)

| Tier (discipline) | Purpose | Intended implementation | Unified? |
|---|---|---|---|
| **Episodic** | Short-term session history | Each agent's own store (Hermes DB, `.opencode/`, `.claude/`) | **No — per-agent by design** |
| **Semantic** | Long-term facts + relationships | OKF bundles + Graphify/`codebase-memory` graph | **Yes** |
| **Procedural** | "How-to" + conventions | Per-repo `AGENTS.md` + Obsidian `40 Knowledge/` | **Yes** |

Mapped onto the **Two-Brain model**: **Primary Brain** = Obsidian human notes; **Secondary Brain** = OKF bundles; both fronted by the **Context Server (MCP)** as the single delivery surface (`opencode_glm_implementation_plan.md` §1.1–1.3).

### 1.2 What exists in code

**Layer 1 — Structural / working memory (semantic graph + context budget):**
- `context_server/app/indexing/store.py` — SQLite `codebase_memory.db`, `nodes` + `edges` tables, content-hash delta indexing. ✅ Works.
- `indexing/graphify.py` — repo walker, extracts `import`/`[[wikilink]]` edges, delta-aware. ✅ Works.
- `indexing/compactor.py` — token-budget compaction. ⚠️ **Stub** (`TODO(phase-5)`); deterministic degree/recency; real LLM summary only if `OPENAI_API_KEY`/`LITELLM_API_KEY` set.
- `indexing/drift.py` — spec↔impl divergence. ⚠️ **Stub**; real embeddings no-op without an API key → falls back to Jaccard token overlap.
- `indexing/headroom.py` — context-budget guard. ⚠️ **Hardcoded 128k / 8k reserve**; no per-model awareness.

**Layer 2 — Durable knowledge ("Secondary Brain"):**
- `okf_backend.py` — OKF concept search/get across bundles. ✅ Works, but **keyword substring scoring only** (no semantic/vector search).
- `obsidian_backend.py` — Obsidian REST proxy (Primary Brain), DLP-scrubbed on read. ✅ Works.
- `hooks/obsidian_export_hook.py` — Obsidian → OKF export with DLP pass. ⚠️ Flattens folders (`dst = join(okf_dir, file)`) → **name collisions silently overwrite**.

**Consolidation ("Dream Cycle" = memory renormalization):**
- `meta/dream_cycle.py` + `meta/runner.py` — nightly pass that turns drift/CAPO/denials into proposals, written via the governed path to `okf/log.md`. ✅ Conceptually sound; LLM reflection optional.

### 1.3 Memory-layer gaps (specific to your "same-context" goal)

| # | Severity | Gap | Evidence |
|---|---|---|---|
| M1 | **Critical (for your goal)** | **No cross-agent same-context hydration.** Delegated/sub-agents receive only `prompt`; no injection of accumulated episodic/working context. "Same context memory" is not wired. | `delegation.py:71`; `adapters.py:24-77` (Echo/Filesystem/Http adapters all pass `prompt` only) |
| M2 | **High** | **Episodic memory is isolated by design** — contradicts your stated requirement. Needs a net-new shared-episodic subsystem (Section 2). | plan §1.3 line 109 |
| M3 | **High** | **Secrets can enter the memory index unredacted.** `graphify` writes `summary=text[:160]` into `codebase_memory.db` with **no DLP scrub**, while read endpoints do scrub. Memory layer is a DLP blind spot. | `graphify.py:48` vs `main.py:273,287,361` |
| M4 | **Medium** | **Semantic graph search is promised but not exposed.** `codebase-memory-mcp.md` advertises "semantic search and graph querying," but the only endpoint is `/dashboard/graph` (dumps all nodes/edges). No `/mcp/search_graph`. | `registry/adapters/codebase-memory-mcp.md:8` vs `main.py:625` |
| M5 | **Medium** | Compactor + drift are stubs (see 1.2) — the "intelligent" memory compression/renormalization is heuristic until API keys are wired. | `compactor.py:6`; `drift.py:39-54` |
| M6 | **Low** | Headroom budget hardcoded (128k) — wrong for smaller-context models; risks silent truncation. | `headroom.py:6-7` |
| M7 | **Low** | Obsidian→OKF export flattening overwrites same-named notes across folders. | `obsidian_export_hook.py:32` |

---

## 2. Remediation Design — Making "Same-Context Memory" Real

This is the subsystem you actually need. It is additive and does not fight the existing architecture.

**Goal:** every agent run (including delegated sub-agents) reads from and writes to a *shared, task-scoped episodic memory*, so context accumulates across agents instead of resetting.

**Design (minimal, uses what's already there):**

1. **Add an `episodic_memory` table** to `control_plane.db` (or a new `episodic.db`):
   `task_id, seq, agent, role (input|output|note), content, ts` — append-only, keyed by `task_id`.
2. **Write on every agent turn.** In `delegation.py`, after `adapter_for(meta).run(...)`, persist the result (already have `TaskResult.output`) as an episodic row. Also persist the inbound prompt.
3. **Hydrate on every agent turn.** Before calling `adapter_for(meta).run(task_id, prompt, meta)`, build a `context_bundle` = recent episodic rows for `task_id` + top-K semantic hits (OKF/graph) + procedural (`AGENTS.md`), and pass it *into* the prompt/meta. This single change turns isolated agents into same-context agents.
4. **Budget it through `headroom` + `compactor`** so the bundle never blows the context window (both already exist — wire them here).
5. **DLP-scrub on write** (fixes M3 at the same time).
6. **Expose `/mcp/recall`** (read task memory) and **`/mcp/remember`** (append) as first-class MCP tools so *external* agents (Claude Code, opencode, hermes) get the same shared memory, not just the internal delegate path.

**Effort:** ~1 focused subsystem. Nothing above requires ripping out existing code — it wraps `delegate_task` and adds two MCP routes. This is the single highest-leverage change for your stated objective.

---

## 3. Phase-by-Phase Setup Audit (0–9)

| Phase | Deliverable | Status | Notes |
|---|---|---|---|
| **P0** Foundations & contracts | Contracts, `IMPLEMENT.md`, `AGENTS.md` | ✅ Done | Contracts present; `sandbox/` deliberately deferred. |
| **P1** Wire the Two Brains | Obsidian binding + OKF scaffold + registry | ⚠️ Partial | `registry/log.md` empty; `registry/capabilities/` exists now; agent `bindings: []` mostly empty. |
| **P2** Context Server core | Locks, identity, DLP, OCC, dashboards | ✅ Done (with defects) | Feature-complete; but locks non-atomic + default identity secret (Section 7). |
| **P3** Registry + adapters + delegate | Delegation, adapters, DoD test | ✅ Done (with defects) | Delegation depth cap ineffective (`depth` always 0); adapters are Echo/Filesystem/Http. |
| **P4** Per-project harness | Triad + `check_harness.py` + `/vault` | ✅ Done | No reference downstream project brought into conformance. |
| **P5** Indexing & generation | Graphify, compactor, drift, headroom | ⚠️ Partial | Works but compactor/drift are stubs; semantic search not exposed (M4/M5). |
| **P6** Governance & resilience | Permissions, HITL, hibernation, reconcile | ⚠️ Partial | Reconcile destructive on startup; lethal-trifecta rule present but **dead** (Section 6 H4); snapshot-restore hazard. |
| **P7** FinOps / CAPO | Meter, rollups, standup | ✅ Done | Aggregation code solid; no real week-long rollup yet (operational). |
| **P8** Meta-harness / Dream Cycle | Analysis + nightly runner | ✅ Done | Governed-write path correct; LLM reflection optional. |
| **P9** Mission Control frontend | Next.js pages + plan parser | ⚠️ Partial (~55%) | Dashboard/login polished; 6 pages raw prototypes; Playwright red (Section 5). |

**Phase-ledger inconsistencies found (docs misreport state):**
- `IMPLEMENT.md:167` lists `/mcp/log_decision` as *missing* → **stale**, route exists at `main.py:319`.
- `CLAUDE.md` "Known Deviation #1" (missing `/mcp/log_decision`) → **stale**, same reason.
- `CLAUDE.md` "sandbox stub removed" → file still exists (`meta/sandbox.py`, dead code).
- Test-count drift across docs: `project_gaps.md` says 48/48, `audit results.md` says 76/76 (current run confirms **76/76**).

---

## 4. Backend / Control-Plane Audit (context_server)

**Route surface:** 21 identity-bound `/mcp/*` routes + ~18 `/dashboard/*` routes. All `/mcp/*` require `X-Agent-Identity`. **No `/mcp/*` route is missing.** Full parameterization → **no SQL injection found.** WAL enables concurrent reads. Permission matrix is default-deny/allow-list. 76/76 tests green.

**Critical & High defects** (full register in Section 6):
- **Forgeable identity** — `identity_secret` defaults to `"default-insecure-secret"` (`config.py:18`). HMAC algo + default key both in-repo → anyone reaching the port can forge *any* agent, including the orchestrator. Linchpin of the entire auth model.
- **Non-atomic lock manager** — check-then-upsert with no transaction / `BEGIN IMMEDIATE` / `busy_timeout`; `ON CONFLICT DO UPDATE` unconditionally overwrites → double-grant, which undermines the OCC guarantee `governed_write` depends on (`locks.py:24-64`).
- **Path traversal write** — `accept_implement` does `os.path.join(root, body.path)` then reads+rewrites the file; absolute/`..` paths escape `root` (`main.py:487-502`).
- **Destructive startup reconcile + snapshot clobber** — `reconcile(startup=True)` treats *every* existing lock as a crash, rewrites `PLAN.md`, and `restore_snapshot` overlays a stale workspace onto the live tree via `copytree(..., dirs_exist_ok=True)` (`reconcile.py:10-71`, `snapshot.py:35-51`). A routine restart can overwrite current code.
- **`/dashboard/task/{id}` 500** — selects `input_tokens/output_tokens`, but the schema and all other code use `tokens_in/tokens_out` → `no such column` on every task-detail load, breaking the `/task/[id]` page (`main.py:557` vs `db.py:28-29`).
- **Unauthenticated state mutation** — `PATCH /dashboard/hitl` and `POST /dashboard/crashes/{id}/rerun` take no identity; `GET /dashboard/secrets` discloses the secrets inventory (`main.py:462,534,567`).
- **Sync SQLite on the async loop + no `busy_timeout`** — every DB call blocks the event loop; concurrent writers get `database is locked` → uncaught 500s (`db.py:101-111`).
- **CWD-dependent DB path** — `hooks_dir="../hooks"` resolves against process CWD; app and test fixture can point at *different* databases (`config.py:17`, `conftest.py:12`).

**Notable robustness bugs:** circuit-breaker half-open branch is dead code (checks `detail` in headers, but it's a body field — `middlewares.py:182`); `_args_hash` ignores POST bodies so breaker replay-detection is meaningless for writes; file-watcher re-graphifies the whole repo on *every* audit-log write because `hooks/` isn't excluded from `awatch` (`watcher.py:11-18`); pervasive `except Exception: pass` hides failures.

---

## 5. Frontend / UI Audit (Mission Control)

**Verdict: MVP-usable dashboard on top of a skeleton app. Design score 5/10. Not production-ready.**

**Is it clean & user-friendly?** *Partly.* The **home dashboard + login** are genuinely well-crafted — cohesive dark "glass-panel" theme, framer-motion animated nav indicator, live status-ping dots, real empty states ("No resources currently locked"), responsive sidebar→topbar collapse, semantic HTML. That part is neat and pleasant.

**But ~75% of the app is not:** `agents`, `kanban`, `hitl`, `crash`, `tokens`, `task/[id]`, `vault` use **zero Tailwind** — 100% raw inline `style={{}}` with hardcoded hex, bypassing the entire design-token system in `globals.css`/`tailwind.config.ts`. The app reads as two different products stitched together. No loading states anywhere; `kanban` `repeat(7,1fr)` breaks on mobile; the HITL modal is inaccessible (no dialog role / focus trap / Esc / backdrop-close).

**Data layer is fragmented & partly broken:**
- **Three competing fetch strategies** — `lib/api.ts` (proxy-aware) used by only half the pages; the rest hardcode `http://127.0.0.1:27180`; WebSockets hardcode `ws://localhost:27180`.
- **Playwright failure root cause (confirmed):** `app/page.tsx` is an async **Server Component** fetching `127.0.0.1:27180` **server-side** (`page.tsx:5,11`). Playwright's `page.route` can only intercept *browser* requests → SSR fetch hits nothing → `error.tsx` renders "Backend Error" → both e2e assertions fail. **The tests are structurally impossible to pass as written**, not flaky.
- Client pages (`crash`/`hitl`/`tokens`) bypass the `/api` CORS proxy → real CORS failures in-browser.
- `ActivityStream` opens 2 WebSockets in `useEffect([])` with **no cleanup** → leak on every mount; hardcoded `ws://` breaks under HTTPS (mixed content).

**Auth is a stub:** `middleware.ts` compares a cookie against a single hardcoded `MISSION_CONTROL_PIN || 'admin-token-123'`; login writes a **non-HttpOnly** cookie client-side with no server validation; `/api` is excluded from the matcher so proxied backend calls are unauthenticated at the edge. Also `lib/api.ts:9` exports a stale **2-part unsigned** `X-Agent-Identity` that the backend now 401s.

---

## 6. Master Gap Register (severity-sorted, deduplicated)

### 🔴 Critical
| ID | Area | Issue | Location |
|---|---|---|---|
| C1 | Memory | No cross-agent same-context hydration (your core requirement unmet) | `delegation.py:71`; `adapters.py` |
| C2 | Security | Default `identity_secret` → forgeable agent identity (incl. orchestrator) | `config.py:18`; `identity.py:11-34` |
| C3 | Concurrency | Non-atomic lock acquire → double-grant, undermines OCC | `locks.py:24-64` |
| C4 | Security | `accept_implement` path traversal → arbitrary file read/write | `main.py:487-502` |
| C5 | Data safety | Startup `restore_snapshot` overlays stale workspace onto live tree | `snapshot.py:35-51`; `reconcile.py:52` |
| C6 | Correctness | `GET /dashboard/task/{id}` selects non-existent columns → **500 on every task-detail load** | `main.py:557` vs `db.py:28-29` |

### 🟠 High
| ID | Area | Issue | Location |
|---|---|---|---|
| H1 | Security | Unauthenticated state-mutation + secrets/token disclosure on `/dashboard/*` | `main.py:462,534,567` |
| H2 | Persistence | Sync SQLite on async loop + no `busy_timeout` → event-loop block, 500s under contention | `db.py:101-111` |
| H3 | Robustness | Startup reconcile treats all live locks as crashes; rewrites `PLAN.md` | `reconcile.py:10-71` |
| H4 | Governance | Lethal-trifecta / cross-agent rule present but **dead** (never enforced) | `permissions.py` |
| H5 | Memory/DLP | Graph index stores unredacted content (DLP blind spot) | `graphify.py:48` |
| H6 | Frontend | SSR fetch un-mockable → Playwright red; "Backend Error" whenever backend down | `page.tsx:5,11` |
| H7 | Frontend | 6 pages ignore design system (raw inline styles) → inconsistent, unfinished | `agents/kanban/hitl/crash/tokens/task/vault` |
| H8 | Frontend | Auth is a shared static token in a non-HttpOnly cookie | `middleware.ts:15`; `login/page.tsx:9` |
| H9 | Persistence | CWD-dependent DB path → app vs test point at different DBs | `config.py:17`; `conftest.py:12` |

### 🟡 Medium
| ID | Issue | Location |
|---|---|---|
| Me1 | Semantic graph search promised, not exposed (no `/mcp/search_graph`) | `codebase-memory-mcp.md:8` |
| Me2 | Compactor + drift are stubs (heuristic without API keys) | `compactor.py:6`; `drift.py` |
| Me3 | Delegation depth cap ineffective (`depth` always 0 from HTTP) | `delegation.py:16-22` |
| Me4 | No per-agent authz on `request_credentials`/`rotate_credentials`; credential returned in body | `main.py:438-460`; `secrets_bridge.py:91` |
| Me5 | DLP: ReDoS-prone CC regex, window-limited entropy scan, stores scrubbed (not original) text, uses HTTP 202 as error | `middlewares.py:210-303` |
| Me6 | Watcher re-graphifies whole repo on every DB write (`hooks/` not excluded from `awatch`) | `watcher.py:11-18` |
| Me7 | In-memory-only state (deadlock DAG, secrets, chaperon, ws clients) lost on restart / not multi-worker safe | `locks.py:17`; `middlewares.py:42`; `secrets_bridge.py:30` |
| Me8 | Client pages bypass `/api` proxy → CORS failures | `crash/hitl/tokens` pages |
| Me9 | WebSocket leak + no reconnect + mixed-content under HTTPS | `ActivityStream.tsx:10-16`; `store.ts:24` |
| Me10 | HITL modal inaccessible; no loading states; kanban not responsive | `hitl/page.tsx:40`; `kanban/page.tsx:15` |

### 🟢 Low
| ID | Issue | Location |
|---|---|---|
| L1 | Identity-spoof check advisory (logs, doesn't block); rate/breaker keyed on unverified agent | `middlewares.py:98-108` |
| L2 | Circuit-breaker half-open branch dead; `_args_hash` ignores body | `middlewares.py:58-65,182` |
| L3 | Headroom budget hardcoded 128k (no per-model awareness) | `headroom.py:6-7` |
| L4 | Obsidian→OKF export flattening overwrites same-named notes | `obsidian_export_hook.py:32` |
| L5 | Stale `AGENT_HEADER` (2-part unsigned) → backend 401s if ever sent | `lib/api.ts:9` |
| L6 | Dead code: `meta/sandbox.py`; unused bridge methods; `import datetime` shadowing | `sandbox.py`; `main.py:473` |
| L7 | Doc/ledger drift: `/mcp/log_decision` "missing", sandbox "removed", test counts | `IMPLEMENT.md:167`; `CLAUDE.md` |
| L8 | Pervasive `except Exception: pass` hides failures; tests only collectible from repo root | multiple |

**What's solid (verified positives):** HMAC identity signing is real (`identity.py`); no SQL injection; WAL concurrent reads; OCC content-hash logic sound *when the lock holds*; default-deny permission matrix; idempotent writes (`If-None-Match: *`); DLP on all *read* egress; governed Dream-Cycle write path; 76/76 backend tests green.

---

## 7. Prioritized Remediation Roadmap

**Gate 0 — before adding any skills/MCPs (safety linchpins):**
1. Require a non-default `identity_secret` at boot (fail closed) — **C2**.
2. Make lock acquisition one atomic `BEGIN IMMEDIATE` txn + set `busy_timeout` on every connection — **C3, H2**.
3. `os.path.commonpath` guard + reject absolute/`..` in `accept_implement` — **C4**.
4. Gate `restore_snapshot`/startup-reconcile behind an explicit crash signal, not "any lock exists" — **C5, H3**.
5. Fix the `input_tokens/output_tokens` column bug — **C6** (one-line rename).

**Gate 1 — your actual objective (shared memory):**
6. Build the same-context episodic memory subsystem (Section 2): `episodic_memory` table, hydrate-before-run + persist-after-run in `delegation.py`, DLP-scrub on write, expose `/mcp/recall` + `/mcp/remember`, budget via headroom/compactor — **C1, M1, M3, M4**.

**Gate 2 — harden governance & memory intelligence:**
7. Add identity to `/dashboard/*` mutations; scope credential endpoints — **H1, Me4**.
8. Wire real embeddings behind `semantic_drift_detected()` and the compactor summary source — **Me1, Me2**.
9. Exclude `hooks/` from the watcher; make DB path absolute — **Me6, H9**.

**Gate 3 — frontend sprint:**
10. Route *all* fetches through one env-configured base (fix SSR mockability), unify pages onto Tailwind + shared components, add loading states, WebSocket cleanup, accessible HITL modal, real session auth — **H6, H7, H8, Me8–Me10**.

**Readiness statement:** The OS is an impressive, feature-broad prototype with green backend tests — but it is **not yet a safe foundation to layer skills + MCPs onto**. Close Gate 0 (safety) and Gate 1 (the shared-memory subsystem you actually asked about) first; those two gates are what convert this from "a demo that passes its own tests" into "an agentic OS whose memory layer does what you designed it to do."
