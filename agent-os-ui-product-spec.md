# Agent OS UI and Product Specification

**Status:** Product planning v1  
**Owner:** Sai Harshith  
**Goal:** Replace manual orchestration with a governed control plane that plans work, assigns specialist agents, routes models, watches cost and quality, and exposes every decision in one operational UI.

---

## 1. Product decision

Do not make Claude, Codex, Hermes, OpenCode, or any single model the permanent orchestrator. They are workers with different strengths, availability, and cost profiles.

Build a dedicated **Supervisor Agent** as your automated replacement. The Supervisor is a role inside Agent OS, not a vendor model. It should combine:

1. A deterministic workflow engine for state, retries, approvals, budgets, and lifecycle rules.
2. A frontier reasoning model used only when a decision is genuinely ambiguous.
3. A policy-driven model router that selects the cheapest model capable of the current step.
4. Specialist agents that execute bounded work with explicit contracts.
5. A monitoring agent that can pause, downgrade, reroute, or escalate runs, but cannot silently change business goals.

**Recommended control pattern:** manager owns the run, specialists act as tools. Use handoffs only when a specialist must fully own the next branch. This keeps task ownership, budgets, and final acceptance in one place.

### Suggested foundation

- **Orchestration runtime:** LangGraph or a custom durable state machine. LangGraph is a strong fit for long-running, stateful workflows and pause/resume behavior.
- **Agent protocol layer:** OpenAI Agents SDK patterns for tools, handoffs, guardrails, and tracing, wrapped behind your own provider-neutral interfaces.
- **Model gateway:** LiteLLM or an equivalent internal gateway for provider normalization, retries, cooldowns, fallbacks, limits, and budget routing.
- **Durability:** PostgreSQL for canonical state and event history, Redis plus a worker queue for scheduling and concurrency.
- **Observability:** OpenTelemetry-compatible traces, append-only run events, cost ledger, tool-call audit log, and replay.
- **UI:** Next.js or React with server-sent events or WebSockets for live run updates.

The orchestration kernel must remain independent from every desktop harness. Claude, Codex, Hermes, Antigravity, and OpenCode should connect through adapters so a new agent can be added without changing the workflow engine.

---

## 2. Core operating model

### 2.1 Responsibilities

| Role | Responsibility | Typical model class |
|---|---|---|
| Supervisor | Owns task outcome, decomposes work, selects workflow, resolves conflicts | Frontier for hard decisions, rules for routine routing |
| Planner | Produces dependency-aware execution plan and acceptance criteria | Frontier reasoning model |
| Primary agent | Owns one task or workstream and produces the deliverable | Best specialist for category |
| Secondary agent | Reviews, researches, tests, or challenges the primary | Mid-tier or specialist model |
| Executor | Performs code edits, commands, migrations, or integrations | Mid-tier coding model or local model |
| Tester | Runs tests, evaluates outputs, finds regressions | Mid-tier model plus deterministic tools |
| Reviewer | Checks architecture, security, quality, and scope | Strong model when risk is high |
| Monitoring agent | Enforces token, cost, latency, loop, and health policies | Small model plus deterministic policy engine |
| Memory curator | Decides what should enter short-term, project, codebase, or durable memory | Small or mid-tier model with strict write policy |
| Human orchestrator | Sets goals, approves risky actions, overrides policies, accepts final output | Sai |

### 2.2 Task lifecycle

`Inbox -> Triage -> Planning -> Ready -> Assigned -> Executing -> Reviewing -> Testing -> Approval -> Done`

Exception states:

`Blocked`, `Paused`, `Budget Hold`, `Needs Input`, `Failed`, `Cancelled`, `Rolled Back`

Every transition must record actor, timestamp, reason, inputs, outputs, policy decision, model, token usage, cost, latency, and related artifacts.

### 2.3 Primary and secondary behavior

- Exactly one primary agent owns a task at a time.
- Zero or more secondary agents can contribute through bounded sub-assignments.
- A secondary cannot overwrite the primary output directly. It submits findings, patches, test results, or objections.
- The Supervisor merges or rejects secondary output and records why.
- Ownership transfer requires a handoff event with current state, remaining work, budget, and acceptance criteria.
- Agents communicate through structured events, not unbounded agent-to-agent chat.

