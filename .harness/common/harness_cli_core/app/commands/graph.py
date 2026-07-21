from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class GraphCommandHandlers:
    apply: Callable[[argparse.Namespace], int]
    plan: Callable[[argparse.Namespace], int]
    rebuild: Callable[[argparse.Namespace], int]
    check: Callable[[argparse.Namespace], int]
    node_show: Callable[[argparse.Namespace], int]
    node_create: Callable[[argparse.Namespace], int]


def register_graph_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: GraphCommandHandlers,
) -> argparse.ArgumentParser:
    graph = subparsers.add_parser("graph")
    graph_sub = graph.add_subparsers(dest="graph_command", required=True)
    p = add_leaf(graph_sub, "apply", handlers.apply)
    p.add_argument("--operation", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--staged", action="store_true")
    p = add_leaf(graph_sub, "plan", handlers.plan)
    p.add_argument("--operation", required=True)
    add_leaf(graph_sub, "rebuild", handlers.rebuild)
    add_leaf(graph_sub, "check", handlers.check)

    graph_node = graph_sub.add_parser("node")
    graph_node_sub = graph_node.add_subparsers(dest="node_command", required=True)
    p = add_leaf(graph_node_sub, "show", handlers.node_show)
    p.add_argument("node_id")
    p = add_leaf(graph_node_sub, "create", handlers.node_create)
    p.add_argument("--node-id", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--lane", required=True)
    p.add_argument("--stage")
    p.add_argument("--status", required=True)
    p.add_argument("--mission-id")
    p.add_argument("--operation-id")
    p.add_argument("--input-node", action="append")
    p.add_argument("--output-node", action="append")

    return graph
