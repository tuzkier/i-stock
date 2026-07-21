#!/usr/bin/env python3
"""delivery M3.1 PostToolUse hook: record acceptance-result.md artifact path
and checksum into delivery.contract.yaml after a successful Write.

This keeps the acceptance_state_ref in sync with the actual artifact so the
delivery_package can reference a real path + checksum.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


_TRIGGER_MARKER = "acceptance-result.md"


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
    if not p.exists():
        return 0

    # Compute checksum of written file.
    try:
        content = p.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()[:16]
    except OSError:
        return 0

    # Update delivery.contract.yaml acceptance_state_ref if contract exists.
    contracts_dir = p.parent / "contracts"
    delivery_contract = contracts_dir / "delivery.contract.yaml"
    if not delivery_contract.exists():
        return 0

    try:
        import yaml  # type: ignore[import]
        doc = yaml.safe_load(delivery_contract.read_text(encoding="utf-8")) or {}
        contract_block = (
            doc.get("control_contract")
            if isinstance(doc.get("control_contract"), dict)
            else doc
        )
        if isinstance(contract_block, dict):
            pkg = contract_block.get("delivery_package")
            if not isinstance(pkg, dict):
                pkg = {}
                contract_block["delivery_package"] = pkg
            # Set acceptance_state_ref with path and checksum.
            pkg["acceptance_state_ref"] = {
                "path": str(file_path),
                "contract_path": str(delivery_contract),
                "checksum_sha256_prefix": checksum,
            }
            delivery_contract.write_text(
                yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False) + "\n",
                encoding="utf-8",
            )
    except Exception:
        pass  # Non-fatal; annotation is best-effort.

    return 0


if __name__ == "__main__":
    sys.exit(main())
