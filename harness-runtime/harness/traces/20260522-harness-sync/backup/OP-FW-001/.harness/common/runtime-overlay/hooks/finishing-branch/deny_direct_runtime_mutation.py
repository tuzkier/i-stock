#!/usr/bin/env python3
"""finishing-branch-improvement-plan M3.1 hook: deny direct Edit of mission-status.yaml.

PreToolUse hook for Edit tool calls targeting harness-runtime/harness/mission-status.yaml.
All mission close state must be written via `harness mission close`.
"""
from __future__ import annotations

import json
import sys

_MISSION_STATUS_PATTERNS = (
    "harness-runtime/harness/mission-status.yaml",
    "harness-runtime/harness/mission_status.yaml",
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Edit", "Write"}:
        return 0
    file_path = str((payload.get("tool_input") or {}).get("file_path") or "")
    for pattern in _MISSION_STATUS_PATTERNS:
        if pattern in file_path.replace("\\", "/"):
            print(
                "HarnessV2 finishing-branch hook BLOCKED (deny_direct_runtime_mutation): "
                f"direct {payload['tool_name']} of {pattern!r} is not permitted. "
                "Use `harness mission close --mission <id> --strategy <enum>` "
                "to update mission close state.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
