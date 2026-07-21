#!/usr/bin/env python3
"""delivery M3.1 PreToolUse hook: block direct Write/Edit of approvals.json.

In delivery stage, approvals.json must only be written via:
  harness approval append --type checkpoint --stage acceptance-result ...
Direct edits bypass the approval type/status validation and the
original_user_text preservation requirement.
"""

from __future__ import annotations

import json
import sys

_TRIGGER_MARKER = "approvals.json"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if _TRIGGER_MARKER not in file_path:
        return 0

    print(
        "HarnessV2 delivery hook BLOCKED: direct Write/Edit of approvals.json is forbidden. "
        "Use `harness approval append --type checkpoint --stage acceptance-result --json`.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
