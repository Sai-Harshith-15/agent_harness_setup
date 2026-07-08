# Agentic OS — Harness Implementation Plan

> Single source of truth for building a unified "Agentic OS" harness that lets multiple AI agents
> (Hermes, opencode, antigravity, Claude Code, Codex, …) share ONE memory and ONE context layer.
>
> This document is a **plan only**. It describes what to build, in what order, and why.
> It is not a project roadmap for the apps you will later build *on top* of this harness —
> it is the harness itself. Every later project and day-to-day task inherits from this layer.

---

## 0. Purpose and North Star

### 0.1 What we are actually building

We are building the **scaffolding around the model**, not the model, and not the apps.
Per the harness-engineering discipline (referenced in
`tools/awesome-harness-engineering/README.md` and `ai_agent_harness_engineering.md`), a harness
has exactly four necessary and sufficient elements:

1. **Agent loop** — the reason/act/observe cycle.
2. **Tool interface** — how the agent touches the world (MCP, skills, shell).
3. **Context management** — what the agent knows right now (curated, compacted).
4. **Control mechanisms** — permissions, verification, sandboxing.

The Agentic OS is the **shared layer underneath all four** that lets many agents reuse the same
memory and context pipeline. The agents themselves keep their own loops, tools, and controls as
they ship — but the memory + context they read from and write to is the **same** across all of them.

### 0.2 North Star (one sentence)

> Any agent I add to my OS reads from the same two brains (Obsidian primary, OKF secondary),
> writes back to the same brains through a single context server, and is governed by the same
> harness templates — so adding a new agent is a *registration* step, not a *re-architecture*
> step.

### 0.3 Non-goals (explicitly excluded)

- We are NOT building a new agent framework. We reuse opencode/hermes/antigravity/claude-code/codex
  as they are.
- We are NOT replacing Obsidian with a database. Obsidian is the human authoring surface and stays
  the primary brain.
- We are NOT locking memory to one agent's session format. Per-session state stays per-agent;
  only the *shared* knowledge surface is unified.
- We are NOT writing agent application code in this plan. Downstream projects live on top of this
  harness; this plan earns the right to those projects by being stable first.

---

## 1. Architecture Overview

### 1.1 The Two-Brain Model

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AGENTIC OS (the harness)                         │
│                                                                         │
│   ┌────────────────┐         ┌────────────────┐                        │
│   │  PRIMARY BRAIN  │         │  SECONDARY BRAIN│                       │
│   │   (authoring)   │         │  (structuring)  │                       │
│   │                 │         │                  │                       │
│   │ D:\ObsidianVaults\Main Brain\ │  OKF bundles │                        │
│   │  - human markdown │        │  - per-repo, git-tracked, yaml+md      │
│   │  - PARA folders    │        │  - agent-parseable, near-zero waste   │
│   └────────┬────────┘         └─────────┬────────┘                       │
│            │                              │                              │
│            └──────────────┬──────────────┘                              │
│                           │                                              │
│                           ▼                                              │
│              ┌───────────────────────────┐                               │
│              │   CONTEXT SERVER (MCP)    │  ← single delivery surface     │
│              │  search_notes, read_note │                               │
│              │  search_okf, get_concept │                               │
│              │  log_decision, append_log│                               │
│              └─────────────┬─────────────┘                               │
│                            │                                             │
│   ┌────────────────────────┼────────────────────────┐                   │
│   │      AGENT REGISTRY + ADAPTERS                 │                    │
│   │  hermes  opencode  antigravity  claude  codex  │                    │
│   └────────────────────────┬────────────────────────┘                   │
│                            │                                             │
│                            ▼                                             │
│              ┌───────────────────────────┐                               │
│              │   PROJECTS & DAILY TASKS   │  ← the layer you build on    │
│              └───────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 The Four Subsystems

| Subsystem         | Lives in                                                       | Role                                                                                |
|-------------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------|
| **Primary Brain** | `D:\ObsidianVaults\Main Brain\`                                | Human-authored notes: ideas, decisions, daily logs, project specs. PARA structure.  |
| **Secondary Brain** | `*/okf/` inside each project repo                             | Structured, agent-parseable bundles generated from Obsidian; lives next to code.    |
| **Context Server** | A single MCP server (FastAPI)                                  | The ONLY surface agents use to pull context. Translate "what I need" → "where it is".|
| **Agent Registry** | `D:\GitRepo\agent_harness_setup\registry\` (an OKF bundle itself) | One entry per agent. Each entry says: config path, adapter type, memory bindings.     |

### 1.3 Memory Tiers (mapped to the discipline)

From `ai_agent_harness_engineering.md` §3 the discipline defines three tiers. We bind each tier
to a concrete artifact in this OS:

| Tier        | Purpose                         | Implementation in this OS                                                |
|-------------|---------------------------------|---------------------------------------------------------------------------|
| **Episodic** | Short-term session history      | Lives inside each agent's own session store (Hermes DB, opencode `.opencode/`, `.claude/`). NOT unified — by design. |
| **Semantic** | Long-term facts + relationships | OKF bundles per project + Graphify/codebase-memory-mcp knowledge graph. UNIFIED. |
| **Procedural** | "How-to" + conventions        | Per-repo `AGENTS.md` (from the harness template) + Obsidian `40 Knowledge/`. UNIFIED. |

The Agentic OS unifies **semantic + procedural** memory. Episodic stays per-agent on purpose,
because that is the layer where each agent's loop implementation differs.

---

## 2. Inventory — What We Already Have

Before adding anything, audit what already exists so we build *on top of* it.

### 2.1 Already present (do not rebuild)

- **Obsidian vault** at `D:\ObsidianVaults\Main Brain\` with PARA folders:
  - `00 Inbox`, `10 Daily`, `20 Projects`, `30 Areas`, `40 Knowledge`,
    `50 Meetings`, `90 Archive`, `99 Templates`, `Attachments`, `Home.md`
- **`obsidianData`** sync/data folder at `D:\obsidianData` (sits outside the vault; used for vault
  sync config / git backing / plugin data). Treat this as *vault plumbing*, not as a knowledge surface.
- **Google OKF spec + reference agent** at
  `tools/knowledge-catalog/` (spec: `okf/SPEC.md`, reference agent code under
  `okf/src/reference_agent/`, sample bundles under `okf/bundles/{ga4,stackoverflow,crypto_bitcoin}`).
- **Harness engineering templates** at `tools/awesome-harness-engineering/templates/`:
  - `AGENTS.md` — repo-level agent instructions (procedural memory template)
  - `HARNESS_CHECKLIST.md` — pre-ship harness review checklist
  - `PLAN.md` — task planning artifact
  - `IMPLEMENT.md` — append-only implementation log
- **Indexed knowledge graph** of this repo in codebase-memory-mcp
  (1,684 nodes / 3,173 edges) — searchable for cross-references.
- **headroom** compression layer (MCP) available for token reduction of bulky tool outputs.
- **Source knowledge docs** in repo root:
  - `ai_agent_harness_engineering.md` — the discipline overview
  - `project_level_ai_harness.txt` — the three-stage pipeline we mirror
  - `okf_knowledge_data.md` — OKF description + project-level setup guide
  - `hermes_agent_cost_reduce_youtube_content.txt` — cost-control settings (informs Phase 7)

### 2.2 Gaps (this plan fills these)

- No defined contract between Obsidian notes and OKF bundles.
- No single context server; no MCP exposing the two brains.
- No agent registry; each agent is configured ad-hoc.
- No per-project OKF scaffold that downstream repos inherit.
- No verification loop (no checklist run before any agent ships work).
- No meta-harness (no `Program.md` directive for the OS to improve itself).

---

## 3. Phase Plan

Phases are sequential by default. Each phase has a **Definition of Done** (DoD) so you can stop
and verify before moving on. Every phase ends with an `AGENTS.md`/`log.md` update so future agents
inherit the state.

---

### Phase 0 — Foundations & Contracts (no code, decisions only)

**Goal:** Decide the contracts everything else depends on. Get these wrong and every later phase
pays for it.

#### 0.1 Adopt OKF v0.1 as the on-disk contract for shared knowledge

- Use the spec at `tools/knowledge-catalog/okf/SPEC.md` verbatim.
- Only **required** frontmatter field is `type`. Recommended: `title`, `description`,
  `resource`, `tags`, `timestamp`.
- Reserved filenames: `index.md` (directory listing for progressive disclosure),
  `log.md` (append-only update ledger).
- Cross-links: prefer **bundle-relative absolute** links (`/tables/users.md`) over relative.
- Permissive consumer rule: never reject a bundle for missing optional fields or unknown types.

**Why this matters:** OKF is the lowest-common-denominator format every agent can read with zero
SDK. Picking it now means agent adapters downstream only need a markdown reader.

#### 0.2 Define the three-document harness triad per repo

Every project under the OS will carry three machine-readable governance docs at its root,
generated from the templates already in `tools/awesome-harness-engineering/templates/`:

| File              | Source template                          | Role                                          |
|-------------------|------------------------------------------|-----------------------------------------------|
| `AGENTS.md`       | `templates/AGENTS.md`                    | Procedural memory: how to behave in this repo. |
| `PLAN.md`         | `templates/PLAN.md`                      | Active plan: task, milestones, scope, risks.  |
| `IMPLEMENT.md`    | `templates/IMPLEMENT.md`                 | Append-only log: decisions, deviations, open Qs. |

A `HARNESS_CHECKLIST.md` ships once per repo and is re-run before merges.

#### 0.3 Define the Obsidian → OKF direction

- **One direction only:** Obsidian is the human authoring surface; OKF is the agent-consumption
  surface. Agents write back to Obsidian only via a *write_log* tool through the context server,
  never by editing arbitrary notes. This keeps humans the source of truth for prose and agents the
  source of truth for structured facts.
- The bridge is a **pre-commit hook / pipeline script** (one per repo) that exports specific
  Obsidian notes into OKF concept documents (see Phase 2).

#### 0.4 Decide the directory of the Agentic OS itself

The OS lives in **this repo**: `D:\GitRepo\agent_harness_setup\`. Its substructure (to be created
in later phases):

```
D:\GitRepo\agent_harness_setup\
├── ai_agent_harness_engineering.md         # reference (existing)
├── okf_knowledge_data.md                   # reference (existing)
├── project_level_ai_harness.txt            # reference (existing)
├── hermes_agent_cost_reduce_youtube_content.txt  # reference (existing)
├── opencode_glm_implementation_plan.md     # THIS file
├── tools\                                  # cloned third-party (gitignored)
│   ├── awesome-harness-engineering\
│   └── knowledge-catalog\
├── registry\                              # NEW — the agent registry (an OKF bundle itself)
├── contracts\                             # NEW — shared schemas / contracts
├── hooks\                                  # NEW — Obsidian→OKF export + harness verification
├── adapters\                              # NEW — per-agent adapters (templates, not code)

