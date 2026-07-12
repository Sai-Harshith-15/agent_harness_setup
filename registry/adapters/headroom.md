---
type: Indexer
title: headroom
tags: [indexer, compression, token-budget]
---
# headroom

Token-budget compactor backend. Ensures context size stays within LLM limits.

## Configuration
- Automatically truncates and summarizes large contexts
- Invoked prior to LLM requests that approach token boundaries
