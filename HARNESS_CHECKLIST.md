# HARNESS_CHECKLIST — agent_harness_setup

> Adapted sections for the Agentic OS harness (Phase 6.1)

- [ ] **AGENTS.md**: Is it accurate? Does it match the registry entry for this project's primary agent?
- [ ] **Tool design**: Does every tool the project exposes to agents have a clear name, schema, and annotation?
- [ ] **Context delivery**: Are there zero secrets in agent-readable context (no Obsidian secrets in notes unless marked agent-invisible)? Is context scoped to what the task needs? Is long-lived state stored in files?
- [ ] **Planning artifacts**: Are PLAN.md and IMPLEMENT.md up to date? Are scope boundaries explicitly written?
- [ ] **Permissions & sandbox**: Are minimum permissions applied? Do destructive operations require confirmation? Are network and FS access scoped?
- [ ] **Verification loop**: Can the agent run the verification command itself?
- [ ] **Removal conditions**: Does each harness component have a documented "can be removed when…" row?
