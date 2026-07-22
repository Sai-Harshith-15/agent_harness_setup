# Snitch — CRM Product and Agent OS Design Specification

**Status:** Product planning v1
**Owner:** Sai Harshith
**Product:** Snitch — a CRM whose day-to-day operation (lead triage, enrichment, outreach, follow-up, pipeline hygiene, forecasting, support handoff) is run by a governed multi-agent control plane, not by manual rep effort or a single chat bot bolted onto a database.
**Relationship to Agent OS:** Snitch is the first production vertical built on the Agent OS control plane described in `agent-os-ui-product-spec.md`. Agent OS is the engine (Supervisor, Planner, specialists, router, monitor, memory). Snitch is the domain: its entities are `Contact`, `Company`, `Deal`, `Activity`, `Email`, `Note`, `Campaign`, and `Ticket` instead of generic `Task`/`Run` software-engineering objects. Every mechanism below (task lifecycle, routing, budgets, approvals, evidence) is the same kernel, retargeted.

---

## 1. Product decision

Do not make a single model or a single "AI SDR" bot the permanent brain of the CRM. Sales, enrichment, outreach, and forecasting are different jobs with different risk levels, cost profiles, and failure modes.

Build a **Supervisor Agent** as the CRM's operating layer. It is a role inside Agent OS, not a vendor model, and it:

1. Runs a deterministic workflow engine for record state, retries, approvals, quotas, and lifecycle rules (a lead or deal is a durable state machine, not a chat thread).
2. Calls a frontier reasoning model only when a decision is genuinely ambiguous — e.g., is this a real buying signal, is this deal actually at risk.
3. Uses a policy-driven model router that picks the cheapest model capable of the current CRM step (drafting a follow-up email is not the same cost class as qualifying a six-figure deal).
4. Delegates to specialist agents with explicit contracts: enrichment, sequencing, drafting, scoring, forecasting, data hygiene.
5. Runs a Monitoring Agent that can pause, downgrade, reroute, or escalate, but cannot silently change a quota, discount a deal, or send an email without the policy allowing it.

**Recommended control pattern:** the Supervisor owns the record (contact, deal, ticket); specialist agents act as tools against that record. Ownership transfer between agents (e.g., SDR agent hands a qualified lead to an AE agent) is an explicit handoff event, never an implicit chat handout.

### Suggested foundation

- **Orchestration runtime:** LangGraph or an equivalent durable state machine, since deals and nurture sequences are long-running and must survive pause/resume across days or weeks.
- **Agent protocol layer:** OpenAI Agents SDK-style tools, handoffs, and guardrails, wrapped behind Snitch's own contracts so the CRM logic never depends on one vendor's SDK shape.
- **Model gateway:** LiteLLM or an internal gateway for provider normalization, retries, cooldowns, fallback, and per-workspace budget routing.
- **Durability:** PostgreSQL for canonical CRM state and event history (contacts, deals, activities are the system of record — not a vector store); Redis plus a worker queue for sequence scheduling, reminders, and concurrency.
- **Observability:** OpenTelemetry-compatible traces, append-only CRM event log, cost ledger per workspace/team/rep, and full send/enrichment audit trail.
- **UI:** Next.js with server-sent events or WebSockets so pipeline boards and live agent activity update without polling.

The orchestration kernel stays independent of any single email provider, enrichment vendor, or calling tool. Gmail/Outlook, Clearbit/Apollo-style enrichment, dialers, and calendar systems connect through adapters so a new channel can be added without touching the workflow engine.

---

## 2. Core operating model

### 2.1 Responsibilities

| Role | Responsibility | Typical model class |
|---|---|---|
| Supervisor | Owns the contact/deal outcome, decomposes work (qualify, enrich, engage, close), resolves conflicting agent output | Frontier for ambiguous calls, rules for routine routing |
| Planner (Sequencer) | Produces the outreach/nurture plan and success criteria for a lead or deal | Frontier reasoning model |
| Primary agent (Rep Agent) | Owns one contact or deal and drives it forward (drafts, schedules, updates stage) | Best specialist for the segment (SDR-style vs. enterprise AE-style) |
| Secondary agent (Enrichment/Research) | Enriches firmographic/contact data, researches signals, challenges the primary's read on the account | Mid-tier or specialist model |
| Executor | Sends emails, logs calls, updates CRM fields, schedules meetings through connected tools | Mid-tier model or deterministic tool call |
| Tester (Data QA) | Validates record hygiene, dedupe, required-field completeness, deliverability | Mid-tier model plus deterministic tools |
| Reviewer (Deal Desk) | Checks discounting, contract terms, compliance-sensitive language, and enterprise deal risk | Strong model when deal size or risk is high |
| Monitoring agent | Enforces send-volume, cost, latency, spam/complaint, and loop policies | Small model plus deterministic policy engine |
| Memory curator | Decides what enters contact memory, account memory, or durable playbook memory | Small or mid-tier model with strict write policy |
| Human orchestrator | Sets quota/goals, approves risky sends and discounts, overrides policy, accepts final deal outcomes | Sai / sales leadership |

### 2.2 Record lifecycle

`Inbox -> Triage -> Enrichment -> Qualified -> Assigned -> Engaging -> Nurturing -> Proposal -> Negotiation -> Won/Lost`

Exception states:

`Blocked` (missing data), `Snoozed`, `Needs Input` (human reply required), `Bounced/Undeliverable`, `Disqualified`, `Escalated`, `Compliance Hold`

Every transition records actor, timestamp, reason, inputs, outputs, policy decision, model used, token/cost, latency, and linked artifacts (email sent, call logged, field changed).

### 2.3 Primary and secondary behavior

