---
type: ContextServerBackend
tags: [obsidian, mcp-http]
---

# Obsidian Local REST API Adapter

This adapter represents the Context Server's primary brain backend: the `obsidian-local-rest-api` MCP.

## Connections
- **MCP URL**: `https://127.0.0.1:27124/mcp/`
- **Fallback URL**: `http://127.0.0.1:27123/mcp/`
- **Authentication**: `Authorization: Bearer <OBSIDIAN_REST_API_KEY>`
  *Note: The key is held by the secrets bridge. The Context Server's Obsidian client is the only consumer of this key.*

## Rules
- **Enforce Direction**: Obsidian → OKF is one-directional. Agents never write arbitrary human notes. Allowed writes are strictly bound to designated log.md headings or the daily note's "Agent Updates" heading.
