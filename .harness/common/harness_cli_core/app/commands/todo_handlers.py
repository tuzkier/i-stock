from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.trace import derive_todos_from_trace, summarize_todos, trace_log_path
from harness_cli_core.infra.runtime_paths import relpath


def cmd_todo_report(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission_id = args.mission
    path = trace_log_path(root, mission_id)
    todos, warnings = derive_todos_from_trace(path)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "todo.report",
            "mission_id": mission_id,
            "trace_path": relpath(root, path),
            "todos": todos,
            "summary": summarize_todos(todos),
            "warnings": warnings,
            "findings": [],
        },
    )


def cmd_todo_sync(args: argparse.Namespace) -> int:
    return cmd_todo_report(args)
