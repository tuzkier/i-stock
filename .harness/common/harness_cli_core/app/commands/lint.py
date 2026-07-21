from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class LintCommandHandlers:
    runtime: Callable[[argparse.Namespace], int]
    graph: Callable[[argparse.Namespace], int]
    project: Callable[[argparse.Namespace], int]


def register_lint_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: LintCommandHandlers,
) -> argparse.ArgumentParser:
    lint = subparsers.add_parser("lint")
    lint_sub = lint.add_subparsers(dest="lint_command", required=True)
    add_leaf(lint_sub, "runtime", handlers.runtime)
    add_leaf(lint_sub, "graph", handlers.graph)
    p = add_leaf(lint_sub, "project", handlers.project)
    p.add_argument("--config")
    p.add_argument("--profile")
    p.add_argument("--mission")
    p.add_argument("--changed-file", action="append")
    p.add_argument("--changed-files-file")
    p.add_argument("--command-evidence")
    p.add_argument("--trace")
    p.add_argument("--output-dir")
    p.add_argument("--no-git-diff", action="store_true")
    return lint
