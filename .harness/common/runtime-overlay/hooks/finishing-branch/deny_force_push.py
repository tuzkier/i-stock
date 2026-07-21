#!/usr/bin/env python3
"""finishing-branch-improvement-plan M3.1 hook: deny `git push --force` / `-f`.

PreToolUse hook for Bash tool calls containing force-push patterns.
Allowed only when a valid force-push boundary approval exists.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_FORCE_PUSH_RE = re.compile(
    r"\bgit\s+push\b.*?(--force\b|-f\b|--force-with-lease\b)", re.IGNORECASE
)
_APPROVAL_ID_RE = re.compile(r"--approval-id\s+(\S+)")


def _find_boundary_approval(cwd: Path) -> bool:
    """Return True if a boundary approval exists for force-push."""
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
            if "force-push" in comment.lower() or "force_push" in comment.lower():
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
    if not _FORCE_PUSH_RE.search(command):
        return 0
    cwd = Path(payload.get("cwd") or ".")
    if _find_boundary_approval(cwd):
        print(
            "HarnessV2 finishing-branch hook ADVISORY (force_push_approved): "
            "force push authorized via boundary approval.",
            file=sys.stderr,
        )
        return 0
    print(
        "HarnessV2 finishing-branch hook BLOCKED (deny_force_push): "
        "git push --force is not permitted without a boundary approval. "
        "Use `harness approval append --type boundary --status approved "
        "--comment force-push` to authorize, then retry.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
