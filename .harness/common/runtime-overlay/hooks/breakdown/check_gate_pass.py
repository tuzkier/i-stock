#!/usr/bin/env python3
"""breakdown-improvement-plan M3.1 PreToolUse hook: block
`harness mission stage complete breakdown` until the latest
`harness execution-brief gate run` result is PASS.

Plan §2.9 Step 8 / Step 10 HARD-GATE: every stage exit must traverse the
gate run; this hook is the physical enforcement layer over the prose
"gate must PASS before stage complete" rule.

The hook reads the gate result from
`harness-runtime/harness/stages/<mission>/contracts/execution-brief.contract.yaml`
where `effectiveness_review.last_gate_run_status` is written by the
`execution-brief gate run` CLI's PASS path. When missing or != PASS, deny.

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

_STAGE_COMPLETE_RE = re.compile(
    r"\bharness\s+mission\s+stage\s+complete\s+breakdown\b"
)
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


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


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not _STAGE_COMPLETE_RE.search(command):
        return 0
    mission_match = _MISSION_FLAG_RE.search(command)
    if mission_match is None:
        return 0
    mission_id = mission_match.group(1)
    cwd = payload.get("cwd") or str(Path.cwd())
    contract = _load_contract(cwd, mission_id)
    if contract is None:
        print(
            "HarnessV2 breakdown hook BLOCKED: cannot verify gate run "
            "result (execution-brief.contract.yaml unloadable). Run "
            "`harness execution-brief gate run --json` and capture the "
            "PASS verdict before stage complete.",
            file=sys.stderr,
        )
        return 2
    eff = contract.get("effectiveness_review") if isinstance(contract.get("effectiveness_review"), dict) else {}
    status = eff.get("last_gate_run_status")
    if status != "PASS":
        print(
            "HarnessV2 breakdown hook BLOCKED: effectiveness_review."
            f"last_gate_run_status={status!r}; must be 'PASS' before "
            "`harness mission stage complete breakdown`. Run "
            "`harness execution-brief gate run --json` and record the "
            "PASS result.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