### 2.4 Task picking policy

Agents should not freely grab arbitrary work. The scheduler ranks eligible tasks using:

`priority + dependency readiness + skill match + context locality + deadline pressure + agent availability + expected cost + failure risk`

Hard filters are checked first: permissions, required tools, environment, model policy, concurrency, budget, data classification, and unresolved dependencies.

The UI must show both **why an agent was selected** and **why alternatives were rejected**.

---

## 3. Model routing policy

### 3.1 Routing stages

1. Classify the step: planning, coding, testing, research, review, summarization, or monitoring.
2. Score complexity, uncertainty, risk, context size, latency target, and privacy constraints.
3. Select an allowed model tier from policy.
4. Estimate token and cost envelope before execution.
5. Run with explicit soft and hard limits.
6. Evaluate output confidence and acceptance checks.
7. Escalate, retry, downgrade, or switch provider according to policy.

### 3.2 Default model strategy

| Work category | Default | Escalation condition |
|---|---|---|
| Product planning and architecture | Frontier reasoning model | Conflicting requirements or low confidence |
| Task decomposition | Frontier for first plan, mid-tier for plan maintenance | New dependency or material scope change |
| Routine code execution | Mid-tier coding agent | Two failed attempts, architectural impact, or risky migration |
| Local edits and formatting | Free-tier or local model | Failed validation |
| Unit and integration test generation | Mid-tier coding model | Weak coverage or nondeterministic failures |
| Deterministic test execution | No model | Model only interprets failures |
| Code review | Mid-tier reviewer | Security, auth, billing, data loss, or broad refactor |
| Summaries and status updates | Small or free-tier model | Missing facts or conflicting trace data |
| Monitoring and anomaly triage | Rules first, small model second | Unknown anomaly pattern |
| Final acceptance | Supervisor plus deterministic gates | Human approval for high-risk classes |

### 3.3 Token governor rules

- Allocate tokens per step, not only per task.
- Send the minimum context packet required by the agent contract.
- Prefer retrieval pointers and summaries over full history.
- Cache stable system instructions and codebase maps.
- Stop repeated loops using semantic similarity and repeated tool-call detection.
- Reserve 15 to 25 percent of the run budget for testing, review, and recovery.
- Never spend the recovery reserve during initial planning.
- Downgrade models when confidence is high and risk is low.
- Upgrade only after a failed gate, unresolved ambiguity, or policy trigger.
- Display projected cost before a run and continuously revise the forecast.

---

## 4. Information architecture

### Primary navigation

1. Command Center
2. Work
3. Runs
4. Agents
5. Teams
6. Models
7. Tools
8. Memory
9. Quality
10. Operations
11. Governance
12. Settings

### Global controls

- Workspace and environment selector
- Global search and command palette
- Create task or run
- Emergency stop
- Queue health
- Active agent count
- Current spend versus budget
- Alerts and approval inbox
- User profile and role

---

## 5. Screen-by-screen UI plan

## Screen 1: Command Center

**Purpose:** Answer four questions immediately: what is running, what is stuck, what is expensive, and what needs human action.

**Layout:**

- Top operational strip: active runs, queue depth, blocked tasks, spend today, token burn rate, system health.
- Main left area: live workflow map showing tasks moving between planning, execution, review, and testing.
- Main right area: approval queue, critical alerts, and budget risks.
- Lower area: agent utilization timeline, model mix, recent failures, and completed outcomes.

**Key interactions:**

- Pause all new dispatches without killing active work.
- Drill into a task, agent, model, or incident.
- Approve, reject, or request revision from the queue.
- Filter by project, team, environment, category, or time range.
- Switch between outcome view, cost view, and reliability view.

**Important behavior:** Metrics must link to traces and tasks. A dashboard that only reports numbers is decoration.

---

## Screen 2: Work Kanban

**Purpose:** Show which agent owns each task, where it is in the lifecycle, and why it is waiting.

