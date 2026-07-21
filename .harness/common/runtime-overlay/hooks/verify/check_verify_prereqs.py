#!/usr/bin/env python3
"""verify M3.1 PreToolUse hook: block `harness gate advance` /
`harness contract advance` until verify prerequisites are satisfied.

Prerequisites checked (all must pass):
  1. command_evidence_collected — trace file or contract field set to true.
  2. last_gate_run_status == PASS — stored in verification contract or
     gate-run trace file.
  3. contradictions_status == PASS — stored in contradiction trace file or
     contract field.

Mirrors the prd / breakdown M3.1 gate_pass hook pattern.

State sources:
  harness-runtime/harness/stages/<mission>/contracts/verification-report.contract.yaml
    gate_run.last_gate_run_status
    gate_run.contradictions_status
    gate_run.command_evidence_collected
  harness-runtime/harness/stages/<mission>/traces/command_evidence_collected.flag
  harness-runtime/harness/stages/<mission>/traces/gate_run_pass.flag
  harness-runtime/harness/stages/<mission>/traces/contradictions_pass.flag

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

_ADVANCE_RE = re.compile(
    r"\bharness\s+(?:gate\s+advance|contract\s+advance)\b",
    re.IGNORECASE,
)
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _load_contract(cwd: Path, mission_id: str) -> dict | None:
    path = (
        cwd
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "verification-report.contract.yaml"
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


def _flag_exists(cwd: Path, mission_id: str, flag_name: str) -> bool:
    flag = (
        cwd
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "traces"
        / flag_name
    )
    return flag.exists()


def _check_prereqs(cwd: Path, mission_id: str) -> list[str]:
    """Return list of unmet prerequisite descriptions (empty = all met)."""
    contract = _load_contract(cwd, mission_id)
    failures: list[str] = []

    # 1. command_evidence_collected
    collected = False
    if _flag_exists(cwd, mission_id, "command_evidence_collected.flag"):
        collected = True
    elif contract is not None:
        gr = contract.get("gate_run") if isinstance(contract.get("gate_run"), dict) else {}
        collected = bool(gr.get("command_evidence_collected", False))
        if not collected:
            # also check top-level field
            collected = bool(contract.get("command_evidence_collected", False))
    if not collected:
        failures.append(
            "command_evidence_collected=false (run `harness evidence command collect` "
            "or `harness verify run-tests` first)"
        )

    # 2. gate_run PASS
    gate_pass = False
    if _flag_exists(cwd, mission_id, "gate_run_pass.flag"):
        gate_pass = True
    elif contract is not None:
        gr = contract.get("gate_run") if isinstance(contract.get("gate_run"), dict) else {}
        status = gr.get("last_gate_run_status") or contract.get("last_gate_run_status")
        gate_pass = status == "PASS"
    if not gate_pass:
        failures.append(
            "last_gate_run_status != PASS (run `harness verify gate run --mission <id> --json`)"
        )

    # 3. contradictions PASS
    contra_pass = False
    if _flag_exists(cwd, mission_id, "contradictions_pass.flag"):
        contra_pass = True
    elif contract is not None:
        gr = contract.get("gate_run") if isinstance(contract.get("gate_run"), dict) else {}
        status = gr.get("contradictions_status") or contract.get("contradictions_status")
        contra_pass = status in {"PASS", "none"}
    if not contra_pass:
        failures.append(
            "contradictions_status != PASS (run "
            "`harness verify detect-contradictions --mission <id> --json`)"
        )

    return failures


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not _ADVANCE_RE.search(command):
        return 0
    mission_match = _MISSION_FLAG_RE.search(command)
    if mission_match is None:
        # Cannot determine mission — pass through rather than false-positive block
        return 0
    mission_id = mission_match.group(1)
    cwd = Path(payload.get("cwd") or ".")
    unmet = _check_prereqs(cwd, mission_id)
    if not unmet:
        return 0
    failures_str = "; ".join(unmet)
    print(
        "HarnessV2 verify hook BLOCKED (VERIFY_PREREQS_NOT_MET): "
        "cannot advance verify gate until all prerequisites are satisfied. "
        f"Unmet: [{failures_str}]. "
        "Complete the required steps before running `harness gate advance`.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
