# Agentic OS — Project Architecture & Creation Prompt

> Companion to `opencode_glm_implementation_plan.md` (the harness *plan*). This document is the
> **project architecture + bootstrap prompt** you hand to the orchestrator (opencode CLI) to
> *build* the Agentic OS as a runnable system: harness + orchestrator + Next.js Mission Control.
>
> Three changes from the parent plan, locked in here:
>
> 1. **Obsidian bridge = `obsidian-local-rest-api` MCP** (in `tools/obsidian-local-rest-api/`), not a
>    hand-rolled ripgrep backend. This server already exposes 16 battle-tested MCP tools over HTTP
>    at `https://127.0.0.1:27124/mcp/` and is the single Obsidian access surface.
> 2. **Main orchestrator = opencode CLI.** Every other agent is a *registered delegate*, dispatched
>    through the `delegate_task` control-plane tool. opencode holds the loop.
> 3. **Frontend = Next.js Mission Control** (dashboard + Jira-style Kanban + token analytics +
>    HITL modal + OTel trajectory view). Driven off the same Context Server the agents use — no
>    second API.
>
> `prompts_necessary_context.md` describes how the broader internet community is building this same
> pattern (Obsidian command center, HITL diff modal, append-only ledgers, telemetry dashboard,
> nightly Dream Cycles, file-handoff chains). This plan folds those community patterns into the
> parent plan's discipline so the build inherits both rigor and proven UX.

---

## 0. The project, in one paragraph

A single local "Agentic OS" where one orchestrator (**opencode CLI**) drives many registered AI
agents (Hermes, claude-code, antigravity, codex, …) against two unified brains — Obsidian (primary,
human-authored, served by the `obsidian-local-rest-api` MCP) and OKF (secondary, agent-parseable,
per-repo) — through one **Context Server (FastAPI MCP)**. A **Next.js Mission Control** frontend
reads the same server to render a Mission-Control dashboard, a Jira-style Kanban of `PLAN.md`
tasks, live token-spend analytics (which tasks burn the most tokens), a HITL diff-modal, and an
OTel trajectory viewer. The whole thing is governed by lock managers, signed-transport identity,
circuit breakers, hibernation, crash reconciliation, and a Dream Cycle that self-improves nightly.

---

## 1. The Project Creation Prompt (copy-paste into opencode CLI)

```
You are bootstrapping the Agentic OS in D:\GitRepo\agent_harness_setup\.

Read these files first, in order, and treat them as the immutable spec:
  1. opencode_glm_implementation_plan.md          (the harness plan — Phases 0–8)
  2. agent_os_project_architecture.md              (THIS file — deltas + build order + frontend)
  3. prompts_necessary_context.md                  (community UX patterns to honor)
  4. tools/obsidian-local-rest-api/README.md        (the Obsidian MCP bridge — 16 tools)
  5. tools/obsidian-local-rest-api/src/mcpHandler.ts(tool surface to wrap)
  6. tools/knowledge-catalog/okf/SPEC.md           (OKF v0.1 contract)
  7. tools/awesome-harness-engineering/templates/* (AGENTS.md, PLAN.md, IMPLEMENT.md,
                                                    HARNESS_CHECKLIST.md templates)

Locked decisions (do not re-debate):
  • Obsidian primary brain is served ONLY via the obsidian-local-rest-api MCP at
    https://127.0.0.1:27124/mcp/  (Authorization: Bearer <key>). Wrap it; do not reimplement.
  • Orchestrator = opencode CLI. It owns the agent loop and the delegate_task control plane.
    Every other agent is registered, not hard-coded.
  • Frontend = Next.js Mission Control at D:\GitRepo\agent_harness_setup\frontend\, talking to the
    Context Server over the same MCP surface plus a thin /dashboard REST namespace.
  • Two local data stores in D:\GitRepo\agent_harness_setup\hooks\:
       token_usage.db    (SQLite — token + CAPO ledger)
       control_plane.db  (SQLite — locks, hibernation records, rate/quota state, OTel span ids)
  • Sandboxing default on this Windows single-host: local gVisor-equivalent (Windows Sandbox /
    containerized runner) for Phase 0–6; E2B/Firecracker path remains the documented target for
    the remote/hybrid variant. Lock the requirement (kernel isolation, no workspace escape), keep
    the implementation swappable behind a SandboxDriver interface.

Execute the build in this exact order — finish each phase's Definition-of-Done in
opencode_glm_implementation_plan.md before starting the next, and append a row to
IMPLEMENT.md with the phase, the green checks, and the agent id (you = opencode) for each:

  Phase 0  Foundations & contracts            → AGENTS.md, IMPLEMENT.md, contracts/
  Phase 1  Wire the two brains                → registry/ bundle + obsidian-local-rest-api binding
  Phase 2  Context server                     → FastAPI MCP wrapping obsidian-local-rest-api +
                                                OKF + graph + lock + identity + breaker + OCC +
                                                rate-limit + DLP + chaperon
  Phase 3  Agent registry + adapters          → 5 agents + delegate_task + opencode-as-orchestrator
  Phase 4  Per-project harness contract        → bring THIS repo into conformance first
  Phase 5  Indexing + generation               → Graphify + codebase-memory-mcp + headroom +
                                                compactor + drift + delta indexing
  Phase 6  Verification + permissions         → checklist + matrix + rollback + HITL + hibernation
                                                + crash reconciliation
  Phase 7  Daily ops + cost discipline         → token_usage.db + CAPO rollups
  Phase 8  Meta-harness + Dream Cycle          → Program.md + registry/agents/meta.md
  Phase 9  Mission Control Next.js frontend     (THIS plan only) → dashboard, Kanban, token
                                                        analytics, HITL modal, trace view

For EVERY problem listed in §8 of THIS file, implement the paired fix at the phase named and add a
citable test/proof-of-concept in the phase's Definition-of-Done.

Constraints:
  • Never reimplement what obsidian-local-rest-api already gives you (search, read, patch, append,
    periodic, tags, commands, document-map). The Context Server is a *policy + identity + audit*
    wrapper around those tools, not a replacement.
  • Every Context-Server tool carries (agent, task_id) bound at the transport layer (Phase 2.8).
  • Every write goes through the lock manager (Phase 2.6), OCC (Phase 2.10), and DLP (Phase 2.12).
  • No agent — including you — edits Obsidian notes directly. Writes go to per-repo IMPLEMENT.md and
    okf/log.md via append_implement / log_decision. The human promotes back to Obsidian.
  • Commit small, atomic, green-only; run npm test / pytest / ruff . per repo before each commit.
  • Keep README.md and contracts/* in sync with every tool-surface change.

Deliverable of the first session: Phases 0–1 green, a smoke test showing opencode calling
search_okf through the Context Server returns one concept from registry/agents/hermes.md, plus an
empty Mission Control Next.js app that boots against the Context Server's GET /health.
Stake the rest on subsequent sessions, one phase per session minimum.

Stop and call request_clarification whenever a Phase 6 Open Question from the parent plan is
unresolved and blocking. Do not invent answers.
```

