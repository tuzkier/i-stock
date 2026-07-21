#!/usr/bin/env python3
"""verify M3.1 PreToolUse hook: deny Edit/Write/MultiEdit from
verification-effectiveness-reviewer sub-agent context.

Reviewer agents must be readonly. If the tool payload carries a
``session_id`` or ``agent_id`` token that resolves to the reviewer role,
all write operations are blocked.

In runtimes where the hook cannot inspect the agent identity (no
``agent_context`` field), we block on the heuristic: if the working
directory contains a reviewer-specific trace file that flags the
current turn as a reviewer turn, the write is denied.

State signal (optional):
  harness-runtime/harness/stages/<mission>/traces/reviewer_turn.flag
  — written by record_dispatch.py PostToolUse hook; presence means the
  current agent is running as a reviewer-class role.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REVIEWER_AGENT_IDS = frozenset(
    {
        "verification-effectiveness-reviewer",
        "verificationeffectivenessreviewer",
    }
)

_REVIEWER_FLAG_GLOB = "harness-runtime/harness/stages/*/traces/reviewer_turn.flag"

_PATH_MARKER = "verification-report.contract.yaml"


def _is_reviewer_context(payload: dict, cwd: Path) -> bool:
    """Return True if the current tool-use turn is a reviewer context."""
    # 1. Explicit agent context in payload (Claude Code / OpenCode)
    agent_ctx = payload.get("agent_context") or {}
    if isinstance(agent_ctx, dict):
        agent_id = (
            agent_ctx.get("agent_id") or agent_ctx.get("subagent_type") or ""
        ).lower().replace("-", "").replace("_", "")
        if any(
            r.replace("-", "").replace("_", "") == agent_id
            for r in _REVIEWER_AGENT_IDS
        ):
            return True

    # 2. Session-level flag written by record_dispatch.py
    for flag_path in cwd.glob(_REVIEWER_FLAG_GLOB):
        if flag_path.exists():
            return True

    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    if not _is_reviewer_context(payload, cwd):
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    print(
        "HarnessV2 verify hook BLOCKED (REVIEWER_WRITE_DENIED): "
        f"verification-effectiveness-reviewer is readonly and must not "
        f"Edit/Write files (attempted: {file_path!r}). "
        "Reviewer may only read artifacts and record a verdict via "
        "`harness contract add-verdict --json`.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
