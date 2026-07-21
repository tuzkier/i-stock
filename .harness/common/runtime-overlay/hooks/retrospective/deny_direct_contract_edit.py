#!/usr/bin/env python3
"""retrospective-improvement-plan M3.1 PreToolUse hook: forbid direct Write /
Edit of `contracts/retrospective.contract.yaml`.

The contract YAML must only be modified through:
  `harness contract init --stage retrospective ...`
  `harness contract patch --artifact contracts/retrospective.contract.yaml ...`

Direct edits bypass typed schema validation and reviewer-round bookkeeping.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys

_PATH_MARKER = "retrospective.contract.yaml"


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
        f"HarnessV2 retrospective hook BLOCKED: direct Write/Edit of "
        f"{_PATH_MARKER} is forbidden. Use "
        "`harness contract init --stage retrospective` or "
        "`harness contract patch --artifact ... --json` to ensure "
        "schema validation and round bookkeeping remain intact.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
