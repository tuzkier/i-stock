from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.parser import root_arg, with_json
from harness_cli_core.infra.process import run_python


COMMON_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = COMMON_ROOT / "skills"


def script(*parts: str) -> Path:
    return SKILLS_ROOT.joinpath(*parts)


def cmd_board_select(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args), "--mission-id", args.mission]
    for attr, flag in (("query", "--query"), ("primary_node", "--primary-node"), ("related_node", "--related-node"), ("spec", "--spec")):
        for value in getattr(args, attr) or []:
            forwarded.extend([flag, value])
    if not args.write_slice or args.no_write:
        forwarded.append("--no-write")
    return run_python(script("board-router", "scripts", "select_next_node.py"), with_json(args, forwarded))