**Columns:** Inbox, Triage, Planning, Ready, Executing, Reviewing, Testing, Approval, Done. Exception lanes appear as filtered overlays rather than permanent clutter.

**Task card content:**

- Task title and priority
- Primary agent avatar and harness
- Secondary agent count
- Current step and elapsed time
- Model currently in use
- Budget consumed versus allocated
- Confidence and risk badges
- Dependency state
- Latest meaningful event

**Interactions:**

- Drag only when policy allows a transition.
- Open task cockpit in a side panel.
- Assign or replace primary agent.
- Add reviewer or tester.
- Pause, resume, cancel, retry, or clone.
- Bulk actions require a preview of impact and cost.
- Toggle between task-centric and agent-centric swimlanes.

**Agent picking visualization:** Opening the assignment explanation shows ranked candidates, skill match, availability, estimated cost, context locality, and rejection reasons.

---

## Screen 3: Task Intake and Triage

**Purpose:** Convert an idea, issue, requirement, or incoming event into a runnable task contract.

**Sections:**

- Goal and desired outcome
- Source material and attachments
- Constraints and forbidden actions
- Acceptance criteria
- Risk and data classification
- Deadline and priority
- Suggested workflow template
- Estimated complexity, cost, and duration

**AI behavior:** The triage agent can propose missing acceptance criteria and identify ambiguity, but cannot silently invent business requirements.

**Actions:** Save to inbox, start planning, run a cheap feasibility check, request clarification, or attach to an existing project.

---

## Screen 4: Task Cockpit

**Purpose:** Provide the canonical, complete view of a task.

**Header:** Status, owner, priority, risk, deadline, environment, current model, budget, and emergency controls.

**Tabs:**

- Overview: goal, acceptance criteria, progress, blockers, dependencies.
- Plan: step graph, owners, estimates, and gates.
- Live: current reasoning summary, tool activity, terminal output, and agent messages.
- Artifacts: patches, files, reports, screenshots, builds, and test output.
- Trace: full event timeline and model/tool spans.
- Cost: tokens, price, latency, cache hit rate, and forecast.
- Memory: retrieved and written memory with provenance.
- Decisions: routing decisions, approvals, overrides, and rejected alternatives.
- History: retries, rollbacks, prior plans, and state changes.

**Critical control:** â€œWhy is this happening?â€ generates an evidence-linked explanation from current events, policies, and task state.

---

## Screen 5: Planning Studio

**Purpose:** Turn a high-level goal into a validated, dependency-aware execution plan before expensive work starts.

**Layout:**

- Left: requirement and context outline.
- Center: editable DAG of steps and quality gates.
- Right: selected agent, model tier, tools, token budget, expected output, and failure policy for the selected node.
- Bottom: plan critique and simulation results.

**Functions:**

- Generate initial plan with a frontier model.
- Split, merge, reorder, or parallelize steps.
- Mark deterministic steps that need no model.
- Assign primary and secondary agents per node.
- Define input and output schemas.
- Set acceptance checks and retry limits.
- Compare two plans by cost, latency, risk, and quality.
- Simulate dependencies and identify deadlocks.
- Lock approved parts so replanning cannot rewrite them.
- Version every plan change and explain the delta.

**Rule:** Planning ends only when every node has an owner, contract, budget, gate, and failure path.

---

## Screen 6: Live Run Graph

**Purpose:** Make multi-agent execution understandable while it is happening.

**Visualization:** A DAG where node state is encoded by shape and label, not color alone. Edges show data, control, handoff, retry, and review relationships.

**Live details:**

- Running agent and harness
- Model and provider
- Input context size
- Tool currently executing
- Tokens per second and cumulative cost
- Time in state
- Retry count
- Latest structured event

**Controls:** Pause node, pause descendants, skip optional node, retry with same model, retry with alternative model, inspect context, edit budget, request human takeover, or terminate branch.

**Replay:** Scrub through the timeline to reconstruct state at any event without changing the live run.

---

## Screen 7: Agent Registry

