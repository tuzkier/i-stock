#!/usr/bin/env python3
"""breakdown-improvement-plan M3.1 PreToolUse hook: forbid direct Write / Edit
of `execution-brief.contract.yaml`.

The contract YAML must only be reached through `harness contract fill`,
`harness contract patch`, or `harness contract add-execution-result`. Direct
edits skip the schema validation + reviewer-round bookkeeping that those
commands perform.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys

_PATH_MARKER = "execution-brief.contract.yaml"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_name = payload.get("tool_name")
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if _PATH_MARKER not in file_path:
        return 0
    print(
        "HarnessV2 breakdown hook BLOCKED: direct Write/Edit of "
        f"{_PATH_MARKER} is forbidden. Use `harness contract fill/patch/"
        "add-execution-result --json` so schema validation and reviewer "
        "bookkeeping stay intact.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
