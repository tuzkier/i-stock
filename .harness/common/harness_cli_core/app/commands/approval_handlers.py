from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.approvals import (
    approval_matches,
    approval_stage_completion_status,
    load_approvals,
    next_approval_id,
    sync_checkpoint_passed,
    write_approvals,
)
from harness_cli_core.infra.runtime_paths import relpath
from harness_cli_core.infra.time import now_iso


def cmd_approval_append(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    document, records = load_approvals(root)
    record = {
        "approval_id": args.approval_id or next_approval_id(records),
        "mission_id": args.mission,
        "type": args.type,
        "stage": args.stage or "",
        "checkpoint": args.checkpoint or args.stage or "",
        "status": args.status,
        "decided_at": args.decided_at or now_iso(),
        "comment": args.comment or "",
    }
    records.append(record)
    path = write_approvals(root, document, records)
    mission_status = None
    checkpoint = str(record.get("checkpoint") or "")
    if record["type"] == "checkpoint" and record["status"] == "approved" and checkpoint:
        mission_status = sync_checkpoint_passed(root, args.mission, checkpoint)
    stage_completion = approval_stage_completion_status(root, args.mission, record, mission_status)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "approval.append",
            "approval": record,
            "approvals_path": relpath(root, path),
            "mission_status": mission_status,
            "stage_completion": stage_completion,
            "findings": [],
        },
    )


def cmd_approval_latest(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    _document, records = load_approvals(root)
    matches = [
        record
        for record in records
        if approval_matches(record, mission=args.mission, approval_type=args.type, stage=args.stage, status=args.status)
    ]
    latest = matches[-1] if matches else None
    return emit_payload(args, {"status": "PASS", "control": "approval.latest", "approval": latest, "count": len(matches), "findings": []})


def cmd_approval_require(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    _document, records = load_approvals(root)
    stage = args.checkpoint or args.stage
    matches = [
        record
        for record in records
        if approval_matches(record, mission=args.mission, approval_type=args.type, stage=stage, status="approved")
    ]
    if not matches:
        message = f"approved {args.type} approval is required for mission {args.mission}"
        if stage:
            message += f" stage/checkpoint {stage}"
        return emit_payload(args, {"status": "BLOCKED", "control": "approval.require", "approval": None, "findings": [{"level": "BLOCKED", "code": "approval_required", "message": message}]})
    return emit_payload(args, {"status": "PASS", "control": "approval.require", "approval": matches[-1], "findings": []})
