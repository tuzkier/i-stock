from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.commands.graph_handlers import cmd_graph_check
from harness_cli_core.app.parser import root_arg, with_json
from harness_cli_core.infra.process import run_python


COMMON_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = COMMON_ROOT / "skills"


def script(*parts: str) -> Path:
    return SKILLS_ROOT.joinpath(*parts)


def cmd_lint_runtime(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    return run_python(script("harness-lint", "scripts", "check_runtime_consistency.py"), with_json(args, forwarded))


def cmd_lint_graph(args: argparse.Namespace) -> int:
    return cmd_graph_check(args)


def cmd_lint_project(args: argparse.Namespace) -> int:
    forwarded = ["--root", root_arg(args)]
    for attr, flag in (
        ("config", "--config"),
        ("profile", "--profile"),
        ("mission", "--mission-id"),
        ("changed_files_file", "--changed-files-file"),
        ("command_evidence", "--command-evidence"),
        ("trace", "--trace"),
        ("output_dir", "--output-dir"),
    ):
        value = getattr(args, attr, None)
        if value:
            forwarded.extend([flag, value])
    for value in args.changed_file or []:
        forwarded.extend(["--changed-file", value])
    if args.no_git_diff:
        forwarded.append("--no-git-diff")
    return run_python(script("project-lint", "scripts", "run_project_lint.py"), with_json(args, forwarded))
