from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class VerifyCommandHandlers:
    compute_scope: Callable[[argparse.Namespace], int]
    run_tests: Callable[[argparse.Namespace], int]
    e2e_status: Callable[[argparse.Namespace], int]
    true_e2e_check: Callable[[argparse.Namespace], int]
    dispatch_worker: Callable[[argparse.Namespace], int]
    dispatch_reviewer: Callable[[argparse.Namespace], int]
    detect_contradictions: Callable[[argparse.Namespace], int]
    compute_conclusion: Callable[[argparse.Namespace], int]
    agent_eval_status: Callable[[argparse.Namespace], int]
    failure_path: Callable[[argparse.Namespace], int]
    prototype_alignment_check: Callable[[argparse.Namespace], int]
    gate_run: Callable[[argparse.Namespace], int]


def register_verify_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: VerifyCommandHandlers,
) -> argparse.ArgumentParser:
    verify_cli = subparsers.add_parser("verify")
    verify_sub = verify_cli.add_subparsers(dest="verify_command", required=True)

    p = add_leaf(verify_sub, "compute-scope", handlers.compute_scope)
    p.add_argument("--mission", required=True)

    p = add_leaf(verify_sub, "run-tests", handlers.run_tests)
    p.add_argument("--mission", required=True)
    p.add_argument("--layer", required=True, choices=["unit", "integration", "e2e"])
    p.add_argument("--command", required=True, help="Test command to run")

    p = add_leaf(verify_sub, "e2e-status", handlers.e2e_status)
    p.add_argument("--mission", required=True)

    p = add_leaf(verify_sub, "true-e2e-check", handlers.true_e2e_check)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--compat",
        action="store_true",
        help="downgrade strict new-gate failures to WARN for historical accepted artifacts",
    )

    p = add_leaf(verify_sub, "dispatch-worker", handlers.dispatch_worker)
    p.add_argument("--mission", required=True)

    p = add_leaf(verify_sub, "dispatch-reviewer", handlers.dispatch_reviewer)
    p.add_argument("--mission", required=True)

    p = add_leaf(verify_sub, "detect-contradictions", handlers.detect_contradictions)
    p.add_argument("--mission", required=True)
    p.add_argument("--artifact", help="Path to verification-report.contract.yaml")

    p = add_leaf(verify_sub, "compute-conclusion", handlers.compute_conclusion)
    p.add_argument("--mission", required=True)

    p = add_leaf(verify_sub, "agent-eval-status", handlers.agent_eval_status)
    p.add_argument("--mission", required=True)

    p = add_leaf(verify_sub, "failure-path", handlers.failure_path)
    p.add_argument("--mission", required=True)
    p.add_argument("--kind", required=True)

    p = add_leaf(verify_sub, "prototype-alignment-check", handlers.prototype_alignment_check)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--compat",
        action="store_true",
        help="downgrade strict new-gate failures to WARN for historical accepted artifacts",
    )

    verify_gate = verify_sub.add_parser("gate")
    verify_gate_sub = verify_gate.add_subparsers(dest="verify_gate_command", required=True)
    p = add_leaf(verify_gate_sub, "run", handlers.gate_run)
    p.add_argument("--mission", required=True)
    return verify_cli
