from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class GateCommandHandlers:
    run: Callable[[argparse.Namespace], int]
    advance: Callable[[argparse.Namespace], int]
    transition: Callable[[argparse.Namespace], int]
    report_render: Callable[[argparse.Namespace], int]
    control_reports: Callable[[argparse.Namespace], int]


def register_gate_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: GateCommandHandlers,
) -> argparse.ArgumentParser:
    gate = subparsers.add_parser("gate")
    gate_sub = gate.add_subparsers(dest="gate_command", required=True)
    p = add_leaf(gate_sub, "run", handlers.run)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--lane-action")
    p.add_argument("--from-lane")
    p.add_argument("--to-lane")
    p.add_argument("--to-stage")
    p.add_argument("--primary-node", action="append")
    p.add_argument("--related-node", action="append")
    p.add_argument("--artifact")
    p.add_argument("--contract-artifact")
    p.add_argument("--contract-check-json")
    p.add_argument("--mission-slice")
    p.add_argument("--control-report", action="append")
    p.add_argument("--required-control", action="append")
    p.add_argument("--required-checkpoint", action="append")
    p.add_argument("--human-checkpoint", action="append")
    p.add_argument("--upstream", action="append")
    p.add_argument("--allow-placeholders", action="store_true")
    p.add_argument(
        "--ai-interpretation",
        help=(
            "One-paragraph AI explanation of why this gate decision is justified. "
            "Required unless --no-interpretation is given with a reason."
        ),
    )
    p.add_argument(
        "--no-interpretation",
        metavar="REASON",
        help=(
            "Explicit reason for omitting --ai-interpretation "
            "(e.g. 'automated rerun, no decision change'). Recorded in the gate report."
        ),
    )
    p.add_argument("--output-dir")

    p = add_leaf(gate_sub, "advance", handlers.advance)
    p.add_argument("--mission", required=True)
    p.add_argument("--gate-report", required=True)
    p.add_argument("--contract-artifact")
    p.add_argument("--allow-warnings", action="store_true")

    p = add_leaf(gate_sub, "transition", handlers.transition)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--to-stage")
    p.add_argument("--mission-slice", required=True)
    p.add_argument("--contract-artifact")
    p.add_argument("--primary-node", action="append")
    p.add_argument("--related-node", action="append")
    p.add_argument("--ai-interpretation", required=True)
    p.add_argument("--allow-warnings", action="store_true")

    gate_report = gate_sub.add_parser("report")
    gate_report_sub = gate_report.add_subparsers(dest="gate_report_command", required=True)
    p = add_leaf(gate_report_sub, "render", handlers.report_render)
    p.add_argument("--contract-check-json", required=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--from-stage", required=True)
    p.add_argument("--to-stage", required=True)
    p.add_argument("--mission-slice")
    p.add_argument("--control-report", action="append")
    p.add_argument("--required-control", action="append")
    p.add_argument("--required-checkpoint", action="append")
    p.add_argument("--human-checkpoint", action="append")
    p.add_argument(
        "--ai-interpretation",
        help=(
            "One-paragraph AI explanation of why this gate decision is justified. "
            "Required unless --no-interpretation is given."
        ),
    )
    p.add_argument(
        "--no-interpretation",
        metavar="REASON",
        help="Explicit reason for omitting --ai-interpretation (recorded in the gate report).",
    )
    p.add_argument("--output-dir")

    p = add_leaf(gate_sub, "control-reports", handlers.control_reports)
    p.add_argument("--mission")
    p.add_argument("--report", action="append")
    p.add_argument("--required-control", action="append")
    return gate
