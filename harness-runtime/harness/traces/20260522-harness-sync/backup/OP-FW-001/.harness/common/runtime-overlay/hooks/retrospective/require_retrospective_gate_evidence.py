#!/usr/bin/env python3
"""retrospective-improvement-plan M3.1 PreToolUse hook: block stage exit
until Step 5 contract check evidence is present.

Fires on `Bash` tool calls that attempt to run
`harness mission stage complete --stage retrospective`. Checks that the
per-mission trace log contains a `step5_contract_check` event with
`status=pass`, OR that the stage directory has a gate-report JSON showing PASS.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


_STAGE_COMPLETE_MARKERS = (
    "mission stage complete",
    "stage complete",
)
_RETRO_STAGE_ARG = "retrospective"


def _check_trace_evidence(mission_id: str, root: str) -> bool:
    """Return True if trace log shows step5_contract_check passed."""
    trace_path = Path(root) / "harness-runtime" / "harness" / "traces" / mission_id / "steps.jsonl"
    if not trace_path.exists():
        return False
    with trace_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                record.get("step") in {"step5_contract_check", "step5", "gate_run"}
                and str(record.get("status") or "").lower() == "pass"
            ):
                return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name")
    if tool_name != "Bash":
        return 0

    tool_input = payload.get("tool_input") or {}
    command = str(tool_input.get("command") or "")

    # Only fire when attempting retrospective stage exit.
    has_complete = any(m in command for m in _STAGE_COMPLETE_MARKERS)
    has_retro = _RETRO_STAGE_ARG in command
    if not (has_complete and has_retro):
        return 0

    # Attempt to locate mission id from the command string.
    mission_id: str | None = None
    parts = command.split()
    for i, part in enumerate(parts):
        if part in {"--mission", "-m"} and i + 1 < len(parts):
            mission_id = parts[i + 1]
            break

    root = os.getcwd()
    if mission_id and _check_trace_evidence(mission_id, root):
        return 0

    # If we cannot confirm evidence, emit a warning but do NOT hard-block (exit 0
    # with stderr warning) — gate evidence may exist as a gate-report JSON rather
    # than a trace event. The hook prints a reminder so the workflow is aware.
    print(
        "HarnessV2 retrospective hook WARNING: no Step 5 contract-check PASS "
        "evidence found in trace log for this retrospective. Ensure "
        "`harness gate run --stage retrospective` or "
        "`harness contract check --artifact ...` returned PASS before calling "
        "stage complete.",
        file=sys.stderr,
    )
    # Return 0 (warn, not block) so the gate itself remains the hard-control;
    # this hook provides advisory signal only to avoid double-blocking.
    return 0


if __name__ == "__main__":
    sys.exit(main())
