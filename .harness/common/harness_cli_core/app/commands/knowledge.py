from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeCommandHandlers:
    init: Callable[[argparse.Namespace], int]
    check: Callable[[argparse.Namespace], int]
    index: Callable[[argparse.Namespace], int]
    resolve: Callable[[argparse.Namespace], int]
    promote: Callable[[argparse.Namespace], int]


def register_knowledge_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: KnowledgeCommandHandlers,
) -> argparse.ArgumentParser:
    knowledge = subparsers.add_parser("knowledge")
    knowledge_sub = knowledge.add_subparsers(dest="knowledge_command", required=True)
    p = add_leaf(knowledge_sub, "init", handlers.init)
    p.add_argument("--replace", action="store_true")
    add_leaf(knowledge_sub, "check", handlers.check)
    p = add_leaf(knowledge_sub, "index", handlers.index)
    p.add_argument("--check", action="store_true", help="check whether project-knowledge/_index.md is up to date without writing")
    p = add_leaf(knowledge_sub, "resolve", handlers.resolve)
    p.add_argument("--stage", required=True, help="Harness stage requesting knowledge context")
    p.add_argument("--capability", help="optional capability filter for specs")
    p = add_leaf(knowledge_sub, "promote", handlers.promote)
    p.add_argument("--mission", required=True)
    p.add_argument("--write-plan", action="store_true", help="write knowledge-promotion-plan.md under the mission retrospective artifact directory")
    p.add_argument("--output", help="optional output path for --write-plan")
    p.add_argument("--apply", action="store_true", help="apply deterministic long-lived knowledge promotion for accepted specs and prototype entry")
    p.add_argument("--replace-existing", action="store_true", help="when used with --apply, replace existing deterministic promotion targets")
    return knowledge
