#!/usr/bin/env python3
"""delivery M3.1 PreToolUse hook: block direct Write/Edit of
delivery-package.contract.yaml / acceptance-result.contract.yaml.
"""

from __future__ import annotations

import json
import sys

_PATH_MARKERS = (
    "delivery-package.contract.yaml",
    "acceptance-result.contract.yaml",
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    for marker in _PATH_MARKERS:
        if marker in file_path:
            print(
                "HarnessV2 delivery hook BLOCKED: direct Write/Edit of "
                f"{marker} is forbidden. Use `harness contract fill/patch/"
                "add-verdict --json`.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
