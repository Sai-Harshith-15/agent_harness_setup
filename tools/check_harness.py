#!/usr/bin/env python3
"""Fails (exit 1) if the repo violates the harness contract. Run before every commit."""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(p: str) -> str:
    fp = os.path.join(ROOT, p)
    return open(fp, encoding="utf-8").read() if os.path.exists(fp) else ""


def check() -> list[str]:
    errors: list[str] = []

    for required in ["AGENTS.md", "PLAN.md", "IMPLEMENT.md", "HARNESS_CHECKLIST.md",
                     "contracts/obsidian_backend.md", "okf/log.md", "okf/SPEC.md"]:
        if not _read(required):
            errors.append(f"missing required file: {required}")

    # exactly one orchestrator in the registry
    orchestrators = []
    for path in glob.glob(os.path.join(ROOT, "registry", "agents", "*.md")):
        if re.search(r"^role:\s*orchestrator\s*$", open(path, encoding="utf-8").read(), re.M):
            orchestrators.append(os.path.basename(path))
    if len(orchestrators) != 1:
        errors.append(f"expected exactly 1 orchestrator, found {len(orchestrators)}: {orchestrators}")

    # PLAN.md rows must be parseable
    row = re.compile(r"^- \[(backlog|in-progress|delegated|awaiting-hitl|hibernated|done|rejected)\] \(([^)]+)\) .+\| agent=\S+")
    plan = _read("PLAN.md")
    bad = [ln for ln in plan.splitlines()
           if ln.strip().startswith("- [") and not row.match(ln.strip())]
    if bad:
        errors.append(f"{len(bad)} malformed PLAN.md row(s); first: {bad[0]!r}")

    # IMPLEMENT.md must be append-only vs. its committed length (simple guard)
    if "| accepted |" not in _read("IMPLEMENT.md"):
        errors.append("IMPLEMENT.md missing the ledger header")

    return errors


if __name__ == "__main__":
    errs = check()
    if errs:
        print("HARNESS CHECK FAILED:")
        for e in errs:
            print(f"  FAIL {e}")
        sys.exit(1)
    print("OK harness check passed")
