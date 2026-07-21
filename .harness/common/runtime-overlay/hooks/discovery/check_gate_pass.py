#!/usr/bin/env python3
"""HarnessV2 discovery PreToolUse hook: block `harness mission stage complete discovery`
unless the most recent `harness gate run --stage discovery` returned PASS.

Triggered on PreToolUse(Bash) matching `harness mission stage complete` (with
either explicit `--stage discovery` or implicit current-stage). Enforces
discovery workflow Step 11 HARD-GATE physically: refuses stage exit until the
gate has actually PASSed (so a FAIL gate cannot be silently bypassed by
calling `stage complete` directly).

Signal source: `harness-runtime/harness/state/gate-reports/<mission>/discovery__*.json`
files. The hook scans for the latest discovery-stage gate report and accepts
status=PASS (case-insensitive); anything else blocks.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HARNESS_STAGE_COMPLETE_RE = re.compile(r"harness\s+mission\s+stage\s+complete")
_MISSION_FLAG_RE = re.compile(r"--mission[=\s]+(\S+)")
_STAGE_FLAG_RE = re.compile(r"--stage[=\s]+(\S+)")


def _resolve_command(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    for key in ("command", "cmd"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    command = _resolve_command(payload) or ""
    if not _HARNESS_STAGE_COMPLETE_RE.search(command):
        return 0

    stage_match = _STAGE_FLAG_RE.search(command)
    if stage_match and stage_match.group(1) != "discovery":
        return 0  # Not a discovery-stage exit; let other stage hooks decide.

    mission_match = _MISSION_FLAG_RE.search(command)
    if not mission_match:
        return 0
    mission = mission_match.group(1)

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    reports_dir = cwd / "harness-runtime" / "harness" / "state" / "gate-reports" / mission
    if not reports_dir.exists():
        print(
            f"HarnessV2 discovery hook BLOCKED: no gate-reports dir for mission {mission!r}; "
            f"run `harness gate run --stage discovery --mission {mission}` first.",
            file=sys.stderr,
        )
        return 2

    # Find latest discovery-stage gate report. Filename convention from intake:
    # `<stage>__<lane>__<operation>.json`.
    candidates = sorted(reports_dir.glob("discovery__*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print(
            f"HarnessV2 discovery hook BLOCKED: no discovery__*.json gate report for mission {mission!r}; "
            f"run `harness gate run --stage discovery --mission {mission}` first.",
            file=sys.stderr,
        )
        return 2

    latest = candidates[0]
    try:
        report = json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(
            f"HarnessV2 discovery hook BLOCKED: gate report {latest.name} is not parseable JSON.",
            file=sys.stderr,
        )
        return 2

    status = str(report.get("status") or "").upper()
    if status == "PASS":
        return 0

    print(
        f"HarnessV2 discovery hook BLOCKED: latest discovery gate report "
        f"{latest.name} has status={status!r} (expected PASS); re-run `harness gate run "
        f"--stage discovery --mission {mission}` after fixing FAIL findings.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
