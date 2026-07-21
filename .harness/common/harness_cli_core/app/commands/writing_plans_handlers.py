from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.breakdown import resolve_execution_brief_contract, writing_plans_refinements
from harness_cli_core.infra.runtime_paths import relpath


def cmd_writing_plans_run(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    if args.mode != "internal-carrier":
        return emit_payload(
            args,
            fail_payload(
                "writing-plans.run",
                "writing_plans_mode_unsupported",
                f"writing-plans run only accepts --mode internal-carrier; got {args.mode!r}",
            ),
        )

    artifact, contract, error_code = resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "writing-plans.run",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "writing-plans.run",
            "mode": args.mode,
            "mission": args.mission,
            "atomic_task_queue_refinement": writing_plans_refinements(contract),
        },
    )
