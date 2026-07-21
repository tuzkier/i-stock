from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecuteCommandHandlers:
    apply_overlay: Callable[[argparse.Namespace], int]
    revoke_overlay: Callable[[argparse.Namespace], int]
    check_ready: Callable[[argparse.Namespace], int]
    gate_run: Callable[[argparse.Namespace], int]
    stop_event_record: Callable[[argparse.Namespace], int]


def register_execute_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ExecuteCommandHandlers,
) -> argparse.ArgumentParser:
    execute_cli = subparsers.add_parser("execute")
    execute_sub = execute_cli.add_subparsers(dest="execute_command", required=True)

    p = add_leaf(execute_sub, "apply-overlay", handlers.apply_overlay)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--task",
        help="Filter to a single Atomic Task id (SDD per-task mode); omit for mission-level snapshot",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Return the overlay payload without writing the state file",
    )

    p = add_leaf(execute_sub, "revoke-overlay", handlers.revoke_overlay)
    p.add_argument("--mission", required=True)

    p = add_leaf(execute_sub, "check-ready", handlers.check_ready)
    p.add_argument("--mission", required=True)

    execute_gate = execute_sub.add_parser("gate")
    execute_gate_sub = execute_gate.add_subparsers(dest="execute_gate_command", required=True)
    p = add_leaf(execute_gate_sub, "run", handlers.gate_run)
    p.add_argument("--mission", required=True)

    stop_event = execute_sub.add_parser("stop-event")
    stop_event_sub = stop_event.add_subparsers(dest="stop_event_command", required=True)
    p = add_leaf(stop_event_sub, "record", handlers.stop_event_record)
    p.add_argument("--mission", required=True)
    p.add_argument("--kind", required=True, help="Stop event kind (matches protocol §stop_event.kind enum)")
    p.add_argument("--task", help="Atomic Task id triggering the stop event")
    p.add_argument(
        "--path",
        action="append",
        help="Affected path (repeat for multiple); typed array per protocol §stop_event.affected_paths",
    )
    p.add_argument(
        "--hook-source",
        help="Hook script name that triggered the event; defaults to `manual` when invoked from workflow",
    )

    return execute_cli
