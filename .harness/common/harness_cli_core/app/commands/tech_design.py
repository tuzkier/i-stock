from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class TechDesignCommandHandlers:
    check_dep_impact_trigger: Callable[[argparse.Namespace], int]
    check_capability_trigger: Callable[[argparse.Namespace], int]


def register_tech_design_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: TechDesignCommandHandlers,
) -> argparse.ArgumentParser:
    tech_design = subparsers.add_parser("tech-design")
    tech_design_sub = tech_design.add_subparsers(dest="tech_design_command", required=True)
    p = add_leaf(
        tech_design_sub, "check-dep-impact-trigger", handlers.check_dep_impact_trigger
    )
    p.add_argument("--mission", required=True)
    p = add_leaf(
        tech_design_sub, "check-capability-trigger", handlers.check_capability_trigger
    )
    p.add_argument("--mission", required=True)
    return tech_design
