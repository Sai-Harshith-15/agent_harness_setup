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

    # ── 1. File existence + contract depth ──────────────────────
    required_files = [
        "AGENTS.md", "PLAN.md", "IMPLEMENT.md", "HARNESS_CHECKLIST.md",
        "contracts/obsidian_backend.md", "contracts/sandbox_driver.md",
        "contracts/dlp.md", "contracts/mcp_tools.md", "contracts/observability.md",
        "contracts/occ.md", "contracts/orchestration.md", "contracts/secrets_bridge.md",
        "okf/log.md", "okf/SPEC.md"
    ]

    for required in required_files:
        content = _read(required)
        if not content:
            errors.append(f"missing required file: {required}")
        if required.startswith("contracts/") and len(content) < 600:
            errors.append(f"contract {required} is too thin ({len(content)} bytes), must be at least 600 bytes")

    # ── 2. Contract structural validation ───────────────────────
    contract_keywords = {
        "contracts/dlp.md": ["Pattern Matching", "Hit Policies", "Coverage", "Secrets-Bridge"],
        "contracts/mcp_tools.md": ["Read Tools", "Write Tools", "Progressive Disclosure", "Request Headers"],
        "contracts/observability.md": ["Span Schema", "Failure Classification", "Logical Sequence"],
        "contracts/occ.md": ["Version Hash", "Read Path", "Write Path", "Append-Only"],
        "contracts/orchestration.md": ["Delegation", "accepted flip"],
        "contracts/obsidian_backend.md": ["Obsidian", "backend"],
        "contracts/sandbox_driver.md": ["Sandbox", "spawn"],
        "contracts/secrets_bridge.md": ["request_credentials", "ephemeral", "rotation", "Sandbox Integration"],
    }
    for contract, keywords in contract_keywords.items():
        content = _read(contract)
        if not content:
            continue
        for kw in keywords:
            if kw.lower() not in content.lower():
                errors.append(f"contract {contract} missing keyword: {kw}")

    # ── 3. Exactly one orchestrator ─────────────────────────────
    orchestrators = []
    for path in glob.glob(os.path.join(ROOT, "registry", "agents", "*.md")):
        content = open(path, encoding="utf-8").read()
        if re.search(r"^role:\s*orchestrator\s*$", content, re.M):
            orchestrators.append(os.path.basename(path))
            if not re.search(r"^forbid_native_cross_agent:\s*true\s*$", content, re.M):
                errors.append(f"orchestrator {os.path.basename(path)} missing forbid_native_cross_agent: true")
    if len(orchestrators) != 1:
        errors.append(f"expected exactly 1 orchestrator, found {len(orchestrators)}: {orchestrators}")

    # ── 4. OKF concept frontmatter ──────────────────────────────
    for path in glob.glob(os.path.join(ROOT, "okf", "concepts", "*.md")):
        content = open(path, encoding="utf-8").read()
        if not content.startswith("---\n"):
            errors.append(f"OKF concept {os.path.basename(path)} missing YAML frontmatter")
        else:
            parts = content.split("---", 2)
            if len(parts) < 3:
                errors.append(f"OKF concept {os.path.basename(path)} malformed frontmatter")
                continue
            frontmatter = parts[1]
            for key in ["id:", "title:", "tags:", "source:"]:
                if key not in frontmatter:
                    errors.append(f"OKF concept {os.path.basename(path)} missing {key} in frontmatter")

    # ── 5. PLAN.md rows must be parseable ───────────────────────
    row = re.compile(r"^- \[(backlog|in-progress|delegated|awaiting-hitl|hibernated|done|rejected)\] \(([^)]+)\) .+\| agent=\S+")
    plan = _read("PLAN.md")
    bad = [ln for ln in plan.splitlines()
           if ln.strip().startswith("- [") and not row.match(ln.strip())]
    if bad:
        errors.append(f"{len(bad)} malformed PLAN.md row(s); first: {bad[0]!r}")

    # ── 6. IMPLEMENT.md append-only guard ───────────────────────
    impl_content = _read("IMPLEMENT.md")
    if "| accepted |" not in impl_content:
        errors.append("IMPLEMENT.md missing the ledger header")
    try:
        committed = subprocess.check_output(
            ["git", "show", "HEAD:IMPLEMENT.md"], encoding="utf-8",
            stderr=subprocess.DEVNULL, cwd=ROOT
        )
        if len(impl_content.splitlines()) < len(committed.splitlines()):
            errors.append("IMPLEMENT.md is shorter than HEAD — must be append-only")
    except Exception:
        pass

    # ── 7. okf/log.md append-only guard ─────────────────────────
    log_content = _read("okf/log.md")
    if log_content and not re.search(r"\d{4}-\d{2}-\d{2}", log_content):
        errors.append("okf/log.md missing ISO-8601 date entries")
    try:
        committed = subprocess.check_output(
            ["git", "show", "HEAD:okf/log.md"], encoding="utf-8",
            stderr=subprocess.DEVNULL, cwd=ROOT
        )
        if committed and len(log_content.splitlines()) < len(committed.splitlines()):
            errors.append("okf/log.md is shorter than HEAD — must be append-only")
    except Exception:
        pass

    # ── 8. DLP patterns exist in code ───────────────────────────
    dlp_code = _read("context_server/app/middlewares.py")
    mandatory_patterns = ["AKIA", "ghp_", "xox[baprs]", "BEGIN", "REDACTED"]
    for pat in mandatory_patterns:
        if pat not in dlp_code:
            errors.append(f"DLP middleware missing mandatory pattern: {pat}")

    # ── 9. Langfuse SDK wired ──────────────────────────────────
    main_code = _read("context_server/app/main.py")
    if "from langfuse import Langfuse" not in main_code:
        errors.append("main.py missing Langfuse SDK import (Gap 3.3)")
    if "ENABLE_LANGFUSE" not in _read("context_server/.env.example"):
        errors.append(".env.example missing Langfuse configuration")

    # ── 10. DLP quarantine table in schema ──────────────────────
    db_code = _read("context_server/app/db.py")
    if "dlp_quarantine" not in db_code:
        errors.append("db.py missing dlp_quarantine table (Gap 3.2)")
    if "credential_leases" not in db_code:
        errors.append("db.py missing credential_leases table (Gap 1.3)")

    # ── 10b. Secrets bridge wired ───────────────────────────────
    main_code_full = _read("context_server/app/main.py")
    if "secrets_bridge" not in main_code_full:
        errors.append("main.py missing secrets_bridge import (Gap 1.3)")
    if "request_credentials" not in main_code_full:
        errors.append("main.py missing request_credentials endpoint (Gap 1.3)")
    bridge_code = _read("context_server/app/governance/secrets_bridge.py")
    if not bridge_code:
        errors.append("missing secrets_bridge.py module (Gap 1.3)")

    # ── 11. Shannon entropy DLP ─────────────────────────────────
    if "_shannon_entropy" not in dlp_code:
        errors.append("middlewares.py missing Shannon entropy DLP detection (Gap 3.2)")

    # ── 12. Test-green gate ─────────────────────────────────────
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pytest", "context_server/tests/"], cwd=ROOT
        )
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
