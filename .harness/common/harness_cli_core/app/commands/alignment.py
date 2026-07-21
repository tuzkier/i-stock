from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class AlignmentCommandHandlers:
    check: Callable[[argparse.Namespace], int]


def register_alignment_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: AlignmentCommandHandlers,
) -> argparse.ArgumentParser:
    alignment = subparsers.add_parser("alignment")
    alignment_sub = alignment.add_subparsers(dest="alignment_command", required=True)
    p = add_leaf(alignment_sub, "check", handlers.check)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--stage",
        required=True,
        choices=["interaction", "solution", "technical_analysis", "breakdown", "verify"],
    )
    p.add_argument(
        "--compat",
        action="store_true",
        help="downgrade strict new-gate failures to WARN for historical accepted artifacts",
    )
    return alignment
