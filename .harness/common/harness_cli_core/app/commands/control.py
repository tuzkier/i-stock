from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ControlCommandHandlers:
    status: Callable[[argparse.Namespace], int]
    candidates: Callable[[argparse.Namespace], int]
    frame: Callable[[argparse.Namespace], int]
    guidance: Callable[[argparse.Namespace], int]
    context_index: Callable[[argparse.Namespace], int]


def register_control_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ControlCommandHandlers,
) -> argparse.ArgumentParser:
    control = subparsers.add_parser("control")
    control_sub = control.add_subparsers(dest="control_command", required=True)

    p = add_leaf(control_sub, "status", handlers.status, help="emit read-only control-plane status snapshot")
    p.set_defaults(json=True)
    p.add_argument("--mission")
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")

    p = add_leaf(control_sub, "candidates", handlers.candidates, help="emit non-decision control-plane candidates")
    p.set_defaults(json=True)
    p.add_argument("--intent", required=True, choices=["continue"])
    p.add_argument("--mission")
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")

    p = add_leaf(control_sub, "frame", handlers.frame, help="emit selected Mission frame facts")
    p.set_defaults(json=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")

    p = add_leaf(control_sub, "guidance", handlers.guidance, help="emit bounded stage guidance facts")
    p.set_defaults(json=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")

    p = add_leaf(control_sub, "context-index", handlers.context_index, help="emit path-only required context index")
    p.set_defaults(json=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--runtime-root", help="explicit runtime root, usually harness-runtime/harness")

    return control
