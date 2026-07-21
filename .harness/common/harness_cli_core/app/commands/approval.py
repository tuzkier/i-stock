from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovalCommandHandlers:
    append: Callable[[argparse.Namespace], int]
    latest: Callable[[argparse.Namespace], int]
    require: Callable[[argparse.Namespace], int]


def register_approval_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ApprovalCommandHandlers,
) -> argparse.ArgumentParser:
    approval = subparsers.add_parser("approval")
    approval_sub = approval.add_subparsers(dest="approval_command", required=True)

    p = add_leaf(approval_sub, "append", handlers.append)
    p.add_argument("--mission", required=True)
    p.add_argument("--type", required=True, choices=["checkpoint", "boundary", "risk", "tradeoff"])
    p.add_argument("--stage")
    p.add_argument("--checkpoint")
    p.add_argument("--status", required=True, choices=["approved", "rejected", "modified"])
    p.add_argument("--comment")
    p.add_argument("--approval-id")
    p.add_argument("--decided-at")

    p = add_leaf(approval_sub, "latest", handlers.latest)
    p.add_argument("--mission")
    p.add_argument("--type", choices=["checkpoint", "boundary", "risk", "tradeoff"])
    p.add_argument("--stage")
    p.add_argument("--status", choices=["approved", "rejected", "modified"])

    p = add_leaf(approval_sub, "require", handlers.require)
    p.add_argument("--mission", required=True)
    p.add_argument("--type", required=True, choices=["checkpoint", "boundary", "risk", "tradeoff"])
    p.add_argument("--stage")
    p.add_argument("--checkpoint")

    return approval
