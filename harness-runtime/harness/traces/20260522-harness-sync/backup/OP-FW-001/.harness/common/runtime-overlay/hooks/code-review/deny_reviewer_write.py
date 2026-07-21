#!/usr/bin/env python3
"""code-review M3.1 PreToolUse hook: deny Edit/Write/MultiEdit when the
current agent role is a reviewer (*-reviewer).

Reviewers are readonly by design (M1.1 install-time readonly install).
This hook provides a runtime defence-in-depth layer so that even if the
install adapter translation is incomplete, reviewer agents cannot silently
write to the filesystem.

Exit conventions:
  0 — pass (no review role detected, or not a write tool)
  2 — block (reviewer role attempted a write tool)
"""

from __future__ import annotations

import json
import sys

_WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
_REVIEWER_SUFFIX = "-reviewer"


def _is_reviewer_role(role: str) -> bool:
    """Return True if the role string looks like a reviewer agent."""
    return bool(role) and (
        role.endswith(_REVIEWER_SUFFIX)
        or role.endswith("-effectiveness-reviewer")
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in _WRITE_TOOLS:
        return 0

    # Claude Code injects `agent_name` into the hook payload when a named
    # sub-agent is executing the tool.  The key may be absent in older runtimes;
    # fall back gracefully (do not block unknown roles).
    agent_name = (
        payload.get("agent_name")
        or payload.get("role")
        or payload.get("subagent_type")
        or ""
    )
    if not _is_reviewer_role(str(agent_name)):
        return 0

    print(
        f"HarnessV2 code-review hook BLOCKED: reviewer role {agent_name!r} "
        "attempted a write tool. Reviewer agents are readonly. "
        "Use harness contract patch/add-verdict to record findings.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
