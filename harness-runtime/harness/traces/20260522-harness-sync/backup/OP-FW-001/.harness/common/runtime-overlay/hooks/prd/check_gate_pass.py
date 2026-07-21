#!/usr/bin/env python3
"""HarnessV2 prd PreToolUse hook: block `harness mission stage complete prd`
when the most recent gate run for prd stage has not passed.

Ensures the stage exit can only happen after a PASS gate run.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_STAGE_COMPLETE_RE = re.compile(r"\bharness\s+mission\s+stage\s+complete\s+prd\b")
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _extract_mission_id(command: str) -> str | None:
    match = _MISSION_FLAG_RE.search(command)
    return match.group(1) if match else None


def _latest_gate_result(cwd: str, mission_id: str) -> str | None:
    """Check the most recent gate report for prd stage."""
    gate_dir = (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "state"
        / "gate-reports"
        / mission_id
    )
    if not gate_dir.exists():
        return None

    # Find gate reports that match prd stage patterns
    latest_report = None
    latest_mtime = 0.0
    for report_path in gate_dir.glob("*.json"):
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        # Match prd-related gate reports
        stage = data.get("stage") or data.get("from_stage") or ""
        if "prd" not in str(stage).lower() and "requirements" not in str(stage).lower():
            continue
        mtime = report_path.stat().st_mtime
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_report = data

    if latest_report is None:
        return None
    gate_effect = latest_report.get("gate_effect") or ""
    decision = latest_report.get("decision") or ""
    if gate_effect == "pass" or decision == "can_continue":
        return "PASS"
    return "FAIL"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command")
    if not isinstance(command, str):
        return 0
    if not _STAGE_COMPLETE_RE.search(command):
        return 0

    mission_id = _extract_mission_id(command)
    if mission_id is None:
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    result = _latest_gate_result(cwd, mission_id)
    if result != "PASS":
        print(
            "HarnessV2 prd hook BLOCKED: cannot complete prd stage without a PASS gate run. "
            "Run `harness gate run --stage prd --mission <id> ...` first.",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
