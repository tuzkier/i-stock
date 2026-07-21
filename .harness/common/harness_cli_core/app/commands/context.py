from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ContextCommandHandlers:
    check: Callable[[argparse.Namespace], int]
    init: Callable[[argparse.Namespace], int]


def register_context_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ContextCommandHandlers,
) -> argparse.ArgumentParser:
    context = subparsers.add_parser("context")
    context_sub = context.add_subparsers(dest="context_command", required=True)
    add_leaf(context_sub, "check", handlers.check)
    p = add_leaf(context_sub, "init", handlers.init)
    p.add_argument("--replace", action="store_true")
    return context
