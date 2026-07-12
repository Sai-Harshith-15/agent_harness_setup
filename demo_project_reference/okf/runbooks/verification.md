---
type: Runbook
title: Verification
description: How to verify this project is conformant.
tags: [testing, verification]
---
# Verification Runbook

## Gate Commands

```bash
# Check conformance from repo root
python tools/check_harness.py

# Backend tests (if applicable)
python -m pytest . -v

# Lint
ruff .
```