**Purpose:** Manage every specialist as a versioned operational component.

**Table fields:** Name, role, status, harness, skill categories, default model policy, active runs, success rate, median cost, last version, and health.

**Functions:**

- Create from template, clone, archive, disable, or canary a version.
- Filter by skill, harness, tool, model compatibility, environment, and trust level.
- Compare performance across agents doing similar work.
- Detect duplicate or overlapping agents.
- Register future agents through a stable adapter contract.

**Onboarding wizard for a new agent:** Identity -> capabilities -> harness adapter -> tools -> memory access -> model policy -> permissions -> evaluation suite -> canary deployment -> production eligibility.

---

## Screen 8: Agent Detail and Builder

**Purpose:** Configure one agent without burying behavior inside a giant system prompt.

**Sections:**

- Identity: name, role, objective, non-goals.
- Contract: accepted inputs, required outputs, structured schema.
- Skills: planning, coding, testing, research, review, deployment, monitoring.
- Harness: Claude, Codex, Hermes, Antigravity, OpenCode, or custom adapter.
- Tools: MCP servers, local tools, shell, browser, repository, database.
- Memory: allowed stores, retrieval policy, write policy, retention.
- Model policy: allowed tiers, defaults, fallbacks, context limits.
- Behavior: autonomy level, retry strategy, communication style, stopping rules.
- Permissions: repositories, branches, environments, secrets, networks, write scopes.
- Guardrails: blocked commands, required approvals, data boundaries.
- Tests: golden tasks, adversarial cases, regression suite.
- Versions: draft, canary, production, deprecated.

**Preview mode:** Run a sandbox task and inspect every prompt, retrieval, tool call, and policy decision before publishing.

---

## Screen 9: Agent Teams and Topology

**Purpose:** Define reusable combinations of agents.

**Views:** Organization chart, workflow graph, responsibility matrix, and capability coverage map.

**Functions:**

- Set Supervisor, primary candidates, reviewers, testers, and fallbacks.
- Define which agents can call or hand off to which agents.
- Set maximum delegation depth and fan-out.
- Prevent circular delegation.
- Configure shared memory and team-specific tools.
- Define quorum rules for high-risk decisions.
- Save team templates such as â€œProduction Featureâ€, â€œBug Fixâ€, â€œResearchâ€, or â€œIncident Responseâ€.

**Coverage check:** Warn when a team lacks planning, execution, testing, review, rollback, or monitoring capability.

---

## Screen 10: Model Catalog

**Purpose:** Treat models as replaceable capacity with measurable behavior.

**Fields:** Provider, model, tier, modalities, context limit, tool support, coding score, reasoning score, latency, input price, output price, rate limits, privacy mode, availability, and last evaluation.

**Functions:**

- Add provider or local endpoint.
- Create aliases such as `frontier-planner`, `mid-code`, or `cheap-summary`.
- Compare models using your own workload evaluations.
- Disable unhealthy models globally or per environment.
- Track model drift, price changes, and regressions.
- Mark preview models as non-production by default.

---

## Screen 11: Routing Policy Studio

**Purpose:** Configure model and agent selection without code changes.

**Rule builder inputs:** Category, risk, complexity, confidence, context size, language, repository, environment, budget remaining, queue pressure, provider health, privacy class, and prior failures.

**Rule outputs:** Model alias, fallback chain, token limits, timeout, retry count, caching, temperature, required reviewer, and approval policy.

**Functions:**

- Priority-ordered rules with conflict detection.
- Dry-run a task against current policies.
- Explain matched and skipped rules.
- Compare proposed policy against historical traces.
- Canary a routing change to a percentage of runs.
- Roll back instantly to a prior version.

**Non-negotiable:** Policies must be versioned and every run must store the version used.

---

## Screen 12: Token and Cost Control

**Purpose:** Give the Monitoring Agent and human operator one place to control consumption.

**Views:** Spend by project, task, agent, model, provider, environment, and workflow step.

**Functions:**

