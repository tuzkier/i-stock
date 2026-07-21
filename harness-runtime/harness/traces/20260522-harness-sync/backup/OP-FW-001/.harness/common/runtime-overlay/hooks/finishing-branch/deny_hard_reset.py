#!/usr/bin/env python3
"""finishing-branch-improvement-plan M3.1 hook: deny `git reset --hard`.

PreToolUse hook for Bash tool calls containing hard reset patterns.
Full-stage deny; requires a Decision Gate approval to override.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HARD_RESET_RE = re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE)


def _find_reset_approval(cwd: Path) -> bool:
    """Return True if a boundary approval for hard-reset exists."""
    approvals_path = cwd / "harness-runtime" / "state" / "approvals.json"
    if not approvals_path.exists():
        return False
    try:
        import json as _j
        data = _j.loads(approvals_path.read_text(encoding="utf-8"))
    except (Exception,):
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
            if "hard-reset" in comment.lower() or "hard_reset" in comment.lower():
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
    if not _HARD_RESET_RE.search(command):
        return 0
    cwd = Path(payload.get("cwd") or ".")
    if _find_reset_approval(cwd):
        print(
            "HarnessV2 finishing-branch hook ADVISORY (hard_reset_approved): "
            "git reset --hard authorized via boundary approval.",
            file=sys.stderr,
        )
        return 0
    print(
        "HarnessV2 finishing-branch hook BLOCKED (deny_hard_reset): "
        "git reset --hard is not permitted at any stage without a Decision Gate. "
        "Use `harness approval append --type boundary --status approved "
        "--comment hard-reset` to authorize, then retry.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
