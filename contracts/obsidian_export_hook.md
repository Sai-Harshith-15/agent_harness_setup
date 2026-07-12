# Contract: Obsidian Export Hook

> Phase 4.2 · One-directional Obsidian -> OKF export bridge.

## 1. Direction Rule

**One direction only:** Obsidian is the human authoring surface; OKF is the agent-consumption surface.
Agents write back to Obsidian only via a `write_log` tool through the context server, never by editing
arbitrary notes.

## 2. PARA -> OKF Type Mapping

| Obsidian path | Maps to OKF `type` | Notes |
|---------------|-------------------|-------|
| `20 Projects/<project>/` | `Project` | One OKF bundle per project |
| `30 Areas/<area>/` | `Area` | Long-lived responsibility |
| `40 Knowledge/<topic>/` | `Reference` | Reusable concept / how-to |
| `50 Meetings/<date>-<topic>.md` | `Meeting` | Datetime-stamped, decisions log |
| `10 Daily/<date>.md` | `DailyLog` | Index-only; rarely promoted |
| `00 Inbox/` | *(not exported)* | Raw capture; human-triaged later |
| `90 Archive/` | *(not exported)* | Frozen |

## 3. Export Hook Behavior

- Watches (or runs on demand / pre-commit) the project's folder inside Obsidian's `20 Projects/<project>/`.
- For each changed `.md`: applies the PARA->OKF type map to write a corresponding concept under `<project-repo>/okf/`.
- For ADRs in Obsidian: exports to `okf/architecture/<slug>.md` (frontmatter `type: ArchitectureDecision`).
- Appends to the project's `okf/log.md` with what was exported and when.
- DLP scrub runs on export (Phase 2.12).

## 4. Frontmatter Flag

Export is opt-in per note: a frontmatter flag `okf_export: true` controls whether a note is exported.
Inbox and Archive are never exported regardless of the flag.

## 5. Interaction With Other Subsystems

- **DLP (Phase 2.12):** Full DLP scrub on export payloads.
- **OKF Backend (Phase 2.3):** Exported concepts land in the project's `okf/` bundle.
- **Drift Detection (Phase 5.5):** Export triggers per-delta drift check after concept update.
