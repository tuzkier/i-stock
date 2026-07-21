from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryCommandHandlers:
    skip: Callable[[argparse.Namespace], int]
    summary: Callable[[argparse.Namespace], int]
    check_dependency_trigger: Callable[[argparse.Namespace], int]
    agent_eng_eval: Callable[[argparse.Namespace], int]


def register_discovery_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: DiscoveryCommandHandlers,
) -> argparse.ArgumentParser:
    discovery = subparsers.add_parser("discovery")
    discovery_sub = discovery.add_subparsers(dest="discovery_command", required=True)
    p = add_leaf(discovery_sub, "skip", handlers.skip)
    p.add_argument("--mission", required=True)
    p.add_argument("--reason", required=True, help="Explanation for skipping discovery.")
    p = add_leaf(discovery_sub, "summary", handlers.summary)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--format",
        choices=["user", "json"],
        default="user",
        help="Human-readable text or pure structured payload.",
    )
    p = add_leaf(discovery_sub, "check-dependency-trigger", handlers.check_dependency_trigger)
    p.add_argument("--mission", required=True)
    p = add_leaf(discovery_sub, "agent-eng-eval", handlers.agent_eng_eval)
    p.add_argument("--mission", required=True)
    p.add_argument("--component", required=True, help="Agent component being evaluated.")
    p.add_argument("--autonomy", action="store_true", help="autonomy boolean (true if set).")
    p.add_argument(
        "--runtime-context",
        dest="runtime_context",
        action="store_true",
        help="runtime_context boolean.",
    )
    p.add_argument(
        "--multi-step",
        dest="multi_step",
        action="store_true",
        help="multi_step_reasoning boolean.",
    )
    p.add_argument("--uncertainty", action="store_true", help="uncertainty boolean.")
    p.add_argument(
        "--recommendation",
        choices=["agentize", "deterministic", "undecided"],
        help="Override the 4-of-4 rule; agentize without all four flags true is rejected.",
    )
    p.add_argument("--notes", help="Optional rationale text appended to the candidate record.")
    return discovery


@dataclass(frozen=True)
class GraphifyCommandHandlers:
    status: Callable[[argparse.Namespace], int]


def register_graphify_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: GraphifyCommandHandlers,
) -> argparse.ArgumentParser:
    graphify = subparsers.add_parser("graphify")
    graphify_sub = graphify.add_subparsers(dest="graphify_command", required=True)
    add_leaf(graphify_sub, "status", handlers.status)
    return graphify
