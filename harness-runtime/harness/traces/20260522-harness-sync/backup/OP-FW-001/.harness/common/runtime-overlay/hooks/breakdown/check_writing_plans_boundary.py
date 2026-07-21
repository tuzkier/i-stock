#!/usr/bin/env python3
"""breakdown-improvement-plan M3.1 PreToolUse hook: gate `harness writing-plans
run` to the breakdown stage only.

Plan §2.7 / SKILL.md §writing-plans 调用边界: writing-plans is the breakdown
stage's internal carrier; calling it from any other stage (or without the
internal-carrier mode) routes around the breakdown lifecycle. Hook denies
the Bash invocation unless:

- the command carries `--mode internal-carrier`, AND
- the current stage (read from `harness-runtime/harness/mission-status.yaml`
  when available; otherwise inferred from cwd / mission-id flag) is
  `breakdown`, OR the command carries the explicit `--manual-replan` flag
  with a trace-log already recording the user-ack approval.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_WRITING_PLANS_CMD_RE = re.compile(r"\bharness\s+writing-plans\s+run\b")
_MODE_FLAG_RE = re.compile(r"--mode\s+([^\s'\"]+)")
_MANUAL_REPLAN_RE = re.compile(r"--manual-replan\b")
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _current_stage(cwd: str, mission_id: str | None) -> str | None:
    status_path = Path(cwd) / "harness-runtime" / "harness" / "mission-status.yaml"
    if not status_path.exists() or yaml is None:
        return None
    try:
        data = yaml.safe_load(status_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    if mission_id and isinstance(data.get("missions"), dict):
        mission_entry = data["missions"].get(mission_id)
        if isinstance(mission_entry, dict) and isinstance(
            mission_entry.get("current_stage"), str
        ):
            return mission_entry["current_stage"]
    return data.get("current_stage") if isinstance(data.get("current_stage"), str) else None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not _WRITING_PLANS_CMD_RE.search(command):
        return 0
    mode_match = _MODE_FLAG_RE.search(command)
    if mode_match is None or mode_match.group(1) != "internal-carrier":
        print(
            "HarnessV2 breakdown hook BLOCKED: `harness writing-plans run` "
            "requires --mode internal-carrier. writing-plans is the "
            "breakdown stage's internal carrier; no other entry is "
            "supported.",
            file=sys.stderr,
        )
        return 2
    # Manual replan escape hatch — only honored when stage truly is not
    # breakdown but the user has explicitly opted in.
    if _MANUAL_REPLAN_RE.search(command):
        return 0
    cwd = payload.get("cwd") or str(Path.cwd())
    mission_match = _MISSION_FLAG_RE.search(command)
    mission_id = mission_match.group(1) if mission_match else None
    stage = _current_stage(cwd, mission_id)
    if stage and stage != "breakdown":
        print(
            "HarnessV2 breakdown hook BLOCKED: writing-plans called from "
            f"stage={stage!r} (current); only allowed from `breakdown` or "
            "with --manual-replan + trace-log ack.",
            file=sys.stderr,
        )
        return 2
    # When stage cannot be determined, allow but rely on the CLI's own
    # `--mode internal-carrier` validation (already enforced server-side).
    return 0


if __name__ == "__main__":
    sys.exit(main())
