#!/usr/bin/env python3
"""Rebuild Work Graph board, indexes, and tree views from node facts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from work_graph_lib import finding_dict, load_nodes, resolve_graph_root, status_from_findings, write_views


def run(root: Path) -> dict:
    graph_root = resolve_graph_root(root)
    graph_root.mkdir(parents=True, exist_ok=True)
    nodes, _paths, findings = load_nodes(graph_root)
    write_views(graph_root, nodes)
    status = status_from_findings(findings)
    return {
        "status": status,
        "control": "work_graph_rebuild_index",
        "graph_root": str(graph_root),
        "nodes": sorted(nodes),
        "findings": [finding_dict(item) for item in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run(Path(args.root).resolve())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Work Graph rebuild: {payload['status']}")
        for item in payload["findings"]:
            print(f"[{item['level']}] {item['code']}: {item['message']}")
    return 1 if payload["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
