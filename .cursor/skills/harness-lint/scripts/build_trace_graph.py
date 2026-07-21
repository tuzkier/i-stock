#!/usr/bin/env python3
"""Build a lightweight cross-mission trace graph from Control Contracts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml

ID_PATTERN = re.compile(r"\b(REQ-[A-Za-z0-9-]+|SCN-[A-Za-z0-9-]+|US-[A-Za-z0-9-]+|UC-[A-Za-z0-9-]+|DEC-[A-Za-z0-9-]+|MOD-[A-Za-z0-9-]+|IF-[A-Za-z0-9-]+|DATA-[A-Za-z0-9-]+|VS-[A-Za-z0-9-]+|T-?\d+|EV-[A-Za-z0-9-]+|CMD-[A-Za-z0-9-]+|FND-[A-Za-z0-9-]+|MEM-[A-Za-z0-9-]+)\b")


def contract_from(path: Path) -> dict[str, Any] | None:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(parsed, dict):
        return None
    contract = parsed.get("control_contract")
    return contract if isinstance(contract, dict) else None


def walk(value: Any) -> list[Any]:
    if isinstance(value, dict):
        out: list[Any] = []
        for nested in value.values():
            out.extend(walk(nested))
        return out
    if isinstance(value, list):
        out = []
        for nested in value:
            out.extend(walk(nested))
        return out
    return [value]


def ids_in(value: Any) -> set[str]:
    ids: set[str] = set()
    for item in walk(value):
        if isinstance(item, str):
            ids.update(ID_PATTERN.findall(item))
    return ids


def build(root: Path) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    for path in list((root / "harness-runtime" / "harness").rglob("*.contract.yaml")) + list((root / "harness").rglob("*.contract.yaml")):
        contract = contract_from(path)
        if not contract:
            continue
        doc_id = f"contract:{path.relative_to(root)}"
        nodes[doc_id] = {"type": "contract", "path": str(path.relative_to(root)), "contract_type": contract.get("type"), "stage": contract.get("stage")}
        for item_id in ids_in(contract):
            nodes.setdefault(item_id, {"type": "id"})
            edges.append({"from": doc_id, "to": item_id, "kind": "declares_or_references"})
        for upstream in contract.get("upstream") or []:
            if isinstance(upstream, dict) and upstream.get("path"):
                edges.append({"from": doc_id, "to": f"doc:{upstream['path']}", "kind": "upstream"})
        for consumer in contract.get("consumers") or []:
            edges.append({"from": doc_id, "to": f"consumer:{consumer}", "kind": "consumer"})
    return {"schema_version": 1, "nodes": nodes, "edges": edges}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="harness-runtime/harness/state/trace-graph.json")
    parser.add_argument("--query")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    graph = build(root)
    if args.query:
        refs = [edge for edge in graph["edges"] if edge["to"] == args.query or edge["from"] == args.query]
        print(json.dumps({"query": args.query, "edges": refs}, ensure_ascii=False, indent=2))
        return 0
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
