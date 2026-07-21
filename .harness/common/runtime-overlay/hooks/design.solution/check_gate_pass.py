#!/usr/bin/env python3
"""Stage-4 solution PreToolUse hook: block
`harness mission stage complete solution` when the most recent gate run for
the solution stage has not passed.

Mirrors the prd stage-exit gating so the solution lane cannot complete
without a PASS gate run.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_STAGE_COMPLETE_RE = re.compile(r"\bharness\s+mission\s+stage\s+complete\s+solution\b")
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _extract_mission(command: str) -> str | None:
    match = _MISSION_FLAG_RE.search(command)
    return match.group(1) if match else None


def _latest_gate_pass(cwd: str, mission_id: str) -> bool:
    """Inspect gate report directory for the latest run for solution.

    Returns True if the latest report shows status=PASS, False otherwise.
    Conservative: missing reports treated as not-passed so the hook blocks.
    """
    gate_dir = (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "gate-reports"
    )
    if not gate_dir.exists():
        return False
    candidates = sorted(
        list(gate_dir.glob("solution*.json"))
        + list(gate_dir.glob("design.solution*.json"))
        + list(gate_dir.glob("design*.json")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for report in candidates:
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        return data.get("status") == "PASS"
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command")
    if not isinstance(command, str) or not _STAGE_COMPLETE_RE.search(command):
        return 0
    mission_id = _extract_mission(command)
    if not mission_id:
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    if not _latest_gate_pass(cwd, mission_id):
        print(
            f"HarnessV2 solution hook BLOCKED: gate report for "
            f"solution (mission={mission_id}) is missing or has status != PASS. "
            "Run `harness gate run --stage solution` and ensure PASS before completing.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
