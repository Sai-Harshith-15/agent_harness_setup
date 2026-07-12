# Contract: Project Contract

> Phase 4 · Per-project harness layout every downstream app inherits.

## 1. Required Files Per Project

Every project under the Agentic OS carries, at its repo root:

```
<project-repo>/
├── AGENTS.md                  # Generated from template; repo-locked rules
├── PLAN.md                    # Active plan: task, milestones, scope, risks
├── IMPLEMENT.md               # Append-only executed log
├── HARNESS_CHECKLIST.md       # Run before merge
├── okf/                       # Project's OKF bundle (local secondary brain)
│   ├── index.md               # Bundle root index
│   ├── log.md                 # Append-only decision log
│   ├── architecture/
│   │   ├── index.md
│   │   └── *.md               # type: ArchitectureDecision
│   ├── runbooks/
│   │   ├── index.md
│   │   └── *.md               # type: Runbook
│   └── domain/
│       ├── index.md
│       └── *.md               # type: table | api | metric | ...
└── … (project's own code)
```

## 2. Harness Triad

| File | Role |
|------|------|
| `AGENTS.md` | Procedural memory: how agents behave in this repo |
| `PLAN.md` | Kanban board with parseable rows: `- [status] (id) title \| agent=X capo=N tokens=M` |
| `IMPLEMENT.md` | Append-only log: decisions, deviations, open questions |

## 3. OKF Bundle

- `okf/index.md` — progressive-disclosure index of all concepts.
- `okf/log.md` — append-only update ledger, writable by agents via Phase 2 write tools.
- `okf/architecture/` — Architecture Decision Records.
- `okf/runbooks/` — Operational procedures.
- `okf/domain/` — Domain model concepts (tables, APIs, metrics).

## 4. Obsidian Relationship

- Obsidian note under `20 Projects/<project>/` is the human authoring surface.
- OKF bundle is the agent-consumption surface.
- One-directional: Obsidian -> OKF via export hook (Phase 4.2).
- Agents never edit Obsidian notes directly.

## 5. Interaction With Other Subsystems

- **Registry (Phase 3):** Project's primary agent registered in `registry/agents/`.
- **Context Server (Phase 2):** Project's OKF bundle paths discovered from registry `bindings`.
- **Export Hook (Phase 4.2):** One-directional Obsidian->OKF sync.
