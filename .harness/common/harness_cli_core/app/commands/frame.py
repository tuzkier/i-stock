from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class FrameCommandHandlers:
    current: Callable[[argparse.Namespace], int]
    explain: Callable[[argparse.Namespace], int]


def register_frame_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: FrameCommandHandlers,
) -> argparse.ArgumentParser:
    frame = subparsers.add_parser("frame")
    frame_sub = frame.add_subparsers(dest="frame_command", required=True)
    p = add_leaf(frame_sub, "current", handlers.current)
    p.add_argument("--mission")
    p = add_leaf(frame_sub, "explain", handlers.explain)
    p.add_argument("--mission", required=True)
    p.add_argument("--node")
    return frame
