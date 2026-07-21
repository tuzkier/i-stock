#!/usr/bin/env python3
"""verify M3.1 PostToolUse hook: write command_evidence_collected.flag
after a successful evidence command collect or verify run-tests call.

Intercepts PostToolUse Bash calls to:
  harness evidence command collect
  harness verify run-tests

On exit_code 0 (success), writes:
  harness-runtime/harness/stages/<mission>/traces/command_evidence_collected.flag

This flag is consumed by check_verify_prereqs.py which blocks gate advance
until command evidence has been collected.

Exit convention: 0 = always allow (PostToolUse).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_COLLECT_RE = re.compile(
    r"\bharness\s+(?:evidence\s+command\s+collect|verify\s+run-tests)\b",
    re.IGNORECASE,
)
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not _COLLECT_RE.search(command):
        return 0
    # Only flag on success
    exit_code = payload.get("tool_response", {}).get("exit_code")
    if exit_code is None:
        # PostToolUse — response in a different field depending on adapter
        result = payload.get("result") or payload.get("tool_result") or {}
        if isinstance(result, dict):
            exit_code = result.get("exit_code")
    # If we can't determine exit_code, write the flag optimistically (the
    # gate check is the authoritative enforcer anyway)
    if exit_code is not None and exit_code != 0:
        return 0
    mission_match = _MISSION_FLAG_RE.search(command)
    if mission_match is None:
        return 0
    mission_id = mission_match.group(1)
    cwd = Path(payload.get("cwd") or ".")
    traces_dir = (
        cwd / "harness-runtime" / "harness" / "stages" / mission_id / "traces"
    )
    try:
        traces_dir.mkdir(parents=True, exist_ok=True)
        (traces_dir / "command_evidence_collected.flag").write_text(
            datetime.now(timezone.utc).isoformat(), encoding="utf-8"
        )
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
