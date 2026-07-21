#!/usr/bin/env python3
"""delivery M3.1 PostToolUse hook: record delivery-package.md artifact path
and checksum into delivery.contract.yaml after a successful Write.
"""

from __future__ import annotations

import hashlib
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
    if not p.exists():
        return 0

    try:
        content = p.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()[:16]
    except OSError:
        return 0

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
            # Append delivery package artifact reference to evidence_links.
            links = pkg.get("evidence_links") or []
            if not isinstance(links, list):
                links = []
            entry = {
                "type": "delivery_package",
                "path": str(file_path),
                "checksum_sha256_prefix": checksum,
            }
            # Replace or append.
            links = [l for l in links if not (isinstance(l, dict) and l.get("type") == "delivery_package")]
            links.append(entry)
            pkg["evidence_links"] = links
            delivery_contract.write_text(
                yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False) + "\n",
                encoding="utf-8",
            )
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
