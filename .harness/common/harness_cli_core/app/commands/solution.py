from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SolutionCommandHandlers:
    decision_scan: Callable[[argparse.Namespace], int]
    lane_action_validate: Callable[[argparse.Namespace], int]


def register_solution_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: SolutionCommandHandlers,
) -> argparse.ArgumentParser:
    solution = subparsers.add_parser("solution")
    solution_sub = solution.add_subparsers(dest="solution_command", required=True)
    p = add_leaf(solution_sub, "decision-scan", handlers.decision_scan)
    p.add_argument("--artifact", required=True, help="Path to solution.md to scan.")
    p = add_leaf(solution_sub, "lane-action-validate", handlers.lane_action_validate)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--stage",
        choices=["solution", "interaction", "technical_analysis"],
        help="Active stage override (default: read from mission-slice.yaml).",
    )
    return solution
