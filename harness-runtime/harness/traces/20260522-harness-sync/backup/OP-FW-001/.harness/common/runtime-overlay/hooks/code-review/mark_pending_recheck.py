#!/usr/bin/env python3
"""code-review M3.1 PostToolUse hook: when a code file is edited after
reviewers have completed a round, mark the contract as requiring recheck.

This hook fires on PostToolUse Edit/Write/MultiEdit.  If the edited file
is NOT the code-review.md or code-review.contract.yaml (those are write-
protected by check_contract_via_cli), and the mission has an existing
code-review.contract.yaml, set
  control_contract.effectiveness_review.pending_reviewer_recheck = true

The check_review_ready hook and `harness review check-ready` CLI will then
refuse stage-complete until the flag is cleared by a fresh reviewer round.

Exit conventions: 0 — always (non-blocking post hook).
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

# Patterns for files that ARE the code-review control-plane artifacts;
# writing these should NOT trigger pending_reviewer_recheck (they are
# written by the control plane itself).
_CONTROL_PLANE_PATTERNS = [
    re.compile(r"code-review\.contract\.yaml$"),
    re.compile(r"code-review\.md$"),
]

# Pattern to extract mission id from the path.
_MISSION_RE = re.compile(
    r"harness(?:-runtime)?/harness/stages/([^/]+)/"
)


def _is_control_plane_file(file_path: str) -> bool:
    return any(p.search(file_path) for p in _CONTROL_PLANE_PATTERNS)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = str(tool_input.get("file_path") or "")

    if not file_path:
        return 0
    if _is_control_plane_file(file_path):
        return 0
    if yaml is None:
        return 0

    # Try to resolve the mission id from the file path.
    mission_match = _MISSION_RE.search(file_path)
    if mission_match is None:
        return 0
    mission_id = mission_match.group(1)

    # Locate the code-review contract relative to the cwd.
    cwd = payload.get("cwd") or str(Path.cwd())
    contract_path = (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "code-review.contract.yaml"
    )
    if not contract_path.exists():
        return 0

    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return 0

    if not isinstance(data, dict):
        return 0

    contract = (
        data.get("control_contract")
        if isinstance(data.get("control_contract"), dict)
        else data
    )
    if not isinstance(contract, dict):
        return 0

    eff = contract.get("effectiveness_review")
    if isinstance(eff, dict):
        eff["pending_reviewer_recheck"] = True
    else:
        contract["effectiveness_review"] = {"pending_reviewer_recheck": True}

    try:
        contract_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
            + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
