#!/usr/bin/env python3
"""delivery M3.1 PreToolUse hook: block direct Write/Edit of mission-status.yaml.

In delivery stage, mission-status must only be updated via:
  harness mission stage complete --stage delivery ...
Direct edits bypass the delivery gate check and handoff pause enforcement.
"""

from __future__ import annotations

import json
import sys

_TRIGGER_MARKERS = ("mission-status.yaml",)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    for marker in _TRIGGER_MARKERS:
        if marker in file_path:
            print(
                "HarnessV2 delivery hook BLOCKED: direct Write/Edit of mission-status.yaml "
                "is forbidden in delivery stage. Use `harness mission stage complete "
                "--stage delivery --json` after delivery gate PASS and handoff pause.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
