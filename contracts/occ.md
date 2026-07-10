# Contract: Optimistic Concurrency Control (OCC)

The OCC contract (Phase 2.10) ensures that multiple agents writing to the same Obsidian file or SQLite ledger do not silently overwrite each other's changes.

## 1. Version Tokens
- Every read operation (e.g., `GET /mcp/read_note`) returns a file along with a version signal (e.g., an ETag or hash).
- Agents must provide this token via the `X-Expected-Version` header when attempting to mutate the resource.

## 2. Server Validation
When a write request is received:
1. The server checks the current version of the resource.
2. If `current_version != X-Expected-Version`, the server aborts the write and returns a `412 Precondition Failed`.

## 3. Agent Retries
If an agent receives a `412` error, it is expected to:
1. Re-read the target file to obtain the latest content and new version token.
2. Re-apply its modifications locally.
3. Attempt the write again with the updated `X-Expected-Version`.