---

## 2. System Overview (three layers)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                          AGENTIC OS — runnable system                          │
│                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │ LAYER 3 — Next.js Mission Control  (frontend/)  port :3000               │  │
│  │  • Mission Control dashboard     • Jira-style Kanban (from PLAN.md)      │  │
│  │  • Token analytics (which task spends most)  • CAPO FinOps panel         │  │
│  │  • HITL diff-modal             • OTel trajectory viewer                  │  │
│  │  • Hibernated-task freezer     • Crash-recovery audit feed             │  │
│  └─────────────────────────────▲──────────────────────────────────────────┘  │
│                                │ same MCP surface + /dashboard/* REST        │
│  ┌─────────────────────────────┴──────────────────────────────────────────┐  │
│  │ LAYER 2 — Context Server (FastAPI MCP)  port :27180                      │  │
│  │  Tools: search_notes read_note search_okf get_concept log_decision      │  │
│  │         append_implement lookup_agent find_capability compress          │  │
│  │         search_tools load_tool_schema request_clarification             │  │
│  │         request_credentials acquire_lock request_snapshot delegate_task │  │
│  │  Backends: obsidian-local-rest-api · OKF · codebase-memory-mcp ·       │  │
│  │            headroom · OTel/Langfuse · lock+DAG · secrets bridge · DLP   │  │
│  │  Controls: transport identity · circuit breaker · OCC · rate-limit ·    │  │
│  │            chaperon · permission matrix · hibernation · crash-reconcile │  │
│  └─────────────────────────────▲──────────────────────────────────────────┘  │
│                                │ MCP (HTTP, signed token in header)          │
│  ┌─────────────────────────────┴──────────────────────────────────────────┐  │
│  │ LAYER 1 — Orchestrator + Registered Agents                              │  │
│  │   opencode CLI  (ORCHESTRATOR — owns the loop, calls delegate_task)    │  │
│  │      ├─ hermes        ├─ claude-code   ├─ antigravity   ├─ codex        │  │
│  │      └─ meta (Phase 8, Dream Cycle)                                    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                │
│  BRAINS:  Obsidian (D:\ObsidianVaults\Main Brain\) — served by MCP at :27124 │
│           OKF bundles — per-repo  */okf/   (git-tracked)                       │
└────────────────────────────────────────────────────────────────────────────────┘
```

Ports (locked): Obsidian MCP `27124`/`27123` (existing plugin), Context Server `27180`, Mission
Control `3000`, Langfuse `3001` (optional self-host), OTel collector `4317`.

---

## 3. Deltas from the parent plan (`opencode_glm_implementation_plan.md`)

| # | Parent plan said…                                    | This plan changes it to…                                                           | Why                                                                                  |
|---|------------------------------------------------------|------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|
| D1 | Phase 2.3 "Obsidian backend: read via ripgrep/Lucene, write via append to designated log.md" | Obsidian backend = thin proxy to `obsidian-local-rest-api` MCP. The 16 MCP tools are the read/write surface; the Context Server only adds *identity, lock, OCC, DLP, audit*. | Don't reimplement a working MCP plugin; inherit search/patch/periodic/tags free.    |
| D2 | Phase 5: generator code is the first "code" phase    | Generator still Phase 5, but the **Context Server** (Phase 2) is real code now too — it wraps an existing MCP. | With D1 the Context Server is mostly a FastAPI policy shell, not raw retrieval work. |
| D3 | "Shared HTTP MCP" was an Open Question (§6)          | **Resolved: shared HTTP MCP** at `http://127.0.0.1:27180/mcp/`. Every agent connects with a signed `X-Agent-Identity` token. | The orchestrator pattern (D4) requires a single rendezvous point; the frontend needs it too. |
| D4 | "any registered agent fits the task" (Phase 7.1)     | **opencode CLI is the orchestrator.** Other agents are dispatched only via `delegate_task`. | Removes the "who calls whom" ambiguity; preserves the registry (other agents can still be used standalone if a human launches them directly). |
| D5 | No frontend in the parent plan                        | **Phase 9 — Next.js Mission Control** is a first-class deliverable. Reads Context Server (MCP + REST `/dashboard/*`). | `prompts_necessary_context.md` §"Telemetry Dashboard" + community Kanban pattern requires it. |
| D6 | Token accounting is to `hooks/token_usage.db` only   | Same SQLite, **plus a live `/dashboard/tokens` websocket** for Mission Control. CAPO join happens in SQL views exposed at `/dashboard/capo`. | Mission Control token analytics needs push, not just daily rollup. |
| D7 | Sandbox = "E2B default, gVisor local fallback"        | On this Windows single-host dev box default is a **local containerized runner** (`Windows Sandbox`/WSL2_FIRECRACKER-equivalent) behind a `SandboxDriver` interface; E2B remains the documented remote path. | Local-first dev loop without a cloud dependency; interface keeps the original target swappable. |
| D8 | HITL `request_clarification` is CLI/webhook           | HITL is rendered in Mission Control's **diff-modal + clarification queue**; webhook remains the fallback. | WebClient community pattern (HITL Modal) + visibility. |

All other contracts (OKF v0.1, harness triad, lock+DAG, identity, breaker, OCC, rate-limit, DLP,
chaperon, drift, delta, hibernation, crash reconciliation, Dream Cycle, CAPO) are inherited
verbatim from the parent plan and only *operationalized* here.

