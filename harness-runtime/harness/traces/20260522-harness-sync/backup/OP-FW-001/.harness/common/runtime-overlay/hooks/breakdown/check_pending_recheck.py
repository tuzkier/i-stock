#!/usr/bin/env python3
"""breakdown-improvement-plan M3.1 PreToolUse hook: block
`harness gate advance` / `harness contract advance` when the breakdown
contract still carries pending_reviewer_recheck=true.

Mirrors the prd hook (plan §M3.1 reuse). When the mark_pending_recheck hook
has flipped the flag after an execution-brief.md edit, the reviewer round
must run before any stage gate advance can proceed.

Exit conventions: 0 = allow; 2 = block.
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

# H2: matcher regex covers both harness gate advance + harness contract advance.
_ADVANCE_CMD_RE = re.compile(r"\bharness\s+(?:gate|contract)\s+advance\b")
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")
_STAGE_FLAG_RE = re.compile(r"--stage\s+([^\s'\"]+)")


def _pending(cwd: str, mission_id: str) -> bool:
    if yaml is None:
        return False
    path = (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "execution-brief.contract.yaml"
    )
    if not path.exists():
        return False
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return False
    if not isinstance(data, dict):
        return False
    contract = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
    if not isinstance(contract, dict):
        return False
    eff = contract.get("effectiveness_review")
    if isinstance(eff, dict):
        return bool(eff.get("pending_reviewer_recheck"))
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not _ADVANCE_CMD_RE.search(command):
        return 0
    stage_match = _STAGE_FLAG_RE.search(command)
    if stage_match and stage_match.group(1) != "breakdown":
        return 0
    mission_match = _MISSION_FLAG_RE.search(command)
    if mission_match is None:
        return 0
    cwd = payload.get("cwd") or str(Path.cwd())
    if _pending(cwd, mission_match.group(1)):
        print(
            "HarnessV2 breakdown hook BLOCKED: execution-brief.contract.yaml "
            "has pending_reviewer_recheck=true. Run execution-plan-"
            "effectiveness-reviewer again (with `harness contract patch "
            "--add-round`) before advancing.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