- Daily, weekly, monthly, project, task, run, agent, and step budgets.
- Soft warning, hard stop, and approval thresholds.
- Token allocation between planning, execution, testing, review, and recovery.
- Forecast completion cost based on remaining DAG nodes.
- Detect context bloat, repeated prompts, retry storms, and expensive low-value steps.
- Recommend model downgrades or context compression.
- Reserve budget for tests and rollback.
- Attribute cached and uncached tokens separately.
- Export invoices and internal chargeback reports.

**Monitoring Agent authority:** It can throttle, pause, compress context, choose an allowed cheaper model, or request approval. It cannot remove mandatory quality gates to save money.

---

## Screen 13: Tools and MCP Hub

**Purpose:** Register and govern tools such as Ponytail, Headroom, Obsidian REST MCP, codebase memory, repositories, terminals, browsers, and internal APIs.

**Functions:**

- Tool catalog with schemas, scopes, owner, version, latency, failure rate, and cost.
- MCP server health, connection status, and capability discovery.
- Per-agent allowlists and environment restrictions.
- Secret binding without exposing secret values to models.
- Read-only, write, destructive, and privileged operation classes.
- Approval gates for high-impact calls.
- Idempotency keys and duplicate-call protection.
- Sandbox test console.
- Tool-call trace, inputs, outputs, redactions, and replay metadata.
- Version compatibility and deprecation alerts.

---

## Screen 14: Memory Control Center

**Purpose:** Make memory visible, scoped, correctable, and safe.

**Memory layers:** Run memory, task memory, project memory, user preference memory, codebase memory, tool memory, and durable knowledge.

**Functions:**

- Browse, search, filter, edit, expire, pin, merge, or delete memories.
- Show source, author, timestamp, confidence, scope, embedding version, and consumers.
- Inspect why a memory was retrieved.
- Preview the exact memory packet sent to an agent.
- Detect contradictions, duplicates, stale facts, and sensitive data.
- Set retention and write approval policies.
- Re-index codebase or Obsidian content.
- Roll back memory writes caused by a failed run.
- Separate factual memory from summaries, preferences, and hypotheses.

**Rule:** Every durable memory must have provenance and a deletion path.

---

## Screen 15: Context Inspector

**Purpose:** Explain exactly what an agent knew when it made a decision.

**Panels:** System instructions, task contract, plan node, retrieved memory, code context, prior messages, tool outputs, compressed summaries, token count, and excluded context.

**Functions:**

- Token heatmap by source.
- Diff context between two attempts.
- Show truncation and compression events.
- Remove irrelevant context and rerun in sandbox.
- Pin required context for future steps.
- Detect prompt injection or conflicting instructions.
- Explain why an item was included or excluded.

---

## Screen 16: Prompt, Policy, and Template Library

**Purpose:** Version reusable behavior separately from agent identity.

**Assets:** System instructions, task templates, workflow templates, acceptance checklists, review rubrics, routing policies, and response schemas.

**Functions:** Draft, review, diff, test, approve, publish, canary, deprecate, and roll back.

**Dependencies:** Show every agent and workflow affected before publishing a change.

---

## Screen 17: Approvals and Human Inbox

**Purpose:** Centralize decisions that require Sai instead of scattering interruptions across tools.

**Approval types:** Plan, budget increase, destructive command, secret access, production deploy, merge, policy exception, memory write, tool permission, and final acceptance.

**Approval item content:** Requested action, rationale, alternatives, risk, affected resources, cost impact, evidence, rollback plan, and expiration.

**Actions:** Approve once, approve with constraints, reject, request changes, delegate approval, or create a reusable policy.

**Quality feature:** Batch similar low-risk approvals, but never batch destructive or production actions by default.

---

## Screen 18: Quality and Evaluation Lab

**Purpose:** Prove agents work before production and keep proving it after changes.

**Functions:**

- Golden datasets by agent and workflow.
- Unit evaluations for structured output and tool selection.
- End-to-end task evaluations.
- LLM judges with calibrated rubrics plus deterministic checks.
- Security and prompt injection tests.
- Regression comparison across agent, prompt, model, tool, and policy versions.
- Cost, latency, quality, and reliability scorecards.
- Historical production traces converted into test cases.
- Canary gates and automatic rollback thresholds.
- Human review sampling for uncertain results.

