from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentCommandHandlers:
    dispatch: Callable[[argparse.Namespace], int]


def register_agent_commands(
    subparsers: argparse._SubParsersAction,
    add_leaf: Callable[..., argparse.ArgumentParser],
    handlers: AgentCommandHandlers,
) -> argparse.ArgumentParser:
    agent_cli = subparsers.add_parser(
        "agent",
        description="TheForce agent dispatch and lifecycle CLI shims (D-04, SCN-AGENT-DISPATCH, SCN-AGENT-LEDGER).",
    )
    agent_sub = agent_cli.add_subparsers(dest="agent_command", required=True)
    p = add_leaf(
        agent_sub,
        "dispatch",
        handlers.dispatch,
        description=(
            "Record a dispatch_agent_run typed action intent into the workspace runtime ledger and "
            "emit a {run_id, status} JSON envelope on stdout. "
            "Exit codes: 0 = dispatched; 2 = invalid argument; 5 = workspace lock or runtime not initialized; "
            "9 = adapter unavailable."
        ),
    )
    p.add_argument("--workspace", required=True, help="Absolute path to the target workspace root")
    p.add_argument("--mission", required=True, help="Mission id receiving the AgentRun")
    p.add_argument("--backend", required=True, choices=["claude", "cursor"], help="Adapter backend identifier")
    p.add_argument(
        "--permission",
        required=True,
        choices=["read-only", "edit", "full"],
        help="Permission mode for the AgentRun",
    )
    return agent_cli
