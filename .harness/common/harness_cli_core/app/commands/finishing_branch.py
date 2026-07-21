from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class FinishingBranchCommandHandlers:
    status: Callable[[argparse.Namespace], int]
    detect_test_cmd: Callable[[argparse.Namespace], int]
    run_tests: Callable[[argparse.Namespace], int]
    readiness: Callable[[argparse.Namespace], int]
    options: Callable[[argparse.Namespace], int]
    pr_body: Callable[[argparse.Namespace], int]
    execute: Callable[[argparse.Namespace], int]
    cleanup: Callable[[argparse.Namespace], int]


def register_finishing_branch_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: FinishingBranchCommandHandlers,
) -> argparse.ArgumentParser:
    finishing_branch = subparsers.add_parser("finishing-branch")
    fb_sub = finishing_branch.add_subparsers(dest="finishing_branch_command", required=True)

    p = add_leaf(fb_sub, "status", handlers.status)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "detect-test-cmd", handlers.detect_test_cmd)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "run-tests", handlers.run_tests)
    p.add_argument("--mission", required=True)
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument("--test-cmd", dest="test_cmd", help="Override test command.")
    p.add_argument(
        "--reuse-evidence-id",
        dest="reuse_evidence_id",
        help="Reuse a named evidence id from verification-report contract.",
    )

    p = add_leaf(fb_sub, "readiness", handlers.readiness)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "options", handlers.options)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "pr-body", handlers.pr_body)
    p.add_argument("--mission", required=True)

    p = add_leaf(fb_sub, "execute", handlers.execute)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--strategy",
        required=True,
        choices=["merge_to_base", "push_pr", "keep", "discard"],
    )
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    p.add_argument(
        "--confirmation-id",
        dest="confirmation_id",
        help="Required for strategy=discard; must be 'discard'.",
    )

    p = add_leaf(fb_sub, "cleanup", handlers.cleanup)
    p.add_argument("--mission", required=True)
    p.add_argument("--dry-run", action="store_true", dest="dry_run")
    return finishing_branch
