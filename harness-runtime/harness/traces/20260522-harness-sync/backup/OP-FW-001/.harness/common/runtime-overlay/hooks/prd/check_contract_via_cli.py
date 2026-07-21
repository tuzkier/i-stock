#!/usr/bin/env python3
"""HarnessV2 prd PreToolUse hook: block direct Write/Edit of prd.contract.yaml.

Contract YAML must only be written through `harness contract fill/patch` commands.
Direct Edit/Write is blocked to enforce the audit trail.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_CONTRACT_PATTERN = re.compile(r"contracts/prd\.contract\.yaml$")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""

    if _CONTRACT_PATTERN.search(file_path):
        print(
            "HarnessV2 prd hook BLOCKED: direct Write/Edit of prd.contract.yaml is not allowed. "
            "Use `harness contract fill` or `harness contract patch` instead.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