---

## 4. The Obsidian bridge — `obsidian-local-rest-api` MCP as the primary-brain backend

The plugin (cloned at `tools/obsidian-local-rest-api/`, run inside the local Obsidian app) exposes
**16 MCP tools** at `https://127.0.0.1:27124/mcp/` (Bearer-auth). The Context Server does **not**
reimplement any of these — it proxies them through a backend adapter, layering policy on top.

### 4.1 Mapping parent-plan tools → obsidian-local-rest-api tools

| Context-Server tool (parent §2.2) | Backed by (obsidian-local-rest-api)              | Policy added by the Context Server                                                |
|------------------------------------|--------------------------------------------------|------------------------------------------------------------------------------------|
| `search_notes`                     | `search_simple` + `search_query` (JsonLogic)     | Identity-bound, DLP-redacted results, chaperoned if provenance=untrusted, rate-limited |
| `read_note`                        | `vault_read` (full or `targetType=target` slice) | OCC version hash attached; DLP scrub on return                                     |
| `log_decision` / `append_implement` (Obsidian targets) | `vault_append` to designated `log.md` headings   | Lock-lease required; OCC position-check for append-only; DLP on payload           |
| (Obsidian write promotion path)   | `vault_patch` (`targetType=frontmatter`/`heading`, `rejectIfContentPreexists=true`) | Idempotent retry guard; permission-matrix gated                                   |
| Daily-note standup (Phase 7.1)    | `periodic_note_get_path` → `vault_append`        | Same lock + DLP                                                                     |
| Tag-based capability discovery     | `tag_list` → joins registry/capabilities         | —                                                                                   |
| Open a review note in Obsidian UI  | `open_file`                                      | Triggered by Mission Control "open in Obsidian" button                             |

### 4.2 New `contracts/obsidian_backend.md` to ship in Phase 1

- Endpoint: `https://127.0.0.1:27124/mcp/` (HTTP fallback `http://127.0.0.1:27123/mcp/`).
- Auth: `Authorization: Bearer <OBSIDIAN_REST_API_KEY>` — key held by the secrets bridge
  (Phase 2.7), never in agent prompts. The Context Server's *own* Obsidian-backend client is the
  only consumer of this key.
- Direction rule (parent §0.3 inherited): **Obsidian → OKF is one-directional.** Agents never call
  `vault_write`/`vault_patch` against arbitrary human notes. The only Obsidian writes the Context
  Server proxies are: (a) to explicitly-designated agent-writable `log.md` headings, and (b) to
  the daily standup note's "Agent Updates" heading. Everything else is a permission-matrix
  **deny**.
- Out-of-bound human writes (typing in Obsidian) are seen by agents only via `vault_read` with OCC
  version hashes, so a mid-flight note edit by a human surfaces as a `state_changed` rejection on
  the next agent write (Phase 2.10), not a silent overwrite.

### 4.3 Important detail: `vault_patch`'s idempotency flag = our retry guard

`vault_patch` accepts `rejectIfContentPreexists: true`. The Context Server wraps every
`log_decision`/`append_implement` Obsidian-bound write with this flag so that a Phase 6.6 thaw
re-issue, a Phase 2.9 breaker retry, or a Phase 6.7 crash-reconciliation replay cannot double-append.
This piggybacks on a battle-tested plugin guard instead of inventing our own.

---

## 5. opencode CLI as the orchestrator

### 5.1 Why opencode holds the loop

- Native MCP HTTP client + subagent support — matches the parent plan's "shared HTTP MCP"
  decision (D3) and the `delegate_task` contract (Phase 3.3) without extra plumbing.
- Filesystem-first adapter (parent §3.2) — ideal for owning `PLAN.md`/`IMPLEMENT.md`/`okf/log.md`
  authorship which is the orchestration ledger.
- The Project Creation Prompt (§1) is itself an opencode prompt — zero translation loss between
  "plan the build" and "execute the build."

### 5.2 What "orchestrator" means concretely

- **opencode owns the top-level agent loop.** `Program.md`, `PLAN.md`, and the daily note drive
  what runs next.
- **Every other agent invocation goes through `delegate_task`.** No private subagent protocols for
  cross-agent work — parent plan Phase 3.3 already mandates this; opencode's native Task tool is
  used **only** for opencode-internal parallelism (e.g. two explore subagents), never to host
  another registered agent. Hosting another agent via the native Task tool is an audit failure.
- **opencode writes the audit trail.** It is the *only* agent allowed to write the project-level
  `IMPLEMENT.md` row that marks a delegated child's result as accepted (Phase 6.3 + Phase 7.4
  CAPO numerator). Other agents may *append* to it (via `append_implement`) but only the
  orchestrator's transport identity can flip a `gate: passed` row to `accepted: true`.
- **opencode is the front-line HITL receiver.** When a delegated child calls
  `request_clarification`, the Context Server pauses the child (Phase 6.6 hibernation) and routes
  the prompt to both opencode (so it can re-delegate or pre-answer) and Mission Control's
  clarification queue (so a human can answer).

### 5.3 Adapter flags specific to opencode (extends parent §3.2)

- `role: orchestrator` (only one agent may carry this tag).
- `native_subagent_protocol: opencode-subagents` — but **disallowed for cross-agent delegation**;
  cross-agent must use `delegate_task`.
