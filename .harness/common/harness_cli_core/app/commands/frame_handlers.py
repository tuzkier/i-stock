from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.frame import build_frame_current_payload, build_frame_explain_payload
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_paths import mission_status_path, relpath


COMMON_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = COMMON_ROOT / "skills"
WORK_GRAPH_SCRIPTS = SKILLS_ROOT / "work-graph" / "scripts"


def load_lane_action_registry(root: Path) -> dict[str, dict[str, Any]]:
    if str(WORK_GRAPH_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))
    from work_graph_lib import lane_action_registry

    return lane_action_registry(root)


def run_board_select_no_write(root: Path, mission_id: str) -> dict[str, Any]:
    board_script = SKILLS_ROOT / "board-router" / "scripts" / "select_next_node.py"
    if not board_script.exists():
        return {}
    result = subprocess.run(
        [sys.executable, str(board_script), "--root", str(root), "--mission-id", mission_id, "--no-write", "--json"],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {}
    if result.returncode != 0 and payload:
        payload.setdefault("status", "FAIL")
    return payload


def cmd_frame_current(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    status_path = mission_status_path(root)
    if not status_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "frame.current",
                "mission_status_uninitialized",
                f"mission-status file not found: {relpath(root, status_path)}; run 'harness mission init' to initialize",
            ),
        )
    status = load_yaml(status_path)
    return emit_payload(
        args,
        build_frame_current_payload(
            root,
            status,
            args.mission,
            load_lane_action_registry(root),
            lambda mission_id: run_board_select_no_write(root, mission_id),
        ),
    )


def cmd_frame_explain(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    status = load_yaml(mission_status_path(root))
    return emit_payload(args, build_frame_explain_payload(root, status, args.mission, args.node))
