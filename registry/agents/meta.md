---
id: meta
role: delegate
adapter: http
cost_defaults: { max_turns: 12 }
bindings: []
capabilities: [reflect, propose_improvement, review_trajectory]
schedule: nightly            # run by the Dream Cycle loop, not by user delegation
---
# meta
The reflection agent. Reads drift + CAPO + audit trails and proposes harness/prompt
improvements. Writes proposals ONLY to okf/log.md and Program.md via append_implement.
Never edits Obsidian human notes. Never flips an IMPLEMENT row to accepted.

