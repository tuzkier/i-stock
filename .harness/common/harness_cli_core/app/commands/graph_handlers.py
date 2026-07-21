from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import yaml

from harness_cli_core.app.parser import root_arg, with_json
from harness_cli_core.infra.process import run_python
from harness_cli_core.infra.runtime_paths import work_graph_root


COMMON_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = COMMON_ROOT / "skills"


def script(*parts: str) -> Path:
    return SKILLS_ROOT.joinpath(*parts)


def cmd_graph_apply(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--operation", args.operation]
    if args.dry_run:
        forwarded.append("--dry-run")
    if args.staged:
        forwarded.append("--staged")
    return run_python(script("work-graph", "scripts", "apply_graph_operation.py"), with_json(args, forwarded))


def cmd_graph_plan(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--operation", args.operation, "--dry-run"]
    return run_python(script("work-graph", "scripts", "apply_graph_operation.py"), with_json(args, forwarded))


def cmd_graph_rebuild(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    return run_python(script("work-graph", "scripts", "rebuild_index.py"), with_json(args, forwarded))


def cmd_graph_check(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    return run_python(script("work-graph", "scripts", "check_graph_consistency.py"), with_json(args, forwarded))


def cmd_graph_node_show(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    graph_root = work_graph_root(root)
    matches = sorted((graph_root / "nodes").glob(f"**/{args.node_id}.yaml"))
    if not matches:
        payload = {
            "status": "FAIL",
            "control": "graph.node.show",
            "node_id": args.node_id,
            "findings": [{"level": "FAIL", "code": "node_not_found", "message": args.node_id}],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"node not found: {args.node_id}", file=sys.stderr)
        return 1
    text = matches[0].read_text(encoding="utf-8")
    if args.json:
        payload = {"status": "PASS", "control": "graph.node.show", "node_id": args.node_id, "path": str(matches[0]), "yaml": text}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(text, end="" if text.endswith("\n") else "\n")
    return 0


def cmd_graph_node_create(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    operation_id = args.operation_id or f"create-{args.node_id}"
    payload = {
        "operation_id": operation_id,
        "type": "create_node",
        "mission_id": args.mission_id or "",
        "target": {
            "id": args.node_id,
            "kind": args.kind,
            "title": args.title,
            "lane": args.lane,
            "status": args.status,
        },
    }
    if args.stage:
        payload["target"]["stage"] = args.stage
    if args.input_node:
        payload["target"]["inputs"] = list(args.input_node)
    if args.output_node:
        payload["target"]["outputs"] = list(args.output_node)
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(payload, tmp, sort_keys=False, allow_unicode=True)
        manifest_path = tmp.name
    try:
        forwarded = ["--root", str(root), "--operation", manifest_path]
        return run_python(script("work-graph", "scripts", "apply_graph_operation.py"), with_json(args, forwarded))
    finally:
        try:
            os.unlink(manifest_path)
        except OSError:
            pass
