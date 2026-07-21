#!/usr/bin/env python3
"""discovery PreToolUse hook: block harness gate/contract advance when
discovery-brief.contract.yaml has pending_reviewer_recheck=true.

物理强制"修复必重审"——改了 discovery-brief 后若未重跑
discovery-effectiveness-reviewer 清除标志，则不能 advance。

镜像副本（活跃实现见 .harness/common/hooks/checks/discovery.py）。

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

_ADVANCE_CMD_RE = re.compile(r"\bharness\s+(?:gate|contract)\s+advance\b")
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _extract_mission(command: str) -> str | None:
    match = _MISSION_FLAG_RE.search(command)
    return match.group(1) if match else None


def _contract_path(cwd: str, mission_id: str) -> Path:
    return (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "discovery-brief.contract.yaml"
    )


def _pending(contract_path: Path) -> bool:
    if not contract_path.exists() or yaml is None:
        return False
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return False
    if not isinstance(data, dict):
        return False
    contract = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
    if not isinstance(contract, dict):
        return False
    eff = contract.get("effectiveness_review")
    return bool(isinstance(eff, dict) and eff.get("pending_reviewer_recheck"))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command")
    if not isinstance(command, str) or not _ADVANCE_CMD_RE.search(command):
        return 0

    mission_id = _extract_mission(command)
    if mission_id is None:
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    contract_path = _contract_path(cwd, mission_id)
    if _pending(contract_path):
        print(
            f"HarnessV2 discovery hook BLOCKED: {contract_path.name} has "
            "pending_reviewer_recheck=true. Re-run discovery-effectiveness-reviewer "
            "before advancing.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
