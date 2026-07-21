from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SpecCommandHandlers:
    check: Callable[[argparse.Namespace], int]
    init: Callable[[argparse.Namespace], int]
    delta_lint: Callable[[argparse.Namespace], int]
    scan: Callable[[argparse.Namespace], int]
    diff_list: Callable[[argparse.Namespace], int]


def register_spec_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: SpecCommandHandlers,
) -> argparse.ArgumentParser:
    spec = subparsers.add_parser("spec")
    spec_sub = spec.add_subparsers(dest="spec_command", required=True)
    p = add_leaf(spec_sub, "check", handlers.check)
    p.add_argument("--capability", help="check that a specific capability spec exists")
    p = add_leaf(spec_sub, "init", handlers.init)
    p.add_argument("--capability", help="scaffold a specific capability spec under project-knowledge/specs; without this flag, initialize the specs index")
    p.add_argument("--replace", action="store_true")
    p = add_leaf(spec_sub, "delta-lint", handlers.delta_lint)
    p.add_argument("--mission", required=True)
    p.add_argument("--capability", dest="capability", required=True, help="Capability name to validate.")
    p = add_leaf(spec_sub, "scan", handlers.scan)
    p.add_argument("--mission", required=True)
    p.add_argument("--from-prd", dest="from_prd", help="Path to product definition; defaults to artifacts/<mission>/product/product-definition.md with legacy stage fallback")
    p.add_argument("--scope-in", dest="scope_in", action="append", help="(discovery flavor) Mission scope_in path; repeat for multiple paths. Activates capability enumeration from project-knowledge/specs/.")
    spec_diff = spec_sub.add_parser("diff")
    spec_diff_sub = spec_diff.add_subparsers(dest="spec_diff_command", required=True)
    p = add_leaf(spec_diff_sub, "list", handlers.diff_list)
    p.add_argument("--mission", required=True)
    return spec
