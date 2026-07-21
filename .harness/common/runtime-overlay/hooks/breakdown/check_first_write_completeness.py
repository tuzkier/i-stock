#!/usr/bin/env python3
"""breakdown-improvement-plan M3.1 PreToolUse hook: enforce first-write
completeness on `execution-brief.md`.

Plan §2.7 / §M3.1 HARD-GATE: when Write(execution-brief.md) lands, every
Parent task block must already declare an `atomic_task_queue:` with
`status: ready` (or `accepted`). Writes that skip the queue OR land in the
forbidden states (`missing` / `incomplete` / `draft`) are blocked so the
"skeleton-now, queue-later" antipattern cannot enter Stage Gate as a
candidate artifact.

The hook parses the proposed `content` payload directly (Write tool input).
A pragmatic heuristic is used in the absence of YAML islands: count
`atomic_task_queue:` markers vs. Parent task section headers. Strict YAML
parsing of embedded fenced YAML is a M5 enhancement; the heuristic catches
the common "no atomic_task_queue at all" failure mode that M3.1 targets.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys

_PATH_MARKER = "execution-brief.md"
_ATOMIC_QUEUE_MARKER_RE = re.compile(r"\batomic_task_queue\s*:", re.IGNORECASE)
_FORBIDDEN_STATUS_RE = re.compile(
    r"atomic_task_queue\s*:[\s\S]{0,200}?status\s*:\s*(missing|incomplete|draft)\b",
    re.IGNORECASE,
)
_PARENT_TASK_HEADER_RE = re.compile(
    r"^(?:#{2,4})\s+(?:Parent\s+Task|Task\s+T-?\d+|T-?\d+\s)",
    re.MULTILINE,
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Write":
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path.endswith(_PATH_MARKER):
        return 0
    content = tool_input.get("content") or ""
    if not isinstance(content, str):
        return 0
    # Heuristic 1: no atomic_task_queue marker at all → forbid (the queue
    # exists nowhere in the proposed content).
    if not _ATOMIC_QUEUE_MARKER_RE.search(content):
        # Allow contract-only stubs that don't yet enumerate Parent tasks
        # (Step 4 prep). If there is no Parent task header either, this is a
        # contract-prep write, not the first commit of the queue — let it pass.
        if not _PARENT_TASK_HEADER_RE.search(content):
            return 0
        print(
            "HarnessV2 breakdown hook BLOCKED: execution-brief.md contains "
            "Parent task headers but no `atomic_task_queue:` block. First "
            "write must include every Parent task's parent-local Atomic Task "
            "Queue (plan §2.7 first-write completeness HARD-GATE).",
            file=sys.stderr,
        )
        return 2
    # Heuristic 2: forbidden status state present.
    bad_state = _FORBIDDEN_STATUS_RE.search(content)
    if bad_state is not None:
        print(
            "HarnessV2 breakdown hook BLOCKED: execution-brief.md "
            f"atomic_task_queue.status='{bad_state.group(1)}' is forbidden. "
            "First write must already declare status: ready (or accepted).",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
