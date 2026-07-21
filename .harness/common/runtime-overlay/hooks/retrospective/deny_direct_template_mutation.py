#!/usr/bin/env python3
"""retrospective-improvement-plan M3.1 PreToolUse hook: forbid direct Write /
Edit of Harness template source paths during retrospective.

retrospective stage may ONLY produce:
  - retrospective.md artifact
  - harness-gaps/proposals.yaml (via CLI only, but path itself is safe)

Any attempt to directly modify the following paths is blocked:
  - .harness/common/rules/**
  - .harness/common/skills/**
  - .harness/common/agents/**
  - .harness/common/schemas/**
  - harness-runtime/templates/**
  - .harness/common/**

Template source changes must instead be expressed as typed learning proposals
(`harness retrospective harness-gap-emit`) with requires_human_approval=true,
and executed in a follow-up mission after human approval.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys

_FORBIDDEN_PATH_MARKERS = (
    ".harness/common/rules/",
    ".harness/common/skills/",
    ".harness/common/agents/",
    ".harness/common/schemas/",
    "harness-runtime/templates/",
    ".harness/common/rules/",
    ".harness/common/skills/",
    ".harness/common/agents/",
    ".harness/common/schemas/",
)


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
    for marker in _FORBIDDEN_PATH_MARKERS:
        if marker in file_path:
            print(
                f"HarnessV2 retrospective hook BLOCKED: direct mutation of "
                f"{file_path!r} is forbidden during retrospective stage. "
                "Retrospective may only produce typed learning proposals via "
                "`harness retrospective harness-gap-emit`. Template source changes "
                "require human approval and must run in a follow-up mission.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
