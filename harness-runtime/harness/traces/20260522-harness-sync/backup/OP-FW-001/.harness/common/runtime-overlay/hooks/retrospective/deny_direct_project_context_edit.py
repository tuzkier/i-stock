#!/usr/bin/env python3
"""retrospective-improvement-plan M3.1 PreToolUse hook: forbid direct Write /
Edit of `project-context.md` during the retrospective stage.

project-context.md lessons must only be appended through:
  `harness project-context add-lesson --content "..." --json`

Direct edits bypass deduplication, source-mission tracking, and the CLI-owned
history audit trail.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys

_PATH_MARKER = "project-context.md"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name")
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path.endswith(_PATH_MARKER) and "/" + _PATH_MARKER not in file_path:
        return 0

    print(
        f"HarnessV2 retrospective hook BLOCKED: direct Write/Edit of "
        f"{_PATH_MARKER} is forbidden during retrospective stage. "
        "Use `harness project-context add-lesson --content \"<lesson>\" --json` "
        "to append lessons with deduplication and source-mission tracking.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
