#!/usr/bin/env python3
"""retrospective-improvement-plan M3.1 PostToolUse hook: record
planning-analyst dispatch evidence in the per-mission trace log.

Fires after any tool invocation that mentions `planning-analyst` to ensure the
dispatch event is machine-readable in the trace JSONL. If the tool output
indicates failure, the hook emits a BLOCKED signal to stderr (exit 2).

Exit convention: 0 = recorded; 2 = planning-analyst dispatch failed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _append_trace(mission_id: str, root: str, record: dict) -> None:
    trace_path = Path(root) / "harness-runtime" / "harness" / "traces" / mission_id / "steps.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    tool_response = payload.get("tool_response") or {}

    # Only care about tool calls that mention planning-analyst.
    command = str(tool_input.get("command") or "") + str(tool_input.get("prompt") or "")
    if "planning-analyst" not in command:
        return 0

    # Try to extract mission id from environment or command.
    mission_id: str | None = None
    parts = command.split()
    for i, part in enumerate(parts):
        if part in {"--mission", "-m"} and i + 1 < len(parts):
            mission_id = parts[i + 1]
            break
    if not mission_id:
        mission_id = os.environ.get("HARNESS_MISSION_ID")

    if not mission_id:
        return 0

    # Determine dispatch success from tool response.
    response_text = str(tool_response.get("output") or tool_response.get("content") or "")
    is_blocked = "BLOCKED" in response_text.upper() or payload.get("exit_code", 0) not in {0, None}

    record = {
        "event": "planning_analyst_dispatch",
        "tool_name": tool_name,
        "status": "BLOCKED" if is_blocked else "dispatched",
        "mission_id": mission_id,
    }
    root = os.getcwd()
    try:
        _append_trace(mission_id, root, record)
    except OSError:
        pass

    if is_blocked:
        print(
            "HarnessV2 retrospective hook BLOCKED: planning-analyst dispatch "
            "returned BLOCKED. retrospective Stage 2 cannot proceed without a "
            "successful sub-agent dispatch. Investigate the dispatch failure "
            "before continuing.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
