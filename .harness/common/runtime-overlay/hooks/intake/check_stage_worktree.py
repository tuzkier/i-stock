#!/usr/bin/env python3
"""HarnessV2 intake PreToolUse hook: block mission-contract writes outside stage worktree.

Triggered on PreToolUse(Edit|Write). Enforces the intake workflow's
`stage-worktree-required` HARD-GATE physically: refuses writes to
`harness-runtime/harness/missions/<mission_id>/mission-contract.md` (or its
external contract YAML) when the current working directory is not inside the
intake stage worktree.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_MISSION_CONTRACT_PATH_RE = re.compile(
    r"harness-runtime/harness/missions/(?P<mission>[^/]+)/"
    r"(?:mission-contract\.md|contracts/mission-contract\.contract\.yaml)$"
)

# A stage worktree path contains either `.worktrees/stage-<id>-intake/`
# (HarnessV2 convention) or `worktrees/stage-<id>-intake/`. Codex / downgraded
# strategy paths bypass this check by setting the env var below.
_STAGE_WORKTREE_RE = re.compile(r"/\.?worktrees/stage-[^/]+-intake/")
_DOWNGRADE_ENV = "HARNESS_GIT_STRATEGY_DOWNGRADED"


def _resolve_target_path(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    for key in ("file_path", "filePath", "path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return 0

    target = _resolve_target_path(payload)
    if target is None:
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    try:
        rel = str(Path(target).resolve().relative_to(Path(cwd).resolve()))
    except (ValueError, OSError):
        rel = target

    if not _MISSION_CONTRACT_PATH_RE.search(rel):
        return 0

    # Downgrade escape hatch (git.strategy == downgraded in mission-status).
    import os

    if os.environ.get(_DOWNGRADE_ENV) == "1":
        return 0

    cwd_norm = str(Path(cwd).resolve()) + "/"
    if _STAGE_WORKTREE_RE.search(cwd_norm):
        return 0

    print(
        f"HarnessV2 intake hook BLOCKED: cannot write {rel} from cwd {cwd!r}. "
        "Run `git-workflow start-stage(intake)` to create the stage worktree first, "
        f"or set {_DOWNGRADE_ENV}=1 for downgraded git strategy.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
