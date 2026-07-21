#!/usr/bin/env python3
"""HarnessV2 prd PostToolUse hook: set pending_reviewer_recheck=true after product-definition.md edit.

Whenever the AI edits product-definition.md, this hook automatically writes
`pending_reviewer_recheck: true` into the corresponding prd.contract.yaml.
This enforces the "fix must be re-reviewed" HARD-GATE physically.

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

_PRODUCT_DEFINITION_PATTERN = re.compile(r"harness-runtime/harness/stages/[^/]+/product/product-definition\.md$")


def _contract_path_from_prd(prd_path: str) -> Path | None:
    """Derive prd.contract.yaml path from product-definition.md path."""
    match = re.search(r"harness-runtime/harness/stages/([^/]+)/product/product-definition\.md$", prd_path)
    if not match:
        return None
    mission_id = match.group(1)
    return (
        Path(prd_path).resolve().parents[1] / "contracts" / mission_id / "prd.contract.yaml"
    ).parent.parent / "contracts" / "prd.contract.yaml"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in ("Edit", "Write", "MultiEdit"):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""

    if not _PRODUCT_DEFINITION_PATTERN.search(file_path):
        return 0

    if yaml is None:
        return 0

    # Derive contract path: stages/<id>/product/product-definition.md → stages/<id>/contracts/prd.contract.yaml
    match = re.search(r"(harness-runtime/harness/stages/[^/]+)/product/product-definition\.md$", file_path)
    if not match:
        return 0
    contract_path = Path(file_path).resolve().parents[1] / "contracts" / "prd.contract.yaml"

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
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
