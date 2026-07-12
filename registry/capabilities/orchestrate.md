---
id: capability-orchestrate
type: Capability
title: Orchestrate
description: Owns the top-level loop. Invokes plan, route, and accept_implement.
tags: [orchestrator, control-plane]
---
# Orchestrate

Top-level orchestration capability. Only the orchestrator agent holds this.
Implies: can invoke `delegate_task`, can flip `IMPLEMENT.md` rows to `accepted: true`, can route HITL escalations.
