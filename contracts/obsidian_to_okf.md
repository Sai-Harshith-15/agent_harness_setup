# Contract: Obsidian to OKF

> Phase 1.1 · Canonical mapping from Obsidian PARA folders to OKF concept types.

## 1. PARA -> OKF Type Map

| Obsidian path | Maps to OKF `type` | Notes |
|---------------|-------------------|-------|
| `20 Projects/<project>/` | `Project` | One OKF bundle per project |
| `30 Areas/<area>/` | `Area` | Long-lived responsibility |
| `40 Knowledge/<topic>/` | `Reference` | Reusable concept / how-to |
| `50 Meetings/<date>-<topic>.md` | `Meeting` | Datetime-stamped, decisions log |
| `10 Daily/<date>.md` | `DailyLog` | Index-only; rarely promoted |
| `00 Inbox/` | *(not exported)* | Raw capture; human-triaged later |
| `90 Archive/` | *(not exported)* | Frozen |

## 2. Direction

One-directional only: Obsidian -> OKF.
Agents write back to Obsidian only via the context server's write tools (`log_decision`, `append_implement`),
never by editing arbitrary notes. Humans remain the source of truth for prose; agents are the source of truth
for structured facts.

## 3. Frontmatter Requirements

For a note to be eligible for export, it must carry:
```yaml
okf_export: true
type: <one of the types above>
```

Inbox and Archive are never exported regardless of frontmatter.

## 4. Export Format

Exported concepts follow the OKF v0.1 spec:
- Required frontmatter field: `type`.
- Recommended: `title`, `description`, `resource`, `tags`, `timestamp`.
- Bundle-relative absolute links (`/tables/users.md`) preferred over relative links.

## 5. Interaction With Other Subsystems

- **OKF Backend (Phase 2.3):** Consumes exported concepts.
- **Export Hook (Phase 4.2):** Script that performs the Obsidian -> OKF export.
- **DLP (Phase 2.12):** Full DLP scrub on export payloads.
