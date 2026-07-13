---
name: registry-agents
description: Five core agents in registry/ with roles and capabilities
metadata:
  type: reference
---

# Agent Registry

Five agents defined in `registry/agents/`:

## 1. **opencode** (Orchestrator)
- **Role:** Primary orchestration + contract enforcement
- **Capabilities:** Registry lookup, agent delegation, RBAC validation
- **Phase 1-4 agent:** Led foundation, contract setup, delegation rules
- **File:** `registry/agents/opencode.md`

## 2. **hermes** (Communication)
- **Role:** Message routing + event logging
- **Capabilities:** Event dispatch, audit log writes, WS broadcasting
- **File:** `registry/agents/hermes.md`

## 3. **claude-code** (Code Agent)
- **Role:** Coding tasks + PR review + refactoring
- **Capabilities:** File read/write, git operations, test execution
- **File:** `registry/agents/claude-code.md`

## 4. **antigravity** (Analysis & Synthesis)
- **Role:** Phase 5-9 heavy lifting (indexing, governance, analytics)
- **Capabilities:** Graph generation, drift detection, FinOps analysis, crash reconciliation
- **Phase 5-9 agent:** Implemented indexing, governance, FinOps, Dream Cycle, frontend
- **File:** `registry/agents/antigravity.md`

## 5. **codex** (Knowledge)
- **Role:** Context retrieval + knowledge synthesis
- **Capabilities:** Graph traversal, contextual response generation
- **File:** `registry/agents/codex.md`

---

## How Agents Are Loaded
- `app/registry.py` parses `registry/agents/*.md` as YAML frontmatter
- `lookup_agent()` endpoint retrieves config by name
- `find_capability()` endpoint routes capability requests to capable agents
- Isolation rules in `app/delegation.py` enforce cross-agent restrictions

**See:** [[isolation-rules]]