- `cost_defaults.orchestrator_overlay`: orchestrator turns are budgeted at a *higher* `max_turns`
  than delegates (the orchestrator mostly routes, so it should rarely burn turns — when it does,
  it's doing reasoning the delegates should have done, a CAPO smell).

---

## 6. Next.js Mission Control (frontend at `frontend/`)

Single Next.js app (App Router, TypeScript, Tailwind, TanStack Query, WebSocket for live pushes).
Talks to the Context Server on two surfaces:

- **MCP-over-HTTP** at `/mcp/` for any sibling tool the UI itself needs (rare — e.g.
  `lookup_agent`, `search_tools`).
- **REST `/dashboard/*`** (added to the Context Server explicitly for the UI; thin SQL-to-JSON
  views over `token_usage.db` and `control_plane.db`, plus OTel/Langfuse query pass-throughs).

### 6.1 Top-level pages

| Route                          | Purpose                                                                                       | Backend                                     |
|--------------------------------|-----------------------------------------------------------------------------------------------|---------------------------------------------|
| `/` (Mission Control)          | Live system state: per-agent status, in-flight tasks (PLAN.md rows) with span counts, breaker/HITL/hibernation badges, recent `infrastructure_crash` feed, drift banners. | WebSocket `/dashboard/events` + REST `/dashboard/state` |
| `/kanban`                      | Jira-style board of every `PLAN.md` task across all projects; columns = Backlog / In-Progress / Delegated / Awaiting-HITL / Hibernated / Done-Rejected. Tickets carry CAPO, token-cost-so-far, owning agent avatar. | REST `/dashboard/plan` (parses PLAN.md rows + joins telemetry) |
| `/tokens`                      | Token analytics: heatmap of (agent × tool × task), top-N tasks by spend, "tokens-per-accepted-outcome" (CAPO) trend, rate-limit / breaker / DLP event counts. Time-range selector; export to CSV. | REST `/dashboard/tokens` + `/dashboard/capo` (SQL views over `token_usage.db`) |
| `/task/[id]`                   | Per-task deep view: OTel trajectory (Phase 2.5), span nesting, failure-class tags, compactor spans, chaperoned branches (collapsed macro-spans expandable), hibernation `thaw` span if any, lock-DAG edges if any. | REST `/dashboard/task/:id` (joins OTel exporter) |
| `/hitl`                        | Clarification queue: open `request_clarification` prompts, expand to a **diff-modal** for any pending write (preview the proposed Obsidian/vault/plan mutation, approve-modify-reject). | REST `/dashboard/hitl` + PATCH to resolve |
| `/crash`                       | Crash-reconciliation audit feed (Phase 6.7): reaped sandboxes, `released:crash_recovery` locks, `infrastructure_crash` spans, rolled-back tasks. One-click "re-run from snapshot." | REST `/dashboard/crashes` |
| `/agents`                      | Registry browser: `registry/agents/*.md` rendered as cards, capability matrix, adapter flags, cost_defaults. | REST `/dashboard/agents` (reads `registry/`) |
| `/vault` (Obsidian command center) | Read-only browser of `D:\ObsidianVaults\Main Brain\` via the same Obsidian backend (Phase 4); open-in-Obsidian buttons use `open_file`. Edit happens only through the `/hitl` modal. | Proxy to Obsidian MCP `vault_list`/`vault_read`/`search_query` |

### 6.2 Token analytics — what makes it "robust"

The `/tokens` page is the difference between "we have a token DB" and "we know what's going on."
Queries the parent plan calls for (Phase 7.3, Phase 7.4 CAPO) materialize as **live SQL views**:

```
-- per task
CREATE VIEW v_task_spend AS
SELECT task_id, agent, project,
       SUM(in_tokens)  AS in_tok,
       SUM(out_tokens) AS out_tok,
       SUM(cost_usd)  AS cost,
       COUNT(*)        AS tool_calls
FROM   token_usage
GROUP BY task_id, agent, project;

-- per (agent, tool, task) heat
CREATE VIEW v_heat AS
SELECT agent, tool, task_id,
       SUM(in_tokens+out_tokens) AS total_tok,
       COUNT(*) AS calls
FROM   token_usage
GROUP BY agent, tool, task_id;

-- CAPO numerator/denominator
CREATE VIEW v_capo AS
SELECT project,
       SUM(cost_usd) AS cost,
       SUM(CASE WHEN outcome='accepted' THEN 1 ELSE 0 END) AS accepted,
       SUM(CASE WHEN outcome='rejected' THEN 1 ELSE 0 END) AS rejected,
       ROUND(SUM(cost_usd) / NULLIF(SUM(CASE WHEN outcome='accepted' THEN 1 ELSE 0 END),0), 4) AS capo
FROM   task_outcomes JOIN token_usage USING (task_id)
GROUP BY project;
```

Frontend visualizations: stacked bar (agent × day), treemap (task share of spend), heatmap
(agent × tool × task, with breaker-trips overlaid as red dots), line chart (CAPO over time), and a
"Where did the tokens go?" drill-down that lists the top-N spans by `in_tokens+out_tokens` with a
link to `/task/[id]` at the exact span (`OpenTelemetry trace id → span id`).

The Mission Control listens on a WebSocket `/dashboard/events` that the Context Server publishes
to on every: token row insert, breaker trip, rate-limit refusal, DLP redaction, hibernation
freeze/thaw, crash-reconciliation event, drift flag flip. Push-notifications beat polling; the
page also degrades gracefully to a 5s poll if the socket is down.

### 6.3 HITL diff-modal (community pattern, parent §6.5)

When a `request_clarification` resolves a write, Mission Control renders the proposed mutation as a
monaco diff editor. For Obsidian writes this is the literal before/after markdown the Context
Server would have sent to `vault_append`/`vault_patch`. Approve → Context Server applies via the
Obsidian backend with `rejectIfContentPreexists=true` idempotency; modify → user edits the right
pane, Context Server re-runs OCC; reject → child task is marked `failed:hitl_reject` and per §7.4
counts toward CAPO's *rejected* denominator.

### 6.4 Auth model for the frontend

Mission Control authenticates to the Context Server with its own orchestrator-issued token (the
"ui" principal) — read-mostly, no mutate ability except HITL resolutions *signed by the human* (a
separate OIDC/local-PIN). Writes from the UI are dual-signed `(ui_principal, human_principal)` so
an attacker who steals the UI token cannot approve their own HITL queue.

---

## 7. Phase-by-phase delivery plan

Every phase below inherits the parent plan's Definition-of-Done verbatim and **adds** the deltas
specific to this build. "DoD +" marks the additions.

### Phase 0 — Foundations & contracts

Inherits parent §0.1–0.5 + D3 (HTTP MCP), D7 (sandbox driver interface).

- Add `contracts/obsidian_backend.md` per §4.2 here.
- Add `contracts/orchestration.md`: states opencode is the orchestrator (D4), explains the
  "no cross-agent native subagent" rule and the `accepted: true`-flip monopoly.
- Add `contracts/sandbox_driver.md`: a `SandboxDriver` interface (`spawn(bounds)→id`,
  `exec(id,cmd)→result`, `terminate(id)`, `snapshot(id)→path`) with two impls: `LocalRunner`
  (default on this host) and `E2BRunner` (documented; enabled by a flag).
- DoD +: GET `/health` on the Context Server returns 503 until Phase 2 ends (placeholder FastAPI).

### Phase 1 — Wire the two brains

Inherits parent §1.1–1.3 + D1 (Obsidian via MCP).

- The "first OKF bundle" (parent §1.2) **is the registry**; opencode is registered as the
  orchestrator with `role: orchestrator` (parent §3.2 is forward-referenced; we set the flag early
  here).
- Add `registry/adapters/obsidian-local-rest-api.md` (`type: ContextServerBackend`, `tags:
  [obsidian, mcp-http]`) recording the MCP URL, auth-via-secrets-bridge, and the
  enforce-direction rule (§4.2).
- DoD +: a smoke script calls the obsidian-local-rest-api `search_simple` from inside the Context
  Server's Obsidian-backend client (key from secrets bridge) and prints one hit from
  `D:\ObsidianVaults\Main Brain\`.

### Phase 2 — Context server

Inherits parent §2.1–2.13 plus these specifics.

- **Stack:** FastAPI + `mcp` Python SDK, one uvicorn process, port 27180.
- **Obsidian backend** = HTTP MCP client to `https://127.0.0.1:27124/mcp/`. Reuse the plugin's
  16 tools; do **not** add `search_notes`/`read_note`/`log_decision` logic of our own beyond
  identity/lock/OCC/DLP wrapping.
- **Lock+DAG backend (§2.6):** `control_plane.db` SQLite, append-only lock table, in-memory
  task-dependency DAG, O(V+E) cycle check on every `acquire_lock` and `delegate_task`.
- **Identity (§2.8):** HMAC-signed token (`HMAC(agent_id|task_id|lsn|exp_lsn)`), `X-Agent-Identity`
  header on HTTP. Lamport sequence numbers from a single primary-counter column in
  `control_plane.db`.
- **Breaker (§2.9), OCC (§2.10), rate-limit (§2.11), DLP (§2.12), chaperon (§2.13):** The
  respective middlewares on the same FastAPI app; each emits its failure-class tag into the OTel
  exporter and the SQLite span id ledger.
- **`/dashboard/*` REST namespace (D5):** read-only SQL views over `token_usage.db` and
  `control_plane.db` for Mission Control, plus a WebSocket `/dashboard/events` fanning out
  publishes from a small in-memory event bus.
- **`delegate_task` (Phase 3.3 forward-ref):** implemented now as a stub that records the
  child `PLAN.md` row and the OTel span nesting so Phase 3 only fills in the adapter dispatch.
- DoD +: every Phase 2 dry-run in the parent DoD runs against this concrete server, and a `curl`
  to `GET /dashboard/state` returns `{agents:[…], tasks:[…], stalls:[]}`.

### Phase 3 — Agent registry + adapters + delegate_task

Inherits parent §3.1–3.4.

- The five adapters (hermes, opencode, antigravity, claude-code, codex) get an **opencode
  orchestrator adapter** as the sixth, with the D4 flags in §5.3.
- `delegate_task` dispatch is implemented: the Context Server calls the `SandboxDriver.spawn`
  for the child, hands the child its own signed token, and the child connects back over the same
  HTTP MCP. opencode's "Task tool for cross-agent work is an audit-fail" rule is enforced by a
  static check in the registry (the `opencode.md` adapter carries a `forbid_native_cross_agent:
  true` flag surfaced to Mission Control's `/agents` page).
- DoD +: synthetic delegation `opencode → claude-code` shows, in Mission Control `/task/[id]`,
  nested OTel spans with the child principal's writes attributed to the child.

### Phase 4 — Per-project harness contract

Inherits parent §4.1–4.3 verbatim; the reference conformant project is **this repo itself**.

- The Obsidian→OKF export hook (§4.2) wraps the Obsidian MCP `vault_read` for the source side and
  writes OKF concept files via the project's own filesystem (not via the Obsidian backend). DLP
  (Phase 2.12) runs on **both** sides of this hook per parent §2.12 "Source-side sweep."
- DoD +: export hook is wired as a `before` git hook + an on-demand CLI in
  `hooks/obsidian_export.py` (Phase 5 builds it; Phase 4 only ships the contract).

### Phase 5 — Indexing + generation + compaction + drift + delta

Inherits parent §5.1–5.7.

- Graphify + codebase-memory-mcp run per project; the Context Server's graph backend is the
  codebase-memory-mcp itself (Phase 2.3 hybrid graph-vector store target ships as "vector added
  in Phase 8 Dream Cycle"; Phase 5 carries only graph + drift hooks).
- The generator (`scripts/generate_agent_configs.py`) emits each agent's native config from
  `registry/agents/*.md` + templates. **opencode's generated config includes the MCP HTTP URL and
  the `X-Agent-Identity` token bootstrapping.**
- DoD +: Mission Control `/agents` page shows "regenerate configs" → runs the generator → diff in
  the UI before commit (uses the `/hitl` diff-modal surface).

### Phase 6 — Verification + permissions + HITL + hibernation + crash reconciliation

Inherits parent §6.1–6.7 verbatim. The HITL interrupt endpoint is *also* the `/hitl` queue Mission
Control reads. Hibernation records live in `control_plane.db`; a `/dashboard/hibernated` view shows
frozen tasks with their `task_id`, age, and "max TTL countdown (7d)".

- DoD +: an end-to-end "long pause" demo — opencode delegates a task to codex, codex calls
  `request_clarification`, Mission Control shows the prompt in `/hitl`, the human waits 10 minutes
  (past lock TTL), then answers; the UI shows thaw → fresh sandbox → blocked-on-lock (because
  someone else grabbed it) → surfaced-banner → resume. All visible in `/task/[id]` as one
  replayable trajectory across the gap.

### Phase 7 — Daily ops + cost discipline + CAPO

Inherits parent §7.1–7.4.

- The daily standup note is read/written through the Obsidian MCP (`periodic_note_get_path` →
  `vault_append` under an "Agent Updates" heading). Agents' evening review writes are gated by
  the permission matrix to that one heading per daily note.
- Token DB lives at `hooks/token_usage.db`; CAPO denominator lives at `hooks/task_outcomes.db`
  (separate file so the append-only ledger can be optimized independently).
- DoD +: Mission Control `/tokens` shows a real week of data with the top-3 CAPO-winners and
  top-3 CAPO-losers highlighted.

### Phase 8 — Meta-harness + Dream Cycle

Inherits parent §8.1–8.3.

- `Program.md` at repo root specifies the optimization metric and editable-by-meta scope.
- `registry/agents/meta.md` is registered; the meta-agent has read access to
  `token_usage.db`/`task_outcomes.db` rollups and `IMPLEMENT.md`, but writes proposals only to a
  `okf/proposals/` folder that the human promotes.
- The Dream Cycle runs nightly (Phase 8.2.1) and surfaces its output into Mission Control
  `/kanban` as a special "Dream Cycle" column: proposed semantic-memory candidates on cards the
  human swipes right/left on (approve/reject), mirroring the community pattern from
  `prompts_necessary_context.md` §"Nightly Dream Cycles."
- DoD +: one night of Dream Cycle produces a candidate, Mission Control shows an
  `accepted`/`rejected` card, the accepted one is exported by Phase 4's hook into OKF.

### Phase 9 — Mission Control Next.js frontend (NEW)

**Goal:** ship the frontend as the human's daily home base once the backend has real telemetry
flowing (post-Phase 7).

- **Stack:** Next.js 15 App Router, TypeScript, Tailwind, shadcn/ui, TanStack Query, Zustand,
  monaco-editor (diff modal), VisX/D3 for OTel waterfall (or use `@opentelemetry/sdk-node`'s
  in-process exporter for the local-viewer mode).
- **Layout:** persistent left rail (Mission Control / Kanban / Tokens / HITL / Crashes / Agents /
  Vault / Settings), top bar with global status pill (live agents, open HITL count, day's spend).
- **Real-time:** single WebSocket `/dashboard/events`; Zustand store fans to components; falls back
  to 5s polling.
- **Auth:** local PIN + signed `(ui, human)` tokens; no remote auth needed for single-host.
- **Test:** Playwright e2e for every page; Vitest for components; Storybook only if the team
  grows past one person.
- **Accessibility + dark mode defaults** (this is the home base; it has to be stare-able).

DoD:

- [ ] Every page in §6.1 renders real (not mocked) data from the Context Server.
- [ ] A full task lifecycle — opaque to the human until they look — is visible end-to-end in
  `/task/[id]`: PALN row → spans → breaker trip → HITL clarif → hibernation freeze → thaw →
  verification gate → CAPO accepted.
- [ ] `/tokens` shows the SQL views in §6.2 live, with the time-range selector and CSV export.
- [ ] The `/hitl` diff-modal can approve, modify (with OCC re-run), and reject a pending Obsidian
  write, each visible in the OTel trace.
- [ ] The `/crash` page can one-click re-run a rolled-back task from its snapshot id.
- [ ] Playwright suite green; lighthouse accessibility ≥ 95.

---

## 8. Problem → Fix catalogue (every harness failure mode from the parent plan)

Each row: the *problem* cited in the parent plan, the *phase that fixes it*, the *mechanism* as
implemented in this build, and the *Mission Control surface* that makes it visible. This is the
single table to use when triaging "what broke and why does the system care."

| #  | Harness problem                                                                                     | Fixed at | Mechanism in this build                                                                                                                       | Mission Control surface                      |
|----|-----------------------------------------------------------------------------------------------------|----------|----------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
| P1 | Agents drift from contract (edit things they shouldn't)                                             | 2,6      | Permission matrix enforced server-side on the FastAPI app; Obsidian writes restricted to designated headings via the obsidian-local-rest-api proxy | `/agents` capability matrix; deny logged as `permission_denied` trace |
| P2 | Obsidian vault grows unbounded and bloats OKF export                                                | 1,4      | Export is opt-in per note (frontmatter flag); Inbox/Archive never exported; `/vault` page surfaces export-eligible notes by tag                | `/vault` "exportable" badge                  |
| P3 | Adapter generator clobbers hand-edits                                                              | 5        | Generator is idempotent + uses preserved regions; diffs reviewed in the `/hitl` modal before commit                                          | `/hitl` diff modal                           |
| P4 | New agent's config format incompatible                                                              | 3        | Adapter documents the mapping; unsupported until adapter is written; the orchestrator (opencode) refuses to `delegate_task` to unsupported agents | `/agents` "unsupported" pill                 |
| P5 | Hermes-style background token burn across all agents                                                | 7        | cost_defaults per adapter; token analytics page surfaces the burn as a top-N task; CAPO flags efficient-but-useless tasks                     | `/tokens` "idle spend" filter                |
| P6 | Meta-agent proposes bad defaults                                                                    | 8        | Meta-agent can only write proposals to `okf/proposals/`; human promotes via the Dream Cycle Kanban column                                     | `/kanban` Dream Cycle column                 |
| P7 | "When can this component be removed" never re-checked                                              | 0,8      | Quarterly audit scheduled in `Program.md`; checklist row enforced at merge; Mission Control surfaces overdue audits on `/`                      | `/` "audits overdue" banner                  |
| P8 | Concurrent writes corrupt shared state                                                              | 2,6      | Lock manager + DAG deadlock detector in `control_plane.db`                                                                                  | `/` contention feed                          |
| P9 | Agent stalls mid-task on ambiguity                                                                  | 2,6      | `request_clarification` HITL with hibernation (no compute burn during pause)                                                                 | `/hitl` queue                                |
| P10| Destructive op breaks workspace; no recovery                                                       | 6        | Auto-snapshot via SandboxDriver before `destructiveHint` tools; auto-rollback on failed gate; `/crash` can re-run from snapshot               | `/crash` re-run button                       |
| P11| Secrets leak via prompt injection/plaintext logs                                                    | 0,2,6    | Sandbox isolation + secrets bridge injects ephemeral creds into sandbox env only; raw keys never enter prompts                                 | `/` "secrets injected (N)" counter           |
| P12| OKF concepts go stale as code drifts                                                                | 1,5      | Drift detection re-tags `status: stale`; read-restricted banner via `get_concept`                                                              | `/<task>` drift banner; `/agents` "stale" badge |
| P13| Lethal trifecta (private data + untrusted content + exfiltration)                                   | 6        | Combinatorial matrix gated on instruction provenance, server-side                                                                            | `/hitl` "elevation required" prompt           |
| P14| Binary green/red gate misses regressions on non-deterministic agents                                | 6        | Two-tier gate: regression evals + LLM-as-judge rubric, both visible per task                                                                  | `/task/[id]` rubric score                     |
| P15| Token spend optimized without outcome signal (CAPO blind)                                          | 7,8      | CAPO = cost/accepted; meta-agent optimizes CAPO, not raw tokens                                                                               | `/tokens` CAPO charts                         |
| P16| Loss of original objective due to context rot                                                       | 5        | Proactive compactor with OTel `compaction` span; Mission Control shows what was lost                                                            | `/task/[id]` compactor spans                  |
| P17| Tool schemas bloat system prompt                                                                     | 2,5      | Progressive tool disclosure via `search_tools`/`load_tool_schema` only                                                                          | `/agents` loaded-tools count                 |
| P18| No trajectory visibility → cause is guesswork                                                       | 2        | OTel/Langfuse per tool call + task; failure-class tags                                                                                        | `/task/[id]` waterfall                        |
| P19| Agent spoofs another agent's identity in the payload                                                | 2,6      | Signed token in `X-Agent-Identity` header (transport binding); payload identity ignored; mismatch → `identity_spoof_attempt`                   | `/crash` spoof-attempt feed                   |
| P20| Tight logic loop (identical repeated calls) burns turns/spams server                                | 2,6,7    | Server-side circuit breaker on N identical `(tool, args-hash)`; auto HITL                                                                     | `/` breaker-trip alert                        |
| P21| Cross-agent delegation via native sub-agent protocols is invisible to the OS                        | 2,3,6    | `delegate_task` (the only allowed cross-agent path); opencode's native Task tool forbidden for cross-agent work (audit-fail)                  | `/task/[id]` nested spans                     |
| P22| Long HITL pause leaks compute / deadlocks / loses state                                             | 0.5,2.6,2.8,6 | Hibernation: freeze (serialize+release+revoke+terminate) → thaw (fresh sandbox+re-acquire+re-issue+hydrate) with stale-on-thaw drift re-check | `/hitl` "frozen" status; `/task/[id]` `thaw` span |
| P23| Lost update across turns despite holding write lock                                                | 2,6      | OCC: version hash on read; `expected_version` on write; `state_changed` rejection forces re-read; append-only uses position-check              | `/hitl` "stale, re-read" prompt                |
| P24| Agent bursts many distinct expensive calls (evades breaker)                                         | 2,7      | Token-bucket rate limiter + per-task compute quota with `429`/`Retry-After`; quota-exhaustion auto-hibernates                                  | `/tokens` rate-limited dots                   |
| P25| Secret/PII pasted into Obsidian or LLM-hallucinated, immortalized in traces/logs                    | 1,2,4    | DLP middleware redacts on read, write, and export hook; redaction events traced; secrets-bridge rotation alerts                               | `/` DLP counter; `/agents` rotation alert    |
| P26| Host crash leaves orphaned sandboxes/stuck locks/open spans/ghost tasks                              | 0.5,2.5,2.6,3.3,6 | Startup reconciliation hook: reap sandboxes, clear locks as `released:crash_recovery`, close spans as `infrastructure_crash`, finalize+rollback. Idempotent. | `/crash` feed; one-click re-run               |
| P27| Full re-index on every save bottlenecks at scale                                                    | 2.3,4,5  | Incremental delta indexing; full rebuild is a repair command; short lock windows                                                                | `/` indexer lock-window metric                |
| P28| Multi-agent lock cycle (dining-philosophers) stalls until TTL                                       | 2.6,3.3  | Server-side DAG deadlock detector refuses cyclic edges with `deadlock_risk` *before* the wait forms                                          | `/` contention feed (cycle path)             |
| P29| Wall-clock drift across hybrid sandboxes breaks span nesting + token expiry                        | 2.5,2.8  | Lamport logical sequence counters for span ordering + token expiry; wall-clock is hint-only                                                    | `/task/[id]` "Lamport" toggle                 |
| P30| Incremental vector injections shift centroids → silent context blindness                           | 2.3,5,8  | Embedding-Density-Variance monitor → `semantic_drift_detected`; async re-normalization in Dream Cycle window                                  | `/` drift banner; Dream Cycle re-norm card   |
| P31| Adversarial read loop from untrusted source blinds observability (denial-of-context)              | 2.5,2.9,2.11,6.2 | Read-edge chaperon: untrusted-provenance branch isolates telemetry, collapses to one macro-span with sampled args, compactor skips it, limiter trip auto-HITLs | `/task/[id]` "chaperoned branch" expandable   |
| P32 | opencode-specific failure: cross-agent delegation via native Task tool                              | 3 (this plan) | Static registry check on `opencode.md` adapter (`forbid_native_cross_agent: true`); Mission Control surfaces violations in `/agents` and the orchestrator audit log | `/agents` violation list                     |
| P33 | Mission Control itself being out of sync with backend state                                          | 9 (this plan) | Single source of truth = Context Server; UI uses MCP+`/dashboard` only; no second backend; WebSocket push for realtime | n/a (this *is* the surface)                  |

---

## 9. End-to-end scenarios (acceptance flows)

These are the proof-of-concepts the parent plan calls "dry runs," re-cast as user-visible Mission
Control scenarios. Each one is a demo you can show.

### S1 — Delegated research, clean handoff

opencode receives "research the OKF spec and propose an adapter." It calls `delegate_task` to
claude-code with narrowed bindings. `/kanban` shows a "Delegated" ticket with a live "child
spans: 0" counter. claude-code calls `search_okf`, `lookup_agent`, `get_concept` (all visible in
`/task/[id]` as nested spans). Verification gate passes. The card flips to "Done". CAPO: cost
$0.07, accepted=1, capo=$0.07.

### S2 — Circuit breaker + HITL

claude-code loops on `search_notes` with the same failing query three times. On the 3rd, the
server returns `circuit_breaker_tripped`. `/` shows a red breaker toast, `/hitl` displays a
clarification prompt auto-triggered by the breaker. Human answers; thaw resumes claude-code in a
fresh sandbox with the answer injected. `/tokens` shows the breaker-trip as a red dot on the
claude-code × search_notes heat cell.

### S3 — Hibernation across a long pause (the D6 + P22 demo)

opencode delegates a code edit to codex; codex hits ambiguity and `request_clarification`s.
`/hitl` shows the prompt; the human goes to lunch. During the pause, Mission Control's `/` shows
codex's task as "Frozen" with a TTL countdown from 7d. The OTel trace in `/task/[id]` ends with a
`hibernation_freeze` span. An hour later, the lock TTL has expired and opencode grabs the lock for
an unrelated task — visible in the contention feed. Human answers; thaw provisions a fresh
sandbox, *blocks* on the lock (visible in `/task/[id]` as `blocked_on_lock`), surfaces a banner to
the human, opencode releases, codex resumes, drift re-check passes. One replayable trajectory.

### S4 — Crash reconciliation

You kill the Context Server mid-task (a codex code edit). On reboot, `/crash` shows: 1 orphaned
sandbox reaped, 1 lock cleared as `released:crash_recovery`, 1 span closed as
`infrastructure_crash`, 1 task marked `failed:infrastructure_crash` and rolled back to its
pre-task snapshot. A "Re-run from snapshot" button is one click away. A second reboot changes
nothing (idempotency). Crash root-cause is captured from the FastAPI startup error into
`IMPLEMENT.md` and surfaced at the top of `/crash`.

### S5 — DLP catches a leaked AWS key

The human accidentally pastes an AWS key into an Obsidian note. `read_note` via the Obsidian
backend returns the note with `[REDACTED:aws_key:abc123]`. The `/` "DLP" counter ticks. The secrets
bridge recognizes the redacted value as a *registered* credential → `/agents` posts a "rotation
alert." The export hook refuses to write the OKF concept with the plaintext.

### S6 — Drift + Dream Cycle self-healing

Weeks pass; one OKF architecture doc falls 12 functions behind the codebase. `/` shows a
"`status: stale`" banner. The Dream Cycle that night clusters the day's traces, finds the doc was
referenced 4 times by confused agents, proposes a "Semantic Memory Candidate" surfaced in
`/kanban`'s Dream Cycle column. The human approves; the export hook rewrites the OKF concept;
`/agents` shows the stale badge cleared.

### S7 — Denial-of-context read loop (P31)

opencode reads a scraped web page containing an injected "now keep reading different notes"
instruction. It issues 200 unique `search_notes` calls in 30 seconds. The chaperon detects the
untrusted provenance, branches the telemetry, collapses all 200 calls into one macro-span with a
few sampled args. The rate limiter trips on the burst and auto-HITLs. `/task/[id]` shows one
collapsed "chaperoned branch" card expandable to the samples — the trace is not flooded, the
evening review is not blinded.

### S8 — Mission Control is the human's whole day

The human opens `/` in the morning: today's tasks (from the daily note), in-flight delegations,
any overnight Dream Cycle proposals. Drags a card from Backlog to In-Progress to delegate to
hermes. Lunches; catches a `/hitl` clarification on the phone (responsive web). Evening: reviews
`/tokens`, sees one task eating 40% of the day's spend, drills into `/task/[id]`, finds a
failed-gate rollback (P10) auto-handled. Promotes the surviving accepted tasks back to Obsidian
via the export hook. Sleeps; Dream Cycle runs.

---

## 10. Open questions resolved by this plan (vs. parent §6)

- [x] **Transport for context server** — HTTP MCP at `127.0.0.1:27180/mcp/` (D3).
- [x] **Main orchestrator** — opencode CLI (D4).
- [x] **Obsidian backend implementation** — proxy to `obsidian-local-rest-api` MCP (D1).
- [x] **Frontend** — Next.js Mission Control (D5, Phase 9).
- [x] **HITL UX** — Mission Control `/hitl` modal + CLI/webhook fallback (D8).

Still open (inherited verbatim from parent §6): lock manager backing store once multi-host;
secrets store keychain vs cloud SM; drift threshold tuning; identity-token signing-key custody
(suggested: single shared HMAC now; per-agent asymmetric when multi-host); circuit-breaker N
defaults (start 3/60s); delegation recursion cap (start 3); hibernation record store; OCC
hash source boundary; rate-limit per-tool cost weights; DLP pattern custody; crash root-cause
sources per sandbox tech; delta-indexing degradation threshold; DAG cycle-detection strategy;
Lamport bootstrap (single primary now; failover-re-sync via Phase 6.7); embedding-density
threshold; chaperon macro-span sample retention. **Resolve each at the phase named in the parent
plan, not earlier.**

---

## 11. First action (right now)

1. Paste the Project Creation Prompt (§1) into opencode CLI at the repo root.
2. opencode creates `IMPLEMENT.md`, appends "Approved Agentic OS project architecture v1", and
   starts Phase 0.
3. Confirm the obsidian-local-rest-api plugin is running in your local Obsidian (Settings → Local
   REST API shows the API key). Save the key into the secrets bridge under service id
   `obsidian-rest-api` so the Context Server's Obsidian backend can read it (do **not** write it
   anywhere in this repo).
4. `cd frontend && npm create next-app@latest .` to scaffold Phase 9's empty shell, then leave it
   stubbed until Phase 7 ships telemetry.

---

*Architecture version: 1.0 — derives from `opencode_glm_implementation_plan.md` (v1.4),
`prompts_necessary_context.md` community patterns, and the `obsidian-local-rest-api` MCP tool
surface (16 tools over HTTP at `127.0.0.1:27124/mcp/`). Adds: D1 Obsidian backend proxy, D3 HTTP
MCP, D4 opencode orchestrator, D5/D8 Mission Control frontend, D6 token analytics, D7 local
sandbox driver. Phase 9 is the new frontend phase; every other phase inherits its parent-plan
Definition-of-Done verbatim plus the "DoD +" rows in §7.*