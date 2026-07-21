#!/usr/bin/env python3
"""delivery M3.1 PreToolUse hook: block dangerous git operations during delivery.

Delivery is a read/package/handoff stage. Dangerous git commands
(push, reset --hard, branch -D) must be blocked to prevent accidentally
destroying work or bypassing the delivery evidence trail.
"""

from __future__ import annotations

import json
import re
import sys

_DANGER_PATTERNS = (
    re.compile(r"\bgit\s+push\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+branch\s+-D\b"),
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    for pattern in _DANGER_PATTERNS:
        if pattern.search(command):
            print(
                f"HarnessV2 delivery hook BLOCKED: dangerous git operation detected: "
                f"{command!r}. Delivery stage prohibits git push, reset --hard, branch -D.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
