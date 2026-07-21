#!/usr/bin/env python3
"""verify M3.1 PostToolUse hook: record context reads (mission-contract /
execution-brief / code-review / project-context) to the trace log.

When the verification-engineer or the main agent reads one of the key
context documents, this hook appends an event to the verify trace so that
gate auditors can confirm the agent grounded its verdicts in the correct
documents.

Trace append target:
  harness-runtime/harness/stages/<mission>/traces/context_reads.jsonl

Exit convention: 0 = always allow (PostToolUse; never blocks).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_CONTEXT_FILE_MARKERS: list[str] = [
    "mission-contract.md",
    "execution-brief.md",
    "execution-brief.contract.yaml",
    "code-review.md",
    "code-review.contract.yaml",
    "project-context.md",
    "project-knowledge/specs",
]

_MISSION_PATH_RE_STR = r"harness-runtime[/\\]harness[/\\]stages[/\\]([^/\\]+)"


def _extract_mission_id(file_path: str) -> str | None:
    import re
    m = re.search(_MISSION_PATH_RE_STR, file_path)
    return m.group(1) if m else None


def _is_context_file(file_path: str) -> bool:
    norm = file_path.replace("\\", "/")
    return any(marker in norm for marker in _CONTEXT_FILE_MARKERS)


def _find_latest_mission(cwd: Path) -> str | None:
    """Fallback: find most recently modified mission directory."""
    stages_dir = cwd / "harness-runtime" / "harness" / "stages"
    if not stages_dir.is_dir():
        return None
    candidates = [p for p in stages_dir.iterdir() if p.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].name


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Read":
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not _is_context_file(file_path):
        return 0
    cwd = Path(payload.get("cwd") or ".")
    mission_id = _extract_mission_id(file_path) or _find_latest_mission(cwd)
    if mission_id is None:
        return 0
    traces_dir = (
        cwd
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "traces"
    )
    try:
        traces_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    record = {
        "event": "context_read",
        "file_path": file_path,
        "tool_name": "Read",
        "mission_id": mission_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(traces_dir / "context_reads.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
