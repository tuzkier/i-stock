#!/usr/bin/env python3
"""breakdown-improvement-plan M3.1 PostToolUse hook: set
pending_reviewer_recheck=true after execution-brief.md edit.

Follows the same shape as the prd hook (plan §M3.1 reuses prd template):
whenever the AI edits execution-brief.md, this hook flips
`effectiveness_review.pending_reviewer_recheck=true` in the matching
execution-brief.contract.yaml. The pre-advance hook (check_pending_recheck)
then refuses to advance the gate until a reviewer round resets the flag.

Exit conventions: 0 = always (non-blocking post hook).
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

_EXEC_BRIEF_MD_PATTERN = re.compile(
    r"harness-runtime/harness/stages/[^/]+/execution-brief\.md$"
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name", "") not in ("Edit", "Write", "MultiEdit"):
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not _EXEC_BRIEF_MD_PATTERN.search(file_path):
        return 0
    if yaml is None:
        return 0
    contract_path = (
        Path(file_path).resolve().parent
        / "contracts"
        / "execution-brief.contract.yaml"
    )
    if not contract_path.exists():
        return 0
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return 0
    if not isinstance(data, dict):
        return 0
    contract = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
    if not isinstance(contract, dict):
        return 0
    eff = contract.get("effectiveness_review")
    if isinstance(eff, dict):
        eff["pending_reviewer_recheck"] = True
    else:
        contract["effectiveness_review"] = {"pending_reviewer_recheck": True}
    contract_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
