from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.clarifications import (
    clarification_matches,
    load_clarifications,
    write_clarification,
)
from harness_cli_core.infra.time import now_iso


def cmd_clarification_record(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    record = {
        "id": getattr(args, "clar_id", None) or None,
        "mission_id": args.mission,
        "stage": getattr(args, "stage", None) or "",
        "gap_id": getattr(args, "gap_id", None) or "",
        "source_role": getattr(args, "source_role", None) or "",
        "approval_id": getattr(args, "approval_id", None) or "",
        "question": args.question,
        "answer": args.answer,
        "decided_at": getattr(args, "decided_at", None) or now_iso(),
    }
    result = write_clarification(root, record)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "clarification.record",
            "clarification": result["clarification"],
            "clarification_path": result["clarification_path"],
            "index_md_path": result["index_md_path"],
            "findings": [],
        },
    )


def cmd_clarification_list(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    records = load_clarifications(root)
    mission = getattr(args, "mission", None)
    matches = [r for r in records if clarification_matches(r, mission=mission)]
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "clarification.list",
            "clarifications": matches,
            "count": len(matches),
            "findings": [],
        },
    )
