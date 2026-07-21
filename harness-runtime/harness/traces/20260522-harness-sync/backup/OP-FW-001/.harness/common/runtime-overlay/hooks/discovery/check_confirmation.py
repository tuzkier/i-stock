#!/usr/bin/env python3
"""HarnessV2 discovery PreToolUse hook: block `harness mission stage start <next>`
unless approvals.json contains a typed discovery_confirmation record for the mission.

Triggered on PreToolUse(Bash) matching `harness mission stage start`. Enforces
discovery workflow Step 10 HARD-GATE physically: the user must have actually
confirmed discovery findings (approval type=checkpoint, checkpoint=discovery_confirmation,
status=approved) before the mission can advance to PRD / next stage.

Skip cases:
- The target stage IS discovery → no-op (this hook only fires on outbound advance).
- approvals.json has a `discovery_skip` record (CLI-recorded explicit skip) → allow.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HARNESS_STAGE_START_RE = re.compile(r"harness\s+mission\s+stage\s+start")
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
    if not _HARNESS_STAGE_START_RE.search(command):
        return 0

    # If the next stage is discovery itself this hook is not the right gate.
    stage_match = _STAGE_FLAG_RE.search(command)
    if stage_match and stage_match.group(1) == "discovery":
        return 0

    mission_match = _MISSION_FLAG_RE.search(command)
    if not mission_match:
        return 0
    mission = mission_match.group(1)

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    approvals_path = cwd / "harness-runtime" / "harness" / "state" / "approvals.json"
    if not approvals_path.exists():
        print(
            f"HarnessV2 discovery hook BLOCKED: approvals.json not found; mission {mission!r} "
            f"has no discovery_confirmation record. Run discovery Step 10 first.",
            file=sys.stderr,
        )
        return 2

    try:
        document = json.loads(approvals_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0  # malformed; let other validators catch this

    records = document.get("approvals") if isinstance(document, dict) else document
    if not isinstance(records, list):
        return 0

    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("mission_id") != mission:
            continue
        # Accept either an explicit discovery_skip OR a discovery_confirmation
        # checkpoint approval as evidence that discovery has been transitioned out.
        rtype = record.get("type") or ""
        checkpoint = record.get("checkpoint") or ""
        status = (record.get("status") or "").lower()
        if rtype == "discovery_skip":
            return 0
        if (
            rtype == "checkpoint"
            and checkpoint == "discovery_confirmation"
            and status == "approved"
        ):
            return 0

    print(
        f"HarnessV2 discovery hook BLOCKED: mission {mission!r} cannot advance past discovery — "
        f"no approvals.json record of type=discovery_skip or "
        f"(type=checkpoint, checkpoint=discovery_confirmation, status=approved). "
        f"Run discovery Step 10 user confirmation first.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
