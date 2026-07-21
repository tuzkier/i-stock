"""Parser registration for the four retrospective-family CLI subcommands.

* ``harness project-context …``
* ``harness retrospective …``
* ``harness harness-gap …``
* ``harness agent-eval …``

Each gets its own ``*CommandHandlers`` dataclass + ``register_*`` function so
the monolith's ``build_parser`` can wire them with a single call apiece.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# project-context
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProjectContextCommandHandlers:
    add_lesson: Callable[[argparse.Namespace], int]
    drift_scan: Callable[[argparse.Namespace], int]
    lint: Callable[[argparse.Namespace], int]


def register_project_context_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: ProjectContextCommandHandlers,
) -> argparse.ArgumentParser:
    project_context = subparsers.add_parser("project-context")
    project_context_sub = project_context.add_subparsers(
        dest="project_context_command", required=True
    )
    p = add_leaf(project_context_sub, "add-lesson", handlers.add_lesson)
    p.add_argument("--lesson", required=True, help="Lesson text to append.")
    p.add_argument("--date", help="Override date (YYYY-MM-DD); defaults to today.")
    p.add_argument("--source", help="Source mission-id for audit trail.")
    add_leaf(project_context_sub, "drift-scan", handlers.drift_scan)
    add_leaf(project_context_sub, "lint", handlers.lint)
    return project_context


# ---------------------------------------------------------------------------
# retrospective
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RetrospectiveCommandHandlers:
    harness_gap_init: Callable[[argparse.Namespace], int]
    harness_gap_emit: Callable[[argparse.Namespace], int]


def register_retrospective_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: RetrospectiveCommandHandlers,
) -> argparse.ArgumentParser:
    retrospective = subparsers.add_parser("retrospective")
    retrospective_sub = retrospective.add_subparsers(
        dest="retrospective_command", required=True
    )
    p = add_leaf(retrospective_sub, "harness-gap-init", handlers.harness_gap_init)
    p.add_argument("--mission", required=True)
    p = add_leaf(retrospective_sub, "harness-gap-emit", handlers.harness_gap_emit)
    p.add_argument("--mission", required=True)
    p.add_argument("--gap-id", required=True)
    p.add_argument("--pattern-key", required=True)
    p.add_argument(
        "--target-kind",
        required=True,
        choices=[
            "workflow",
            "hook",
            "schema",
            "lint_check",
            "agent_prompt",
            "methodology",
            "other",
        ],
    )
    p.add_argument(
        "--severity",
        choices=["critical", "high", "medium", "low"],
        default="medium",
    )
    p.add_argument("--description", required=True)
    p.add_argument("--first-seen")
    p.add_argument("--verification-ref")
    return retrospective


# ---------------------------------------------------------------------------
# harness-gap
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HarnessGapCommandHandlers:
    pattern_scan: Callable[[argparse.Namespace], int]


def register_harness_gap_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: HarnessGapCommandHandlers,
) -> argparse.ArgumentParser:
    harness_gap = subparsers.add_parser("harness-gap")
    harness_gap_sub = harness_gap.add_subparsers(dest="harness_gap_command", required=True)
    p = add_leaf(harness_gap_sub, "pattern-scan", handlers.pattern_scan)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--min-repeat",
        type=int,
        default=2,
        help="Minimum repeat_count to flag as a recurring pattern.",
    )
    return harness_gap


# ---------------------------------------------------------------------------
# agent-eval
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentEvalCommandHandlers:
    drift: Callable[[argparse.Namespace], int]


def register_agent_eval_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: AgentEvalCommandHandlers,
) -> argparse.ArgumentParser:
    agent_eval = subparsers.add_parser("agent-eval")
    agent_eval_sub = agent_eval.add_subparsers(dest="agent_eval_command", required=True)
    p = add_leaf(agent_eval_sub, "drift", handlers.drift)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--baseline",
        dest="baseline_mission",
        help="Mission id to use as drift baseline.",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Regression threshold (0.0-1.0); delta below -threshold triggers a finding.",
    )
    return agent_eval
