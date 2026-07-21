#!/usr/bin/env python3
"""delivery M3.1 PreToolUse hook: block direct Write/Edit of work-graph/** files.

In delivery stage, Work Graph operations must go through CLI:
  harness graph apply --operation <manifest>
  harness graph split-node / defer-node / block-node / advance-node
Direct edits bypass the follow-up graph_op trace event recording.
"""

from __future__ import annotations

import json
import sys

_TRIGGER_MARKERS = (
    "work-graph/",
    "work-graph\\",
)


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
                "HarnessV2 delivery hook BLOCKED: direct Write/Edit of work-graph/** "
                "is forbidden. Use `harness graph apply --operation <manifest> --json` "
                "or `harness graph split-node/defer-node/block-node`.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
