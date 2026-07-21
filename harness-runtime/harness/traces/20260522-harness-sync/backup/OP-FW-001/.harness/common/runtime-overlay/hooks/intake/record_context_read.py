#!/usr/bin/env python3
"""HarnessV2 intake PostToolUse hook: record project-context.md read in trace.

Triggered on PostToolUse(Read). Appends a structured event to the active
mission's JSONL trace whenever the AI reads `project-context.md`. The trace
is later consumed by retrospective stage / verification stage to confirm the
main flow actually loaded the project context required by the workflow.

Exit conventions: 0 = always (PostToolUse cannot block).
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from pathlib import Path

_CONTEXT_PATH_RE = re.compile(r"(?:^|/)project-context\.md$")


def _resolve_target_path(payload: dict) -> str | None:
    for source in ("tool_input", "tool_response"):
        block = payload.get(source) or {}
        for key in ("file_path", "filePath", "path"):
            value = block.get(key)
            if isinstance(value, str):
                return value
    return None


def _active_mission(cwd: str) -> str | None:
    """Best-effort: derive the active mission id from the harness state file.

    Returns None when no active mission is identifiable; the hook then
    appends to a generic `harness-runtime/harness/traces/_context-reads.jsonl`
    so the event is not lost.
    """
    state_path = Path(cwd) / "harness-runtime" / "harness" / "state" / "active-mission"
    if state_path.exists():
        try:
            mission = state_path.read_text(encoding="utf-8").strip()
            return mission or None
        except OSError:
            return None
    return None


def _trace_path(cwd: str, mission_id: str | None) -> Path:
    base = Path(cwd) / "harness-runtime" / "harness" / "traces"
    if mission_id:
        return base / mission_id / "steps.jsonl"
    return base / "_context-reads.jsonl"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in {"Read"}:
        return 0

    target = _resolve_target_path(payload)
    if target is None or not _CONTEXT_PATH_RE.search(target):
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    mission_id = _active_mission(cwd)
    trace_file = _trace_path(cwd, mission_id)
    trace_file.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "event": "context-read",
        "path": target,
        "mission_id": mission_id,
        "timestamp": _dt.datetime.now().astimezone().isoformat(),
    }
    try:
        with trace_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
