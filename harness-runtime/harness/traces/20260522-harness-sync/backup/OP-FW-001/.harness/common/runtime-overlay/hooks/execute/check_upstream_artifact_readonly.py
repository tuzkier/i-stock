#!/usr/bin/env python3
"""execute-improvement-plan M3.1 PreToolUse hook: enforce upstream artifact
read-only at the execute stage.

The execute stage must consume but never mutate execution-brief.md or its
contract.yaml (those are owned by breakdown). The stage-aware overlay
already denies these at Claude's permission level; this hook adds an
explicit, message-rich block to give the agent the right error message
when overlay enforcement is somehow bypassed.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys

_UPSTREAM_MARKERS = (
    "/execution-brief.md",
    "/execution-brief.contract.yaml",
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    for marker in _UPSTREAM_MARKERS:
        if marker in file_path:
            print(
                "HarnessV2 execute hook BLOCKED: upstream artifact "
                f"{marker.strip('/')} is read-only at the execute stage. "
                "If the upstream needs revision, BLOCKED the current "
                "mission and return to breakdown via Decision Gate; do "
                "not mutate the contract from execute.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
