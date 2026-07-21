#!/usr/bin/env python3
"""verify M3.1 PostToolUse hook: record subagent dispatch envelopes to
the verify trace and set reviewer_turn / worker_turn flag files.

When the harness dispatches verification-engineer or
verification-effectiveness-reviewer, this hook:
  1. Appends a dispatch record to traces/dispatches.jsonl
  2. Writes traces/reviewer_turn.flag (if reviewer) or
     traces/worker_turn.flag (if worker)
     — these flags are read by deny_reviewer_write.py and
       check_worker_write_scope.py to identify the current role context.

Intercepts: PostToolUse Task (subagent dispatch).

Exit convention: 0 = always allow (PostToolUse).
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REVIEWER_IDS = frozenset(
    {
        "verification-effectiveness-reviewer",
        "verificationeffectivenessreviewer",
    }
)
_WORKER_IDS = frozenset({"verification-engineer", "verificationengineer"})

_MISSION_PATH_RE_STR = r"harness-runtime[/\\]harness[/\\]stages[/\\]([^/\\]+)"


def _normalize(agent_id: str) -> str:
    return agent_id.lower().replace("-", "").replace("_", "")


def _find_latest_mission(cwd: Path) -> str | None:
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
    tool_name = payload.get("tool_name") or ""
    if tool_name not in {"Task", "dispatch", "Dispatch"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    agent_id = (
        tool_input.get("subagent_type")
        or tool_input.get("agent_id")
        or tool_input.get("agent")
        or ""
    )
    if not agent_id:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    mission_id = _find_latest_mission(cwd)
    if mission_id is None:
        return 0
    traces_dir = (
        cwd / "harness-runtime" / "harness" / "stages" / mission_id / "traces"
    )
    try:
        traces_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    norm = _normalize(agent_id)
    is_reviewer = any(_normalize(r) == norm for r in _REVIEWER_IDS)
    is_worker = any(_normalize(w) == norm for w in _WORKER_IDS)
    record = {
        "event": "dispatch",
        "agent_id": agent_id,
        "is_reviewer": is_reviewer,
        "is_worker": is_worker,
        "mission_id": mission_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(traces_dir / "dispatches.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        pass
    # Write turn flags
    if is_reviewer:
        try:
            (traces_dir / "reviewer_turn.flag").write_text(
                datetime.now(timezone.utc).isoformat(), encoding="utf-8"
            )
        except OSError:
            pass
    elif is_worker:
        try:
            (traces_dir / "worker_turn.flag").write_text(
                datetime.now(timezone.utc).isoformat(), encoding="utf-8"
            )
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
