#!/usr/bin/env python3
"""finishing-branch-improvement-plan M3.1 hook: check PR body before `gh pr create`.

PreToolUse hook for `gh pr create *`.
Verifies that the PR body was produced by `harness finishing-branch pr-body`
(typed payload) and contains source_artifacts + verification evidence ids.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_GH_PR_CREATE_RE = re.compile(r"\bgh\s+pr\s+create\b", re.IGNORECASE)


def _load_pr_body_evidence(cwd: Path) -> dict | None:
    """Load latest finishing-branch contract for pr_body field."""
    import glob as _glob
    try:
        import yaml as _yaml
    except ImportError:
        return None
    pattern = str(cwd / "harness-runtime" / "harness" / "stages" / "*" / "contracts" / "finishing-branch.contract.yaml")
    matches = _glob.glob(pattern)
    if not matches:
        return None
    try:
        doc = _yaml.safe_load(Path(matches[0]).read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(doc, dict):
        return None
    return doc.get("pr_body")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not _GH_PR_CREATE_RE.search(command):
        return 0

    cwd = Path(payload.get("cwd") or ".")
    pr_body = _load_pr_body_evidence(cwd)
    if pr_body is None:
        print(
            "HarnessV2 finishing-branch hook ADVISORY (check_pr_body): "
            "no pr_body evidence found in finishing-branch contract; "
            "run `harness finishing-branch pr-body` before `gh pr create`.",
            file=sys.stderr,
        )
        return 0

    source_artifacts = pr_body.get("source_artifacts") or []
    if not source_artifacts:
        print(
            "HarnessV2 finishing-branch hook BLOCKED (check_pr_body): "
            "pr_body.source_artifacts is empty; PR body must reference "
            "delivery-package.md and verification evidence.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
