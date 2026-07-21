#!/usr/bin/env python3
"""Stage-4 design+solution PostToolUse hook: set solution.contract.yaml
pending_reviewer_recheck=true after any solution.md edit.

Mirrors the prd modify-then-recheck loop so solution-architect cannot ship
a fix and silently advance past the reviewer.

Exit conventions: 0 = always (PostToolUse hooks are advisory).
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

_SOLUTION_PATH_RE = re.compile(r"harness-runtime/harness/stages/([^/]+)/solution\.md$")


def _extract_mission_from_path(path: str) -> str | None:
    match = _SOLUTION_PATH_RE.search(path.replace("\\", "/"))
    return match.group(1) if match else None


def _contract_path(cwd: str, mission_id: str) -> Path:
    return (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "solution.contract.yaml"
    )


def _set_pending(contract_path: Path) -> None:
    if not contract_path.exists() or yaml is None:
        return
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return
    if not isinstance(data, dict):
        return
    contract = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
    if not isinstance(contract, dict):
        return
    eff = contract.setdefault("effectiveness_review", {})
    if isinstance(eff, dict):
        eff["pending_reviewer_recheck"] = True
    try:
        contract_path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    except OSError:
        return


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name")
    if tool_name not in {"Edit", "Write", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not isinstance(file_path, str):
        return 0

    mission_id = _extract_mission_from_path(file_path)
    if not mission_id:
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    _set_pending(_contract_path(cwd, mission_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
