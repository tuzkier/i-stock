#!/usr/bin/env python3
"""HarnessV2 discovery PreToolUse hook: block `harness contract advance` when
dependency-impact was triggered but dependency-validity-reviewer hasn't PASSED.

Triggered on PreToolUse(Bash) matching `harness contract advance` or
`harness gate advance`. Enforces discovery workflow Step 6 HARD-GATE: when
`check-dependency-trigger.required=true`, the dependency-impact skill must run
AND its dependency-validity-reviewer verdict must be PASS before the discovery
stage gate can advance.

Signals (from the discovery-brief contract on disk):

- contract.dependency_trigger.required (set by `harness discovery check-dependency-trigger`)
- OR contract.degradations[] containing a dependency-related entry (acknowledged skip)
- contract.role_verdicts[] containing a dependency-validity-reviewer entry with verdict=PASS

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

_HARNESS_ADVANCE_RE = re.compile(r"harness\s+(?:contract|gate)\s+advance")
_MISSION_FLAG_RE = re.compile(r"--mission[=\s]+(\S+)")


def _resolve_command(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    for key in ("command", "cmd"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def _extract_mission(command: str) -> str | None:
    match = _MISSION_FLAG_RE.search(command)
    return match.group(1) if match else None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = _resolve_command(payload) or ""
    if not _HARNESS_ADVANCE_RE.search(command):
        return 0

    mission = _extract_mission(command)
    if not mission:
        # Cannot determine which mission's contract to inspect — allow but the
        # CLI itself will surface a clearer error.
        return 0

    if yaml is None:
        return 0

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    contract_path = cwd / "harness-runtime" / "harness" / "stages" / mission / "contracts" / "discovery-brief.contract.yaml"
    if not contract_path.exists():
        # Not a discovery-stage advance; let other stage hooks decide.
        return 0

    try:
        document = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return 0

    contract = document.get("control_contract")
    if not isinstance(contract, dict):
        return 0

    dependency_trigger = contract.get("dependency_trigger") or {}
    required = bool(dependency_trigger.get("required")) if isinstance(dependency_trigger, dict) else False
    if not required:
        # Dependency-impact was not required for this mission; allow.
        return 0

    # Required = true. Look for a dependency-validity-reviewer PASS verdict.
    role_verdicts = contract.get("role_verdicts") or []
    for entry in role_verdicts:
        if not isinstance(entry, dict):
            continue
        role = (entry.get("dispatch") or {}).get("subagent_id") if isinstance(entry.get("dispatch"), dict) else entry.get("role")
        if role == "dependency-validity-reviewer" and str(entry.get("verdict") or entry.get("status") or "").upper() == "PASS":
            return 0

    # Also accept an explicit degradation acknowledging the dependency gap.
    degradations = contract.get("degradations") or []
    for entry in degradations:
        if isinstance(entry, dict) and "dependency" in str(entry.get("kind", "")).lower():
            return 0

    print(
        f"HarnessV2 discovery hook BLOCKED: mission {mission!r} contract has "
        f"dependency_trigger.required=true but no dependency-validity-reviewer PASS "
        f"in role_verdicts[]. Run dependency-impact skill and record reviewer verdict "
        f"before advancing the gate.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
