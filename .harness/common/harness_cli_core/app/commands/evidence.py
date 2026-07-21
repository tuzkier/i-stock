from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceCommandHandlers:
    graph_build: Callable[[argparse.Namespace], int]
    graph_check: Callable[[argparse.Namespace], int]
    add: Callable[[argparse.Namespace], int]
    link: Callable[[argparse.Namespace], int]
    command_collect: Callable[[argparse.Namespace], int]
    visual_manifest: Callable[[argparse.Namespace], int]


def register_evidence_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: EvidenceCommandHandlers,
) -> argparse.ArgumentParser:
    evidence = subparsers.add_parser("evidence")
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)

    evidence_graph = evidence_sub.add_parser("graph")
    evidence_graph_sub = evidence_graph.add_subparsers(dest="evidence_graph_command", required=True)
    p = add_leaf(evidence_graph_sub, "build", handlers.graph_build)
    p.add_argument("--mission")
    p.add_argument("--artifact", action="append", required=True)
    p.add_argument("--evidence-store")
    p.add_argument("--output")
    p = add_leaf(evidence_graph_sub, "check", handlers.graph_check)
    p.add_argument("--graph", required=True)
    p.add_argument("--current-git-ref")

    p = add_leaf(evidence_sub, "add", handlers.add)
    p.add_argument("--mission", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--store")

    p = add_leaf(evidence_sub, "link", handlers.link)
    p.add_argument("--mission", required=True)
    p.add_argument("--from", dest="from_id", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--type", default="supported_by")
    p.add_argument("--store")

    evidence_command = evidence_sub.add_parser("command")
    evidence_command_sub = evidence_command.add_subparsers(dest="evidence_command_command", required=True)
    p = add_leaf(evidence_command_sub, "collect", handlers.command_collect)
    p.add_argument("--mission")
    p.add_argument("--cwd")
    p.add_argument("--timeout", type=int)
    p.add_argument("--output-dir")
    p.add_argument("--store")
    p.add_argument("--no-run", action="store_true")

    evidence_visual = evidence_sub.add_parser("visual")
    evidence_visual_sub = evidence_visual.add_subparsers(dest="evidence_visual_command", required=True)
    p = add_leaf(evidence_visual_sub, "manifest", handlers.visual_manifest)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage-dir", required=True)
    p.add_argument("--source-dir", required=True, action="append")
    p.add_argument("--copy", action="store_true")
    p.add_argument("--output")
    return evidence
