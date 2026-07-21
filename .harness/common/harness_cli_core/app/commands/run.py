from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class RunCommandHandlers:
    cancel: Callable[[argparse.Namespace], int]
    retry: Callable[[argparse.Namespace], int]


def register_run_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: RunCommandHandlers,
) -> argparse.ArgumentParser:
    run_cli = subparsers.add_parser(
        "run",
        description="TheForce AgentRun lifecycle CLI shims: cancel / retry (D-04, INV-09, SCN-RUN-CANCEL-DEGRADE).",
    )
    run_sub = run_cli.add_subparsers(dest="run_command", required=True)
    p = add_leaf(
        run_sub,
        "cancel",
        handlers.cancel,
        description=(
            "Record a cancel_run typed action intent. When THEFORCE_ADAPTER_CANCEL_SUPPORT=none, "
            "degrades to cancellation_requested with capability_downgrade=true (still exit 0)."
        ),
    )
    p.add_argument("--workspace", required=True, help="Absolute path to the target workspace root")
    p.add_argument("--run", required=True, help="run_id of the AgentRun to cancel")
    p = add_leaf(
        run_sub,
        "retry",
        handlers.retry,
        description=(
            "Record a retry_run typed action intent. Always allocates a new run_id and links "
            "back via retry_of; honors INV-09 (old AgentRun is never overwritten)."
        ),
    )
    p.add_argument("--workspace", required=True, help="Absolute path to the target workspace root")
    p.add_argument("--run", required=True, help="run_id of the AgentRun to retry")
    return run_cli
