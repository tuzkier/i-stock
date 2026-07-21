#!/usr/bin/env python3
"""execute-improvement-plan M3.1 PreToolUse hook: forbid direct Write/Edit of
execution-result.contract.yaml.

execution-result.contract.yaml must only be reached through
`harness contract fill/patch/add-verdict/add-execution-result`. Direct
edits skip schema validation and reviewer-round bookkeeping.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys

_PATH_MARKER = "execution-result.contract.yaml"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if _PATH_MARKER not in file_path:
        return 0
    print(
        "HarnessV2 execute hook BLOCKED: direct Write/Edit of "
        f"{_PATH_MARKER} is forbidden. Use `harness contract fill/patch/"
        "add-verdict/add-execution-result --json` so schema validation and "
        "reviewer bookkeeping stay intact.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