- Exactly one agent (or human rep) owns a contact/deal at a time.
- Zero or more secondary agents contribute bounded sub-work: enrichment, research, drafting alternatives, deliverability checks.
- A secondary cannot send an email, change deal stage, or edit a field directly. It submits a proposed draft, enrichment result, or objection.
- The Supervisor merges or rejects secondary output and records why (e.g., "rejected enrichment: conflicting company size signal, kept existing value").
- Ownership transfer (SDR agent -> AE agent, or agent -> human rep) requires a handoff event with current state, remaining playbook steps, budget, and the qualification criteria met so far.
- Agents communicate through structured CRM events (field changes, logged activities, draft proposals), never unbounded agent-to-agent chat.

### 2.4 Record/task picking policy

Agents do not freely grab any lead or deal. The scheduler ranks eligible work using:

`lead score + reply/engagement recency + deal value + stage deadline pressure + rep/agent territory match + context locality (existing relationship) + expected cost to advance + risk of over-contact`

Hard filters checked first: do-not-contact/consent flags, territory and account ownership rules, required tools (email/calendar connected), model policy for the account's data classification, concurrency (max active sequences per contact), budget, and unresolved dependencies (e.g., waiting on enrichment before drafting).

The UI must show both **why an agent picked this contact/deal next** and **why others were skipped** — reps stop trusting an "AI SDR" the moment it looks random.

---

## 3. Model routing policy

### 3.1 Routing stages

1. Classify the step: qualification, enrichment, drafting, sequencing, objection handling, forecasting, deal risk review, or reporting.
2. Score complexity, ambiguity, deal risk, contact/account sensitivity, and turnaround target.
3. Select an allowed model tier from policy.
4. Estimate token/cost envelope before sending anything to the model (and before any external send).
5. Run with explicit soft and hard limits.
6. Evaluate output confidence and acceptance checks (tone match, factual accuracy against CRM record, no invented commitments).
7. Escalate, retry, downgrade, or route to human draft according to policy.

### 3.2 Default model strategy

| Work category | Default | Escalation condition |
|---|---|---|
| Account/deal qualification and ICP fit | Frontier reasoning model | Conflicting signals or borderline ICP fit |
| Sequence/playbook generation | Frontier for first sequence, mid-tier for maintenance | New objection type or material ICP change |
| Routine outreach drafting (cold, follow-up, nurture) | Mid-tier writing model | Two rejected drafts, enterprise account, or sensitive topic (pricing, legal) |
| Field cleanup, dedupe suggestions, formatting | Free-tier or local model | Failed validation or ambiguous duplicate match |
| Contact/company enrichment synthesis | Mid-tier model | Conflicting source data or low-confidence match |
| Data hygiene / required-field / deliverability checks | No model (deterministic) | Model only interprets ambiguous failures |
| Objection handling and negotiation drafting | Mid-tier, escalate for enterprise | Discount request, legal language, churn-risk account |
| Deal risk / forecast commentary | Mid-tier reviewer | High ACV, stalled stage, or executive-visible deal |
| Meeting summaries and activity logging | Small or free-tier model | Missing facts vs. transcript or conflicting notes |
| Monitoring and anomaly triage (spam complaints, bounce spikes) | Rules first, small model second | Unknown anomaly pattern |
| Final send / stage-change acceptance | Supervisor plus deterministic gates | Human approval for high-risk sends (new domain, large discount, contract stage) |

### 3.3 Token/cost governor rules

- Allocate budget per sequence step, not only per contact/deal.
- Send the minimum context packet: current record fields, last N relevant activities, active playbook step — not the entire contact history by default.
- Prefer retrieval pointers (contact memory, account memory) over dumping full email threads.
- Cache stable system instructions, brand voice guide, and product/pricing facts.
- Stop repeated-loop drafting using semantic similarity detection (agent should not regenerate the same follow-up five times).
- Reserve 15–25% of a sequence's budget for objection handling and recovery steps; never spend that reserve during initial outreach drafting.
- Downgrade models once a sequence is running smoothly with high acceptance rate and low deal risk.
- Upgrade only after a rejected draft, an unresolved objection, or a policy trigger (deal value crosses a threshold).
- Display projected sequence cost before launch and revise continuously as replies come in.

---

## 4. Information architecture

### Primary navigation

1. Command Center
2. Contacts
3. Companies
4. Deals (Pipeline)
5. Activities & Inbox
6. Sequences & Automations
7. Reports
8. Agents
9. Teams
10. Models
11. Tools
12. Memory
13. Quality
14. Operations
15. Governance
16. Settings

### Global controls

- Workspace and territory selector
- Global search and command palette (contact, company, deal, email)
- Create contact / deal / sequence
- Emergency stop (halt all sends)
- Queue health (sequences pending, replies unhandled)
- Active agent count
- Current send/enrichment spend versus budget
- Alerts and approval inbox
- User profile and role (rep, manager, admin)

---

## 5. Screen-by-screen UI plan

## Screen 1: Command Center

**Purpose:** Answer four questions immediately: what's being worked, what's stuck, what's expensive, and what needs a human.

**Layout:**

- Top strip: active sequences, replies awaiting response, deals at risk, spend today, send volume, deliverability health.
- Main left: live pipeline map — contacts/deals moving through triage, enrichment, engaging, nurturing, closing.
- Main right: approval queue (sends, discounts, stage changes needing sign-off), critical alerts (bounce spike, spam complaint), budget risks.
- Lower area: agent utilization timeline, model mix, recent failed sends/rejected drafts, and deals closed.

**Key interactions:**

- Pause all new outbound without stopping in-flight replies.
- Drill into a contact, deal, agent, model, or incident.
- Approve, reject, or request a revised draft from the queue.
- Filter by territory, team, segment, or time range.
- Switch between pipeline view, cost view, and deliverability view.

**Important behavior:** Every metric links to the underlying contact/deal/trace. A number with no drill-through is decoration.

---

## Screen 2: Pipeline (Deals Kanban)

