#!/usr/bin/env python3
"""code-review M3.1 PreToolUse hook: deny dangerous git commands.

Blocks `git push --force`, `git reset --hard`, `git branch -D`, and
`git push --force-with-lease` during code-review stage.  Normal read-only
git operations (diff, status, log, show) are allowed.

Exit conventions:
  0 — pass (not a dangerous git command)
  2 — block (dangerous git command detected)
"""

from __future__ import annotations

import json
import re
import sys

# Patterns that match dangerous git invocations.
_DANGEROUS_PATTERNS = [
    re.compile(r"\bgit\s+push\s+.*--force(?:-with-lease)?\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+branch\s+.*-[dD]\b"),
    re.compile(r"\bgit\s+clean\s+.*-f\b"),
    re.compile(r"\bgit\s+checkout\s+--\b"),   # checkout -- discards changes
    re.compile(r"\bgit\s+restore\s+\.\b"),     # restore . discards all changes
]


def _is_dangerous(command: str) -> tuple[bool, str]:
    for pattern in _DANGEROUS_PATTERNS:
        m = pattern.search(command)
        if m:
            return True, m.group(0)
    return False, ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = str((payload.get("tool_input") or {}).get("command") or "")
    dangerous, matched = _is_dangerous(command)
    if not dangerous:
        return 0

    print(
        f"HarnessV2 code-review hook BLOCKED: dangerous git command {matched!r} "
        "is not allowed during code-review stage. "
        "Use safe git operations (diff, status, log) instead.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
