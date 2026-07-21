#!/usr/bin/env python3
"""Stage-4 interaction PreToolUse hook: block harness mission stage
complete interaction when gate has not passed.
Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_STAGE_COMPLETE_RE = re.compile(r"\bharness\s+mission\s+stage\s+complete\s+interaction\b")
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _latest_gate_pass(cwd: str, mission_id: str) -> bool:
    gate_dir = Path(cwd) / "harness-runtime" / "harness" / "stages" / mission_id / "gate-reports"
    if not gate_dir.exists():
        return False
    candidates = sorted(
        list(gate_dir.glob("interaction*.json"))
        + list(gate_dir.glob("design.interaction*.json"))
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
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or not _STAGE_COMPLETE_RE.search(command):
        return 0
    m = _MISSION_FLAG_RE.search(command)
    if not m:
        return 0
    cwd = payload.get("cwd") or str(Path.cwd())
    if not _latest_gate_pass(cwd, m.group(1)):
        print(
            "HarnessV2 interaction hook BLOCKED: gate report for "
            f"interaction (mission={m.group(1)}) is missing or has "
            "status != PASS.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
