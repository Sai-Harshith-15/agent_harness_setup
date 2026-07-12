# Contract: Daily Flow

> Phase 7.1 · Standard daily operating loop for the Agentic OS.

## 1. Morning Standup

- Human writes daily note under `10 Daily/<YYYY-MM-DD>.md` in Obsidian (PARA-supported, no change).
- `post_standup` tool (9am local) appends CAPO summary to `Agent Updates` heading on the daily note.
- Runs as a server-side background task.

## 2. Task Day

- Human promotes tasks from daily note to relevant projects' `PLAN.md`.
- Agents run under whichever registered agent fits the task.
- All agents read from the same context server.
- Decisions written via `log_decision` and `append_implement` tools — never by editing Obsidian notes directly.

## 3. Evening Review

- Human reviews `IMPLEMENT.md` entries.
- Noteworthy entries are promoted back to `20 Projects/<project>/` or `40 Knowledge/` in Obsidian.
- Dream Cycle (3am) analyzes the day's traces and proposes improvements.

## 4. Weekly Rollup

- Token accounting rollup written to `registry/log.md` (CAPO trend, heatmap).
- Meta-agent reviews proposals and human accepts/rejects.

## 5. Interaction With Other Subsystems

- **Dream Cycle (Phase 8):** Runs nightly at 3am.
- **Standup (Phase 7.1):** Runs morning at 9am.
- **Token Accounting (Phase 7.3):** Rolled up weekly.
- **Obsidian (Phase 1):** Human authoring surface throughout.
