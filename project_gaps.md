Read the whole audit. Straight version: the backend genuinely works and even beats spec in places (real HMAC identity, tiktoken, litellm compactor), but it's not production-ready against its own spec, and the "everything done/accepted" ledger is optimistic. The frontend is the real hole at ~25%. Here's the plan to make it actually robust, in priority order.



P0 — Spec-truth blockers (do first, they're cheap and they're lies right now)
Ship /mcp/log_decision. It's referenced in AGENTS.md and middlewares.py but the route doesn't exist. Either add it or stop pretending it's there.
Fix the forbid_native_cross_agent flag. opencode.md uses cross_agent_delegation instead, so the P32 anti-spoofing check is unenforceable. Rename it AND make check_harness.py assert it.
Fix OKF concept frontmatter. concepts/*.md are bare prose, violating your own SPEC.md (id, title, tags, source). Either add frontmatter or fix the SPEC. Self-contradicting contracts rot fast.
Correct the ledger. IMPLEMENT.md claims "24/24 tests" for Phase 5; there are 19. Fill the empty "Deviations summary" with every PARTIAL below. An honest ledger is the whole point of the harness.


P1 — Robustness hardening (the "runnable" → "trustworthy" gap)
Durable breaker + rate-limit. Both are in-memory, so they reset on restart and don't work per-worker. Move state into control_plane.db (you already have it).
OCC on content hash, not mtime. mtime is fragile (clock skew, no-op saves). Switch to a git-blob/xxhash of note content. This is the core "no silent overwrite" guarantee, so it has to be real.
Widen DLP. Only AWS keys + Bearer today. Add GitHub PATs, Slack xox*, private-key blocks, generic high-entropy. A narrow DLP is a false sense of safety.
Wire the sandbox. sandbox/ (SandboxDriver + LocalRunner + E2BRunner stub) is dead code. Either wire LocalRunner behind delegate_task execution or delete it and record the deviation. Dead security code is worse than none.
Lock DAG + cycle detection (P28). Single-row leases can't detect deadlock. Add the in-memory task-dependency DAG with O(V+E) cycle detection the spec calls for.


P2 — Real observability (currently faked)
OTel is the biggest architectural lie. /task/[id] shows filtered audit_log rows relabeled as "spans." Stand up the actual OTel collector (:4317), emit real nested spans with failure-class tags and Lamport sequence counters (P29), and point the trajectory view at them. Half your Mission Control value depends on this being real.


P3 — Finish the frontend (it's 25%, this is the headline gap)
Six of eight DoD items are missing: no WebSocket consumer (you expose /dashboard/events and /dashboard/tokens/ws, nothing reads them), no Monaco diff modal (it's a <pre>), no CSV export, no crash re-run button, no Playwright, no auth. And Tailwind/shadcn/Zustand/Monaco/Playwright aren't even installed. This is a focused sprint: install the stack, wire live pushes, swap the diff modal to Monaco, add the missing actions, add Playwright e2e.



Highly-robust additions (beyond just closing gaps)
Contract completeness. ~80% of the parent-plan contracts are absent (mcp_tools, lock_manager, identity, secrets_bridge, breaker, occ, rate_limit, dlp, chaperon, observability, delta_indexing, project_contract, obsidian_export_hook). Write them, because your validator can only enforce what's contractually stated.
Make check_harness.py a discipline enforcer, not a presence check. Right now it checks files exist and one orchestrator. Add: flag-key assertions, OKF frontmatter conformance, append-only monotonicity on IMPLEMENT.md, and a test-green gate.
Registry as a real OKF bundle. Missing index.md, log.md, agents/index.md, capabilities/. This is the self-bootstrap contract.
Secrets rotation + ephemeral injection. Add rotation alerts and per-sandbox ephemeral credential injection (P11).
CI. None of this stays green without a pipeline running pytest + ruff + check_harness.py + Playwright on every commit.


My honest take: don't touch P3 frontend until P0 + P1 land. A pretty dashboard over unenforced governance is theater. Fix the truth-telling and the safety guarantees first.



Want me to load this into Team Space > Agentic OS Build17 as a prioritized remediation epic (roughly 20 tasks across these tiers), or write it up as a doc alongside the phase code first?