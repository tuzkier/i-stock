#!/usr/bin/env python3
"""finishing-branch-improvement-plan M3.1 hook: check branch cleanliness before merge/push.

PreToolUse hook for `git merge *` and `git push -u origin *`.
Verifies that `harness finishing-branch status` has been run and branch_status
indicates no active/BLOCKED stage worktrees and no dirty worktrees.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_MERGE_RE = re.compile(r"\bgit\s+merge\b", re.IGNORECASE)
_PUSH_U_RE = re.compile(r"\bgit\s+push\b.*?-u\s+origin\b", re.IGNORECASE)


def _load_branch_status_evidence(cwd: Path) -> dict | None:
    """Load the latest branch_status evidence from the finishing-branch contract."""
    import glob as _glob
    try:
        import yaml as _yaml
    except ImportError:
        return None
    # Look for any finishing-branch contract under harness-runtime/harness/stages/*/contracts/
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
    return doc.get("branch_status")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""

    is_merge = bool(_MERGE_RE.search(command))
    is_push = bool(_PUSH_U_RE.search(command))
    if not (is_merge or is_push):
        return 0

    cwd = Path(payload.get("cwd") or ".")
    branch_status = _load_branch_status_evidence(cwd)
    if branch_status is None:
        # No evidence found — advisory only, not hard block (evidence may not
        # exist yet on first use of this hook).
        print(
            "HarnessV2 finishing-branch hook ADVISORY (check_branch_cleanliness): "
            "no branch_status evidence found; run `harness finishing-branch status` "
            "before merge/push.",
            file=sys.stderr,
        )
        return 0

    active = branch_status.get("active_stage_worktrees") or []
    blocked = branch_status.get("blocked_stage_worktrees") or []
    dirty = branch_status.get("dirty") or False

    if active or blocked or dirty:
        issues = []
        if active:
            issues.append(f"active stage worktrees: {active}")
        if blocked:
            issues.append(f"blocked/dirty stage worktrees: {blocked}")
        if dirty:
            issues.append("root worktree has uncommitted changes")
        print(
            "HarnessV2 finishing-branch hook BLOCKED (check_branch_cleanliness): "
            f"merge/push blocked: {'; '.join(issues)}. "
            "Resolve all stage worktree and dirty state issues before proceeding.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