**Rule:** No agent version reaches production without passing its required evaluation pack.

---

## Screen 19: Testing and Verification Console

**Purpose:** Separate code generation from proof that the output works.

**Functions:**

- Test plan linked to acceptance criteria.
- Unit, integration, end-to-end, lint, type, security, performance, and visual test stages.
- Environment setup and fixture status.
- Live logs with structured failure grouping.
- Flaky test detection and quarantine policy.
- Coverage deltas and untested risk areas.
- Tester-agent findings and primary-agent responses.
- Rerun failed tests only, rerun affected suite, or full verification.
- Required evidence bundle before completion.

---

## Screen 20: Artifacts and Deliverables

**Purpose:** Make outputs easy to inspect, compare, approve, and reuse.

**Artifact types:** Plans, patches, commits, branches, pull requests, files, reports, screenshots, recordings, test evidence, builds, deployments, and datasets.

**Functions:** Version history, side-by-side diff, provenance graph, signed checksums, generated-by metadata, dependency links, retention rules, and promotion between environments.

---

## Screen 21: Schedules, Queue, and Capacity

**Purpose:** Control when work runs and prevent resource contention.

**Functions:**

- Queue by priority, deadline, project, and environment.
- Per-agent, per-model, per-provider, and per-tool concurrency limits.
- Scheduled and recurring workflows.
- Quiet hours and maintenance windows.
- Rate-limit awareness and provider backpressure.
- Fairness policy across projects.
- Capacity forecast and estimated start time.
- Dead-letter queue for exhausted retries.
- Manual reorder with impact preview.

---

## Screen 22: Incidents and Recovery

**Purpose:** Detect, contain, understand, and recover from production failures.

**Incident triggers:** Cost spike, retry storm, stuck run, tool outage, provider outage, policy violation, data leak risk, repeated bad output, or environment failure.

**Functions:**

- Severity and affected scope.
- Automatic containment actions.
- Timeline built from run events and infrastructure signals.
- Suspected root cause with evidence.
- Rollback, reroute, quarantine agent, disable tool, or stop environment.
- Recovery checklist and owner.
- Post-incident report generated from evidence.
- Convert incident patterns into policies and regression tests.

---

## Screen 23: Audit, Security, and Governance

**Purpose:** Make every consequential action attributable and reviewable.

**Functions:**

- Role-based and attribute-based access controls.
- Agent service identities and scoped credentials.
- Environment separation for development, staging, and production.
- Immutable audit events.
- Secret access audit without secret values.
- Data classification and residency policies.
- PII and sensitive data redaction.
- Prompt injection detection and untrusted-content boundaries.
- Network and filesystem policies.
- Command allowlists and denylists.
- Approval separation for high-risk actions.
- Session expiry, credential rotation, and emergency revocation.
- Exportable compliance evidence.

---

## Screen 24: Integration and Extension Center

**Purpose:** Add future agents, harnesses, models, tools, memory stores, and event sources without rebuilding the product.

**Extension types:** Agent adapter, harness adapter, model provider, MCP server, memory provider, trigger, artifact store, evaluator, notification channel, and UI panel.

**Adapter contract:**

- Manifest and version
- Capabilities and required permissions
- Input and output schemas
- Health check
- Start, pause, resume, cancel, and status methods
- Streaming event interface
- Token, cost, and latency reporting
- Artifact and trace references
- Error taxonomy
- Compatibility range

**Functions:** Install, configure, permission, sandbox, canary, update, disable, and uninstall.

---

## Screen 25: Settings and Environments

**Purpose:** Configure workspace behavior without mixing global and project-level rules.

**Scopes:** Organization, workspace, project, team, agent, workflow, and environment.

**Functions:** Defaults, inheritance visualization, override detection, notifications, retention, feature flags, regional settings, webhooks, backups, disaster recovery, and API keys.

---

## 6. Shared UI components

