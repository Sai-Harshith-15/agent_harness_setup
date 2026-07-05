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
- The lock table itself is append-only and logged, so contention is visible in the Phase 2.5 trace.

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

**Definition of Done (Phase 2):**
- [ ] `contracts/mcp_tools.md` documents the tool surface, payloads, and annotations, including
  the progressive-disclosure tools (`search_tools`, `load_tool_schema`).
- [ ] `contracts/observability.md` documents the OTel/Langfuse span schema + failure-class tags.
- [ ] `contracts/lock_manager.md` documents lease semantics, default TTL, and the lock table.
- [ ] `contracts/secrets_bridge.md` documents the `request_credentials` flow and sandbox injection.
- [ ] `registry/adapters/context-server.md` exists (`type: ContextServer`) listing the tool set.
- [ ] Registry now also advertises the context server's connection string/conventions.
- [ ] A dry run shows `search_okf` returning one concept from `registry/agents/hermes.md`.
- [ ] A dry run shows `acquire_lock` + a gated write succeeding, and a leaseless write refused.
- [ ] A dry run shows `request_credentials` injecting an ephemeral credential into an empty sandbox
  without the secret value entering the trace.
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

#### 3.3 The registration ritual (documented once, repeated forever)

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
- [ ] `registry/index.md` lists all five agents + the context server + the adapters.

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

#### 5.6 Progressive tool disclosure (mechanization)

Phase 2 specifies `search_tools` + `load_tool_schema`; here we wire the backing catalog. The
context server builds a tool index from `registry/capabilities/*` plus each project's declared
project-local tools (from `AGENTS.md`), and serves `search_tools` queries against it. Full
schemas are loaded on demand only — keeping the default system prompt minimal across all agents.

**Definition of Done (Phase 5):**
- [ ] `registry/adapters/` lists each indexer as a concept.
- [ ] A single command (documented) regenerates the registry-derived native configs for the
  five registered agents.
- [ ] Re-indexing is shown end-to-end on this repo: change a note → export → regenerate →
  re-index → agent sees the new OKF concept through the context server.
- [ ] The compactor fires once on a long synthetic session and the OTel span shows the compaction.
- [ ] Drift detection flags an intentionally-stale `okf/` concept as `status: stale` after a
  simulated code-graph divergence.

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

*Plan version: 1.1 — generated from the indexed knowledge graph of this repo
(1,684 nodes / 3,173 edges) plus the OKF v0.1 spec, the awesome-harness-engineering templates,
and the Obsidian vault structure at `D:\ObsidianVaults\Main Brain\`. `obsidianData` at
`D:\obsidianData` is treated as vault plumbing, not a knowledge surface. v1.1 incorporates the
harness-engineering audit: compute-plane sandbox (Phase 0.5), trajectory tracing (2.5), lock
manager (2.6), secrets bridge (2.7), progressive tool disclosure + compaction + drift detection
(5.4–5.6), combinatorial risk + LLM-as-judge gate + checkpoint/rollback + HITL (6.2–6.5), CAPO
FinOps (7.4), and the Dream Cycle (8.2.1).*