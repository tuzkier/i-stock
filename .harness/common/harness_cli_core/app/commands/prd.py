from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PrdCommandHandlers:
    anti_pattern_scan: Callable[[argparse.Namespace], int]
    domain_model_lint: Callable[[argparse.Namespace], int]
    agent_cap_eval: Callable[[argparse.Namespace], int]


def register_prd_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: PrdCommandHandlers,
) -> argparse.ArgumentParser:
    prd = subparsers.add_parser("prd")
    prd_sub = prd.add_subparsers(dest="prd_command", required=True)
    p = add_leaf(prd_sub, "anti-pattern-scan", handlers.anti_pattern_scan)
    p.add_argument("--artifact", required=True, help="Path to PRD artifact to scan.")
    p = add_leaf(prd_sub, "domain-model-lint", handlers.domain_model_lint)
    p.add_argument("--artifact", required=True, help="Path to product-domain-model.md.")
    p.add_argument(
        "--product-definition",
        dest="product_definition",
        help="Optional path to product-definition.md for traceability checks.",
    )
    p.add_argument(
        "--contract",
        help="Optional path to prd.contract.yaml for structured field checks.",
    )
    p = add_leaf(prd_sub, "agent-cap-eval", handlers.agent_cap_eval)
    p.add_argument("--mission", required=True)
    p.add_argument(
        "--component",
        required=True,
        help="Name of the agent component being evaluated.",
    )
    p.add_argument(
        "--work-rights",
        dest="work_rights",
        help=(
            "Comma-separated list of work rights (read_context,decide_action,"
            "write_artifact,dispatch_subagent,request_human_input,halt_for_review)."
        ),
    )
    p.add_argument("--priority", choices=["P0", "P1", "P2"], help="Priority level.")
    p.add_argument("--notes", help="Optional rationale text.")
    return prd
