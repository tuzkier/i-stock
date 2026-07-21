"""Handlers for `harness acceptance ...` typed action shims.

PT-CLI-EXTEND-04: `harness acceptance record` is the CLI Bridge shim for the
`acceptance_decision` typed action (DATA-11). Enforces INV-10: an `accept`
decision with no `--evidence-ref` blocks with exit=7. To accept despite
missing evidence, the user must take the explicit Decision Gate path
(`harness approval append --type tradeoff --status approved`).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from harness_cli_core.app.commands.agent_handlers import (
    AGENT_DISPATCH_EXIT_OK,
    AGENT_DISPATCH_EXIT_WORKSPACE_LOCK,
)
from harness_cli_core.domain.runs import (
    append_control_event,
    workspace_initialized,
    workspace_runtime_dir,
)


ACCEPTANCE_DECISION_CLOSED_SET = ("accept", "request_changes")
ACCEPTANCE_EXIT_EVIDENCE_GAP = 7


def cmd_acceptance_record(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    if not workspace_initialized(workspace):
        sys.stderr.write(
            f"workspace_lock: harness-runtime not initialized at {workspace_runtime_dir(workspace)}\n"
        )
        return AGENT_DISPATCH_EXIT_WORKSPACE_LOCK

    evidence_refs = list(args.evidence_ref or [])
    if args.decision == "accept" and not evidence_refs:
        sys.stderr.write(
            "evidence_gap: accept requires at least one --evidence-ref (INV-10). "
            "To accept despite gaps, take the Decision Gate path "
            "(`harness approval append --type tradeoff --status approved`).\n"
        )
        return ACCEPTANCE_EXIT_EVIDENCE_GAP

    acceptance_id = f"acc-{uuid.uuid4().hex[:16]}"
    control_event_id = f"evt-{uuid.uuid4().hex[:16]}"
    append_control_event(
        workspace,
        kind="acceptance_decision",
        filename="acceptance-decisions.jsonl",
        extra={
            "acceptance_id": acceptance_id,
            "control_event_id": control_event_id,
            "mission_id": args.mission,
            "decision": args.decision,
            "evidence_refs": evidence_refs,
        },
    )

    sys.stdout.write(
        json.dumps(
            {
                "acceptance_id": acceptance_id,
                "control_event_id": control_event_id,
                "mission_id": args.mission,
                "decision": args.decision,
                "evidence_refs": evidence_refs,
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    return AGENT_DISPATCH_EXIT_OK
