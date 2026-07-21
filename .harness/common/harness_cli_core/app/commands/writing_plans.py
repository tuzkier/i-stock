from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class WritingPlansCommandHandlers:
    run: Callable[[argparse.Namespace], int]


def register_writing_plans_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: WritingPlansCommandHandlers,
) -> argparse.ArgumentParser:
    writing_plans = subparsers.add_parser("writing-plans")
    writing_plans_sub = writing_plans.add_subparsers(dest="writing_plans_command", required=True)

    p = add_leaf(writing_plans_sub, "run", handlers.run)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--mode",
        required=True,
        help="must be `internal-carrier`; other values are rejected (breakdown M2.1 boundary)",
    )

    return writing_plans
