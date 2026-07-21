#!/usr/bin/env python3
"""code-review M3.1 PreToolUse hook: block direct Write/Edit of
code-review.contract.yaml. Must go through harness contract fill/patch/
add-verdict so multi-reviewer verdict and rounds_used stay typed.
"""

from __future__ import annotations

import json
import sys

_PATH_MARKER = "code-review.contract.yaml"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if _PATH_MARKER not in file_path:
        return 0
    print(
        "HarnessV2 code-review hook BLOCKED: direct Write/Edit of "
        f"{_PATH_MARKER} is forbidden. Use `harness contract fill/patch/"
        "add-verdict --json` so multi-reviewer verdicts stay typed.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
