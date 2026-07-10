# Contract: MCP Tools

This contract defines the Model Context Protocol (MCP) API surface exported by the context server.

## 1. Core Tools
The context server exposes the following high-level tools to agents:
- `append_implement`: Appends a finished task row to the `IMPLEMENT.md` file. It goes through OCC validation and DLP scrubbing.
- `log_decision`: Records an architectural or implementation decision to `okf/log.md`.
- `post_standup`: Allows agents to broadcast their daily standup or progress updates to a designated markdown file.
- `delegate_task`: (Orchestrator only) Spawns or assigns a new sub-task to a registered agent.

## 2. Permissions and Scopes
Each tool is subject to the `PermissionMatrix`. For example:
- **Codex** can only write to implementation and code paths.
- **Orchestrator** is the only agent permitted to call `delegate_task`.

## 3. Headers and Identity
All MCP endpoints require the following headers:
- `X-Agent-Identity`: E.g., `codex:task-123`
- `X-Expected-Version`: E.g., `v2` (for OCC)
- `X-Provenance`: `trusted` or `untrusted` (for chaperon policies)
