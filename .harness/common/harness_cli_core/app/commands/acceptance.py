from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass

from harness_cli_core.app.commands.acceptance_handlers import (
    ACCEPTANCE_DECISION_CLOSED_SET,
)


@dataclass(frozen=True)
class AcceptanceCommandHandlers:
    record: Callable[[argparse.Namespace], int]


def register_acceptance_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: AcceptanceCommandHandlers,
) -> argparse.ArgumentParser:
    acceptance_cli = subparsers.add_parser(
        "acceptance",
        description="TheForce acceptance lifecycle CLI shims (D-05, INV-10, SCN-ACCEPTANCE-EVIDENCE).",
    )
    acceptance_sub = acceptance_cli.add_subparsers(dest="acceptance_command", required=True)
    p = add_leaf(
        acceptance_sub,
        "record",
        handlers.record,
        description=(
            "Record an acceptance_decision typed action intent (accept / request_changes). "
            "INV-10: accept without --evidence-ref blocks with exit=7; use the Decision Gate "
            "path for accept_with_risk."
        ),
    )
    p.add_argument("--workspace", required=True, help="Absolute path to the target workspace root")
    p.add_argument("--mission", required=True, help="Mission id receiving the decision")
    p.add_argument(
        "--decision",
        required=True,
        choices=list(ACCEPTANCE_DECISION_CLOSED_SET),
        help="Decision; one of: " + " / ".join(ACCEPTANCE_DECISION_CLOSED_SET),
    )
    p.add_argument(
        "--evidence-ref",
        action="append",
        help="Evidence reference id (repeat for multiple). Required for accept.",
    )
    return acceptance_cli
