from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class BoardCommandHandlers:
    select: Callable[[argparse.Namespace], int]


def register_board_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: BoardCommandHandlers,
) -> argparse.ArgumentParser:
    board = subparsers.add_parser("board")
    board_sub = board.add_subparsers(dest="board_command", required=True)
    p = add_leaf(board_sub, "select", handlers.select)
    p.add_argument("--mission", required=True)
    p.add_argument("--query", action="append")
    p.add_argument("--primary-node", action="append")
    p.add_argument("--related-node", action="append")
    p.add_argument("--spec", action="append")
    p.add_argument("--write-slice", action="store_true")
    p.add_argument("--no-write", action="store_true")
    return board
