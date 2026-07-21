#!/usr/bin/env python3
"""delivery M3.1 PostToolUse hook: record split/defer/block/advance graph op
events after `harness graph *` commands in delivery stage.

This hook appends a trace event so `delivery check-followups` can verify
that each follow-up actually had a graph operation executed (not just declared).
"""

from __future__ import annotations

import json
import re
import sys

_GRAPH_PATTERNS = (
    re.compile(r"\bharness\s+graph\s+(apply|split-node|defer-node|block-node|advance-node)\b"),
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern in _GRAPH_PATTERNS:
        m = pattern.search(command)
        if m:
            # Emit a trace event to stderr (delivery trace channel).
            event = {
                "event": "followup_graph_op",
                "operation": m.group(1),
                "command": command,
            }
            print(json.dumps(event), file=sys.stderr)
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
