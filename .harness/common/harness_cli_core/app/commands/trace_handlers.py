from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.trace import (
    append_trace_record,
    build_round_record,
    build_step_record,
    init_trace_log,
    trace_report,
    trace_log_path,
)
from harness_cli_core.infra.runtime_paths import relpath
from harness_cli_core.infra.time import now_iso


def _uninitialized_trace_payload(root: Path, path: Path, control: str) -> dict:
    return fail_payload(
        control,
        "TRACE_LOG_UNINITIALIZED",
        f"trace log not found: {relpath(root, path)}; run 'harness trace log-init' first",
    )


def cmd_trace_log_init(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission_id = args.mission
    path, is_new = init_trace_log(root, mission_id, stage=getattr(args, "stage", None), timestamp=now_iso())
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "trace.log-init",
            "mission_id": mission_id,
            "trace_path": relpath(root, path),
            "created": is_new,
            "findings": [],
        },
    )


def cmd_trace_report(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission_id = args.mission
    payload = trace_report(root, mission_id, stage=getattr(args, "stage", None))
    payload.update(
        {
            "status": "PASS" if "trace_log_missing" not in payload.get("warnings", []) else "WARN",
            "control": "trace.report",
            "mission_id": mission_id,
            "trace_path": relpath(root, Path(str(payload["trace_path"]))),
            "findings": [
                {"level": "WARN", "code": warning, "message": warning}
                for warning in payload.get("warnings", [])
            ],
        }
    )
    return emit_payload(args, payload)


def _trace_step_event(args: argparse.Namespace, event: str, *, require_status: bool) -> int:
    root = Path(root_arg(args))
    mission_id = args.mission
    path = trace_log_path(root, mission_id)
    control = f"trace.step-{event}"
    if not path.exists():
        return emit_payload(args, _uninitialized_trace_payload(root, path, control))

    record = build_step_record(
        mission_id=mission_id,
        step=args.step,
        event=event,
        timestamp=now_iso(),
        phase=getattr(args, "phase", None),
        rounds=getattr(args, "rounds", None),
        note=getattr(args, "note", None),
        status=args.status if require_status else None,
    )
    append_trace_record(path, record)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": control,
            "mission_id": mission_id,
            "step": args.step,
            "trace_path": relpath(root, path),
            "record": record,
            "findings": [],
        },
    )


def cmd_trace_step_enter(args: argparse.Namespace) -> int:
    return _trace_step_event(args, "enter", require_status=False)


def cmd_trace_step_exit(args: argparse.Namespace) -> int:
    return _trace_step_event(args, "exit", require_status=True)


def _trace_round_event(args: argparse.Namespace, event: str) -> int:
    root = Path(root_arg(args))
    mission_id = args.mission
    path = trace_log_path(root, mission_id)
    control = f"trace.round-{event}"
    if not path.exists():
        return emit_payload(args, _uninitialized_trace_payload(root, path, control))

    record = build_round_record(
        mission_id=mission_id,
        round_number=getattr(args, "round", None),
        event=event,
        timestamp=now_iso(),
        status=getattr(args, "status", None),
        note=getattr(args, "note", None),
    )
    append_trace_record(path, record)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": control,
            "mission": mission_id,
            "round": record["round"],
            "trace_path": relpath(root, path),
            "record": record,
            "findings": [],
        },
    )


def cmd_trace_round_enter(args: argparse.Namespace) -> int:
    return _trace_round_event(args, "enter")


def cmd_trace_round_exit(args: argparse.Namespace) -> int:
    return _trace_round_event(args, "exit")
