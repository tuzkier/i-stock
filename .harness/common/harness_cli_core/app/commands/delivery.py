from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryCommandHandlers:
    summarize: Callable[[argparse.Namespace], int]
    compute_follow_ups: Callable[[argparse.Namespace], int]
    check_followups: Callable[[argparse.Namespace], int]
    compute_conclusion: Callable[[argparse.Namespace], int]
    handoff: Callable[[argparse.Namespace], int]
    agent_capability_status: Callable[[argparse.Namespace], int]


def register_delivery_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: DeliveryCommandHandlers,
) -> argparse.ArgumentParser:
    delivery_cli = subparsers.add_parser("delivery")
    delivery_sub = delivery_cli.add_subparsers(dest="delivery_command", required=True)

    p = add_leaf(delivery_sub, "summarize", handlers.summarize)
    p.add_argument("--mission", required=True)

    p = add_leaf(delivery_sub, "compute-follow-ups", handlers.compute_follow_ups)
    p.add_argument("--mission", required=True)

    p = add_leaf(delivery_sub, "check-followups", handlers.check_followups)
    p.add_argument("--mission", required=True)

    p = add_leaf(delivery_sub, "compute-conclusion", handlers.compute_conclusion)
    p.add_argument("--mission", required=True)

    p = add_leaf(delivery_sub, "handoff", handlers.handoff)
    p.add_argument("--mission", required=True)
    p.add_argument("--approval-id", dest="approval_id", help="User acceptance approval id")

    p = add_leaf(delivery_sub, "agent-capability-status", handlers.agent_capability_status)
    p.add_argument("--mission", required=True)
    return delivery_cli
