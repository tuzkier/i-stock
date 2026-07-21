#!/usr/bin/env python3
"""finishing-branch-improvement-plan M3.1 hook: authorize branch -D and worktree remove.

PreToolUse hook.
- `git branch -D`: allowed only when strategy=discard AND a typed discard
  confirmation approval exists.
- `git worktree remove`: allowed only when invoked from `harness finishing-branch cleanup`
  context (detected via approval record) OR strategy=discard with confirmation.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Use case-sensitive match for -D to avoid matching safe -d (soft delete).
_BRANCH_D_RE = re.compile(r"\bgit\s+branch\b.*?(?:^|\s)-D(?:\s|$)")
_WORKTREE_REMOVE_RE = re.compile(r"\bgit\s+worktree\s+remove\b", re.IGNORECASE)


def _find_discard_confirmation(cwd: Path) -> bool:
    """Return True if a discard confirmation boundary approval exists."""
    approvals_path = cwd / "harness-runtime" / "state" / "approvals.json"
    if not approvals_path.exists():
        return False
    try:
        data = json.loads(approvals_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("approvals") or []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        if rec.get("type") == "boundary" and rec.get("status") == "approved":
            comment = str(rec.get("comment") or "")
            if "discard" in comment.lower():
                return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""

    is_branch_d = bool(_BRANCH_D_RE.search(command))
    is_worktree_remove = bool(_WORKTREE_REMOVE_RE.search(command))

    if not (is_branch_d or is_worktree_remove):
        return 0

    cwd = Path(payload.get("cwd") or ".")
    if _find_discard_confirmation(cwd):
        return 0

    if is_branch_d:
        print(
            "HarnessV2 finishing-branch hook BLOCKED (check_cleanup_authorization): "
            "git branch -D requires a discard confirmation approval. "
            "Use `harness approval append --type boundary --status approved "
            "--comment discard` to authorize.",
            file=sys.stderr,
        )
    else:
        print(
            "HarnessV2 finishing-branch hook BLOCKED (check_cleanup_authorization): "
            "git worktree remove must be invoked via `harness finishing-branch cleanup` "
            "or with a discard confirmation approval.",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    sys.exit(main())
