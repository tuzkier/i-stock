#!/usr/bin/env python3
"""retrospective M3.1 PreToolUse hook: enforce data-producer zero-write
semantics on planning-analyst output.

retrospective stage consumes mission-wide data; the planning-analyst
subagent returns structured payload to the orchestrator (data-producer-class
per breakdown M1.2 contract). This hook denies any direct file writes by
processes whose cwd points at the retrospective stage UNLESS the target is
retrospective.md or project-context.md (the two artifacts the workflow
explicitly authors).
"""

from __future__ import annotations

import json
import sys

_ALLOWED_TARGETS = (
    "/retrospective.md",
    "/project-context.md",
)
_FORBIDDEN_MARKERS = (
    "/mission-status.yaml",
    "/work-graph/",
    "/contracts/",
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    # Allow the two whitelisted retrospective artifacts.
    if any(marker in file_path for marker in _ALLOWED_TARGETS):
        return 0
    # Block writes into mission-status / work-graph / any stage contract.
    for marker in _FORBIDDEN_MARKERS:
        if marker in file_path:
            print(
                "HarnessV2 retrospective hook BLOCKED: retrospective stage "
                f"may not mutate {file_path!r}. Lessons land in "
                "project-context.md; analysis lands in retrospective.md.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
