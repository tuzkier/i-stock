#!/usr/bin/env python3
"""delivery M3.1 PreToolUse hook: block `harness gate advance` unless
delivery.contract.yaml has handoff_evidence.pause_required=true.

This enforces the no-auto-continue policy: delivery gate PASS alone is not
sufficient to advance to finishing-branch. The handoff pause must be explicit.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_GATE_ADVANCE_PATTERN = re.compile(r"\bharness\s+gate\s+advance\b")


def _find_delivery_contract(cwd: str | None) -> Path | None:
    """Search for delivery.contract.yaml from cwd up through harness-runtime."""
    if not cwd:
        return None
    search = Path(cwd)
    for _ in range(8):
        # harness-runtime layout
        candidate = search / "harness-runtime" / "harness" / "stages"
        if candidate.exists():
            for stage_dir in candidate.iterdir():
                dc = stage_dir / "contracts" / "delivery.contract.yaml"
                if dc.exists():
                    return dc
        search = search.parent
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not _GATE_ADVANCE_PATTERN.search(command):
        return 0

    # Attempt to find delivery contract.
    cwd = payload.get("cwd") or None
    dc_path = _find_delivery_contract(cwd)
    if dc_path is None:
        # Cannot verify; allow but emit warning.
        return 0

    try:
        import yaml  # type: ignore[import]
        doc = yaml.safe_load(dc_path.read_text(encoding="utf-8")) or {}
        block = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
        if isinstance(block, dict):
            pkg = block.get("delivery_package") or {}
            handoff = pkg.get("handoff_evidence") or {}
            if not handoff.get("pause_required"):
                print(
                    "HarnessV2 delivery hook BLOCKED: delivery_package.handoff_evidence."
                    "pause_required is not true. Run `harness delivery handoff --pause "
                    "--mission <id>` first.",
                    file=sys.stderr,
                )
                return 2
    except Exception:
        pass  # yaml not available or parse error; allow

    return 0


if __name__ == "__main__":
    sys.exit(main())
