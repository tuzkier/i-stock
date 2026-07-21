#!/usr/bin/env python3
"""delivery M3.1 PreToolUse hook: block direct Write/Edit of delivery-package.md
unless delivery.contract.yaml has acceptance_state_ref set.

The acceptance_state_ref is the hard reference linking delivery-package to the
acceptance-result contract. Without it, the delivery-package can silently
drift from what the user actually accepted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_TRIGGER_MARKER = "delivery-package.md"


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

    p = Path(file_path)
    contracts_dir = p.parent / "contracts"
    delivery_contract = contracts_dir / "delivery.contract.yaml"

    if not delivery_contract.exists():
        # First write before contract init: allow with warning (contract will be
        # created by agent in Step 3). Only block if contract exists but
        # acceptance_state_ref is missing.
        return 0

    # If contract exists, check acceptance_state_ref.
    try:
        import yaml  # type: ignore[import]
        doc = yaml.safe_load(delivery_contract.read_text(encoding="utf-8")) or {}
        block = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
        if isinstance(block, dict):
            pkg = block.get("delivery_package")
            if isinstance(pkg, dict):
                ref = pkg.get("acceptance_state_ref")
                if ref is None:
                    print(
                        "HarnessV2 delivery hook BLOCKED: delivery_package.acceptance_state_ref "
                        "is null in delivery.contract.yaml. Set it to the acceptance-result "
                        "contract path before writing delivery-package.md.",
                        file=sys.stderr,
                    )
                    return 2
    except Exception:
        pass  # yaml not available or parse error; allow write

    return 0


if __name__ == "__main__":
    sys.exit(main())
