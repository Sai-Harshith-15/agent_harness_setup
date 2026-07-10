# Agentic OS — v3 Gaps & Fixes

# Agentic OS — v3 Gaps & Fixes
> Repo: `D:\GitRepo\agent_harness_setup` · Re-audit date: 2026-07-10 (v3, post Tier-0 + Tier-1 remediation)  
> Status: Backend strongest it's been (48/48 pytest, harness validator green). **1 gate still RED (ruff). Frontend ~50%.**
* * *
## Priority 0 — Blocks a green gate set (do first, ~2 min)

| # | Gap | Fix | Location |
| ---| ---| ---| --- |
| 0.1 | ruff: 23 violations — 16×W293, 3×I001, 2×W291, 1×E401, 1×E741. Sole RED gate; CI stays red until fixed. | `ruff check context_server --fix` clears 22. Then manually rename ambiguous `l` → `line_`. | `main.py:320` + [hibernation.py](http://hibernation.py) / [permissions.py](http://permissions.py) / [reconcile.py](http://reconcile.py) |

* * *
## Priority 1 — Real gaps still open in code

| # | Gap | Detail | Fix |
| ---| ---| ---| --- |
| 1.1 | Crash reconciliation (P26) — 2 of 4 sub-items missing | Crash-vs-TTL distinction + PLAN finalize are done. Missing: (a) close OTel spans as `infrastructure_crash`, (b) rollback-to-snapshot. | Emit span-close on reconcile; build snapshot rollback (see add-on 3.1). Until then the UI "re-run from snapshot" is only a thaw, not a restore. |
| 1.2 | Semantic drift (P30) — placeholder engine | Jaccard token-overlap has the right banners/shape but isn't real embeddings; misses renamed-symbol / semantically-equivalent drift. | Swap Jaccard for a real vector store + embeddings behind the existing `semantic_drift_detected()` interface. |
| 1.3 | Secrets rotation + ephemeral injection (P11) — not implemented | Only Tier-1 item that didn't move. No rotation alerts, no per-sandbox ephemeral credential injection. | Add key-rotation detection (401/auth-class → refresh from bridge) + ephemeral per-sandbox credential injection. Critical once the sandbox is wired. |
| 1.4 | New contracts are thin stubs | `dlp.md`, `mcp_tools.md`, `observability.md`, `occ.md` are 2-3 lines each. Validator can only enforce what's written. | Flesh each out to a real interface contract, or they're decoration. |
| 1.5 | OTel export noise (robustness nit) | With Jaeger down, `BatchSpanProcessor` spams export failures + adds ~5s to tests. Not a gate failure. | Add a no-op exporter in test mode (env-gated, like `ENABLE_WATCHER`). |

* * *
## Priority 2 — Frontend (Phase 9, ~50% — the headline gap)

| # | Gap | Fix |
| ---| ---| --- |
| 2.1 | Monaco is a read-only editor, not a diff | Swap to Monaco diff view. This is the whole point of the HITL modal (before/after of the proposed write). |
| 2.2 | `/tokens` page incomplete | Add SQL-view backing + CSV export + time-range selector (currently just table + heatmap). |
| 2.3 | No auth | Add PIN / signed-token auth on the frontend (the `/login` route exists but isn't wired). |
| 2.4 | No full task lifecycle view | `/task/[id]` shows spans only; build the full lifecycle (delegation → spans → HITL → acceptance/crash). |
| 2.5 | Silent `.catch()` fallbacks | Remove them; surface real error states. Silent fallbacks make a broken backend look healthy — exactly what bit v2. |
| 2.6 | Playwright configured but not verified green | Run the e2e suite in CI and confirm green. |

* * *
## Priority 3 — Add-ons (beyond closing gaps, make it _highly_ robust)

| # | Add-on | Why |
| ---| ---| --- |
| 3.1 | Snapshot / restore subsystem | Feeds BOTH hibernation thaw (P22) and crash rollback (P26). Build once, two P-items benefit. Unblocks 1.1. |
| 3.2 | DLP depth | Only 5 patterns today. Add high-entropy detection + a hit policy (redact vs block vs quarantine), not just more patterns. |
| 3.3 | Langfuse tracing | Port already reserved (3001). LLM-call-level tracing on top of OTel spans — cheap debugging win for agent behavior. |
| 3.4 | Harness validator depth | Keep growing `check_harness.py` into a discipline enforcer (append-only monotonicity, contract conformance, test-green gate) as contracts fill in. |

* * *
## Recommended sequence
1. **Today:** `ruff --fix` + the E741 rename → all backend gates green (0.1).
2. **Next:** the snapshot/restore subsystem (3.1) — it unblocks crash rollback (1.1) and hardens thaw.
3. **Then:** one focused **frontend sprint** — Monaco diff (2.1), tokens page (2.2), auth (2.3), drop silent catches (2.5).
4. **After:** secrets rotation (1.3), real embeddings for drift (1.2), flesh out contracts (1.4).
5. **Polish:** OTel no-op test exporter (1.5), Langfuse (3.3), DLP depth (3.2).

**Bottom line:** one `ruff --fix` from green backend gates. The real remaining work is a single frontend sprint plus the snapshot/restore subsystem that unblocks two P-items at once. Everything else is polish.