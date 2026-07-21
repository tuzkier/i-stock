from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewCommandHandlers:
    check_ready: Callable[[argparse.Namespace], int]
    select_reviewers: Callable[[argparse.Namespace], int]
    snapshot_diff: Callable[[argparse.Namespace], int]
    toolchain_status: Callable[[argparse.Namespace], int]
    e2e_status: Callable[[argparse.Namespace], int]


def register_review_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ReviewCommandHandlers,
) -> argparse.ArgumentParser:
    review_cli = subparsers.add_parser("review")
    review_sub = review_cli.add_subparsers(dest="review_command", required=True)
    p = add_leaf(review_sub, "check-ready", handlers.check_ready)
    p.add_argument("--mission", required=True)
    p = add_leaf(review_sub, "select-reviewers", handlers.select_reviewers)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--diff-summary",
        dest="diff_summary",
        help="Path to JSON file listing changed feature keywords.",
    )
    p = add_leaf(review_sub, "snapshot-diff", handlers.snapshot_diff)
    p.add_argument("--mission", required=True)
    p.add_argument("--base", default="HEAD~1", help="Git ref to diff against (default: HEAD~1)")
    p = add_leaf(review_sub, "toolchain-status", handlers.toolchain_status)
    p.add_argument("--mission", required=True)
    p = add_leaf(review_sub, "e2e-status", handlers.e2e_status)
    p.add_argument("--mission", required=True)
    return review_cli
