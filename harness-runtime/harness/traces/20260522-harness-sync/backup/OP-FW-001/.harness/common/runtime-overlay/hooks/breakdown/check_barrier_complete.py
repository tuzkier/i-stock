#!/usr/bin/env python3
"""breakdown-improvement-plan M3.1 PreToolUse hook: enforce the parallel-worker
barrier on `harness gate advance` / `harness contract advance` /
`harness mission stage complete breakdown`.

Plan §2.2 Step 1: breakdown is the only stage that dispatches two execution
workers (delivery-slicer + test-planning-expert) in parallel under a shared
barrier_group. Stage advance must not proceed until both workers have
landed a DONE entry in `execution_results[]` (or dispatch evidence) with the
shared `barrier_group=breakdown-workers-parallel`.

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

_ADVANCE_CMD_RE = re.compile(
    r"\bharness\s+(?:gate\s+advance|contract\s+advance|mission\s+stage\s+complete)\b"
)
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")
_STAGE_FLAG_RE = re.compile(r"--stage\s+([^\s'\"]+)")
_STAGE_COMPLETE_RE = re.compile(r"mission\s+stage\s+complete\s+([a-z_-]+)")
_REQUIRED_ROLES = ("delivery-slicer", "test-planning-expert")
_BARRIER = "breakdown-workers-parallel"


def _command_targets_breakdown(command: str) -> bool:
    stage_match = _STAGE_FLAG_RE.search(command)
    if stage_match and stage_match.group(1) == "breakdown":
        return True
    complete_match = _STAGE_COMPLETE_RE.search(command)
    if complete_match and complete_match.group(1) == "breakdown":
        return True
    return False


def _load_contract(cwd: str, mission_id: str) -> dict | None:
    path = (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "execution-brief.contract.yaml"
    )
    if not path.exists() or yaml is None:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data


def _done_roles(contract: dict) -> set[str]:
    roles: set[str] = set()
    for entry in contract.get("execution_results") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("status") != "DONE":
            continue
        if entry.get("barrier_group") and entry["barrier_group"] != _BARRIER:
            continue
        role = entry.get("role")
        if isinstance(role, str):
            roles.add(role)
    return roles


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
    if not _command_targets_breakdown(command):
        return 0
    mission_match = _MISSION_FLAG_RE.search(command)
    if mission_match is None:
        return 0
    mission_id = mission_match.group(1)
    cwd = payload.get("cwd") or str(Path.cwd())
    contract = _load_contract(cwd, mission_id)
    if contract is None:
        return 0
    done = _done_roles(contract)
    missing = [r for r in _REQUIRED_ROLES if r not in done]
    if missing:
        print(
            "HarnessV2 breakdown hook BLOCKED: parallel-worker barrier "
            f"'{_BARRIER}' incomplete. Missing DONE entries for: "
            f"{', '.join(missing)}. Re-dispatch the missing roles before "
            "advancing.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
