from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class TraceCommandHandlers:
    log_init: Callable[[argparse.Namespace], int]
    report: Callable[[argparse.Namespace], int]
    step_enter: Callable[[argparse.Namespace], int]
    step_exit: Callable[[argparse.Namespace], int]
    round_enter: Callable[[argparse.Namespace], int]
    round_exit: Callable[[argparse.Namespace], int]


def register_trace_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: TraceCommandHandlers,
) -> argparse.ArgumentParser:
    trace = subparsers.add_parser("trace")
    trace_sub = trace.add_subparsers(dest="trace_command", required=True)

    p = add_leaf(trace_sub, "log-init", handlers.log_init)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", help="optional stage label to record on the init event")

    p = add_leaf(trace_sub, "report", handlers.report)
    p.add_argument("--mission", required=True)
    p.add_argument("--stage", help="optional stage label to count stage-scoped events")

    p = add_leaf(trace_sub, "step-enter", handlers.step_enter)
    p.add_argument("--mission", required=True)
    p.add_argument("--step", required=True, help="step id or phase label, e.g. 'phase-1' or 'review-loop'")
    p.add_argument("--phase", help="optional phase grouping label")
    p.add_argument("--rounds", type=int, help="optional rounds counter (e.g. reviewer round number)")
    p.add_argument("--note", help="optional free-text note appended to the trace record")

    p = add_leaf(trace_sub, "step-exit", handlers.step_exit)
    p.add_argument("--mission", required=True)
    p.add_argument("--step", required=True)
    p.add_argument("--status", required=True, choices=["pass", "fail", "blocked"])
    p.add_argument("--phase")
    p.add_argument("--rounds", type=int)
    p.add_argument("--note")

    p = add_leaf(trace_sub, "round-enter", handlers.round_enter)
    p.add_argument("--mission", required=True)
    p.add_argument("--round", type=int, required=True, help="Review round number (1-based)")
    p.add_argument("--note", help="Optional note appended to the trace record")

    p = add_leaf(trace_sub, "round-exit", handlers.round_exit)
    p.add_argument("--mission", required=True)
    p.add_argument("--round", type=int, required=True, help="Review round number (1-based)")
    p.add_argument("--status", required=True, choices=["pass", "fail", "hold", "blocked"], help="Outcome of this review round")
    p.add_argument("--note", help="Optional note appended to the trace record")

    return trace
