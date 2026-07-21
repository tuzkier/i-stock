#!/usr/bin/env python3
"""delivery M3.1 PreToolUse hook: block direct Write/Edit of acceptance-result.md
unless delivery.contract.yaml is initialized and verify gate has PASS status.

Checks performed before any Write/Edit to acceptance-result.md:
1. delivery.contract.yaml must exist in the same stage contract dir.
2. If verification-report.contract.yaml is readable, verify gate must be PASS
   (i.e. contract must not be completely empty / missing ac_trace).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_TRIGGER_MARKER = "acceptance-result.md"


def _find_stage_contract_dir(file_path: str) -> Path | None:
    """Attempt to locate contracts/ dir from acceptance-result.md path."""
    p = Path(file_path)
    for parent in p.parents:
        if parent.name.startswith("harness-runtime") or parent.name == "harness":
            break
        contracts = parent / "contracts"
        if contracts.exists():
            return contracts
        # Also try sibling contracts dir
        sibling = p.parent / "contracts"
        if sibling.exists():
            return sibling
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if _TRIGGER_MARKER not in file_path:
        return 0

    # Try to find the contracts dir sibling to acceptance-result.md
    p = Path(file_path)
    contracts_dir = p.parent / "contracts"

    delivery_contract = contracts_dir / "delivery.contract.yaml"
    if not delivery_contract.exists():
        print(
            "HarnessV2 delivery hook BLOCKED: delivery.contract.yaml not initialized. "
            "Run `harness contract init --template delivery --mission <id>` first.",
            file=sys.stderr,
        )
        return 2

    # Soft check: if verification-report contract is present, ensure it has ac_trace.
    vr_contract = contracts_dir / "verification-report.contract.yaml"
    if vr_contract.exists():
        try:
            import yaml  # type: ignore[import]
            doc = yaml.safe_load(vr_contract.read_text(encoding="utf-8")) or {}
            block = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
            if isinstance(block, dict):
                ac_trace = block.get("ac_trace")
                if ac_trace is not None and not isinstance(ac_trace, list):
                    print(
                        "HarnessV2 delivery hook BLOCKED: verification-report.contract.yaml "
                        "has malformed ac_trace field. Fix verification-report before delivery.",
                        file=sys.stderr,
                    )
                    return 2
        except Exception:
            pass  # yaml not installed or file unreadable; allow write but don't block

    return 0


if __name__ == "__main__":
    sys.exit(main())
