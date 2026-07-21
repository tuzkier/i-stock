from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


_COMPAT_HELP = (
    "downgrade strict new-gate failures to WARN for historical accepted artifacts"
)


@dataclass(frozen=True)
class PrototypeAsFrontendCommandHandlers:
    changeset_check: Callable[[argparse.Namespace], int]
    path_check: Callable[[argparse.Namespace], int]
    drift_check: Callable[[argparse.Namespace], int]
    gate_run: Callable[[argparse.Namespace], int]


def register_prototype_as_frontend_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: PrototypeAsFrontendCommandHandlers,
) -> argparse.ArgumentParser:
    prototype_frontend = subparsers.add_parser("prototype-as-frontend")
    prototype_frontend_sub = prototype_frontend.add_subparsers(
        dest="prototype_as_frontend_command", required=True
    )
    for name, handler in (
        ("changeset-check", handlers.changeset_check),
        ("path-check", handlers.path_check),
        ("drift-check", handlers.drift_check),
    ):
        p = add_leaf(prototype_frontend_sub, name, handler)
        p.add_argument("--mission", required=True)
        p.add_argument("--compat", action="store_true", help=_COMPAT_HELP)

    prototype_frontend_gate = prototype_frontend_sub.add_parser("gate")
    prototype_frontend_gate_sub = prototype_frontend_gate.add_subparsers(
        dest="prototype_as_frontend_gate_command", required=True
    )
    p = add_leaf(prototype_frontend_gate_sub, "run", handlers.gate_run)
    p.add_argument("--mission", required=True)
    p.add_argument("--compat", action="store_true", help=_COMPAT_HELP)
    return prototype_frontend
