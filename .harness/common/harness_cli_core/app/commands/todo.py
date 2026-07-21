from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class TodoCommandHandlers:
    report: Callable[[argparse.Namespace], int]
    sync: Callable[[argparse.Namespace], int]


def register_todo_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: TodoCommandHandlers,
) -> argparse.ArgumentParser:
    todo = subparsers.add_parser("todo")
    todo_sub = todo.add_subparsers(dest="todo_command", required=True)

    p = add_leaf(todo_sub, "report", handlers.report)
    p.add_argument("--mission", required=True)

    p = add_leaf(todo_sub, "sync", handlers.sync)
    p.add_argument("--mission", required=True)

    return todo
