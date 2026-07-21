#!/usr/bin/env python3
"""HarnessV2 prd PreToolUse hook: block writes outside prd stage worktree.

Ensures product definition package and spec.md files are only written within
harness-runtime/harness/stages/<id>/ directories.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_PRD_WRITE_PATTERN = re.compile(r"harness-runtime/harness/stages/[^/]+/(product/(product-definition|product-evidence|product-domain-model)\.md|specs/.+/spec\.md)$")


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

    if _PRD_WRITE_PATTERN.search(file_path):
        # This is a valid prd write path — allow
        return 0

    # Check if it's attempting to write any prd-related file outside the stage dir
    if "product-definition.md" in file_path or "product-evidence.md" in file_path or "product-domain-model.md" in file_path or "spec.md" in file_path:
        if not _PRD_WRITE_PATTERN.search(file_path):
            print(
                f"HarnessV2 prd hook BLOCKED: prd artifact write outside stage directory: {file_path}. "
                "product artifacts and spec.md must be under harness-runtime/harness/stages/<id>/.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
