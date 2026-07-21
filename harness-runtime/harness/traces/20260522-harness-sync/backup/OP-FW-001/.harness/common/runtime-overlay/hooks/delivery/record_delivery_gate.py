#!/usr/bin/env python3
"""delivery M3.1 PostToolUse hook: record delivery gate PASS/BLOCKED evidence
after `harness gate run --stage delivery` in delivery stage.

Emits a trace event that `require_handoff_pause.py` can use to confirm the
gate was run before `harness gate advance` is attempted.
"""

from __future__ import annotations

import json
import re
import sys

_GATE_PATTERN = re.compile(r"\bharness\s+gate\s+run\b.*--stage\s+delivery\b")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not _GATE_PATTERN.search(command):
        return 0

    event = {
        "event": "delivery_gate_run",
        "command": command,
    }
    print(json.dumps(event), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
