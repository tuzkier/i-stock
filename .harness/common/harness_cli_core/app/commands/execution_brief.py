from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionBriefCommandHandlers:
    self_check: Callable[[argparse.Namespace], int]
    check_coverage: Callable[[argparse.Namespace], int]
    gate_run: Callable[[argparse.Namespace], int]


def register_execution_brief_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ExecutionBriefCommandHandlers,
) -> argparse.ArgumentParser:
    execution_brief = subparsers.add_parser("execution-brief")
    execution_brief_sub = execution_brief.add_subparsers(dest="execution_brief_command", required=True)

    p = add_leaf(execution_brief_sub, "self-check", handlers.self_check)
    p.add_argument("--mission", required=True)

    p = add_leaf(execution_brief_sub, "check-coverage", handlers.check_coverage)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--spec-mode",
        choices=["strict", "warn"],
        default="strict",
        help="strict: uncovered scenarios FAIL; warn: surface only",
    )

    execution_brief_gate = execution_brief_sub.add_parser("gate")
    execution_brief_gate_sub = execution_brief_gate.add_subparsers(dest="execution_brief_gate_command", required=True)
    p = add_leaf(execution_brief_gate_sub, "run", handlers.gate_run)
    p.add_argument("--mission", required=True)

    return execution_brief
