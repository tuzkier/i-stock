#!/usr/bin/env python3
"""delivery M3.1 PostToolUse hook: record approval id, status, and original
text ref after `harness approval append` in delivery stage.

Emits a trace event so the delivery gate can verify the acceptance checkpoint
actually landed in approvals.json with the correct type/stage/status.
"""

from __future__ import annotations

import json
import re
import sys

_APPROVAL_PATTERN = re.compile(
    r"\bharness\s+approval\s+append\b.*--stage\s+acceptance-result\b"
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not _APPROVAL_PATTERN.search(command):
        return 0

    # Parse --status value from command.
    status_match = re.search(r"--status\s+(\S+)", command)
    status = status_match.group(1) if status_match else "unknown"

    event = {
        "event": "acceptance_checkpoint",
        "status": status,
        "command": command,
    }
    print(json.dumps(event), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
