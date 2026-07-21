#!/usr/bin/env python3
"""Report static and trace-log protocol coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PROTOCOLS = ("quality-control", "bug-fix")


def common_root(root: Path) -> Path:
    candidates = (
        root / "package" / "common",
        root / ".harness" / "common",
    )
    for candidate in candidates:
        if (candidate / "skills").is_dir() and (candidate / "rules").is_dir():
            return candidate
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="harness-runtime/harness/state/protocol-coverage")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    common = common_root(root)
    files = list((common / "skills").rglob("*.md")) + list((common / "rules").glob("*.md"))
    coverage = {protocol: {"static_references": [], "trace_hits": 0} for protocol in PROTOCOLS}
    for path in files:
        text = path.read_text(encoding="utf-8")
        for protocol in PROTOCOLS:
            if protocol in text:
                coverage[protocol]["static_references"].append(str(path.relative_to(root)))
    for trace_path in [root / "harness-runtime" / "harness" / "state" / "trace-log.md", root / "harness" / "state" / "trace-log.md"]:
        if trace_path.exists():
            text = trace_path.read_text(encoding="utf-8")
            for protocol in PROTOCOLS:
                coverage[protocol]["trace_hits"] += text.count(protocol)
    out_base = root / args.output
    out_base.parent.mkdir(parents=True, exist_ok=True)
    json_path = out_base.with_suffix(".json")
    md_path = out_base.with_suffix(".md")
    payload = {"schema_version": 1, "protocols": coverage}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = ["# Protocol Coverage", "", "| Protocol | Static References | Trace Hits |", "|----------|-------------------|------------|"]
    for protocol, data in coverage.items():
        rows.append(f"| {protocol} | {len(data['static_references'])} | {data['trace_hits']} |")
    md_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