**Purpose:** Show which agent or rep owns each deal, where it sits in the pipeline, and why it's stalled.

**Columns:** New, Qualifying, Enriching, Assigned, Engaging, Nurturing, Proposal, Negotiation, Closed Won, Closed Lost. Exception states (Blocked, Compliance Hold, Escalated) appear as filtered overlays.

**Deal card content:**

- Deal name, company, value, close date
- Primary agent/rep avatar and channel (agent-run vs. human-run)
- Secondary agent count (enrichment/research active)
- Current sequence step and elapsed time
- Model currently drafting/analyzing
- Budget consumed versus allocated for this deal
- Confidence and risk badges (deal-risk score)
- Dependency state (waiting on reply, waiting on legal, waiting on enrichment)
- Latest meaningful activity

**Interactions:**

- Drag only when policy allows the stage transition (e.g., can't jump to Negotiation without a logged proposal).
- Open deal cockpit in a side panel.
- Assign or replace primary agent/rep.
- Add a research or deal-desk reviewer.
- Pause, resume, cancel, retry, or clone a sequence.
- Bulk actions (e.g., re-sequence 30 stalled deals) require a preview of impact and cost.
- Toggle between deal-centric and rep/agent-centric swimlanes.

**Agent picking visualization:** Opening the assignment explanation shows ranked candidate reps/agents, territory match, availability, estimated cost to advance, relationship history, and rejection reasons.

---

## Screen 3: Lead Intake and Triage

**Purpose:** Convert an inbound form fill, list import, referral, or signal event into a qualified, workable contact/deal.

**Sections:**

- Source and channel (form, import, referral, intent signal, event)
- Contact and company snapshot
- Consent/do-not-contact status
- ICP fit and disqualification reasons
- Suggested segment and playbook template
- Estimated deal potential and priority
- Territory/owner match

**AI behavior:** The triage agent can propose an ICP score and flag missing firmographic data, but cannot silently mark a lead disqualified without a recorded reason, and cannot invent company facts it hasn't verified through enrichment.

**Actions:** Save to inbox, start enrichment, run a cheap fit check, request clarification (route to human), or attach to an existing account.

---

## Screen 4: Deal Cockpit

**Purpose:** The canonical, complete view of one deal or contact relationship.

**Header:** Stage, owner (agent/rep), value, risk, close date, territory, current model, budget, and emergency stop.

**Tabs:**

- Overview: goal (close/expand/renew), qualification criteria, progress, blockers, dependencies.
- Plan: sequence/playbook steps, owners, estimated timing, and gates (e.g., "no proposal without deal-desk review above $50k").
- Live: current agent reasoning summary, tool activity (email sent, calendar checked), and draft in progress.
- Artifacts: sent emails, call logs, meeting notes, proposals, contracts, screenshots.
- Trace: full event timeline — every field change, send, and model/tool span.
- Cost: tokens, price, latency, cache hit rate, and forecast to close.
- Memory: retrieved and written contact/account memory with provenance.
- Decisions: routing decisions, approvals, overrides, and rejected draft alternatives.
- History: retries, re-sequences, prior stage changes, and reopened deals.

**Critical control:** "Why is this happening?" generates an evidence-linked explanation (e.g., "agent paused outreach because contact replied 'not now' — nurture sequence scheduled in 60 days per policy").

---

## Screen 5: Playbook Studio

**Purpose:** Turn a segment/ICP definition into a validated, dependency-aware sequence before expensive outreach starts.

**Layout:**

- Left: segment definition, ICP criteria, and messaging pillars.
- Center: editable DAG of sequence steps (touch 1, wait, touch 2, call task, wait, breakup email) and quality gates.
- Right: selected agent, model tier, tools (email/calendar/dialer), token budget, expected output, and failure policy for the selected step.
- Bottom: playbook critique (spam-trigger check, tone check) and simulated reply-rate estimate.

**Functions:**

- Generate an initial playbook with a frontier model from a segment brief.
- Split, merge, reorder, or parallelize touches (email + LinkedIn + call).
- Mark deterministic steps that need no model (e.g., scheduled reminder).
- Assign primary (rep agent) and secondary (research/enrichment) agents per step.
- Define input/output schemas (what fields must be filled before drafting).
- Set acceptance checks (no pricing claims without approval, no false urgency) and retry limits.
- Compare two playbook variants by reply rate, cost, and risk (A/B).
- Simulate a segment through the playbook and identify deadlocks (e.g., step needs a phone number no contact has).
- Lock approved parts so replanning can't silently rewrite an active sequence.
- Version every playbook change and explain the delta.

**Rule:** A playbook goes live only when every step has an owner, message contract, budget, gate, and failure path (what happens on no reply, on bounce, on opt-out).

---

## Screen 6: Live Agent Activity Graph

**Purpose:** Make multi-agent CRM execution understandable while it's happening.

**Visualization:** A DAG where node state is encoded by shape and label, not color alone. Edges show data, control, handoff, retry, and review relationships between agents working a deal.

**Live details:**

- Running agent and channel (email/call/enrichment)
- Model and provider
- Input context size (fields + recent activity pulled in)
- Tool currently executing (send email, fetch enrichment, log call)
- Tokens per second and cumulative cost
- Time in state
- Retry count
- Latest structured event (draft rejected, reply received, meeting booked)

**Controls:** Pause node, pause descendants, skip optional step, retry with same model, retry with alternative model, inspect context, edit budget, request human takeover, or terminate the sequence.

**Replay:** Scrub through the timeline to reconstruct the deal's state at any past event without touching the live sequence.

---

## Screen 7: Agent Registry

**Purpose:** Manage every specialist (SDR agent, AE agent, enrichment agent, deal-desk reviewer) as a versioned operational component.

**Table fields:** Name, role, status, channel/harness, skill categories (cold outreach, enterprise nurture, renewal), default model policy, active deals, reply/win rate, median cost per deal, last version, health.

**Functions:**

- Create from template, clone, archive, disable, or canary a version.
- Filter by segment, channel, tool, model compatibility, territory, and trust level.
- Compare performance across agents working similar segments.
- Detect duplicate or overlapping agent responsibilities (two agents both drafting cold outreach to the same segment).
- Register future agents (support-ticket agent, renewal agent) through a stable adapter contract.

**Onboarding wizard for a new agent:** Identity -> capabilities -> channel adapter (email/dialer/calendar) -> tools -> memory access -> model policy -> permissions (send limits, discount limits) -> evaluation suite -> canary deployment -> production eligibility.

---

## Screen 8: Agent Detail and Builder

**Purpose:** Configure one agent without burying behavior inside a giant system prompt.

**Sections:**

- Identity: name, role (SDR, AE, CSM, deal desk), objective, non-goals (e.g., "never quote a discount").
- Contract: accepted inputs (contact/deal record shape), required outputs (draft, field update, escalation).
- Skills: qualification, enrichment, drafting, sequencing, objection handling, forecasting, hygiene.
- Channel: email provider, calendar, dialer, CRM adapter, or custom integration.
- Tools: MCP servers, enrichment APIs, calendar, e-signature, Slack notifications.
- Memory: allowed stores (contact memory, account memory, playbook memory), retrieval policy, write policy, retention.
- Model policy: allowed tiers, defaults, fallbacks, context limits.
- Behavior: autonomy level (draft-only vs. auto-send), retry strategy, tone/voice, stopping rules (opt-out, no-reply-after-N).
- Permissions: send limits per day, discount authority, deal-size ceiling before human review, data scope.
- Guardrails: blocked phrases/claims, required approvals (pricing, legal, enterprise), data boundaries (no PII to unapproved tools).
- Tests: golden sequences, adversarial replies (angry customer, price objection), regression suite.
- Versions: draft, canary, production, deprecated.

**Preview mode:** Run a sandbox contact through the agent and inspect every prompt, retrieval, tool call, and policy decision before publishing — including a simulated reply thread.

---

## Screen 9: Teams and Territory Topology

**Purpose:** Define reusable combinations of agents and reps by territory or segment.

**Views:** Org chart, sequence-ownership graph, responsibility matrix, and capability coverage map.

**Functions:**

- Set Supervisor, primary agent/rep candidates, reviewers (deal desk), and fallbacks per territory.
- Define which agents can hand off to which (SDR agent -> AE agent -> CSM agent).
- Set maximum delegation depth and fan-out (no more than 3 hops before human review).
- Prevent circular handoffs.
- Configure shared memory (account-level) and team-specific tools.
- Define quorum rules for high-risk decisions (large discount requires two approvers).
- Save team templates such as "SMB Outbound," "Enterprise Land-and-Expand," "Renewal Motion," or "Win-Back."

**Coverage check:** Warn when a territory lacks enrichment, drafting, deal-desk review, or renewal coverage.

---

## Screen 10: Model Catalog

**Purpose:** Treat models as replaceable capacity with measured behavior on CRM tasks specifically (tone quality, factual grounding to CRM data, cost).

**Fields:** Provider, model, tier, modalities, context limit, tool support, writing-quality score, reasoning score, latency, input/output price, rate limits, privacy mode, availability, last evaluation.

**Functions:**

- Add provider or local endpoint.
- Create aliases such as `frontier-qualifier`, `mid-draft-writer`, `cheap-summary`.
- Compare models using Snitch's own workload evaluations (reply-worthy draft rate, factual accuracy against CRM fields).
- Disable unhealthy models globally or per environment.
- Track model drift, price changes, and regressions.
- Mark preview models as non-production by default.

---

## Screen 11: Routing Policy Studio

**Purpose:** Configure model and agent selection without code changes.

**Rule builder inputs:** Work category, deal risk, ICP tier, confidence, context size, territory, environment, budget remaining, queue pressure, provider health, data classification, prior rejected drafts.

**Rule outputs:** Model alias, fallback chain, token limits, timeout, retry count, caching, temperature, required reviewer, approval policy.

**Functions:**

- Priority-ordered rules with conflict detection.
- Dry-run a contact/deal against current policies.
- Explain matched and skipped rules.
- Compare a proposed policy against historical outcomes (would this rule have changed past deals?).
- Canary a routing change to a percentage of new sequences.
- Roll back instantly to a prior version.

**Non-negotiable:** Policies are versioned and every sequence step stores the version used.

---

## Screen 12: Token and Cost Control

**Purpose:** Give the Monitoring Agent and revenue ops one place to control consumption.

**Views:** Spend by territory, segment, deal, agent, model, provider, and sequence step.

**Functions:**

- Daily, weekly, monthly, territory, segment, deal, and per-step budgets.
- Soft warning, hard stop, and approval thresholds.
- Token allocation between qualification, enrichment, drafting, objection handling, and recovery.
- Forecast cost-to-close based on remaining playbook steps.
- Detect context bloat, repeated draft regeneration, reply-storm handling, and expensive low-value enrichment calls.
- Recommend model downgrades or context trimming (e.g., stop pulling full email history into every draft).
- Reserve budget for objection handling and win-back attempts.
- Attribute cached vs. uncached tokens separately.
- Export invoices and per-team chargeback reports.

**Monitoring Agent authority:** It can throttle sends, pause a sequence, compress context, or choose an allowed cheaper model. It cannot skip a required deal-desk review or a compliance hold to save money.

---

## Screen 13: Tools and MCP Hub

**Purpose:** Register and govern tools such as email/calendar providers, enrichment vendors (Clearbit/Apollo-style), e-signature, dialers, Slack, Obsidian REST MCP (playbook/knowledge notes), and internal APIs.

**Functions:**

- Tool catalog with schemas, scopes, owner, version, latency, failure rate, and cost.
- MCP server health, connection status, and capability discovery.
- Per-agent allowlists (which agents can send email vs. only draft).
- Secret binding (API keys, OAuth tokens) without exposing values to models.
- Read-only, write, destructive, and privileged operation classes (send email = write; delete contact = destructive).
- Approval gates for high-impact calls (bulk send, bulk delete, contract send).
- Idempotency keys and duplicate-send protection.
- Sandbox test console (send to a test inbox before going live).
- Tool-call trace, inputs, outputs, redactions, and replay metadata.
- Version compatibility and deprecation alerts.

---

## Screen 14: Memory Control Center

**Purpose:** Make contact/account memory visible, scoped, correctable, and safe.

**Memory layers:** Sequence memory, contact memory, account memory, rep/agent preference memory, playbook memory, tool memory, and durable knowledge (won-deal patterns, objection library).

**Functions:**

- Browse, search, filter, edit, expire, pin, merge, or delete memories.
- Show source, author, timestamp, confidence, scope, embedding version, and consumers.
- Inspect why a memory was retrieved (e.g., "pulled prior objection: 'too expensive' from account memory").
- Preview the exact memory packet sent to an agent before it drafts.
- Detect contradictions, duplicates, stale facts (old job title, old company size), and sensitive data.
- Set retention and write approval policies (e.g., never write inferred personal facts without a source).
- Re-index Obsidian playbook notes or enrichment data.
- Roll back memory writes caused by a bad sequence or bad enrichment match.
- Separate factual memory (verified firmographic data) from summaries, preferences, and hypotheses (inferred buying intent).

**Rule:** Every durable memory has provenance and a deletion path — required for consent/right-to-be-forgotten requests.

---

## Screen 15: Context Inspector

**Purpose:** Explain exactly what an agent knew when it drafted an email or changed a deal stage.

**Panels:** System instructions, playbook step contract, retrieved contact/account memory, CRM field snapshot, prior activity/messages, tool outputs (enrichment result), compressed summaries, token count, and excluded context.

**Functions:**

- Token heatmap by source.
- Diff context between two draft attempts.
- Show truncation and compression events.
- Remove irrelevant context and rerun in sandbox (e.g., "what if it hadn't seen the old objection?").
- Pin required context for future steps (e.g., always include the signed NDA status).
- Detect prompt injection from inbound email content or conflicting instructions.
- Explain why an item was included or excluded from the draft context.

---

## Screen 16: Prompt, Policy, and Template Library

**Purpose:** Version reusable behavior (voice, message templates, policies) separately from agent identity.

**Assets:** System instructions, message templates (cold, follow-up, breakup, renewal), playbook templates, qualification checklists, deal-desk review rubrics, routing policies, and response schemas.

**Functions:** Draft, review, diff, test, approve, publish, canary, deprecate, and roll back.

**Dependencies:** Show every agent and active sequence affected before publishing a template or voice change.

---

## Screen 17: Approvals and Human Inbox

**Purpose:** Centralize decisions that require a human instead of scattering interruptions across email and Slack.

**Approval types:** Discount/pricing exception, contract send, bulk send, new-domain send, enterprise stage change, data-consent exception, secret/credential access, memory write correction, tool permission, and final deal acceptance.

**Approval item content:** Requested action, rationale, alternatives considered, risk, affected contacts/companies, cost impact, evidence (draft, prior thread), rollback plan, and expiration.

**Actions:** Approve once, approve with constraints, reject, request changes, delegate approval, or create a reusable policy.

**Quality feature:** Batch similar low-risk approvals (e.g., 20 routine follow-ups), but never batch discount, contract, or bulk-send actions by default.

---

## Screen 18: Quality and Evaluation Lab

**Purpose:** Prove agents draft and qualify well before production, and keep proving it after changes.

**Functions:**

- Golden datasets by agent and playbook (known-good sequences, known objection replies).
- Unit evaluations for structured output (correct field extraction, correct next-step selection).
- End-to-end sequence evaluations (simulated multi-touch runs against synthetic personas).
- LLM judges with calibrated rubrics (tone match, factual grounding to CRM record) plus deterministic checks (no banned claims, no missing unsubscribe link).
- Prompt injection and adversarial-reply tests (angry customer, phishing-style reply, jailbreak attempt).
- Regression comparison across agent, prompt, model, tool, and policy versions.
- Cost, latency, reply-rate, and win-rate scorecards.
- Historical production sequences converted into test cases.
- Canary gates and automatic rollback thresholds (e.g., spam-complaint rate spike).
- Human review sampling for uncertain drafts.

**Rule:** No agent version reaches production without passing its required evaluation pack.

---

## Screen 19: Testing and Verification Console

**Purpose:** Separate draft/field-update generation from proof that it's correct and safe to send.

**Functions:**

- Verification plan linked to qualification/acceptance criteria.
- Stages: factual accuracy (vs. CRM record), tone/brand check, deliverability/spam check, compliance check (CAN-SPAM/GDPR consent), link/attachment validation, visual check for proposal documents.
- Environment/sandbox setup (test inbox, test calendar) status.
- Live logs with structured failure grouping (bounce, spam-flag, broken merge field).
- Flaky-check detection (enrichment source disagreement) and quarantine policy.
- Coverage deltas and untested risk areas (new objection type with no golden example).
- Reviewer-agent findings and primary-agent responses.
- Rerun failed checks only, rerun affected sequence, or full re-verification.
- Required evidence bundle before a send is marked complete.

---

## Screen 20: Artifacts and Deliverables

**Purpose:** Make CRM outputs easy to inspect, compare, approve, and reuse.

**Artifact types:** Playbooks, email drafts/sends, call logs and transcripts, meeting notes, proposals, contracts, enrichment reports, screenshots, recordings, and exported datasets.

**Functions:** Version history, side-by-side diff (draft v1 vs. v2), provenance graph, signed checksums for contracts, generated-by metadata, dependency links, retention rules, and promotion between sandbox/production.

---

## Screen 21: Schedules, Queue, and Capacity

**Purpose:** Control when outreach runs and prevent resource contention or over-contact.

**Functions:**

- Queue by priority, deal value, territory, and deadline (renewal date, contract expiry).
- Per-agent, per-model, per-provider, and per-mailbox concurrency/send-rate limits.
- Scheduled and recurring sequences (quarterly check-ins, renewal reminders).
- Quiet hours, time-zone-aware sending, and holiday windows.
- Rate-limit awareness and provider backpressure (email provider throttling).
- Fairness policy across territories/segments.
- Capacity forecast and estimated time-to-first-touch for new leads.
- Dead-letter queue for exhausted retries (bounced, unreachable).
- Manual reorder with impact preview.

---

## Screen 22: Incidents and Recovery

**Purpose:** Detect, contain, understand, and recover from production failures.

**Incident triggers:** Spam-complaint spike, bounce-rate spike, retry storm, stuck sequence, enrichment provider outage, email/calendar provider outage, policy violation (unapproved discount sent), data-leak risk (PII to wrong tool), or repeated bad drafts.

**Functions:**

- Severity and affected scope (contacts, deals, territory).
- Automatic containment actions (pause sending domain-wide, quarantine agent).
- Timeline built from CRM events and infrastructure signals.
- Suspected root cause with evidence.
- Rollback, reroute, quarantine agent, disable tool, or stop a sequence.
- Recovery checklist and owner.
- Post-incident report generated from evidence.
- Convert incident patterns into policies and regression tests (e.g., new golden case for the objection that triggered the bad draft).

---

## Screen 23: Audit, Security, and Governance

**Purpose:** Make every consequential CRM action attributable and reviewable.

**Functions:**

- Role-based and attribute-based access controls (rep, manager, admin, agent service identity).
- Agent service identities and scoped credentials (an agent's email-send credential is scoped and rotatable).
- Environment separation for sandbox, staging, and production sending.
- Immutable audit events for every send, field change, and stage transition.
- Secret access audit without secret values.
- Data classification and residency policies (contact PII, contract terms).
- PII and sensitive-data redaction in traces and logs.
- Prompt injection detection and untrusted-content boundaries (inbound email/reply content treated as untrusted).
- Network and integration policies (which tools an agent can reach).
- Send/action allowlists and denylists (banned claims, banned discount language).
- Approval separation for high-risk actions (no single agent both proposes and approves a large discount).
- Session expiry, credential rotation, and emergency revocation.
- Exportable compliance evidence (consent records, opt-out handling, CAN-SPAM/GDPR evidence).

---

## Screen 24: Integration and Extension Center

**Purpose:** Add future channels, agents, models, tools, memory stores, and event sources without rebuilding the product.

**Extension types:** Agent adapter, channel adapter (new email/dialer provider), model provider, MCP server, memory provider, trigger (webhook, intent signal), artifact store, evaluator, notification channel, and UI panel.

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

**Purpose:** Configure workspace behavior without mixing global, territory, and team rules.

**Scopes:** Organization, workspace, territory, team, agent, playbook, and environment.

**Functions:** Defaults, inheritance visualization, override detection, notifications, retention, feature flags, regional/data-residency settings, webhooks, backups, disaster recovery, and API keys.

---

## 6. Shared UI components

- **Agent badge:** identity, channel, status, model, and trust level.
- **Model chip:** alias, concrete model, provider, tier, and fallback state.
- **Budget meter:** allocated, used, reserved, forecast, and hard limit.
- **Confidence indicator:** score, evidence count, and calibration warning.
- **Risk badge:** deal/contact risk class with the policy that assigned it.
- **Activity event row:** actor, action, object (email/call/field), result, duration, cost, and trace link.
- **Handoff panel:** from, to, reason, transferred context, remaining budget, and qualification criteria met.
- **Decision explanation:** selected option, alternatives, evidence, policy, and model contribution.
- **Emergency stop:** clear scope (this deal / this territory / all sending), confirmation, and consequence preview.
- **Diff viewer:** playbook, prompt, policy, context, draft, memory, and field-change diffs.

---

## 7. System entities

Minimum canonical entities:

`Workspace`, `Territory`, `Contact`, `Company`, `Deal`, `DealVersion`, `Playbook`, `PlaybookStep`, `Dependency`, `Sequence`, `SequenceAttempt`, `Agent`, `AgentVersion`, `Team`, `ChannelAdapter`, `Model`, `ModelAlias`, `RoutingPolicy`, `Tool`, `ToolVersion`, `MemoryItem`, `ContextPacket`, `Activity`, `Email`, `Note`, `Artifact`, `Evaluation`, `TestCase`, `Approval`, `Budget`, `CostEntry`, `Trace`, `Event`, `Incident`, `Environment`, `CredentialBinding`, `Policy`, and `User`.

Use immutable IDs and append-only events. Current CRM state (deal stage, contact status) should be a projection of events, not the only record of what happened.

---

## 8. Event model

Every event should include:

- Event ID, type, timestamp, schema version
- Workspace, territory, contact/company, deal, sequence, and step references
- Actor type and actor version
- Previous and next state
- Input and output references, not uncontrolled payload duplication
- Model, provider, tokens, cached tokens, cost, and latency when applicable
- Tool and channel references when applicable
- Policy and decision references
- Correlation, causation, and parent event IDs
- Redaction and data classification metadata
- Error class, retryability, and recovery action

Critical event types:

`contact.created`, `deal.created`, `playbook.generated`, `playbook.approved`, `agent.assigned`, `sequence.started`, `step.started`, `model.selected`, `context.built`, `tool.called`, `email.sent`, `email.bounced`, `reply.received`, `handoff.requested`, `handoff.completed`, `budget.warning`, `policy.blocked`, `approval.requested`, `artifact.created`, `verification.failed`, `sequence.paused`, `deal.stage_changed`, `deal.won`, `deal.lost`, `memory.written`, `incident.opened`, and `rollback.completed`.

---

## 9. Automation rules to ship

1. Auto-triage incoming leads by ICP fit, source, and consent status.
2. Generate a first playbook for every newly qualified segment or enterprise deal.
3. Assign a primary agent/rep only after territory and permission checks.
4. Add a deal-desk reviewer for every deal above the discount/ACV threshold.
5. Add compliance review for pricing, legal, security, and enterprise contract language.
6. Reserve objection-handling and recovery budget before launching a sequence.
7. Downgrade the model after a playbook is approved unless the step policy requires frontier reasoning (e.g., objection handling on a large deal).
8. Escalate to a human after two semantically similar rejected drafts or two unanswered breakup attempts.
9. Pause on repeated tool calls, token spikes, spam-complaint upticks, or no-reply loops.
10. Route around unhealthy email/enrichment providers.
11. Require approval before discount, contract send, bulk send, or new-domain send.
12. Convert accepted drafts, won deals, and incident patterns into evaluation golden cases.
13. Write durable contact/account memory only after a verified reply or explicit review — never from unverified inference.
14. Produce a final evidence bundle (consent, sends, replies, approvals) before marking a deal closed.
15. Compare actual versus estimated cost-to-close and feed the error back into routing.

---

## 10. Production-grade nonfunctional requirements

### Reliability

- Durable pause/resume for sequences across process restarts (a 90-day nurture sequence must survive redeploys).
- Idempotent send calls and duplicate-event protection (never double-send a follow-up).
- Bounded retries with backoff and dead-letter handling for failed sends/enrichment calls.
- Provider and tool circuit breakers (email/enrichment provider outage doesn't cascade).
- Deterministic replay using stored inputs and version references.
- Graceful partial failure for parallel branches (one channel failing doesn't kill the whole sequence).

### Security

- Least-privilege access for every agent and tool (drafting agents don't get send credentials by default).
- Separate credentials from prompts and model-visible context.
- Sandbox test sends by default before production.
- Egress controls and data-scope restrictions per tool.
- Signed and versioned policies.
- Human approval for irreversible actions (contract send, large discount, bulk delete).

### Performance

- Stream events rather than poll entire pipeline state.
- Virtualize large pipeline/Kanban and activity-trace views.
- Summarize old activity while retaining immutable originals.
- Cache stable model inputs (voice guide, product facts) and enrichment lookups.
- Use deterministic code for classification/hygiene checks when rules are sufficient.

### Observability

- Trace from inbound lead through agent, model, tool, provider, and outcome (won/lost).
- Quality, cost, latency, reliability, and safety (spam/complaint) metrics.
- Alerts linked directly to the causal sequence/deal segment.
- Natural-language interrogation of activity ("why did this deal stall?") backed by evidence links.

---

## 11. UX states required on every operational screen

- Loading skeleton
- Empty first-run state with setup guidance
- Partial data and delayed telemetry
- Provider or tool degraded state (email provider down)
- Permission denied state
- Offline or reconnecting state
- Stale data warning
- Budget exhausted state
- Sequence paused state
- Error with recovery options
- Archived or unavailable version
- Large-scale overflow with filtering and virtualization (10k+ contacts)

Never hide a failed send or failed approval behind a toast. Persist operational failures in the relevant contact/deal timeline.

---

## 12. Visual direction

Use a light, restrained operations interface with tinted neutral surfaces and one strong accent. Avoid a wall of identical contact cards.

- Kanban for pipeline ownership and flow.
- DAG for playbook and sequence dependencies.
- Timeline for activity causality.
- Tables for comparison and governance (agent performance, model catalog).
- Split panes for inspection and action (deal cockpit).
- Color is secondary to labels, icons, and shape (risk should not rely on red/green alone).
- Monospace is reserved for model IDs, trace IDs, and token data.
- Show details progressively, but keep emergency stop always reachable.
- Desktop is the primary operations surface for pipeline and playbook editing. Mobile is for monitoring, approvals, pause, and incident response — not sequence editing.

---

## 13. Recommended build sequence

### Phase 1: Visible orchestration MVP

Build lead intake, pipeline Kanban, deal cockpit, Playbook Studio, live agent activity graph, agent registry, basic model aliases, event stream, manual approvals, and token/cost ledger.

**Success condition:** Submit one lead, approve its playbook, watch a primary rep agent and secondary enrichment agent work it, inspect every event and artifact, and see cost by step.

### Phase 2: Automated routing and governance

Add Supervisor Agent, policy-based assignment, model router, budget governor, tool permissions, memory inspector, retries, provider failover, and evaluation gates.

**Success condition:** Routine outreach and follow-up completes without manual routing while discounts, contract sends, and enterprise deals still stop for approval.

### Phase 3: Production hardening

Add durable replay, sandboxed sending, security controls, incident response, canary agent versions, advanced evaluations, capacity management, audit exports, and disaster recovery.

**Success condition:** A failed email provider, agent, tool, or worker does not lose deal state, double-send, or produce untracked actions.

### Phase 4: Self-optimization

Add historical policy simulation, routing optimization, playbook estimation feedback, automatic regression generation, capability gap detection, and an extension marketplace (new enrichment vendors, new channels).

**Success condition:** The system reduces cost-per-won-deal and time-to-first-touch without lowering reply/win rate or bypassing governance.

---

## 14. First vertical slice

Do not build all 25 screens first. Build one complete path:

1. A lead comes in through a form or import with acceptance/qualification criteria (ICP fit).
2. Supervisor classifies fit and risk, invokes a frontier Planner to generate a playbook.
3. User reviews the sequence DAG in Playbook Studio.
4. Scheduler chooses a primary rep agent and a secondary enrichment agent.
5. Model router assigns a mid-tier drafting model with a bounded send budget.
6. Live Agent Activity Graph streams model, enrichment, and send events.
7. Verification console checks deliverability, factual grounding, and compliance before each send.
8. Primary agent receives a structured revision request if a draft fails verification.
9. Monitoring Agent pauses on reply-loop or bounce/spam spikes.
10. User approves any discount, contract send, or stage change requiring sign-off.
11. A won deal writes reviewed account memory and playbook memory (what worked).
12. Cost, duration, reply rate, and win rate feed the evaluation dataset for the next playbook.

This slice proves the architecture. Everything else extends it — it does not create a second execution path.

---

## 15. Final recommendation

Snitch's automated backbone should be a **Supervisor Agent backed by a durable, deterministic control plane** — the same Agent OS kernel described in `agent-os-ui-product-spec.md`, retargeted at CRM entities. Use frontier reasoning models as interchangeable qualification/planning engines, not as the operating system itself. Use mid-tier and free-tier models for bounded drafting, enrichment synthesis, hygiene, and summarization only after the playbook, context, qualification criteria, and send limits are explicit.

The winning design is not "an AI SDR that chats and sends." It is **specialist agents operating under contracts, budgets, evidence, and a visible pipeline state machine** — with every send, discount, and stage change attributable and reversible.

---

## 16. Agent OS functionality and behavior in Snitch

This section describes concretely how the Agent OS kernel behaves once wired into a CRM, step by step, so the mechanism in Sections 1–3 is unambiguous in context.

### 16.1 Supervisor Agent behavior

- Owns every contact and deal as a durable state object; never lets an LLM call be the source of truth for "what stage is this deal in."
- On any new event (lead created, reply received, meeting booked, no-reply timeout), re-evaluates: is the current owner still correct, is the current step still valid, has risk changed.
- Decomposes a goal ("grow SMB segment 20% this quarter") into playbooks, not by writing free-form instructions to one big model, but by invoking the Planner to produce a DAG with owners and budgets per step.
- Resolves conflicts between agents deterministically: if an enrichment agent's company-size estimate conflicts with a previously verified value, the Supervisor keeps the verified value and logs the conflict rather than picking whichever ran last.
- Never changes a deal's committed forecast or an approved discount on its own authority — those require a `policy.approval` event from a human.

### 16.2 Planner (Sequencer) behavior

- Invoked once per new segment/playbook, and again only when a material change occurs (new objection pattern, ICP shift, product change) — not on every single contact.
- Produces steps with explicit contracts: what fields must exist before this step runs, what tool it may call, what "success" and "failure" look like, and what happens next in each case.
- Marks which steps are deterministic (e.g., "wait 3 days") so the router never wastes a model call on them.

### 16.3 Rep Agent (primary) behavior

- Owns exactly one contact/deal at a time; drafts outreach, updates fields, and proposes stage changes — but stage changes and sends still pass through verification and, above policy thresholds, human approval.
- Reads only the context packet the Supervisor assembles for the current step (current fields + recent activity + active step contract), not the full historical thread, to keep cost and hallucination risk down.
- When it fails twice in semantically similar ways (e.g., two rejected "reconnect" emails), it must stop and request escalation rather than trying a third near-identical draft.

### 16.4 Enrichment/Research Agent (secondary) behavior

- Cannot write directly to the contact/company record. It returns a proposed enrichment result with source and confidence; the Supervisor decides whether to accept, reject, or hold for review.
- Runs before drafting steps that depend on firmographic data, and is skipped (not re-run) if the record already has high-confidence recent data — token governor rule from Section 3.3.

### 16.5 Monitoring Agent behavior

- Watches deterministic signals first (bounce rate, spam-complaint rate, send-volume rate, retry counts) and only invokes a model to interpret an anomaly it can't classify with rules.
- Authority: throttle sends, pause a sequence, downgrade to a cheaper model, or request human approval. No authority to waive a required deal-desk review, skip a compliance hold, or approve a discount.
- Every monitoring action is itself an event (`policy.blocked`, `budget.warning`) with a reason, so a paused sequence is explainable, not mysterious.

### 16.6 Memory Curator behavior

- Writes to contact/account memory only after a verified outcome (a reply was received, a meeting happened, a deal closed) — never from an agent's unverified inference about buying intent.
- Every write carries provenance (which event, which agent, which source) and a deletion path, which is required for consent/right-to-be-forgotten handling.

### 16.7 Human orchestrator behavior

- Approves anything irreversible or high-risk by policy: discounts, contract sends, bulk sends, new-domain sends, enterprise stage changes.
- Can override any agent decision, and the override is recorded as an event with the reason, so it feeds back into the Quality/Evaluation Lab as a training signal for what "good" looks like.

### 16.8 End-to-end behavior in one sentence

The Supervisor keeps the deal/contact state authoritative and deterministic; specialists (Planner, Rep Agent, Enrichment Agent) propose changes under explicit contracts and budgets; verification and policy gate every send, field change, and stage transition; the Monitoring Agent watches for drift and pauses rather than silently degrading; and every one of these steps is an append-only event a human can inspect, question, and override.

---

## 17. Reference patterns

- [OpenAI orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)
- [OpenAI Agents SDK orchestration](https://openai.github.io/openai-agents-python/multi_agent/)
- [OpenAI Agents SDK tracing](https://github.com/openai/openai-agents-python/blob/3a11cf52/docs/tracing.md)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LiteLLM routing and load balancing](https://docs.litellm.ai/docs/routing-load-balancing)
- Source spec: `agent-os-ui-product-spec.md` (this document is its CRM-domain adaptation)
