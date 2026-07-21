#!/usr/bin/env python3
"""HarnessV2 intake PostToolUse hook: mark contract as needing re-review after edit.

Triggered on PostToolUse(Edit|Write). When the AI modifies
`harness-runtime/harness/missions/<mission_id>/mission-contract.md` or its
external `mission-contract.contract.yaml`, this hook flips
`control_contract.pending_reviewer_recheck=true` on the contract YAML so the
companion PreToolUse hook `check_pending_recheck.py` can block subsequent
`harness gate/contract advance` until the reviewer re-runs.

Exit conventions: 0 = always (PostToolUse cannot block).
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

_MISSION_CONTRACT_PATH_RE = re.compile(
    r"harness-runtime/harness/missions/(?P<mission>[^/]+)/"
    r"(?:mission-contract\.md|contracts/mission-contract\.contract\.yaml)$"
)


def _resolve_target_path(payload: dict) -> str | None:
    for source in ("tool_input", "tool_response"):
        block = payload.get(source) or {}
        for key in ("file_path", "filePath", "path"):
            value = block.get(key)
            if isinstance(value, str):
                return value
    return None


def _contract_path(cwd: str, mission_id: str) -> Path:
    return (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "missions"
        / mission_id
        / "contracts"
        / "mission-contract.contract.yaml"
    )


def main() -> int:
    if yaml is None:
        return 0
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return 0

    target = _resolve_target_path(payload)
    if target is None:
        return 0

    cwd = payload.get("cwd") or str(Path.cwd())
    try:
        rel = str(Path(target).resolve().relative_to(Path(cwd).resolve()))
    except (ValueError, OSError):
        rel = target

    match = _MISSION_CONTRACT_PATH_RE.search(rel)
    if not match:
        return 0

    mission_id = match.group("mission")
    contract_path = _contract_path(cwd, mission_id)
    if not contract_path.exists():
        return 0

    try:
        text = contract_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except (yaml.YAMLError, OSError):
        return 0

    if not isinstance(data, dict):
        return 0

    contract = data.setdefault("control_contract", {})
    if not isinstance(contract, dict):
        return 0

    if contract.get("pending_reviewer_recheck"):
        return 0

    contract["pending_reviewer_recheck"] = True
    try:
        contract_path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
