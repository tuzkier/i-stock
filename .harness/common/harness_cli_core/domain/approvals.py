from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from harness_cli_core.domain.control_state import as_str_list
from harness_cli_core.infra.io import load_yaml, write_yaml
from harness_cli_core.infra.runtime_paths import load_runtime_config, mission_status_path, runtime_harness_root
from harness_cli_core.infra.time import today


def approvals_path(root: Path) -> Path:
    return runtime_harness_root(root) / "state" / "approvals.json"


def load_approvals(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = approvals_path(root)
    if not path.exists():
        return {"schema_version": 1, "approvals": []}, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"schema_version": 1, "approvals": []}, []
    if isinstance(data, list):
        records = [item for item in data if isinstance(item, dict)]
        return {"schema_version": 1, "approvals": records}, records
    if isinstance(data, dict):
        raw_records = data.get("approvals")
        if isinstance(raw_records, list):
            records = [item for item in raw_records if isinstance(item, dict)]
            return {**data, "schema_version": data.get("schema_version") or 1, "approvals": records}, records
        if data.get("mission_id"):
            return {"schema_version": 1, "approvals": [data]}, [data]
    return {"schema_version": 1, "approvals": []}, []


def write_approvals(root: Path, document: dict[str, Any], records: list[dict[str, Any]]) -> Path:
    path = approvals_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {**document, "schema_version": document.get("schema_version") or 1, "approvals": records}
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def next_approval_id(records: list[dict[str, Any]]) -> str:
    return f"APR-{today().replace('-', '')}-{len(records) + 1:03d}"


def checkpoint_name(args: argparse.Namespace) -> str:
    return str(getattr(args, "checkpoint", None) or getattr(args, "stage", None) or "")


def sync_checkpoint_passed(root: Path, mission_id: str, checkpoint: str) -> dict[str, Any] | None:
    if not checkpoint:
        return None
    path = mission_status_path(root)
    status = load_yaml(path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    if not entry:
        return None
    checkpoints = as_str_list(entry.get("checkpoints_passed"))
    if checkpoint not in checkpoints:
        checkpoints.append(checkpoint)
    entry["checkpoints_passed"] = checkpoints
    status[mission_id] = entry
    write_yaml(path, status)
    return entry


def stage_completion_config(root: Path) -> dict[str, Any]:
    config = load_runtime_config(root)
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    policy = work_graph.get("stage_completion") if isinstance(work_graph.get("stage_completion"), dict) else {}
    return policy


def approval_stage_completion_status(root: Path, mission_id: str, record: dict[str, Any], mission_status: dict[str, Any] | None) -> dict[str, Any]:
    policy = stage_completion_config(root)
    checkpoint_policy = policy.get("checkpoint_approval") if isinstance(policy.get("checkpoint_approval"), dict) else {}
    if not checkpoint_policy:
        return {}
    stage = str(record.get("stage") or record.get("checkpoint") or "")
    status = str(record.get("status") or "")
    approval_type = str(record.get("type") or "")
    entry = mission_status if isinstance(mission_status, dict) else {}
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    current_stage = str(work_graph.get("stage") or entry.get("current_stage") or "")
    last_operation_status = str(work_graph.get("last_operation_status") or "")
    pending_graph_operation = (
        approval_type == "checkpoint"
        and status == "approved"
        and bool(stage)
        and (not current_stage or stage == current_stage)
        and not last_operation_status
    )
    return {
        "event": "checkpoint_approval",
        "stage": stage,
        "terminal": bool(checkpoint_policy.get("terminal", False)),
        "effect": checkpoint_policy.get("effect") or "",
        "pending_graph_operation": pending_graph_operation,
        "required_next_controls": as_str_list(checkpoint_policy.get("required_next_controls")) if pending_graph_operation else [],
        "pause_boundary_when_user_defers_next_stage": checkpoint_policy.get("pause_boundary_when_user_defers_next_stage") or "",
    }


def mission_stage_completion_status(root: Path, stage: str, mission_status: dict[str, Any] | None) -> dict[str, Any]:
    policy = stage_completion_config(root)
    gate_policy = policy.get("gate_continue") if isinstance(policy.get("gate_continue"), dict) else {}
    if not gate_policy:
        return {}
    entry = mission_status if isinstance(mission_status, dict) else {}
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    current_stage = str(work_graph.get("stage") or entry.get("current_stage") or "")
    last_operation_status = str(work_graph.get("last_operation_status") or "")
    pending_graph_operation = bool(stage) and (not current_stage or stage == current_stage) and not last_operation_status
    return {
        "event": "stage_complete",
        "stage": stage,
        "pending_graph_operation": pending_graph_operation,
        "required_next_controls": as_str_list(gate_policy.get("required_next_controls")) if pending_graph_operation else [],
        "state_sync_control": gate_policy.get("state_sync_control") or "",
        "pause_boundary_when_user_defers_next_stage": gate_policy.get("pause_boundary_when_user_defers_next_stage") or "",
    }


def approval_matches(record: dict[str, Any], *, mission: str | None = None, approval_type: str | None = None, stage: str | None = None, status: str | None = None) -> bool:
    if mission and str(record.get("mission_id") or "") != mission:
        return False
    if approval_type and str(record.get("type") or "") != approval_type:
        return False
    if stage and str(record.get("stage") or record.get("checkpoint") or "") != stage:
        return False
    if status and str(record.get("status") or "") != status:
        return False
    return True