- **Agent badge:** identity, harness, status, model, and trust level.
- **Model chip:** alias, concrete model, provider, tier, and fallback state.
- **Budget meter:** allocated, used, reserved, forecast, and hard limit.
- **Confidence indicator:** score, evidence count, and calibration warning.
- **Risk badge:** risk class with the policy that assigned it.
- **Run event row:** actor, action, object, result, duration, cost, and trace link.
- **Handoff panel:** from, to, reason, transferred context, remaining budget, and acceptance criteria.
- **Decision explanation:** selected option, alternatives, evidence, policy, and model contribution.
- **Emergency stop:** clear scope, confirmation, and consequence preview.
- **Diff viewer:** plan, prompt, policy, context, output, memory, and code diffs.

---

## 7. System entities

Minimum canonical entities:

`Workspace`, `Project`, `Task`, `TaskVersion`, `Plan`, `PlanNode`, `Dependency`, `Run`, `RunAttempt`, `Agent`, `AgentVersion`, `Team`, `HarnessAdapter`, `Model`, `ModelAlias`, `RoutingPolicy`, `Tool`, `ToolVersion`, `MemoryItem`, `ContextPacket`, `Artifact`, `Evaluation`, `TestCase`, `Approval`, `Budget`, `CostEntry`, `Trace`, `Event`, `Incident`, `Environment`, `CredentialBinding`, `Policy`, and `User`.

Use immutable IDs and append-only events. Current state should be a projection of events, not the only record of what happened.

---

## 8. Event model

Every event should include:

- Event ID, type, timestamp, schema version
- Workspace, project, task, run, attempt, and node references
- Actor type and actor version
- Previous and next state
- Input and output references, not uncontrolled payload duplication
- Model, provider, tokens, cached tokens, cost, and latency when applicable
- Tool and environment references when applicable
- Policy and decision references
- Correlation, causation, and parent event IDs
- Redaction and data classification metadata
- Error class, retryability, and recovery action

Critical event types:

`task.created`, `plan.generated`, `plan.approved`, `agent.assigned`, `run.started`, `node.started`, `model.selected`, `context.built`, `tool.called`, `handoff.requested`, `handoff.completed`, `budget.warning`, `policy.blocked`, `approval.requested`, `artifact.created`, `test.failed`, `run.paused`, `run.completed`, `memory.written`, `incident.opened`, and `rollback.completed`.

---

## 9. Automation rules to ship

1. Auto-triage incoming work by category, risk, and required capabilities.
2. Generate a first plan for medium and large tasks.
3. Assign a primary agent only after dependency and permission checks.
4. Add a tester for every code-producing task.
5. Add security review for auth, secrets, payments, production data, and permissions.
6. Reserve review and recovery budget before execution.
7. Downgrade the model after the plan is approved unless the step policy requires frontier reasoning.
8. Escalate after two semantically similar failed attempts.
9. Pause on repeated tool calls, token spikes, or no-progress loops.
10. Route around unhealthy providers and tools.
11. Require approval before destructive or production actions.
12. Convert accepted artifacts and incident patterns into evaluations.
13. Write durable memory only after successful completion or explicit review.
14. Produce a final evidence bundle before marking a task done.
15. Compare actual versus estimated cost and feed the error back into routing.

---

## 10. Production-grade nonfunctional requirements

### Reliability

- Durable pause and resume across process restarts.
- Idempotent tool calls and duplicate-event protection.
- Bounded retries with backoff and dead-letter handling.
- Provider and tool circuit breakers.
- Deterministic replay using stored inputs and version references.
- Graceful partial failure for parallel branches.

### Security

- Least-privilege access for every agent and tool.
- Separate credentials from prompts and model-visible context.
- Sandbox code execution by default.
- Egress controls and repository path restrictions.
- Signed and versioned policies.
- Human approval for irreversible actions.

### Performance

- Stream events rather than poll entire task state.
- Virtualize large Kanban and trace views.
- Summarize old events while retaining the immutable originals.
- Cache stable model inputs and codebase indexes.
- Use deterministic code for classification when rules are sufficient.

### Observability

