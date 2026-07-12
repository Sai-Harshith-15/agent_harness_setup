# AGENTS.md — demo_project_reference

> Procedural memory for agents working in this repo.

## Repo identity
- **Project:** Demo Reference Project (conforms to Agentic OS harness contract)
- **Primary agent:** opencode (orchestrator)
- **Secondary agents:** hermes, claude-code, codex, antigravity

## Rules
- All writes go through the Context Server on `http://127.0.0.1:27180`
- Never edit Obsidian notes directly — use `append_implement` and `log_decision` only
- Before every commit: `ruff . && pytest`
- Append-only `IMPLEMENT.md` — never delete rows

## Tool surface
- `search_notes` — search the primary brain (Obsidian)
- `search_okf` — search the secondary brain (OKF bundles)
- `append_implement` — write to IMPLEMENT.md
- `log_decision` — log decisions to log.md
- `delegate_task` — delegate to other registered agents

## Verification
```bash
python -m pytest . -v      # backend tests
npm test                    # frontend tests (if applicable)
ruff .                      # lint
```
