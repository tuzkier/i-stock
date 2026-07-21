#!/usr/bin/env python3
"""HarnessV2 intake PreToolUse hook: block edits to runtime YAML before mission branch.

Triggered on PreToolUse(Edit|Write). Enforces the intake workflow's
`git-prepare-before-runtime-write` HARD-GATE physically: refuses to let the AI
write `harness-runtime/harness/mission-status.yaml` or anything under
`harness-runtime/harness/work-graph/` while the current git branch is not a
mission branch.

Exit conventions: 0 = allow; 2 = block (Claude Code surfaces stderr to user).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# Paths whose write must follow `git-workflow prepare`.
_PROTECTED_PATH_PATTERNS = (
    re.compile(r"harness-runtime/harness/mission-status\.yaml$"),
    re.compile(r"harness-runtime/harness/work-graph/"),
)

_MISSION_BRANCH_RE = re.compile(r"^mission/.+")


def _resolve_target_path(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    for key in ("file_path", "filePath", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def _is_protected(rel_path: str) -> bool:
    return any(pat.search(rel_path) for pat in _PROTECTED_PATH_PATTERNS)


def _current_git_branch(cwd: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # If the hook protocol can't be parsed, allow rather than block (the
        # AI shouldn't be stranded because of a hook bug).
        return 0

    if payload.get("tool_name") not in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        return 0

    target = _resolve_target_path(payload)
    if target is None:
        return 0

    # Normalize to repo-relative form when the path is absolute.
    cwd = payload.get("cwd") or str(Path.cwd())
    try:
        rel = str(Path(target).resolve().relative_to(Path(cwd).resolve()))
    except (ValueError, OSError):
        rel = target

    if not _is_protected(rel):
        return 0

    branch = _current_git_branch(cwd)
    if branch is None:
        # Not a git repo or git unavailable — let the write proceed; workflow
        # HARD-GATE prompt is the remaining safety net.
        return 0
    if _MISSION_BRANCH_RE.match(branch):
        return 0

    print(
        f"HarnessV2 intake hook BLOCKED: cannot write {rel} on branch {branch!r}. "
        "Run `git-workflow prepare` to create a mission/<mission-id> branch first.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