- Trace from user request through agent, model, tool, database, and artifact.
- Quality, cost, latency, reliability, and safety metrics.
- Alerts linked directly to the causal run segment.
- Natural-language trace interrogation backed by evidence links.

---

## 11. UX states required on every operational screen

- Loading skeleton
- Empty first-run state with setup guidance
- Partial data and delayed telemetry
- Provider or tool degraded state
- Permission denied state
- Offline or reconnecting state
- Stale data warning
- Budget exhausted state
- Run paused state
- Error with recovery options
- Archived or unavailable version
- Large-scale overflow with filtering and virtualization

Never hide a failed action behind a toast. Persist operational failures in the relevant task or run timeline.

---

## 12. Visual direction

Use a light, restrained operations interface with tinted neutral surfaces and one strong accent. Avoid a wall of identical cards.

- Kanban for ownership and flow.
- DAG for plan and execution dependencies.
- Timeline for causality.
- Tables for comparison and governance.
- Split panes for inspection and action.
- Color is secondary to labels, icons, and shape.
- Monospace is reserved for code, model IDs, traces, and token data.
- Show details progressively, but keep emergency controls always reachable.
- Desktop is the primary operations surface. Mobile is for monitoring, approvals, pause, and incident response, not plan editing.

---

## 13. Recommended build sequence

### Phase 1: Visible orchestration MVP

Build task intake, Kanban, task cockpit, Planning Studio, live run graph, agent registry, basic model aliases, event stream, manual approvals, and token/cost ledger.

**Success condition:** You can submit one coding task, approve its plan, watch a primary coder and secondary tester execute, inspect every event and artifact, and see cost by step.

### Phase 2: Automated routing and governance

Add Supervisor Agent, policy-based assignment, model router, budget governor, tool permissions, memory inspector, retries, provider failover, and evaluation gates.

**Success condition:** Routine work completes without manual routing while risky actions still stop for approval.

### Phase 3: Production hardening

Add durable replay, sandboxing, security controls, incident response, canary agent versions, advanced evaluations, capacity management, audit exports, and disaster recovery.

**Success condition:** A failed provider, agent, tool, or worker does not lose task state or produce untracked actions.

### Phase 4: Self-optimization

Add historical policy simulation, routing optimization, plan estimation feedback, automatic regression generation, capability gap detection, and extension marketplace.

**Success condition:** The system reduces cost and latency without lowering measured quality or bypassing governance.

---

## 14. First vertical slice

Do not build all 25 screens first. Build one complete path:

1. User creates a coding task with acceptance criteria.
2. Supervisor classifies risk and invokes a frontier Planner.
3. User reviews the DAG in Planning Studio.
4. Scheduler chooses a primary coding agent and secondary testing agent.
5. Model router assigns a mid-tier coding model with a bounded budget.
6. Live Run Graph streams model and tool events.
7. Tester executes deterministic tests and interprets failures.
8. Primary receives a structured revision request if tests fail.
9. Monitoring Agent pauses loops or budget overruns.
10. User approves the final evidence bundle.
11. Successful outcome writes reviewed project and codebase memory.
12. Cost, duration, quality, and routing accuracy feed the evaluation dataset.

This slice proves the architecture. Everything else should extend it, not create a second execution path.

---

## 15. Final recommendation

Your automated replacement should be a **Supervisor Agent backed by a durable, deterministic control plane**. Use Claude Opus, GPT frontier reasoning models, or another high-capability model as interchangeable planning engines, not as the operating system itself. Use mid-tier and free-tier models for bounded coding, testing, summarization, and monitoring only after the plan, context, acceptance criteria, and limits are explicit.

The winning design is not â€œmany agents chatting.â€ It is **many specialists operating under contracts, budgets, evidence, and a visible state machine**.

---

## 16. Reference patterns

- [OpenAI orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [OpenAI Agents SDK orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
- [OpenAI Agents SDK tracing](https://github.com/openai/openai-agents-python/blob/3a11cf52/docs/tracing.md)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LiteLLM routing and load balancing](https://docs.litellm.ai/docs/routing-load-balancing)