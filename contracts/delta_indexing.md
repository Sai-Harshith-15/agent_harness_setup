# Contract: Delta Indexing

> Phase 5.7 · Incremental delta updates for the codebase graph index.

## 1. Delta Patch Schema

A delta carries:
```
(node_id, op, new_signature, new_content_hash, affected_edge_set)
```

- `node_id`: Unique path identifier in the index.
- `op`: `add`, `modify`, or `delete`.
- `new_signature`: Updated code signature (for code nodes).
- `new_content_hash`: Content hash for change detection.
- `affected_edge_set`: List of edges incident on this node that must be updated.

## 2. Transactional Apply

- Graph backend applies the patch transactionally.
- Records the delta id in the Phase 2.5 trace.
- An index state is reconstructable at any point from the delta log.

## 3. Content-Hash Skip

Before applying a delta, the system checks `needs_reindex(path, new_hash)`.
Unchanged files are skipped — only files whose content hash differs from the stored hash are patched.

## 4. Degradation-to-Full Trigger

A full `index_repository` rebuild remains available as an explicit repair command:
- For corruption recovery or schema migration.
- After a configurable N deltas when drift between the delta-applied graph and a from-scratch
  graph exceeds a threshold.

## 5. Lock Window Budget

Delta patches are bounded: the lock held on the graph backend is held for seconds, not minutes.
Concurrent agent reads are barely interrupted.

## 6. Drift Detection Coupling

Phase 5.5 drift detection runs **after a delta is applied**, not after a full reindex.
Staleness of OKF concepts is caught per-change in near-real-time.

## 7. Interaction With Other Subsystems

- **Drift Detection (Phase 5.5):** Runs per-delta for near-real-time staleness detection.
- **Graph Backend (Phase 2.3):** Delta patches applied to the codebase graph.
- **Observability (Phase 2.5):** Delta ids recorded in trace for reconstructability.
