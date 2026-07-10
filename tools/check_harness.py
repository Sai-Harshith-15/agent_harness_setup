#!/usr/bin/env python3
"""Fails (exit 1) if the repo violates the harness contract. Run before every commit."""
import glob
import os
import re
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(p: str) -> str:
    fp = os.path.join(ROOT, p)
    return open(fp, encoding="utf-8").read() if os.path.exists(fp) else ""


def check() -> list[str]:
    errors: list[str] = []

    required_files = [
        "AGENTS.md", "PLAN.md", "IMPLEMENT.md", "HARNESS_CHECKLIST.md",
        "contracts/obsidian_backend.md", "contracts/sandbox_driver.md",
        "contracts/dlp.md", "contracts/mcp_tools.md", "contracts/observability.md", "contracts/occ.md",
        "okf/log.md", "okf/SPEC.md"
    ]
    
    for required in required_files:
        content = _read(required)
        if not content:
            errors.append(f"missing required file: {required}")
        # Phase 3.4 Harness Validator Depth: Enforce contracts are fleshed out
        if required.startswith("contracts/") and len(content) < 300:
            errors.append(f"contract {required} is too thin (under 300 bytes), must be fleshed out")

    # exactly one orchestrator in the registry
    orchestrators = []
    for path in glob.glob(os.path.join(ROOT, "registry", "agents", "*.md")):
        content = open(path, encoding="utf-8").read()
        if re.search(r"^role:\s*orchestrator\s*$", content, re.M):
            orchestrators.append(os.path.basename(path))
            if not re.search(r"^forbid_native_cross_agent:\s*true\s*$", content, re.M):
                errors.append(f"orchestrator {os.path.basename(path)} missing forbid_native_cross_agent: true")
    if len(orchestrators) != 1:
        errors.append(f"expected exactly 1 orchestrator, found {len(orchestrators)}: {orchestrators}")

    # OKF concept frontmatter
    for path in glob.glob(os.path.join(ROOT, "okf", "concepts", "*.md")):
        content = open(path, encoding="utf-8").read()
        if not content.startswith("---\n"):
            errors.append(f"OKF concept {os.path.basename(path)} missing YAML frontmatter")
        else:
            frontmatter = content.split("---")[1]
            for key in ["id:", "title:", "tags:", "source:"]:
                if key not in frontmatter:
                    errors.append(f"OKF concept {os.path.basename(path)} missing {key} in frontmatter")

    # PLAN.md rows must be parseable
    row = re.compile(r"^- \[(backlog|in-progress|delegated|awaiting-hitl|hibernated|done|rejected)\] \(([^)]+)\) .+\| agent=\S+")
    plan = _read("PLAN.md")
    bad = [ln for ln in plan.splitlines()
           if ln.strip().startswith("- [") and not row.match(ln.strip())]
    if bad:
        errors.append(f"{len(bad)} malformed PLAN.md row(s); first: {bad[0]!r}")

    # IMPLEMENT.md must be append-only vs. its committed length (simple guard)
    impl_content = _read("IMPLEMENT.md")
    if "| accepted |" not in impl_content:
        errors.append("IMPLEMENT.md missing the ledger header")
    try:
        committed = subprocess.check_output(["git", "show", "HEAD:IMPLEMENT.md"], encoding="utf-8", stderr=subprocess.DEVNULL, cwd=ROOT)
        if len(impl_content.splitlines()) < len(committed.splitlines()):
            errors.append("IMPLEMENT.md is shorter than the committed version (must be append-only)")
    except Exception:
        pass  # Not a git repo or no HEAD yet

    # Test-green gate
    try:
        subprocess.check_call([sys.executable, "-m", "pytest", "context_server/tests/"], cwd=ROOT)
    except subprocess.CalledProcessError:
        errors.append("pytest suite failed (all tests must be green)")

    return errors


if __name__ == "__main__":
    errs = check()
    if errs:
        print("HARNESS CHECK FAILED:")
        for e in errs:
            print(f"  FAIL {e}")
        sys.exit(1)
    print("OK harness check passed")
