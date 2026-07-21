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
{
  "_comment": "finishing-branch-improvement-plan M1 + M3.1 hook manifest. Registers 9 hooks total.",
  "stage": "finishing-branch",
  "hooks": [
    {
      "id": "finishing-branch-check-legacy-alias",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "check_legacy_alias.py",
      "purpose": "Soft-block (advisory) for legacy mission close aliases (manual/cancelled); hard-block when finishing_branch.legacy_alias_window=closed."
    },
    {
      "id": "finishing-branch-deny-force-push",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "deny_force_push.py",
      "purpose": "Block git push --force / -f / --force-with-lease without boundary approval."
    },
    {
      "id": "finishing-branch-deny-hard-reset",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "deny_hard_reset.py",
      "purpose": "Block git reset --hard without decision gate approval."
    },
    {
      "id": "finishing-branch-check-cleanup-authorization",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "check_cleanup_authorization.py",
      "purpose": "Block git branch -D and git worktree remove without discard confirmation approval."
    },
    {
      "id": "finishing-branch-check-branch-cleanliness",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "check_branch_cleanliness.py",
      "purpose": "Advisory/block before git merge or push based on branch_status evidence in contract."
    },
    {
      "id": "finishing-branch-check-pr-body",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "check_pr_body.py",
      "purpose": "Advisory/block before gh pr create if pr_body.source_artifacts is empty."
    },
    {
      "id": "finishing-branch-check-close-gate",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "check_close_gate.py",
      "purpose": "Block harness mission close if effectiveness_review.last_gate_run_status != PASS."
    },
    {
      "id": "finishing-branch-deny-direct-runtime-mutation",
      "event": "PreToolUse",
      "matcher": ["Edit", "Write"],
      "script": "deny_direct_runtime_mutation.py",
      "purpose": "Block Edit/Write tool calls targeting mission-status.yaml directly."
    },
    {
      "id": "finishing-branch-record-git-ops",
      "event": "PostToolUse",
      "matcher": "Bash",
      "script": "record_git_ops.py",
      "purpose": "Record git_ops evidence to finishing-branch contract after execute commands."
    }
  ]
}