```

#### 0.5 Define the compute plane (sandbox technology)

The plan's control-plane (memory, registry, context server) is well-specified, but the *compute
plane* — where tools actually execute — must also be defined up front so isolation is a contract,
not a bolt-on.

- **Tool execution happens in an ephemeral, resource-capped sandbox**, not in the host shell.
- **Chosen technology (decision):** E2B-style Firecracker microVMs as the default; gVisor/Kata
  Containers as an acceptable local fallback. The exact pick is finalized in Phase 0, but the
  *requirement* (kernel-level isolation, no workspace escape, no PII leakage to host) is fixed now.
- **Resource caps:** per-tool CPU / wall-clock / memory / egress limits, derived from the task's
  `bounds` field in `PLAN.md`.
- **Lifecycle:** a sandbox is spawned per task (or per destructive tool call, see Phase 6.4), torn
  down at task end. No long-lived state escapes the sandbox except via the context-server write tools.

**Why this matters:** an agent that runs shell tools directly on the host can exfiltrate secrets or
corrupt the workspace. Fixing the sandbox contract in Phase 0 means every later phase's permission
and rollback logic (Phase 6) has a guaranteed isolation baseline to build on.

**Definition of Done (Phase 0):**
- [ ] Decision log entry in `D:\GitRepo\agent_harness_setup\IMPLEMENT.md` (create the file) recording
  the decisions above (0.1–0.5) with rationale and rejections considered.
- [ ] `AGENTS.md` created at repo root using the template, customized for this OS repo.
- [ ] Confirm `D:\obsidianData` role is documented (vault plumbing, not a knowledge layer).
- [ ] `contracts/compute_plane.md` records the sandbox technology choice + resource-cap defaults.

---

### Phase 1 — Wire the Two Brains

**Goal:** Obsidian stays the primary brain untouched; OKF becomes the secondary brain by creating
the *first* OKF bundle inside this OS repo. No agents touch either brain yet — that's Phase 2.

#### 1.1 Stabilize the Obsidian primary brain

- **Do not** restructure existing PARA folders. PARA is the contract.
- Define the canonical mapping from PARA folders to OKF concept types (informational — used by the
  Phase 2 export hook):

  | Obsidian path                       | Maps to OKF `type`   | Notes                              |
  |-------------------------------------|----------------------|------------------------------------|
  | `20 Projects\<project>\`            | `Project`            | One OKF bundle per project.        |
  | `30 Areas\<area>\`                  | `Area`               | Long-lived responsibility.         |
  | `40 Knowledge\<topic>\`            | `Reference`          | Reusable concept / how-to.         |
  | `50 Meetings\<date>-<topic>.md`     | `Meeting`            | Datetime-stamped, decisions log.   |
  | `10 Daily\<date>.md`               | `DailyLog`           | Index-only; rarely promoted.       |
  | `00 Inbox\`                         | _(not exported)_    | Raw capture; human-triaged later.  |
  | `90 Archive\`                       | _(not exported)_    | Frozen.                            |

- Document this mapping in `D:\GitRepo\agent_harness_setup\contracts\obsidian_to_okf.md`
  (an OKF `Reference` document accordingly).

#### 1.2 Create the first OKF bundle — the OS registry bundle

Treat the agent registry itself as an OKF bundle so it bootstraps its own contract.
Create `D:\GitRepo\agent_harness_setup\registry\` as an OKF bundle:

```
registry\
├── index.md                # bundle root index, lists registered agents
├── log.md                  # every agent add/remove/update is recorded here
├── agents\
│   ├── index.md
│   ├── hermes.md           # type: Agent; config path, adapter, memory bindings
│   ├── opencode.md
│   ├── antigravity.md
│   ├── claude-code.md
│   └── codex.md
├── adapters\
│   ├── index.md
│   └── <adapter-name>.md   # one per adapter type (see Phase 3)
└── capabilities\
    ├── index.md
    └── <capability>.md      # e.g. browser, shell, filesystem, mcp, repo-edit
```

Each `agents/<name>.md` carries at minimum:
- `type: Agent`
- `title:` display name
- `description:` one-sentence role
- `tags:` capabilities this agent provides
- body: config path, how its `AGENTS.md` is generated, which memory tiers it reads/writes,
  the **removal condition** from the harness-discipline template
  ("when can this component be removed?" — see HARNESS_CHECKLIST §"When this harness component
  should be removed").

**This is the mechanism that answers your "if an agent is added it reflects in the OS":**
adding/removing/updating an agent = creating/editing/archiving one OKF concept file + appending
to `registry/log.md`. The registry IS the OS's source of truth.

#### 1.3 Initialize `log.md` on registry

`registry/log.md` is the OS's audit ledger. First entry records the bundle creation and the
five initial agents registered conceptually (hermes, opencode, antigravity, claude-code, codex).
ISO-8601 `YYYY-MM-DD` headings, newest first.

**Definition of Done (Phase 1):**
- [ ] `contracts/obsidian_to_okf.md` exists and explains the PARA → OKF type mapping.
- [ ] `registry/index.md` and `registry/agents/index.md` exist and validate as OKF.
- [ ] At least two `registry/agents/*.md` concept files exist (hermes + opencode)
  as worked examples; the rest are stubs.
- [ ] `registry/log.md` has its first entry.
- [ ] Obsidian vault structure is unchanged (verified by `ls` of PARA folders).

---

### Phase 2 — Context Server (the single delivery surface)

**Goal:** Build the ONE place agents go to ask "what do I need to know?" and to write back
"here's what I decided." Everything in later phases assumes this exists.

#### 2.1 Choose the server shape

- A single **MCP server** (FastAPI, stdio or HTTP, configured once and shared by every agent
  that supports MCP — which is all five target agents today).
- The server is itself a registered component in `registry/adapters/` (an
  `adapter` OKF concept with `type: ContextServer`).
- Hosts the Graphify + codebase-memory-mcp + headroom integrations as *backends*, not as separate
  exposed surfaces. Agents see one set of tools, not three.

#### 2.2 Tool surface (the contract)

The server exposes a deliberately small tool set. Each tool is named so an agent can pick it
without ambiguity (per the writing-effective-tools principle from the harness README):

| Tool                | Reads                                  | Writes                                   |
|---------------------|----------------------------------------|------------------------------------------|
| `search_notes`      | Obsidian via ripgrep / Lucene          | —                                        |
| `read_note`         | one Obsidian `.md`                     | —                                        |
| `search_okf`        | OKF bundles (frontmatter + body)       | —                                        |
| `get_concept`       | one OKF concept by concept-id          | —                                        |
| `log_decision`      | —                                      | appends to a target `log.md`             |
| `append_implement`  | —                                      | appends to a target `IMPLEMENT.md`      |
| `lookup_agent`      | `registry/agents/*`                    | —                                        |
| `find_capability`   | `registry/capabilities/*`              | —                                        |
| `compress`          | — (delegates to headroom)              | returns compressed blob + hash           |
| `search_tools`      | `registry/capabilities/*` + project tool catalog | —                              |
| `load_tool_schema` | one capability by id                   | returns full schema on demand            |
| `request_clarification` | —                                | pauses loop, serializes state, pushes HITL prompt |
| `request_credentials` | service registry (e.g. "AWS","GitHub") | injects scoped ephemeral creds into sandbox env |
| `acquire_lock`      | lock manager state                     | takes a lease on a resource path (file/domain) |
| `request_snapshot`  | workspace VCS / filesystem             | creates a named restore point before destructive ops |
| `delegate_task`     | registry/agents + PLAN.md              | spawns a child task under another agent; child spans nest under caller's OTel trace (Phase 3.3) |

Design rules (from harness-discipline guidance):
- **Progressive tool disclosure:** the full tool set is *not* loaded into the system prompt. The
  agent starts with only `search_tools`; it loads a concrete tool's schema via `load_tool_schema`
  only when strategically relevant. This prevents context bloat at the source, not just after the
  fact via `compress` (see also Phase 5.4 compaction).
- Two retrieval tools (`search_notes` + `search_okf`) not one, because human-prose and
  structured-fact retrieval have different relevance profiles.
- Every write tool accepts a structured payload, not free text, so writes are deterministic and
  auditable.
- Tools carry **annotations** (`readOnlyHint`, `destructiveHint`) per MCP guidance; the harness
  uses them for permission decisions in Phase 6.
- `compress` is exposed so agents can hand off large outputs (logs, file dumps) to headroom
  themselves, avoiding context bloat — directly addressing the Hermes-cost learnings in
  `hermes_agent_cost_reduce_youtube_content.txt`.

#### 2.3 Backends (pluggable)

- **Obsidian backend**: read from `D:\ObsidianVaults\Main Brain\`; never write prose, only append
  to `log.md`-style ledgers the human has explicitly designated as agent-writable.
- **OKF backend**: read from every registered `*/okf/` bundle (paths discovered from
  `registry/agents/<agent>.md`'s `bindings` field).
- **Graph backend**: codebase-memory-mcp, refreshed per project via `index_repository`. Future
  evolution: turn this into a **hybrid graph-vector store** so recall works by both semantic
  similarity (vector) and structured traversal (graph) — i.e. the codebase graph captures the
  relationships *between Obsidian notes and project code*, not just code-internal edges. This
  lifts retrieval accuracy above flat-markdown lookup and is the substrate OKF concepts (Phase 5.1)
  hang off of.
- **Compression + compaction backend**: headroom for reactive compression; a separate compactor
  handles proactive history compaction (see Phase 5.4).
- **Observability backend**: OTel/Langfuse exporter for trajectory tracing (see Phase 2.5).
- **Lock backend**: an internal lease table (see Phase 2.6).
- **Secrets backend**: pluggable secret stores (OS keychain / vault / cloud SM) fronted by one
  `request_credentials` tool (see Phase 2.7).

#### 2.4 Identity propagation

Per the MCP design-patterns note in the harness README, every tool call carries the calling
agent's identity (registered name) and the current task id. The server refuses writes that don't
match an allowed `(agent, target)` pair from the registry. This is the first control mechanism
in the harness — see Phase 6 for the full permission layer.

#### 2.5 Observability layer (trajectory-level tracing)

A production harness must let you audit and replay every reasoning step and tool call, not just
account for cost. Beyond the Phase 7 token ledger, the context server emits structured traces:

- **OTel/Langfuse instrumentation** on every tool call: span per call with `(agent, task_id,
  tool, args-hash, in_tokens, out_tokens, latency, status)`, parent span per task. This correlates
  agent decisions with system events (DB pressure, sandbox lifecycle) — essential for debugging
  deep agents that span hundreds of steps.
- **Failure classification hook:** when a tool call or verification fails, the trace is tagged
  `context` / `constraint` / `planning` so root-cause is not guesswork. This feeds the Phase 8
  meta-agent and Dream Cycle.
- **Retention:** raw spans kept N days; rollups to `registry/log.md` per Phase 7 cadence.
- **Logical sequence counters (clock-drift neutralization).** In hybrid environments (claude-code
  in a remote E2B microVM, opencode local on the host), wall-clocks inevitably drift — even 200ms
  desync breaks span nesting (child spans appearing to finish before they start, negative
  latencies) and corrupts Phase 2.8 token-expiry checks during a Phase 6.6 thaw. The Context
  Server therefore **decouples telemetry and ordering from the host wall-clock**: every span and
  every identity-token baggage header carries a **monotonically increasing logical sequence
  number** (Lamport timestamp) issued strictly by the primary server process. Spans are ordered
  and nested by logical sequence position, not `end_at`/`start_at` timestamps; wall-clock values
  are kept only as human-readable hints. This keeps multi-sandbox trajectories coherent
  regardless of clock skew.

This is what turns "the agent failed" into "the agent failed because step 14 loaded a stale OKF
concept" — the same diagnosis loop the harness discipline calls trajectory-level observability.

#### 2.6 Distributed lock manager (concurrency safety)

The OS allows multiple agents (primary + background sub-agents) to coexist. Without mutual
exclusion on the Secondary Brain and project files, concurrent writes to `IMPLEMENT.md`,
`okf/log.md`, or the same source file produce race conditions and git conflicts.

- The context server hosts a **lock manager**. Any write tool (`log_decision`,
  `append_implement`, `acquire_lock`-gated file edits) calls `acquire_lock(resource_path)` first
  and receives a **time-bounded lease** (default TTL e.g. 120s, renewable). Writes without a live
  lease are refused.
- Locks are keyed by `(agent, resource_path, task_id)` so an agent's failure releases stale
  leases on TTL expiry (no permanent deadlock).
- **DAG deadlock detector (cyclic-wait prevention).** Every `acquire_lock` request *and* every
  Phase 3.3 `delegate_task` instantiation is recorded as a directed edge in a server-side
  **task-dependency DAG**: an edge `T_holder → T_requester` means "task T_requester is blocked
  waiting for a resource held by T_holder" (delegation edges: parent → child). Before granting a
  lease, the server checks whether the new edge would create a *cycle*. If it would, the lease is
  **instantly refused** with a `deadlock_risk` exception (carrying the would-be cycle path) — the
  requesting agent must then yield its current locks, abort, or enter Phase 6.6 hibernation, rather
  than stalling the loop. This matters because Phase 3.3 delegation across multiple agents turns
  the lock table into a multi-agent dining-philosophers graph; the 120s TTL would eventually break
  a real deadlock, but a 2-minute full lockup breaks real-time execution and silently inflates CAPO
  (Phase 7.4) via useless retry spend. The DAG rejects the cycle *before* the wait begins, so no
  stall ever forms. Cycle-detection is O(V+E) per request against a graph bounded by live tasks,
  so it is cheap relative to the cost of a deadlock.
- The lock table itself is append-only and logged, so contention (and any refused `deadlock_risk`
  edges) is visible in the Phase 2.5 trace.

#### 2.7 Secrets manager bridge (credential injection)

Agents need to authenticate to external services, but raw API keys must never sit in agent-readable
context (prompt injection could exfiltrate them).

- A **secrets bridge** lives behind the context server. Agents call `request_credentials(service)`
  (e.g. "AWS", "GitHub", "Stripe"); the server resolves a **scoped, short-lived, ephemeral**
  credential and **injects it into the sandbox environment** only — never into the agent's prompt.
- The agent never sees the raw secret; it sees only `{ ok: true, env_injected: ["AWS_*"] }`.
- Credential scope reflects the task's `bounds` and the calling agent's `bindings` (Phase 6.2).
- All `request_credentials` calls are traced (Phase 2.5) with the service name and lease TTL, but
  never the secret value.

#### 2.8 Zero-trust identity (transport-layer authentication)

Phase 2.4 relies on "identity propagation" where every tool call carries the calling agent's
identity and task id. **If that identity is self-reported inside the tool payload** (e.g.
`{ "agent": "opencode" }`) it is vulnerable to prompt injection: a compromised agent could send a
payload claiming to be the meta-agent and bypass the Phase 6.2 Permission Matrix to escalate write
privileges. Identity must be enforced at the connection/transport layer, never the payload layer.

- **Per-agent signed local token at startup.** When the OS provisions an agent (Phase 3
  registration + Phase 5 config generation), it issues that agent a unique, short-lived, signed
  identity token (e.g. HMAC over `{agent_id, task_id, issued_at, exp}`). The token is delivered
  out-of-band to the agent process (env var / startup handshake), **never via the LLM prompt**.
- **Transport binding, not payload binding.**
  - HTTP MCP server: the agent presents its token in an `Authorization` / `X-Agent-Identity` header
    on every request. The Context Server extracts identity strictly from the authenticated
    connection.
  - stdio / socket MCP: the server validates the peer PID / socket credential
    (`SO_PEERCRED` on Linux, named-pipe ACL on Windows) and maps it to a registered agent via a
    startup-supplied PID→agent table.
- **Payload identity is ignored.** Any `agent` / `task_id` field the LLM places in the JSON body
  is treated as untrusted hint text only; the server overwrites it with the transport-derived
  principal. A mismatch (payload claims a different agent than the transport proves) is logged as
  a `identity_spoof_attempt` failure class in the Phase 2.5 trace and counted toward the Phase 2.9
  circuit breaker.
- **Token revocation / rotation.** Tokens are task-scoped and expire with the task's `bounds`
  window; the Phase 6.6 Hibernation Protocol re-issues a fresh token on state hydration so a
  resumed task is not bound to a stale credential.
- **Logical clock for expiry (clock-drift safe).** The signed token payload carries a
  **monotonically increasing logical sequence step** (Lamport timestamp, per Phase 2.5) in
  addition to `issued_at`/`exp`. Expiry and freshness are validated against the server's logical
  sequence counter, **not** the host wall-clock — so a token minted in a remote E2B microVM and
  validated during a Phase 6.6 thaw on the local host is never rejected as prematurely expired
  due to clock skew, and never accepted past its logical step budget. Wall-clock fields remain
  for human display only.
- **Mandatory for all writes.** The Phase 6.2 Permission Matrix is evaluated against the
  transport principal, not the body. This is what makes the matrix survive prompt injection.

**Why this matters:** this is the difference between a permission system the LLM can talk its way
past and one it cannot. It closes the zero-trust gap that v1.1 left open by relying on
self-reported payload identity.

#### 2.9 Server-side circuit breaker (infinite-loop defense)

Phase 7.2 caps tokens via `max_turns` and hard caps, but agents frequently get stuck in *tight
logic loops* — repeatedly calling `search_notes` with the exact same failed query, or re-running a
broken tool hoping for a different result. A looped agent spams the Context Server, artificially
inflates the Phase 7.3 token database, and can DDoS the local lock manager or FastAPI instance.
`max_turns` is too coarse to catch this; the loop lives inside one turn budget.

- **Argument-hash replay detection.** Phase 2.5 already hashes the arguments of every tool call
  (`args-hash`). The Context Server maintains a sliding window per `(agent, task_id, tool)` of the
  last N `args-hash` values.
- **Trip condition.** If the *exact same* `(tool, args-hash)` combination is observed **≥ N times
  within a short wall-clock window** (defaults: N=3, window=60s; tuned via Phase 2.5 trace stats),
  the breaker trips *on the server side*, before the tool executes again.
- **On trip:**
  1. The repeated call is refused with a structured `circuit_breaker_tripped` error carrying the
     repeated hash and the trip count — the agent gets a clear signal, not silence.
  2. The event is tagged `circuit_breaker` in the Phase 2.5 trace and written to
     `IMPLEMENT.md` by the context server (not the agent) so the loop is auditable.
  3. The Phase 6.5 `request_clarification` HITL handoff is **auto-triggered** — the loop is
     escalated to a human instead of burning the turn budget silently.
- **Half-open recovery.** After a trip, the breaker stays open for a cool-down interval; the next
  call is allowed through as a *probe*. A probe that succeeds with a *different* args-hash resets
  the window; a probe that repeats the same hash re-trips immediately and re-escalates HITL.
- **Scope.** Per `(agent, task_id, tool)` — a healthy agent calling `search_notes` with varied
  queries is unaffected; only identical, rapid, repeated calls trip. This keeps the breaker from
  false-positive-ing on legitimate retry-with-backoff patterns.

This turns "the agent looped for 60 turns and I only found out from the bill" into "the agent
looped twice, the OS caught it on the third identical call, and a human was pinged."

#### 2.10 Optimistic concurrency control (read-modify-write protection)

Phase 2.6's distributed lock manager prevents *concurrent* writes by requiring a time-bounded
lease, but it does not prevent a **lost update across multiple turns**. Agent A reads `script.py`,
spends 5 turns reasoning, then acquires a lock and writes. During those 5 turns Agent B acquired
the lock, edited `script.py`, and released it. Agent A's write now succeeds and **silently
overwrites Agent B's logic** because A is acting on a stale mental model of the file — the lock
guarantees mutual exclusion at write time, not freshness at read time.

- **ETag / Git-SHA version hash on every read.** When the Context Server serves a read tool
  (`read_note`, `get_concept`, `search_okf` results, or a sandbox file read routed through the
  server), it attaches a **content version hash** to the returned payload — the file's git blob SHA
  for tracked files, or a fast content hash (e.g. xxhash) for untracked `log.md` / `IMPLEMENT.md`.
  The agent stores this hash alongside its read of the resource.
- **Hash required on write.** Every write tool (`append_implement`, `log_decision`, file edits
  routed through the server) must carry the `expected_version` hash of the resource it is modifying,
  sourced from the agent's most recent read of that resource.
- **Reject-on-stale.** On write, the server recomputes the current hash of the target; if it
  differs from `expected_version`, the write is refused with a structured `state_changed` error
  carrying the current hash. The agent is forced to **re-read before re-writing** — it cannot
  clobber a change it never observed.
- **Append-only exception.** `log.md` and `IMPLEMENT.md` are append-only ledgers; for these the
  hash check is replaced by a *position* check (expected tail offset), so concurrent appends are
  serialized without false `state_changed` rejections. Full-content hash checks apply to mutable
  files and OKF concepts only.
- **Interaction with the lock manager (Phase 2.6).** OCC and locks are **complementary**, not
  alternatives: the lock serializes the write instant; OCC guarantees the write is based on a
  current view. A flow may hold a lock yet still fail OCC if it read stale data *before* acquiring
  the lock — which is exactly the lost-update scenario this closes.
- **Interaction with hibernation (Phase 6.6).** The hibernation record stores the version hashes
  the task last read; on thaw, the stale-on-thaw drift re-check is implemented *as* an OCC
  comparison — if any watched resource's hash changed during hibernation, the resumed agent is
  handed a `state_changed` banner before it touches anything, unifying hibernation and OCC under
  one staleness primitive.

**Why this matters:** this is the difference between "the write succeeded" and "the write was
correct relative to the world the agent thinks it lives in." Without OCC, a multi-turn agent is a
silent data-corruption vector even with locks in place.

#### 2.11 Rate limiting + compute quota (resource protection)

Phase 2.9's circuit breaker trips on *identical* repeated calls, and Phase 7.2 caps `max_turns`.
But nothing stops an agent from rapidly firing **500 unique, expensive** queries — e.g. running
`search_okf` across massive bundles with slightly different arguments each time. This evades the
Phase 2.9 breaker (args differ each call) while overwhelming a local LLM runner or exhausting an
API budget in minutes. `max_turns` is turn-count coarse; it does not see burst rate.

- **Token-bucket rate limiter per `(agent, task_id)`.** The Context Server enforces a maximum
  requests-per-minute (RPM) and a per-tool compute-cost quota (weighted: a `search_okf` over a
  large bundle costs more than a `lookup_agent`). Defaults derived from the task's `bounds` and
  the adapter's `cost_defaults` (Phase 7.2).
- **On burst over the limit:** the server returns a `429 Too Many Requests` (or the MCP-equivalent
  delay/queue signal) with a `Retry-After` hint, forcing the agent to throttle its pace rather than
  burn host resources. The refused call is still traced (Phase 2.5) as `rate_limited` so the
  throttle is visible in the trajectory, not silent.
- **Quota, not just rate.** Beyond RPM, a hard per-task compute-quota ceiling (token-equivalent
  units) acts as a circuit-breaker-of-last-resort: an agent that burns its quota mid-task is
  auto-paused into the Phase 6.6 hibernation flow for human review, not allowed to overspend.
- **Distinguishing rate-limit from circuit-breaker.** Phase 2.9 catches *repetition* (same call,
  likely a stuck loop → HITL); Phase 2.11 catches *volume* (many distinct calls, possibly
  legitimate exploration → throttle and let it proceed slower). Both feed the same Phase 7.3
  token accounting so cost is attributed either way.

**Why this matters:** this protects the host (CPU, local LLM runner) and the budget (API spend)
from a well-meaning but over-eager agent, distinct from the malicious/stuck agent the breaker
catches.

#### 2.12 Data-loss-prevention middleware (trace + log sanitization)

Phase 2.7 ensures raw API keys never sit in agent-readable context via the secrets bridge. But
secrets can enter the system through paths the secrets bridge does not cover: a user accidentally
pastes an AWS key into an Obsidian note (Phase 1.1), an LLM hallucinates a sensitive internal
token into a tool result, or a scraped web page contains PII that gets logged. Without
intervention, that plaintext is **permanently written** to the Phase 2.5 OTel traces, the
append-only `IMPLEMENT.md` (Phase 4.3), and the OKF bundles (Phase 4.2) — a durable leak.

- **DLP middleware in the write path.** Before any output is persisted to disk, shipped to
  Langfuse, or committed to an OKF bundle, the payload passes through a **high-entropy regex
  scrubber** in the Context Server. Patterns cover known secret shapes (AWS `AKIA…`, Stripe
  `sk_live_…`, GitHub `ghp_…`, Slack tokens, generic high-entropy strings) plus configurable PII
  patterns (emails, phone numbers, credit-card-shaped digit runs).
- **Redaction, not rejection.** Matched spans are replaced with a `[REDACTED:<kind>:<hash6>]`
  token (the short hash lets a human with the vault re-identify *which* secret it was without the
  secret itself being present). The write proceeds so the agent's workflow is not blocked, but the
  secret never lands in a durable store.
- **Redaction log.** Every redaction is itself a traced event (`pii_redacted` / `secret_redacted`
  failure-class in Phase 2.5) so the human can see *that* a leak was attempted and *where*, and
  root-cause it (e.g. "the source Obsidian note `X` contains a pasted key — go rotate it").
- **Source-side sweep.** The DLP layer also runs on the Phase 4.2 Obsidian→OKF export hook and on
  `read_note` *return* payloads, so a secret pasted into Obsidian is caught at the boundary before
  it ever reaches an agent's context in the first place — defense at both the read edge and the
  write edge.
- **Vault coordination.** When a redaction matches a known secret shape, the Phase 2.7 secrets
  bridge is consulted: if the redacted value *is* a registered credential, an alert is raised
  (a registered secret leaked into prose = a rotation event); if it is unrecognized, it is
  surfaced as a "suspected leaked credential" candidate in the Phase 7 evening review.

**Why this matters:** Phase 2.7 stops the OS from *handing* secrets to agents; Phase 2.12 stops
secrets that slipped in anyway from being *immortalized* in traces and logs. Together they form a
full DLP boundary around the durable stores.

#### 2.13 Read-edge context chaperoning (denial-of-context defense)

Phase 6.2 blocks untrusted-provenance inputs from reaching *destructive write* tools, and Phase
2.12 redacts secrets from durable stores. But adversarial read loops are unaddressed: an agent
that reads an untrusted external file or webpage containing a malicious injection can be commanded
to run an **infinite, randomized loop of read-only tools** — hundreds of unique `search_notes` /
`search_okf` calls with high-entropy keywords. This evades the Phase 2.9 circuit breaker (args
hashes differ every call) and slips under Phase 2.11 rate limiting if paced carefully. The
payload is denial-of-*context*: OTel trace storage explodes, the Phase 5.4 compactor gets
throttled summarizing trash text, and append-only logs flood with nonsense — blinding the Phase 7
evening human review.

- **Untrusted-provenance read isolation.** When an agent reads data flagged with an untrusted
  provenance tag (per Phase 6.2's instruction-provenance tracking), the Context Server temporarily
  **isolates that task's telemetry stream** into a chaperoned branch. Reads are still allowed (the
  open loop must be able to process the untrusted content), but the branch is marked
  `untrusted_processing`.
- **Macro-span collapsing.** While the chaperoned branch is open, the server **collapses
  duplicate or high-frequency read spans into a single aggregated macro-span wrapper**, dropping
  individual high-entropy arguments from permanent trace storage (a count + the first/last args
  are retained as samples, not the full firehose). This bounds trace growth to O(1) per branch,
  not O(calls), so a 500-call read loop produces one macro-span, not 500 spans.
- **Branch-exit flush.** When the agent exits the untrusted processing branch (signals it is done
  with the untrusted content, or the Phase 2.9 breaker / Phase 2.11 limiter trips), the macro-span
  is sealed and a single summary entry is written to `IMPLEMENT.md` — the human review pipeline
  sees one line ("agent processed untrusted source X, made N read calls"), not a flooded log.
- **Compactor protection.** The Phase 5.4 compactor treats chaperoned branches as already-summarized
  and skips them, so it is not throttled re-summarizing injected trash — the DoC attack cannot
  starve the compactor's budget for legitimate history.
- **Coupling with the rate limiter.** Chaperoning is *complementary* to Phase 2.11: the limiter
  caps raw call volume; the chaperon ensures whatever volume *does* get through is not
  immortalized token-for-token. A burst that trips the limiter inside a chaperoned branch
  auto-escalates to Phase 6.5 HITL, since an untrusted-source-driven burst is the highest-risk
  read pattern.

**Why this matters:** without chaperoning, a single malicious read source can blind the entire
observability + review pipeline by drowning it in noise — a denial-of-context attack that the
write-side controls (6.2) and the secret-side controls (2.12) are structurally blind to, because
no destructive write and no secret ever occurs.

**Definition of Done (Phase 2):**
- [ ] `contracts/mcp_tools.md` documents the tool surface, payloads, and annotations, including
  the progressive-disclosure tools (`search_tools`, `load_tool_schema`) and the `delegate_task`
  tool (Phase 3.3).
- [ ] `contracts/lock_manager.md` documents lease semantics, default TTL, the lock table, **and**
  the task-dependency DAG deadlock detector with `deadlock_risk` refusal on cyclic edges
  (covering `acquire_lock` + `delegate_task` edges) (Phase 2.6).
- [ ] `contracts/observability.md` documents the OTel/Langfuse span schema + failure-class tags
  **and** the logical sequence counter (Lamport timestamp) ordering that neutralizes cross-sandbox
  wall-clock drift (Phase 2.5).
- [ ] `contracts/identity.md` documents the signed-token issuance, transport binding (HTTP header
  vs. PID/socket), payload-identity override rule, `identity_spoof_attempt` failure class, token
  rotation on hibernation, **and** the Lamport logical-sequence-step expiry that replaces
  wall-clock validation across distributed VM sandboxes (Phase 2.8).
- [ ] `contracts/secrets_bridge.md` documents the `request_credentials` flow and sandbox injection.
- [ ] `contracts/read_chaperon.md` documents the untrusted-provenance read branch, macro-span
  collapsing with sampled args, branch-exit flush to `IMPLEMENT.md`, compactor skip, and the
  limiter-coupled HITL escalation (Phase 2.13).
- [ ] `contracts/circuit_breaker.md` documents the args-hash replay window, trip defaults (N / window),
  half-open probe semantics, and the auto-HITL escalation (Phase 2.9).
- [ ] `contracts/occ.md` documents the version-hash-on-read, `expected_version`-on-write,
  `state_changed` rejection, append-only position-check exception, and hibernation interaction
  (Phase 2.10).
- [ ] `contracts/rate_limit.md` documents the token-bucket RPM, per-tool cost weighting, `429` /
  `Retry-After` semantics, per-task compute-quota ceiling, and the auto-hibernate-on-quota-exhaustion
  handoff (Phase 2.11).
- [ ] `contracts/dlp.md` documents the regex scrubber patterns, `[REDACTED:...]` token format,
  redaction-event tracing, read-edge + write-edge + export-hook coverage, and secrets-bridge
  coordination (Phase 2.12).
- [ ] `registry/adapters/context-server.md` exists (`type: ContextServer`) listing the tool set.
- [ ] Registry now also advertises the context server's connection string/conventions.
- [ ] A dry run shows `search_okf` returning one concept from `registry/agents/hermes.md`.
- [ ] A dry run shows `acquire_lock` + a gated write succeeding, and a leaseless write refused.
- [ ] A dry run shows `request_credentials` injecting an ephemeral credential into an empty sandbox
  without the secret value entering the trace.
- [ ] A dry run shows a payload-claimed identity being **ignored** in favor of the transport
  principal, with the mismatch logged as `identity_spoof_attempt` (Phase 2.8).
- [ ] A dry run shows the breaker tripping on the Nth identical `(tool, args-hash)` call, returning
  `circuit_breaker_tripped`, and auto-triggering `request_clarification` (Phase 2.9).
- [ ] A dry run shows OCC rejecting a write whose `expected_version` is stale (file changed between
  read and write) with `state_changed`, and the agent re-reading successfully (Phase 2.10).
- [ ] A dry run shows a burst of distinct expensive calls being throttled with `429` + `Retry-After`
  and traced as `rate_limited`, while a quota-exhausted task auto-hibernates (Phase 2.11).
- [ ] A dry run shows a pasted AWS-key-shaped string in an Obsidian note being redacted to
  `[REDACTED:aws_key:...]` on both `read_note` return and OKF export, with a `secret_redacted`
  trace event and a secrets-bridge rotation alert (Phase 2.12).
- [ ] A dry run shows the DAG deadlock detector refusing a cyclic `acquire_lock` (or
  `delegate_task`) edge with `deadlock_risk` *before* the wait forms, vs. granting an acyclic
  one (Phase 2.6).
- [ ] A dry run shows spans ordered by logical sequence counter (not wall-clock) across a
  simulated remote-E2B + local-host clock skew, with no negative latencies, and a token
  validated by logical step rather than `exp` (Phase 2.5 / 2.8).
- [ ] A dry run shows an untrusted-provenance read loop of N unique calls collapsed into a single
  macro-span with sampled args and one `IMPLEMENT.md` summary line, vs. a trusted read loop
  recorded span-for-span (Phase 2.13).
- [ ] No agent has been wired yet — wiring is Phase 3.

---

### Phase 3 — Agent Registry + Adapter Pattern

**Goal:** Make "add a new agent to the OS" a registration task, not an architecture task.

#### 3.1 The adapter contract

Every agent in the OS is paired with an **adapter** — a thin documentation + templating layer that
maps the *shared* protocol (tools from Phase 2, `AGENTS.md`/`PLAN.md`/`IMPLEMENT.md` from Phase 0,
OKF bundles from Phase 1) to the agent's *native* configuration file(s). The adapter does NOT
execute code; it is a documented mapping so a future script (Phase 5) can generate the native config
deterministically.

Each adapter is an OKF concept at `registry/adapters/<adapter-name>.md`:

| Field                  | Example (opencode)                                  |
|------------------------|-----------------------------------------------------|
| `type`                 | `AgentAdapter`                                      |
| `title`                | opencode adapter                                    |
| `tags`                 | [mcp, filesystem, subagent]                          |
| native config file     | `opencode.json` / `opencode.jsonc`                  |
| memory surfaces reads  | Obsidian (via context server), OKF bundle (per repo)|
| memory surfaces writes | `IMPLEMENT.md` (per repo), `log.md` (per bundle)     |
| `AGENTS.md` source     | repo root (`./AGENTS.md`)                           |
| registration step      | create `registry/agents/opencode.md`                |

#### 3.2 Initial adapter set (one per current agent)

Create the following adapters as OKF concept docs. For each, fill in the agent's *actual*
config location and register it in `registry/agents/<agent>.md`:

1. **hermes** — config in Hermes' `config.yaml`; uses MCP; exhibits background-scan/idle-token cost
   (per the Hermes cost transcript). Adapter flags: needs ephemeral-prompt + auto-memory-off
   recommendation.
2. **opencode** — config `opencode.json`/`opencode.jsonc`; supports subagents, MCP. Adapter flags:
   filesystem-first.
3. **antigravity** — TBD config path; MCP support unknown until registered.
4. **claude-code** — uses `CLAUDE.md` + `.claude/` state; supports MCP and subagents. Adapter
   maps `CLAUDE.md` to be generated from `AGENTS.md` template (`CLAUDE.md` is just a renamed
   `AGENTS.md`).
5. **codex** — uses `AGENTS.md` natively (per OpenAI's Plan.md/Implement.md discipline in the
   harness README). Adapter is the canonical mapping — adapter Almost-a-no-op.

#### 3.3 Inter-agent delegation contract (the `delegate_task` tool)

Phase 3.2 acknowledges that agents like opencode and claude-code support native sub-agents. But
delegating purely through each agent's *native* sub-agent protocol (opencode subagents, claude-code
Task tool, Codex sub-agents) **bypasses the OS's control plane**: those calls are invisible to the
Phase 2.5 trajectory trace, ungated by the Phase 6.2 Permission Matrix, and unrecorded in
`PLAN.md`. To keep all orchestration inside the harness, delegation goes through a single
context-server tool.

- **The tool:** `delegate_task` (added to the Phase 2.2 tool surface). Payload is structured, not
  free text: `{ delegate_to, task_spec, input_bindings, expected_output, bounds }`.
  - `delegate_to`: a registered agent id from `registry/agents/` (validated against the
    transport-authenticated caller — Phase 2.8; the caller *cannot* delegate as someone else).
  - `task_spec`: a self-contained scope string written into `PLAN.md` as a child task.
  - `input_bindings`: which OKF concepts / files / locks the child is allowed to touch — inherited
    from the parent's `bindings` by default, narrowed only.
  - `expected_output`: the contract the child must satisfy for the delegation to count as done.
  - `bounds`: CPU/wall-clock/token budget for the child, ≤ the parent's remaining budget.
- **What the Context Server does on `delegate_task`:**
  1. Writes a **child task** row into the project's `PLAN.md` (parented to the caller's task_id),
     so delegation is visible in the plan, not hidden in a side channel.
  2. Provisions a **new sandbox** (Phase 0.5) for the child with the narrowed `input_bindings`.
  3. Issues the child agent its own **signed identity token** (Phase 2.8) — the child's writes are
     attributed to the child, not the parent, in the audit ledger.
  4. **Nests OTel spans:** every tool call the child makes becomes a child span under the parent's
     task trace (Phase 2.5), so a delegated sub-tree is a single replayable trajectory.
  5. Applies the Phase 6.2 Permission Matrix to the child independently — delegation never widens
     privilege; a parent without filesystem-write cannot delegate filesystem-write.
- **Completion contract.** When the child's Phase 6.3 gate passes, the result (compressed via
  headroom if bulky) is returned to the parent's context as the tool's return value, and the
  `PLAN.md` child row is marked done. If the child fails or hits the Phase 2.9 circuit breaker,
  the failure class propagates up the span tree and the parent can choose to retry, re-delegate,
  or call `request_clarification`.
- **Recursion guard.** `delegate_task` depth is capped (default 3) and counted toward the parent's
  `max_turns` budget so a chain of delegations cannot silently spend the whole turn budget. Each
  hop is visible as its own span subtree.

**Why this matters:** without this, "Claude delegates a search to opencode" happens through
claude-code's private Task protocol — invisible to your OS. With `delegate_task`, every
cross-agent hop is a first-class, traced, permission-gated, plan-recorded event.

#### 3.4 The registration ritual (documented once, repeated forever)

To add a new agent `X`:
1. Create `registry/agents/X.md` (OKF `type: Agent`).
2. If no existing adapter fits, create `registry/adapters/X.md` (OKF `type: AgentAdapter`).
3. Append to `registry/log.md` under today's date: `**Registration**: agent X added (adapter Y).`
4. Update `registry/index.md` to list X.
5. (Phase 5) Regenerate each project's native agent config from the shared templates.

Step 5 is the only place *code* is required; steps 1–4 are pure documentation and are enough to
say "agent X is now part of the OS."

**Definition of Done (Phase 3):**
- [ ] All five initial `registry/agents/*.md` are filled out (not stubs).
- [ ] All five have a `bindings` field naming their OKF bundle paths.
- [ ] `registry/adapters/` has at least three adapter concepts (hermes, opencode, claude-code).
- [ ] The "registration ritual" is documented in `registry/adapters/index.md`.
- [ ] `contracts/delegation.md` documents the `delegate_task` payload, sandbox provisioning, span
  nesting, permission narrowing, recursion guard, and completion contract (Phase 3.3).
- [ ] `registry/index.md` lists all five agents + the context server + the adapters.
- [ ] A synthetic delegation (opencode → claude-code) shows a child task row in `PLAN.md`, a
  nested OTel span subtree, and the child's writes attributed to the child principal.

---

### Phase 4 — Per-Project Harness (where downstream apps live)

**Goal:** Define what a "project" looks like inside this OS, so every later app (Flutter, Next.js,
Django, etc.) starts from the same scaffold. This is the surface you build your day-to-day tasks on.

#### 4.1 The project contract

Every project under this OS carries, at its repo root:

```
<project-repo>/
├── AGENTS.md                  # generated/from-fills the template
├── PLAN.md                    # active plan (template)
├── IMPLEMENT.md               # append-only log
├── HARNESS_CHECKLIST.md       # run before merge (template)
├── okf/                       # THIS project's OKF bundle (the local secondary brain)
│   ├── index.md
│   ├── log.md
│   ├── architecture/
│   │   ├── index.md
│   │   └── *.md               # type: ArchitectureDecision
│   ├── runbooks/
│   │   ├── index.md
│   │   └── *.md               # type: Runbook
│   └── domain/
│       ├── index.md
│       └── *.md               # type: table | api | metric | …
└── … (the project's own code)
```

The `okf/` directory is the project's **structured brain**; Obsidian remains the **unstructured
brain** for that project (a note under `20 Projects\<project>\` is the human authoring surface
and the source from which `okf/` is exported).

#### 4.2 The Obsidian → OKF export hook

A single repo-agnostic hook script (Phase 5 builds it; here it is specified) that:

- Watches (or runs on demand / pre-commit) the project's folder inside
  `D:\ObsidianVaults\Main Brain\20 Projects\<project>\`.
- For each changed `.md`, applies the PARA→OKF type map (Phase 1 §1.1) to write a corresponding
  concept under `<project-repo>/okf/`.
- For architectural-decision records (ADRs) in Obsidian, exports to
  `okf/architecture/<slug>.md` (frontmatter `type: ArchitectureDecision`).
- Appends to the project's `okf/log.md` with what was exported and when.

**Important boundary:** the hook is one-directional (Obsidian → OKF). Agents never edit Obsidian
notes directly; they write to `IMPLEMENT.md` and `okf/log.md` via the Phase 2 context server, and
the human promotes noteworthy entries back to Obsidian.

#### 4.3 The harness triad per project

- `AGENTS.md` — locked rules for this repo (per the template in `tools/awesome-harness-engineering/`).
- `PLAN.md` — current task, milestones with verification commands, scope, risks.
- `IMPLEMENT.md` — append-only executed log.
- `HARNESS_CHECKLIST.md` — re-run before any non-trivial change is merged.

The OS repo (`agent_harness_setup`) is itself the first conformant project under this contract —
its own `AGENTS.md`/`PLAN.md`/`IMPLEMENT.md` already started in Phase 0.

**Definition of Done (Phase 4):**
- [ ] `contracts/project_contract.md` documents the per-project layout above.
- [ ] One reference downstream project (existing or new tiny demo) is brought into conformance
  with the contract (i.e., its `okf/` bundle is created with at least an `index.md`, a `log.md`,
  and one concept doc).
- [ ] The export-hook specification is recorded in `contracts/obsidian_export_hook.md`.

---

### Phase 5 — Indexing + Generation Layer (the "code" phase)

**Goal:** Make Phases 1–4 mechanical. Up to here everything is documentation and contracts; here
we add the small amount of tooling that turns those contracts into running artifacts.

#### 5.1 Indexing

For every project under the OS:

1. Run **Graphify** on the repo to produce `graphify-out/graph.json` (token-efficient knowledge
   graph of the code). Already done for this repo today (1,684 nodes / 3,173 edges).
2. Run **codebase-memory-mcp** `index_repository` so the structured graph is queryable from the
   context server (Phase 2 graph backend).
3. Run **headroom** compression on any bulky output (logs, large file reads) before it enters an
   agent's context — directly operationalizing the Hermes cost-control learnings
   (`hermes_agent_cost_reduce_youtube_content.txt`): compress-often, lower compression threshold,
   lower target ratio, tool-output limits, ephemeral prompts.

Each indexing tool is registered in `registry/adapters/` with `type: Indexer` so its connection
info lives in the same registry as agents.

#### 5.2 Generation

A small generator (spec it now, implement later) that turns a project's OKF + the harness
templates into each agent's native config:

- `AGENTS.md` → `CLAUDE.md` for claude-code (and any agent that accepts a sibling of `AGENTS.md`).
- `AGENTS.md` → Hermes' instructions field.
- `okf/<project>.okf` → `opencode.json` project-context block.
- Capability/adapter decisions in `registry/agents/<agent>.md` → enabled tools, MCP servers,
  permission scope.

The generator is idempotent and append-aware (won't clobber hand-edits inside designated
preserved regions, mirroring the `claude install` convention from the graphify skill).

#### 5.3 Re-index on demand

- After Phase 5 ships, the workflow is: edit in Obsidian → run export hook → regenerate native
  configs → re-index graph → agents pick up new context server-side.

#### 5.4 Automatic context compaction (proactive, not just reactive)

Compression (Phase 2 `compress`) is a *reactive* measure on bulky tool output. A production
harness also compacts *proactively* so the agent does not lose its objective to "context rot":

- A **compactor** runs as a server-side hook on the active session transcript. When the working
  context crosses a configured token threshold, the oldest interaction history is summarized into
  a compact `Episodic summary` block, preserving the original objective, key decisions, and the
  tail of recent tool calls verbatim.
- The compactor emits an OTel span (Phase 2.5) so you can see *when* compaction happened and
  *what* was lost — turning "the agent forgot my goal" into a diagnosable event.
- Default thresholds are cost-aware per the Hermes learnings (Phase 7): compression threshold
  below default, low target ratio.

#### 5.5 OKF drift detection (cache invalidation for the secondary brain)

The Obsidian → OKF bridge is human-triggered and one-directional (Phase 0.3, Phase 4.2). It does
not catch the reverse: when the codebase changes so much that the OKF architecture docs become
stale. An agent reading a stale OKF concept will assume it reflects live code and decide badly.

- After each `index_repository` (Phase 5.1), a **drift check** compares the current code graph
  against the architecture/domain concepts stored in the project's `okf/` bundle (signatures,
  referenced symbols, module boundaries).
- When divergence exceeds a configurable threshold, the affected OKF concept is re-tagged
  frontmatter `status: stale` and surfaced to: (a) the human via the daily note / Phase 7 evening
  review, and (b) the Phase 8 meta-agent / Dream Cycle as a "sync candidate."
- A stale concept is **read-restricted**: context-server `get_concept` still returns it but with
  a visible `Status: Stale` banner so agents treat it as a hint, not ground truth.
- **Vector-space centroid shift (semantic drift).** Phase 5.7 delta-indexing patches graph
  nodes/edges cleanly per change, but **vector spaces do not delta-patch**: weeks of incremental
  embedding injections silently shift cluster centroids, so old documentation partitions drift
  semantically distant from newly patched modules. The agent then queries the vector store and
  misses a relevant note — localized "context blindness" with no code-level signal. The drift
  engine therefore also monitors **Embedding Density Variance**: the ratio of incremental vector
  injections to total files. When that ratio crosses a configured threshold, the index is flagged
  not merely `status: stale` (code drift) but `status: semantic_drift_detected` (vector drift),
  and a read-restriction banner distinguishes the two so the agent knows *which* kind of
  untrustworthiness it is hitting.
- **Asynchronous re-normalization.** A `semantic_drift_detected` flag does **not** trigger a
  synchronous full re-embedding (that would re-introduce the Phase 5.7 bottleneck mid-task).
  Instead it schedules an **offline, asynchronous background re-indexing pass** that runs
  exclusively inside the Phase 8.2.1 Dream Cycle evening window, re-normalizing the vector space
  so the semantic retrieval layer stays as unified as the graph layer without ever locking the
  context server during agent hours.

#### 5.6 Progressive tool disclosure (mechanization)

Phase 2 specifies `search_tools` + `load_tool_schema`; here we wire the backing catalog. The
context server builds a tool index from `registry/capabilities/*` plus each project's declared
project-local tools (from `AGENTS.md`), and serves `search_tools` queries against it. Full
schemas are loaded on demand only — keeping the default system prompt minimal across all agents.

#### 5.7 Incremental (delta) indexing (scale safeguard)

Phase 5.3's workflow (edit in Obsidian → export → regenerate → **re-index graph**) and Phase 5.1's
`index_repository` work fine at the current scale (1,684 nodes / 3,173 edges). At enterprise scale
(e.g. 50,000+ files, or a monorepo with many projects under one OS), triggering a **full
wipe-and-rebuild** of the Phase 2.3 graph backend on every save creates a massive computational
bottleneck — the secondary brain is locked for indexing while the agent waits, defeating the
purpose of having a live context layer.

- **Delta updates, not full rebuilds.** The Phase 4.2 Obsidian→OKF export hook and the Phase 5.1
  indexer are upgraded to emit **delta patches**: on a change event the system patches *only* the
  added / modified / deleted nodes (and their incident edges) into the existing graph, rather than
  re-walking the whole repo.
- **Change attribution.** A delta carries `(node_id, op, new_signature, new_content_hash,
  affected_edge_set)`; the graph backend applies the patch transactionally and records the delta id
  in the Phase 2.5 trace so an index state is reconstructable at any point.
- **Degradation-to-full.** A full `index_repository` rebuild remains available as an explicit
  repair command (corruption recovery, schema migration, or after a configurable N deltas when
  drift between the delta-applied graph and a from-scratch graph exceeds a threshold — the same
  drift-detection primitive as Phase 5.5, applied to the index itself).
- **Lock window shrinkage.** Because deltas are bounded, the lock the indexer holds on the graph
  backend (Phase 2.6) is held for seconds, not minutes — concurrent agent reads are barely
  interrupted even at large scale.
- **Coupling to drift detection (Phase 5.5).** Phase 5.5 runs *after* a delta is applied, not after
  a full reindex, so staleness of OKF concepts is caught per-change in near-real-time instead of
  once per full reindex cycle.

**Why this matters:** without delta indexing, scaling the OS past a handful of repos makes the
"edit → agent sees new context" loop latency climb from seconds to tens of minutes, and the
indexer becomes a single-host bottleneck. Delta updates keep the secondary brain live at scale.

**Definition of Done (Phase 5):**
- [ ] `registry/adapters/` lists each indexer as a concept.
- [ ] A single command (documented) regenerates the registry-derived native configs for the
  five registered agents.
- [ ] Re-indexing is shown end-to-end on this repo: change a note → export → regenerate →
  re-index → agent sees the new OKF concept through the context server.
- [ ] The compactor fires once on a long synthetic session and the OTel span shows the compaction.
- [ ] Drift detection flags an intentionally-stale `okf/` concept as `status: stale` after a
  simulated code-graph divergence.
- [ ] Drift detection flags `status: semantic_drift_detected` after a simulated run of incremental
  vector injections crosses the Embedding-Density-Variance threshold, and an asynchronous
  re-normalization pass (Dream Cycle window) clears the flag without locking the context server
  (Phase 5.5 / 8.2.1).
- [ ] `contracts/delta_indexing.md` documents the delta patch schema, transactional apply,
  degradation-to-full repair trigger, and lock-window budget (Phase 5.7).
- [ ] A proof-of-concept shows a single-file change patching the graph via delta (sub-second,
  short lock) vs. a full reindex, and the delta-applied graph matching a from-scratch graph within
  the configured drift threshold (Phase 5.7).

---

### Phase 6 — Verification + Permissions (control mechanisms)

**Goal:** Wire the fourth harness element (control mechanisms) so the OS doesn't degenerate into
"agents editing each other's state."

#### 6.1 Harعدess checklist at merge time

Every project inherits `HARNESS_CHECKLIST.md` from `tools/awesome-harness-engineering/templates/`.
Adapted sections for this OS:

- **AGENTS.md:** accurate? matches the registry entry for this project's primary agent?
- **Tool design:** every tool the project exposes to agents has a clear name + schema + annotation.
- **Context delivery:** no secrets in agent-readable context (this is where the "no Obsidian
  secrets in notes unless marked agent-invisible" rule gets enforced); scoped to what the task
  needs; long-lived state is in files.
- **Planning artifacts:** PLAN.md/IMPLEMENT.md up to date; scope boundaries written.
- **Permissions & sandbox:** minimum permissions; destructive ops require confirmation; network
  and FS scoped.
- **Verification loop:** agent can run the verification command itself.
- **Removal conditions:** each harness component has a documented "can be removed when…" row.

A failing item is a blocker. A skipped item needs a written justification in `IMPLEMENT.md`.

#### 6.2 Permission matrix

Driven by `registry/agents/<agent>.md` `bindings` and `registry/capabilities/<cap>.md`. The
context server enforces: an agent can only write to a target `IMPLEMENT.md` / `log.md` if the
target's project is listed in that agent's `bindings`. Reads are open to all registered agents by
default; certain concepts may carry `tags: [confidential]` and be gated.

Tool annotations (`readOnlyHint`, `destructiveHint`) per the MCP guidance are propagated to each
agent's permission system (Hermes tool toggles, claude-code permission rules, opencode `permissions`).

Beyond single-tool checks, the matrix enforces **combinatorial risk analysis** to block the
"lethal trifecta": an agent with simultaneous access to (a) private data, (b) untrusted external
content (e.g. a web-search tool), and (c) external-communication tools. The matrix gates tool use
on the **instruction provenance**: a tool call whose trigger content came from an untrusted source
(a fetched web page, a scraped doc) cannot pair with private-data or external-egress tools in the
same session unless a human explicitly elevates. This is a server-side control, not a prompt-level
hint, so it survives prompt injection.
- **Read-side mirror (Phase 2.13).** The provenance tag that drives the lethal-trifecta write gate
  *also* drives read-edge context chaperoning: an untrusted-provenance read branches the task's
  telemetry into an isolated, macro-span-collapsed stream so a malicious read loop cannot flood
  traces and blind the evening review. Provenance is thus the single primitive gating both the
  write edge (here) and the read edge (Phase 2.13).

#### 6.3 Verification gate per task

Before any agent declares a task done: run the project's documented verification command
(degined in PLAN.md), capture its output, compress via headroom, write the result into
`IMPLEMENT.md` with the timestamp and agent identity.

Because agents are non-deterministic, a binary green/red gate is insufficient to detect
regressions and quality drift. The gate therefore has **two tiers**:

- **Regression evals (near-100% target):** deterministic checks the project already has
  (build, lint, test suite). A red here blocks the task — this is the binary gate from before.
- **Capability evals + LLM-as-judge rubric (lower pass-rate target):** a rubric run over the task
  trajectory (steps traced in Phase 2.5) scoring: did the agent follow the plan, ask when
  ambiguous, avoid forbidden tools, preserve state. A sub-threshold rubric score is a *soft*
  blocker — the task can ship but the trajectory is flagged into `IMPLEMENT.md` and Phase 8
  meta-agent review.

A task is "done" only when the `IMPLEMENT.md` entry exists, the regression gate is green, *and*
the rubric score is recorded.

#### 6.4 State checkpointing + automated rollback

Append-only logs (Phase 6.3, `IMPLEMENT.md`) record decisions but do not repair a broken
workspace. Production harnesses need point-in-time recovery before destructive operations.

- Before any tool annotated `destructiveHint` executes (or any Phase 2 `request_snapshot`
  request), the context server takes a **workspace snapshot** via VCS (`git stash`-style named
  label) or filesystem snapshot, identified by `task_id`.
- If the Phase 6.3 verification gate fails for that task, the harness **automatically rolls back**
  the workspace to the pre-execution snapshot, then appends a `ROLLBACK` entry to `IMPLEMENT.md`
  with the snapshot id, failing step (from the OTel trace), and the agent identity.
- Snapshots live only for the task window (plus a short retention) so cost stays bounded.

This makes "the agent broke the build" recoverable in seconds, not "wait for the evening human
review to fix it."

#### 6.5 HITL pre-execution gates

The `request_clarification` tool (Phase 2) is the runtime interrupt protocol — it pauses the agent
loop, serializes current state, and pushes a notification (CLI prompt / webhook) so a human can
unblock ambiguity instead of the agent hallucinating or failing outright. This closes the gap left
by Phase 7's purely-asynchronous daily flow.

#### 6.6 Hibernation protocol (zombie-task resolution)

Phase 6.5 pauses the agent loop on `request_clarification`, but three other phases create a
conflict when the pause is long: Phase 0.5 says sandboxes are ephemeral and torn down at task end;
Phase 2.6 says lock leases are time-bounded (default 120s TTL); Phase 2.8 says identity tokens are
task-scoped and short-lived. **If a human takes 18 hours to answer a clarification**, the
intuitive outcomes are all bad: keep the sandbox alive and it burns idle compute memory; let the
lock lease expire and another agent may alter the file mid-pause; let the sandbox hit its hard
timeout and the entire in-progress state is lost. A production harness must hibernate, not stall.

- **On `request_clarification` (the freeze step):**
  1. **Serialize agent memory state.** The Context Server fully serializes the agent's working
     state — active OKF concept pointers, lock set, accumulated Phase 2.5 trace/span id, sandbox
     filesystem delta (diff against the Phase 6.4 pre-task snapshot), and the open clarification
     prompt — into a hibernation record keyed by `task_id`, stored durably (not in the sandbox).
  2. **Voluntarily release all active locks** (Phase 2.6). The lock table entry is marked
     `released:hibernation` rather than `expired`, so the evening review can distinguish a
     deliberately-paused task from a deadlocked one.
  3. **Explicitly terminate the sandbox** (Phase 0.5). No idle compute burn; no leaked process.
  4. **Revoke the identity token** (Phase 2.8). The paused task holds no live credential.
  5. The task is marked `state: hibernated` in `PLAN.md` and surfaced in the Phase 7 evening
     review so a long-paused task does not vanish.
- **On human answer (the thaw step):**
  1. The OS provisions a **fresh sandbox** (Phase 0.5) with the same `bounds` as the original.
  2. **Re-acquires the necessary locks** (Phase 2.6). If a lock is now held by another agent
     (because it was released at freeze), thaw blocks on `acquire_lock` rather than silently
     overwriting — the conflict is surfaced, not created.
  3. **Re-issues a fresh identity token** (Phase 2.8) so the resumed task is not bound to a stale
     credential; the new token's `task_id` matches the hibernation record so the OTel trace stays
     continuous across the gap.
  4. **Hydrates state:** replays the serialized memory pointers, restores the filesystem delta onto
     the fresh sandbox, and resumes the agent loop *at the clarification prompt* with the human's
     answer injected — not from scratch.
  5. A `thaw` span is emitted (Phase 2.5) linking the pre-hibernation span subtree to the
     post-hibernation continuation, so a paused-then-resumed task is one replayable trajectory,
     not two.
- **Stale-on-thaw detection.** Between freeze and thaw the workspace may have moved (another agent
  edited a file the hibernated task held). On thaw, the Phase 5.5 drift check is re-run against
  the concepts/paths the task was working on; if they drifted, the agent is handed the drift banner
  *before* resuming so it does not act on stale state. This binds hibernation directly to the
  drift-detection layer rather than leaving the resumed agent to discover staleness by failing.
- **Forced hibernation cap.** A hibernated task is not kept forever: a max hibernation TTL (default
  7 days, configurable in `Program.md`) after which the task is auto-cancelled, its
  hibernation record archived, and the human is notified. This prevents an infinite backlog of
  unanswered clarifications.

**Why this matters:** this is what makes HITL pauses cheap (no compute burn, no leaked locks, no
stale credentials) *and* lossless (full state restore, continuous trace). Without it, a long
clarification pause is a slow resource leak; with it, a pause is a clean checkpoint.

#### 6.7 Infrastructure crash reconciliation (orphaned-state cleanup)

Phase 6.4 handles *logical* failures via automated rollback and Phase 6.6 handles *human* pauses
via hibernation, but neither covers **host infrastructure crashes**: an OS reboot, a FastAPI
Context Server crash, or a power loss mid-execution. After an ungraceful shutdown the OS is left
with **orphaned state**: Phase 0.5 sandboxes may linger as zombie microVMs/processes, Phase 2.6
lock leases may be stuck `held` with no live agent to release them (TTL will eventually clear them,
but the window is a deadlock window), Phase 3.3 delegated child tasks leave their OTel span
subtrees (Phase 2.5) perpetually `open`, and `PLAN.md` tasks remain `in_progress` forever. A
clean cold-start must reconcile this before accepting new work.

- **Startup reconciliation hook.** On boot, before the Context Server serves any agent request, it
  runs a reconciliation pass:
  1. **Orphaned sandbox sweep.** Query the host (microVM control plane / process list / container
     runtime) for any sandbox whose `task_id` is not present in the active-connections table, and
     terminate them. Each kill is logged with the orphaned `task_id` so the human can see what was
     reaped.
  2. **Stale-lock clearance.** Clear all lock-lease entries whose owning `(agent, task_id)` is not
     backed by a live connection — *not* by waiting for TTL, but immediately, marking them
     `released:crash_recovery` in the append-only lock table (Phase 2.6) so the distinction between
     a clean release, a hibernation release, and a crash recovery is auditable.
  3. **Open-span closure.** For every task whose span tree is still `open` and whose owning
     connection is gone, emit a terminal `crash_recovery` span (Phase 2.5) closing the subtree,
     with the failure class `infrastructure_crash`, so traces are not left dangling and the
     Phase 8 Dream Cycle clustering has complete trajectories to learn from.
  4. **Task-state finalization.** Mark every `in_progress` `PLAN.md` task not backed by a live
     connection as `failed:infrastructure_crash`, append a corresponding entry to `IMPLEMENT.md`
     (with the last-known span id for replay), and trigger a Phase 6.4 rollback to the task's
     pre-execution snapshot so the workspace is not left in a half-applied state.
  5. **Hibernation-record integrity check.** Verify the Phase 6.6 hibernation store is intact
     (no partial writes from the crash); corrupted records are quarantined and surfaced in the
     Phase 7 evening review rather than silently loaded on the next thaw.
- **Idempotency.** The reconciliation pass is idempotent — running it twice yields the same state
  — so a crash during recovery itself is safe (the next boot re-runs it cleanly).
- **Crash root-cause capture.** Where the host exposes it (e.g. systemd journal, container exit
  code, FastAPI startup error), the reconciliation hook captures the crash cause into the first
  `IMPLEMENT.md` entry after boot, closing the loop between "the OS restarted" and "why."
- **Interaction with quota (Phase 2.11).** Reaped tasks' compute spend up to the crash instant is
  still attributed to their `task_id` in the Phase 7.3 token ledger — crash recovery does not lose
  accounting, so CAPO (Phase 7.4) correctly counts a crashed task as a rejected outcome.

**Why this matters:** without crash reconciliation, every unexpected restart leaves a residue of
zombie processes, deadlocked locks, and ghost tasks that compounds over time — the OS degrades
silently until a human notices. With it, a crash is a single recoverable event, not a permanent
scar.

**Definition of Done (Phase 6):**
- [ ] `contracts/permission_matrix.md` exists with the (agent × target) write table **and** the
  combinatorial lethal-trifecta rule + instruction-provenance rule.
- [ ] `HARNESS_CHECKLIST.md` at this repo's root is filled in and passes for the OS repo itself.
- [ ] A proof-of-concept shows the context server rejecting an out-of-binding write attempt.
- [ ] A proof-of-concept shows the lethal-trifecta combination being refused when triggered by
  untrusted provenance.
- [ ] A proof-of-concept shows an automated rollback firing after a deliberately-failed gate.
- [ ] A synthetic task shows the LLM-as-judge rubric producing a score that lands in
  `IMPLEMENT.md`.
- [ ] A synthetic ambiguous task shows `request_clarification` pausing the loop and resuming.
- [ ] `contracts/hibernation.md` documents the freeze/thaw steps, lock-release-as-hibernation,
  token re-issue, stale-on-thaw drift re-check, and max hibernation TTL (Phase 6.6).
- [ ] A proof-of-concept shows a task freezing (sandbox terminated, locks released, token revoked,
  state serialized), waiting past the lock TTL, then thawing into a fresh sandbox with state
  restored, locks re-acquired, and the OTel trace spanning the gap.
- [ ] A proof-of-concept shows a thaw correctly blocking (not overwriting) when a released lock
  is now held by another agent, and a thaw correctly surfacing the drift banner when the
  workspace moved during hibernation.
- [ ] `contracts/crash_recovery.md` documents the startup reconciliation hook: orphaned-sandbox
  sweep, stale-lock clearance as `released:crash_recovery`, open-span closure as
  `infrastructure_crash`, task-state finalization + rollback, hibernation-record integrity check,
  idempotency, and crash root-cause capture (Phase 6.7).
- [ ] A proof-of-concept shows a simulated crash (kill the Context Server mid-task) followed by a
  reboot that reaps the orphaned sandbox, clears the stale lock immediately (not via TTL), closes
  the open span as `infrastructure_crash`, marks the `PLAN.md` task `failed:infrastructure_crash`,
  rolls back to the pre-task snapshot, and leaves the OS in a clean state on a second reboot
  (idempotency).

---

### Phase 7 — Daily Operations + Cost Discipline

**Goal:** Make the OS usable on day-to-day work, not just on big projects. Fold the Hermes
cost-control techniques (already documented in this repo) into the harness defaults.

#### 7.1 Daily-flow contract

The standard loop for every working day:

1. **Morning standup note** under `D:\ObsidianVaults\Main Brain\10 Daily\<YYYY-MM-DD>.md`
   (Obsidian's PARA already supports this; no change).
2. **Tasks of the day** promoted from the daily note to relevant projects' `PLAN.md`
   (the human, not the agent, decides promotion).
3. **Agents run** under whichever registered agent fits the task; all of them read the same
   context server.
4. **Decisions** are written via `log_decision` and `append_implement` tools — never by editing
   Obsidian notes directly.
5. **Evening** — the human reviews `IMPLEMENT.md` entries and promotes noteworthy ones back to
   `20 Projects\<project>\` (or `40 Knowledge\`) in Obsidian.

#### 7.2 Cost discipline defaults (apply Hermes learnings)

Per the transcript's findings, bake the cost savers into the adapter defaults:

- Aux tasks (image reading, skill search, MCP loading, profile writing) → cheaper model.
- Sub-agents → cheaper model.
- Effort level → off for simple tasks.
- Compression threshold → below default.
- Target ratio → low.
- Tool output limits → low (with headroom `compress` as the escape valve).
- Ephemeral prompts for one-time instructions.
- Auto-memory off unless team-context is needed.
- `undo` instead of reprompting to keep context lean.
- Disable unused tools / skills / MCP servers per project.
- Hard caps: max_tokens, max_turns (e.g. 60 not 150), hard_stop=true, per-cron max_turns.

These defaults live in each `registry/adapters/<adapter>.md` so any agent brought in inherits
them at registration.

#### 7.3 Token accounting

Every context-server call records `(agent, tool, in_tokens, out_tokens, task_id)` to a single
token database at `D:\GitRepo\agent_harness_setup\hooks\token_usage.db`. A weekly roll-up is
written into `registry/log.md` so the OS improves its own defaults over time (Phase 8).

#### 7.4 FinOps upgrade — CAPO (Cost-per-Accepted-Outcome)

Token accounting tells you an agent spent $0.50; it does not tell you whether that $0.50 produced
a merged PR or a completed task. Upgrade technical metrics to business value:

- Define **CAPO = cost / accepted-outcomes**, where an "accepted outcome" is a task whose gate
  passed *and* the human promoted it (Phase 6.3 rubric accepted + Phase 7 evening review
  promoted it to `20 Projects\`).
- Token rows (7.3) are joined to outcome rows (from `IMPLEMENT.md` gate + human promotion) so
  every spend is attributable to an accept/reject verdict.
- CAPO is the metric the Phase 8 meta-agent optimizes for, *not* raw token count — efficiency,
  not just throughput. This directly upgrades the Phase 8 objective.

**Definition of Done (Phase 7):**
- [ ] `contracts/daily_flow.md` documents the standup-to-evening loop above.
- [ ] Each adapter concept has a `cost_defaults` section reflecting the Hermes learnings.
- [ ] Token accounting is live and a one-week rollup has been written to `registry/log.md`.
- [ ] CAPO is computed and a one-week rollup has been written to `registry/log.md` alongside the
  token rollup, joined to accepted/rejected outcomes.

---

### Phase 8 — Meta-Harness (self-improvement)

**Goal:** Close the loop. The OS should improve its own defaults the way the discipline's
"meta-harnesses" do.

#### 8.1 The `Program.md` directive

At `D:\GitRepo\agent_harness_setup\Program.md`, a high-level optimization directive humans
maintain. It specifies: which metric to optimize (cost / quality / latency), which adapter
defaults are editable by the meta-agent, which are not.

#### 8.2 Meta-agent role

Register a new agent in `registry/agents/meta.md` (`type: Agent`, `tags: [meta-harness]`) whose
job is to read the weekly token rollup, the `IMPLEMENT.md` logs, and the
`HARNESS_CHECKLIST.md` failures, and propose edits to:

- adapter `cost_defaults` (Phase 7),
- the tool surface (Phase 2),
- the permission matrix (Phase 6),
- the per-project `AGENTS.md` defaults.

The meta-agent is governed by the same harness contract as every other agent: it cannot edit
Obsidian notes, only write proposals to `IMPLEMENT.md` and `log.md`. Humans promote accepted
proposals back to Obsidian.

#### 8.2.1 The Dream Cycle (proactive semantic-memory extraction)

Manual Obsidian entry to OKF is human-directed; the OS should learn from its own failures
between sessions, not rely on humans noticing patterns.

- A background process, triggered at end-of-day (Phase 7 evening window), clusters the day's
  episodic traces (Phase 2.5 spans + Phase 6.3 failure classifications) and identifies recurring
  patterns / pain points — repeated clarification requests, repeated-tool-call mis-picks, drift
  it had to work around, recurring lethal-trifecta elevations.
- These are staged as **Semantic Memory Candidates** under `okf/` with `status: proposed`,
  surfaced to the human in the evening review for accept/reject.
- Accepted candidates are promoted by the human (or promoted-by-magic via the export hook after
  review) into `40 Knowledge\` and `okf/` semantic concepts; rejected candidates are tagged so
  they are not re-proposed.
- The Dream Cycle output also seeds the meta-agent's default-improvement proposals, closing the
  loop between observability (Phase 2.5), drift (Phase 5.5), and self-improvement.
- **Vector re-normalization pass.** The Dream Cycle evening window is also when any
  `semantic_drift_detected` flags (Phase 5.5) are serviced: a background re-embedding pass
  re-normalizes the vector space globally, then clears the flag. Because it runs offline and
  asynchronously, agents are never blocked by a full vector rebuild during working hours — the
  semantic layer self-heals nightly.

#### 8.3 Removal conditions audit

Quarterly, re-walk the `HARNESS_CHECKLIST.md` "When this harness component should be removed" rows
for every registered component. Anything the model can now do alone gets retired — this is the
"every component exists because the model can't do something; those assumptions expire" principle
from the harness discipline.

**Definition of Done (Phase 8):**
- [ ] `Program.md` exists at the OS repo root.
- [ ] `registry/agents/meta.md` is registered.
- [ ] One full meta-cycle has been run and a proposal accepted.
- [ ] A removal-condition audit is scheduled (calendar entry) for one quarter out.

---

## 4. Sequencing Summary

```
Phase 0  Foundations & contracts          ─┐
Phase 1  Two brains wired                  ─┤  Foundations
Phase 2  Context server                     ├─┐
Phase 3  Agent registry + adapters         ─┤ │
                                          │ │
Phase 4  Per-project harness contract       ─┤  Surface you build on
                                          │ │
Phase 5  Indexing + generation (code)       ─┤  Mechanization
Phase 6  Verification + permissions        ─┤  Control
Phase 7  Daily ops + cost discipline       ─┤  Usability
Phase 8  Meta-harness (self-improve)        ─┘  Closure
```

- Phases 0–3 must be sequential; they establish contracts.
- Phase 4 can start during Phase 3 once adapters exist (you can conform one project early to
  de-risk).
- Phase 5 is the first phase that requires real code; everything before it is documentation
  and OKF concept files.
- Phases 6–7 can run in parallel once 5 lands.
- Phase 8 only starts once 7 has produced at least one week of rollup data.

---

## 5. Risk Register

| Risk                                                       | Phase | Mitigation                                                                |
|------------------------------------------------------------|-------|---------------------------------------------------------------------------|
| Agents drift from contract (edit things they shouldn't)    | 2,6   | Permission matrix enforced server-side; writes only via 2 typed tools.    |
| Obsidian vault grows unbounded and bloats OKF export       | 1,4   | Export is opt-in per note (frontmatter flag); Inbox/Archive never exported. |
| Adapter generator clobbers hand-edits                      | 5     | Generator is idempotent + uses preserved regions; reviewed at merge.       |
| New agent's config format is incompatible                  | 3     | Adapter documents the mapping; if no mapping exists, agent is registered as `unsupported` until adapter is written. |
| Hermes-style background token burn across all agents       | 7     | Cost defaults baked per adapter; token accounting surfaces runaway usage.  |
| Meta-agent proposes bad defaults                           | 8     | Meta-agent can only write proposals, never edit configs directly.          |
| "When can this component be removed" never gets re-checked | 0,8   | Quarterly audit scheduled in Phase 8; checklist row enforces it per ship. |
| Concurrent writes corrupt shared state (`IMPLEMENT.md`, `okf/log.md`, source files) | 2,6 | Distributed lock manager (Phase 2.6): lease-gated writes; append-only lock table. |
| Agent stalls mid-task on ambiguity, fails silently for hours | 2,6   | `request_clarification` HITL interrupt pauses + serializes state (Phase 6.5). |
| Destructive op breaks workspace; no recovery               | 6     | Auto-snapshot before `destructiveHint` tools; auto-rollback on failed gate (Phase 6.4). |
| Secrets leak via prompt injection or plaintext logs       | 0,2,6 | Sandbox isolation (Phase 0.5) + secrets bridge injects only ephemeral scoped creds into sandbox (Phase 2.7); secret values never enter traces. |
| OKF concepts go stale as code drifts; agent decides on stale facts | 1,5 | Drift detection re-tags stale concepts `status: stale`; read-restricted (Phase 5.5). |
| Lethal trifecta (private data + untrusted content + exfiltration) | 6 | Combinatorial permission matrix gates on instruction provenance, server-side (Phase 6.2). |
| Binary green/red gate misses regressions on non-deterministic agents | 6 | Two-tier gate: deterministic regression evals + LLM-as-judge rubric (Phase 6.3). |
| Token spend optimized without outcome signal (CAPO blind) | 7,8   | CAPO metric joins spend to accepted outcomes; meta-agent optimizes it (Phase 7.4, 8.2). |
| Loss of original objective due to context rot             | 5     | Automatic compactor summarizes older history past a token threshold (Phase 5.4). |
| Tool schemas bloat system prompt across all agents        | 2,5   | Progressive tool disclosure: only `search_tools` + on-demand schema load (Phase 5.6). |
| No trajectory visibility → failure cause is guesswork     | 2     | OTel/Langfuse span per tool call + task; failure-class tags (Phase 2.5). |
| Agent spoofs another agent's identity in the tool payload (prompt injection) to escalate writes | 2,6 | Zero-trust identity enforced at transport layer; payload identity ignored; mismatch logged as `identity_spoof_attempt` (Phase 2.8). |
| Agent stuck in a tight logic loop (identical repeated tool calls) burns turns, spams the Context Server, inflates the token DB | 2,6,7 | Server-side circuit breaker trips on N identical `(tool, args-hash)` calls; auto-escalates to HITL (Phase 2.9). |
| Cross-agent delegation via native sub-agent protocols is invisible to the OS (untraced, ungated, unrecorded) | 2,3,6 | `delegate_task` tool routes all delegation through the control plane: traced, permission-narrowed, plan-recorded, depth-capped (Phase 3.3). |
| Long HITL clarification pause leaks compute (idle sandbox), deadlocks locks, or loses state on sandbox timeout | 0.5,2.6,2.8,6 | Hibernation protocol: freeze serializes state + releases locks + revokes token + terminates sandbox; thaw provisions fresh sandbox + re-acquires locks + re-issues token + restores state; stale-on-thaw drift re-check (Phase 6.6). |
| Lost update across turns: agent writes based on a stale read, silently overwriting another agent's change despite holding the write lock | 2,6 | Optimistic concurrency control: version hash on every read, `expected_version` required on write, `state_changed` rejection forces re-read; append-only ledgers use position-check (Phase 2.10). |
| Agent bursts many *distinct* expensive calls (evades the identical-args circuit breaker) and overwhelms the local LLM runner or exhausts the API budget | 2,7 | Token-bucket rate limiter per `(agent, task_id)` with per-tool cost weighting + `429`/`Retry-After`; per-task compute-quota ceiling auto-hibernates on exhaustion (Phase 2.11). |
| Secret/PII pasted into Obsidian or hallucinated by the LLM is immortalized in OTel traces, `IMPLEMENT.md`, and OKF bundles | 1,2,4 | DLP middleware: high-entropy regex scrubber redacts to `[REDACTED:...]` at read edge, write edge, and export hook; redaction events traced; secrets-bridge coordination raises rotation alerts (Phase 2.12). |
| Host crash / reboot leaves orphaned sandboxes, stuck lock leases, perpetually-open OTel spans, and ghost `in_progress` tasks that compound over time | 0.5,2.5,2.6,3.3,6 | Startup reconciliation hook: reap orphaned sandboxes, clear stale locks as `released:crash_recovery`, close open spans as `infrastructure_crash`, finalize tasks `failed:infrastructure_crash` + rollback, idempotent (Phase 6.7). |
| Full re-index on every save bottlenecks the secondary brain at scale (50k+ files), locking context for minutes | 2.3,4,5 | Incremental delta indexing: export hook + indexer emit per-change node/edge patches; full rebuild remains a repair command; short lock windows; drift detection runs per-delta (Phase 5.7). |
| Multi-agent lock cycle (dining-philosophers via `delegate_task` + `acquire_lock`) stalls execution until TTL breaks it, inflating CAPO with useless retries | 2.6,3.3 | Server-side task-dependency DAG deadlock detector: cyclic edge refused with `deadlock_risk` *before* the wait forms; agent yields/aborts/hibernates instead of stalling (Phase 2.6). |
| Wall-clock drift across hybrid sandboxes (remote E2B vs. local host) breaks OTel span nesting and rejects valid tokens during thaw | 2.5,2.8,6.6 | Logical monotonic sequence counters (Lamport timestamps) issued by the server for span ordering and token expiry; wall-clock kept as hint only (Phase 2.5 / 2.8). |
| Incremental vector injections silently shift cluster centroids → localized "context blindness" with no code-level signal | 2.3,5,8 | Embedding-Density-Variance drift monitor flags `semantic_drift_detected`; offline asynchronous re-normalization runs in the Dream Cycle evening window without locking agents (Phase 5.5 / 8.2.1). |
| Adversarial read loop from untrusted source (unique high-entropy read calls) evades breaker + limiter, floods traces/logs and blinds human review (denial-of-context) | 2.5,2.9,2.11,6.2 | Read-edge context chaperoning: untrusted-provenance read branch isolates telemetry, collapses reads into one macro-span with sampled args, compactor skips it, limiter-trip auto-escalates HITL (Phase 2.13 / 6.2). |

---

## 6. Open Questions (to resolve before/while executing)

- [ ] Which transport for the context server: stdio MCP per agent, or a shared HTTP MCP? Decide in
  Phase 2 after confirming each of the five agents' MCP support.
- [ ] Where does the generator live (this repo vs. a separate tooling repo)? Phase 5 decision.
- [ ] Should the meta-agent have read access to Obsidian's confidential notes? Phase 6 decision.
- [ ] Do antigravity's MCP capabilities match opencode/claude-code? Phase 3 informational probe.
- [ ] Sandbox default: E2B (managed) vs. local gVisor/Kata — confirm in Phase 0 once CI/host OS is fixed.
- [ ] Lock manager backing store: in-process SQLite vs. external (Redis/etcd) once multi-host is in scope.
- [ ] Secrets store: OS keychain (single-host) vs. cloud SM (multi-host) — Phase 2.7 decision point.
- [ ] Drift threshold calibration — start conservative; tune from Phase 2.5 trace stats after N weeks.
- [ ] Identity token signing key custody — single shared HMAC key (single-host) vs. per-agent
  asymmetric keys (multi-host). Phase 2.8 decision point; ties into the Phase 2.7 secrets store.
- [ ] Circuit-breaker trip defaults (N / window) — start at N=3, window=60s; tune from Phase 2.5
  args-hash replay stats to avoid false-positives on legitimate retry-with-backoff.
- [ ] Delegation recursion depth cap — default 3; confirm against real opencode↔claude-code
  handoffs once Phase 3.3 ships.
- [ ] Hibernation record store — durable local SQLite (single-host) vs. external store once
  multi-host is in scope; max hibernation TTL default 7 days, tunable in `Program.md`.
- [ ] OCC version-hash source — git blob SHA (tracked files) vs. xxhash (untracked ledgers); confirm
  the append-only position-check vs. full-content-hash boundary per resource type (Phase 2.10).
- [ ] Rate-limit + quota defaults — RPM and per-tool cost weights per adapter; tune from Phase 7.3
  token stats after N weeks so legitimate exploration is not false-throttled (Phase 2.11).
- [ ] DLP pattern set custody — who maintains the secret/PII regex catalogue; start with AWS /
  Stripe / GitHub / Slack + email/phone/CC; add project-specific patterns via `AGENTS.md`
  (Phase 2.12).
- [ ] Crash-recovery crash-cause sources — which host signals (systemd journal, container exit
  code, FastAPI startup error) to capture into `IMPLEMENT.md` per supported sandbox technology
  (Phase 6.7, ties to the Phase 0.5 sandbox pick).
- [ ] Delta-indexing degradation threshold — how many deltas before a from-scratch reindex is
  forced to bound drift between the patched graph and a clean rebuild (Phase 5.7).
- [ ] DAG deadlock-detector cycle-detection strategy — incremental reachability vs. union-find;
  confirm O(V+E) per request holds at the expected live-task fan-out from Phase 3.3 delegation
  (Phase 2.6).
- [ ] Lamport logical-clock bootstrap — single primary server (single-host) vs. distributed
  sequence service (multi-host); how a server failover re-synchronizes the counter with the
  Phase 6.7 crash-reconciliation hook (Phase 2.5 / 2.8).
- [ ] Embedding-Density-Variance threshold — start conservative; tune from Phase 2.5 read-stats
  after N weeks so legitimate feature growth does not false-trigger re-normalization (Phase 5.5).
- [ ] Chaperon macro-span sample retention — how many arg samples to keep per collapsed branch so
  forensics stays possible without re-introducing the trace flood the chaperon prevents
  (Phase 2.13).

---

## 6.1 Audit-Driven Hardening Checklist (mapping audit gaps → this plan)

Cross-reference of every gap surfaced in the harness-engineering audit to the phase that closes it:

- [x] Phase 0: sandbox technology defined (E2B/Firecracker; gVisor/Kata fallback) → Phase 0.5.
- [x] Phase 2: OTel/Langfuse trajectory tracing for full visibility → Phase 2.5.
- [x] Phase 2: distributed lock manager (concurrency / mutual exclusion) → Phase 2.6.
- [x] Phase 2: secrets bridge with ephemeral scoped credential injection → Phase 2.7.
- [x] Phase 5: progressive tool disclosure (`search_tools` + `load_tool_schema`) → Phase 5.6.
- [x] Phase 5: automatic compaction past a token threshold → Phase 5.4.
- [x] Phase 5: OKF drift detection / cache invalidation → Phase 5.5.
- [x] Phase 5: hybrid graph-vector store as the retrieval substrate → Phase 2.3 graph backend.
- [x] Phase 6: LLM-as-judge rubric upgrades the binary "green gate" → Phase 6.3.
- [x] Phase 6: combinatorial lethal-trifecta gating on instruction provenance → Phase 6.2.
- [x] Phase 6: state checkpointing + automated rollback → Phase 6.4.
- [x] Phase 6: real-time HITL handoff (`request_clarification`) → Phase 6.5.
- [x] Phase 7: FinOps upgrade to CAPO → Phase 7.4.
- [x] Phase 8: Dream Cycle for proactive semantic-memory extraction → Phase 8.2.1.
- [x] Phase 2: zero-trust identity enforced at transport layer (signed token, payload identity ignored) → Phase 2.8.
- [x] Phase 2: server-side circuit breaker on identical repeated tool calls (auto-HITL escalation) → Phase 2.9.
- [x] Phase 3: standardized inter-agent delegation contract (`delegate_task`, traced + plan-recorded + permission-narrowed) → Phase 3.3.
- [x] Phase 6: hibernation protocol for long HITL pauses (freeze/thaw, lock release + re-acquire, token rotation, stale-on-thaw drift re-check) → Phase 6.6.
- [x] Phase 2: optimistic concurrency control (version-hash on read, `expected_version` on write, `state_changed` rejection) → Phase 2.10.
- [x] Phase 2: token-bucket rate limiter + per-task compute quota (throttle distinct-call bursts, auto-hibernate on quota exhaustion) → Phase 2.11.
- [x] Phase 2: DLP middleware (regex scrubber redacts secrets/PII at read + write + export edges; redaction events traced; secrets-bridge rotation alerts) → Phase 2.12.
- [x] Phase 5: incremental delta indexing (per-change node/edge patches, short lock windows, full rebuild as repair command, per-delta drift detection) → Phase 5.7.
- [x] Phase 6: startup crash-reconciliation hook (reap orphaned sandboxes, clear stale locks, close open spans as `infrastructure_crash`, finalize + rollback ghost tasks, idempotent) → Phase 6.7.
- [x] Phase 2: DAG deadlock detector on the lock manager (cyclic `acquire_lock`/`delegate_task` edges refused with `deadlock_risk` before the wait forms) → Phase 2.6.
- [x] Phase 2: logical monotonic sequence counters (Lamport timestamps) decouple OTel span ordering + identity-token expiry from host wall-clock across hybrid sandboxes → Phase 2.5 / 2.8.
- [x] Phase 5 / 8: vector-space centroid-shift drift detection (`semantic_drift_detected` via Embedding-Density-Variance) + asynchronous Dream-Cycle re-normalization → Phase 5.5 / 8.2.1.
- [x] Phase 2 / 6: read-edge context chaperoning (untrusted-provenance read branch, macro-span collapsing, compactor skip, limiter-coupled HITL) defeats denial-of-context read loops → Phase 2.13 / 6.2.

---

## 7. What This Plan Is Not (re-stating the boundary)

- Not a schedule. No dates are committed here; the Definition-of-Done per phase is the schedule.
- Not an application design for any project you'll later build. Project specs live in Obsidian
  `20 Projects\` and per-project `okf/architecture/`.
- Not a replacement for any agent. Agents stay as installed; the OS only adds the shared
  memory + context + registry + control layer underneath them.

---

## 8. First Action (what to do right after approving this plan)

1. Create `D:\GitRepo\agent_harness_setup\IMPLEMENT.md` from the template at
   `tools/awesome-harness-engineering/templates/IMPLEMENT.md`.
2. Append the first log entry: "Approved Phase 0 of the Agentic OS plan."
3. Create `D:\GitRepo\agent_harness_setup\AGENTS.md` from
   `tools/awesome-harness-engineering/templates/AGENTS.md`, customized for the OS repo.
4. Begin Phase 0 §0.1–0.4 decisions and log them in `IMPLEMENT.md`.

---

*Plan version: 1.4 — generated from the indexed knowledge graph of this repo
(1,684 nodes / 3,173 edges) plus the OKF v0.1 spec, the awesome-harness-engineering templates,
and the Obsidian vault structure at `D:\ObsidianVaults\Main Brain\`. `obsidianData` at
`D:\obsidianData` is treated as vault plumbing, not a knowledge surface. v1.1 incorporated the
harness-engineering audit: compute-plane sandbox (Phase 0.5), trajectory tracing (2.5), lock
manager (2.6), secrets bridge (2.7), progressive tool disclosure + compaction + drift detection
(5.4–5.6), combinatorial risk + LLM-as-judge gate + checkpoint/rollback + HITL (6.2–6.5), CAPO
FinOps (7.4), and the Dream Cycle (8.2.1). v1.2 incorporated the v1.1 stress-test audit:
zero-trust transport-layer identity (2.8), server-side circuit breaker (2.9), inter-agent
delegation contract (3.3), and the hibernation protocol for long HITL pauses (6.6). v1.3
incorporated the distributed-systems edge-case audit: optimistic concurrency control against
lost-update across turns (2.10), token-bucket rate limiting + compute quota (2.11), DLP/trace
sanitization middleware (2.12), incremental delta indexing for scale (5.7), and the startup
crash-reconciliation hook for orphaned state (6.7). v1.4 incorporates the deep production audit:
DAG deadlock detector on the lock manager (2.6), Lamport logical-sequence counters for
clock-drift-safe telemetry + token expiry (2.5 / 2.8), vector-space centroid-shift drift
detection with asynchronous Dream-Cycle re-normalization (5.5 / 8.2.1), and read-edge context
chaperoning against denial-of-context read loops (2.13 / 6.2).*