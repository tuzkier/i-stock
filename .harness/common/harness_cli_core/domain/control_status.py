from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_cli_core.app.output import finding, status_from_findings
from harness_cli_core.domain.collections import unique
from harness_cli_core.domain.control_state import (
    as_str_list,
    control_nodes_by_id,
    load_control_slice,
    mission_slice_lane_consistency_findings,
    mission_summary,
)
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_layout import control_runtime_root, control_status_path


CLOSED_MISSION_STATUSES = {"done", "closed", "cancelled", "delivered"}
CHECKPOINT_ALIASES = {
    "acceptance_result": "acceptance-result",
    "tech_design": "tech-design",
    "execution_brief": "execution-brief",
    "verification_report": "verification-report",
    "delivery_package": "delivery-package",
    "code_review": "code-review",
    "mission_contract": "mission-contract",
    "dependency_impact": "dependency-impact",
}


def active_mission_ids(status: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for mission_id, entry in status.items():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "").lower() in CLOSED_MISSION_STATUSES:
            continue
        work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
        if work_graph.get("last_operation_status") == "PASS":
            continue
        if work_graph.get("mission_slice"):
            ids.append(str(mission_id))
    return sorted(ids, key=lambda item: str((status.get(item) or {}).get("started_at") or ""))


def mission_entry_operation_completed(entry: dict[str, Any]) -> bool:
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    return str(work_graph.get("last_operation_status") or "").upper() == "PASS"


def open_mission_ids(status: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for mission_id, entry in status.items():
        if not isinstance(entry, dict):
            continue
        if str(entry.get("status") or "").lower() in CLOSED_MISSION_STATUSES:
            continue
        ids.append(str(mission_id))
    return sorted(ids, key=lambda item: str((status.get(item) or {}).get("started_at") or ""))


def normalize_checkpoint(value: str) -> str:
    stripped = value.strip()
    return CHECKPOINT_ALIASES.get(stripped, stripped)


def checkpoint_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [normalize_checkpoint(value)] if value.strip() else []
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, str):
            names.append(normalize_checkpoint(item))
        elif isinstance(item, dict):
            name = str(item.get("stage") or item.get("checkpoint") or item.get("id") or "")
            if name:
                names.append(normalize_checkpoint(name))
    return unique([item for item in names if item])


def load_control_approval_records(layout: dict[str, Any]) -> list[dict[str, Any]]:
    path = control_runtime_root(layout) / "state" / "approvals.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        records = data.get("approvals")
        if isinstance(records, list):
            return [item for item in records if isinstance(item, dict)]
        if data.get("mission_id"):
            return [data]
    return []


def approved_checkpoints_for_mission(layout: dict[str, Any], mission_id: str) -> dict[str, str]:
    approved: dict[str, str] = {}
    for record in load_control_approval_records(layout):
        if str(record.get("mission_id") or mission_id) != mission_id:
            continue
        if str(record.get("type") or "") != "checkpoint":
            continue
        if str(record.get("status") or "") != "approved":
            continue
        checkpoint = normalize_checkpoint(str(record.get("stage") or record.get("checkpoint") or record.get("id") or ""))
        if checkpoint and checkpoint not in approved:
            approved[checkpoint] = str(record.get("approval_id") or "")
    return approved


def gate_report_paths(layout: dict[str, Any]) -> list[Path]:
    root = control_runtime_root(layout) / "state" / "gate-reports"
    return sorted(root.glob("**/*.json")) if root.exists() else []


def load_control_gate_reports(layout: dict[str, Any], mission_ids: set[str]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in gate_report_paths(layout):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(report, dict):
            continue
        mission_id = str(report.get("mission_id") or "")
        if mission_ids and mission_id not in mission_ids:
            continue
        approval_status = report.get("approval_status") if isinstance(report.get("approval_status"), dict) else {}
        missing = checkpoint_names(approval_status.get("missing_checkpoints"))
        gate_effect = str(report.get("gate_effect") or "")
        decision = str(report.get("decision") or "")
        if gate_effect in {"pause", "block"} or decision == "cannot_continue" or missing:
            reports.append({
                "mission_id": mission_id,
                "path": str(path),
                "stage": str(report.get("stage") or ""),
                "legacy_action": str(report.get("stage" + "_action") or ""),
                "operation": str(report.get("operation") or ""),
                "gate_effect": gate_effect,
                "decision": decision,
                "missing_checkpoints": missing,
            })
    return reports


def collect_required_approvals(
    root: Path,
    layout: dict[str, Any],
    status_doc: dict[str, Any],
    active_ids: list[str],
    active_slices: list[dict[str, Any]],
    pending_gates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    required: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_required(mission_id: str, checkpoint: str, source: str, source_path: str = "") -> None:
        checkpoint = normalize_checkpoint(checkpoint)
        if not checkpoint:
            return
        approved = approved_checkpoints_for_mission(layout, mission_id)
        if checkpoint in approved:
            return
        key = (mission_id, checkpoint, source)
        if key in seen:
            return
        seen.add(key)
        required.append({
            "mission_id": mission_id,
            "type": "checkpoint",
            "checkpoint": checkpoint,
            "status": "missing",
            "source": source,
            "source_path": source_path,
        })

    for slice_summary in active_slices:
        mission_id = str(slice_summary.get("mission_id") or "")
        if not mission_id:
            continue
        entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
        slice_path, mission_slice = load_control_slice(layout, root, mission_id, entry)
        for checkpoint in checkpoint_names(mission_slice.get("required_checkpoints")) + checkpoint_names(mission_slice.get("human_checkpoints")):
            add_required(mission_id, checkpoint, "mission_slice", str(slice_path))

    for gate in pending_gates:
        mission_id = str(gate.get("mission_id") or "")
        for checkpoint in checkpoint_names(gate.get("missing_checkpoints")):
            add_required(mission_id, checkpoint, "gate_report", str(gate.get("path") or ""))

    _ = active_ids
    return required


def control_active_slice_ids(status_doc: dict[str, Any], root: Path, layout: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for mission_id in open_mission_ids(status_doc):
        entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
        work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
        if not work_graph.get("mission_slice"):
            continue
        ids.append(mission_id)
    _ = root, layout
    return sorted(ids, key=lambda item: str((status_doc.get(item) or {}).get("started_at") or ""))


def collect_control_status(root: Path, layout: dict[str, Any], *, mission: str | None = None) -> dict[str, Any]:
    status_path = control_status_path(layout)
    if not status_path.exists():
        item = finding(
            "BLOCKED",
            "mission_status_uninitialized",
            f"mission-status file not found: {status_path}",
            source="mission_status",
            blocking=True,
        )
        return {
            "status": "BLOCKED",
            "runtime_layout": layout,
            "missions": {"active": [], "open": []},
            "slices": {"active": []},
            "work_graph": {"ready_nodes": [], "blocked_nodes": []},
            "pending_gates": [],
            "required_approvals": [],
            "consistency_findings": [item],
        }
    status_doc = load_yaml(status_path)
    status_doc = status_doc if isinstance(status_doc, dict) else {}
    active_ids = control_active_slice_ids(status_doc, root, layout)
    open_ids = open_mission_ids(status_doc)
    if mission:
        active_ids = [item for item in active_ids if item == mission]
        open_ids = [item for item in open_ids if item == mission]

    findings: list[dict[str, Any]] = []
    active_slices: list[dict[str, Any]] = []
    nodes_by_id = control_nodes_by_id(layout)
    for mission_id in active_ids:
        entry = status_doc.get(mission_id) if isinstance(status_doc.get(mission_id), dict) else {}
        slice_path, mission_slice = load_control_slice(layout, root, mission_id, entry)
        if not mission_slice:
            findings.append(finding(
                "BLOCKED",
                "missing_mission_slice",
                f"active mission {mission_id} references a missing Mission Slice: {slice_path}",
                source="mission_slice",
                blocking=True,
                mission_id=mission_id,
                path=str(slice_path),
            ))
            continue
        if not mission_entry_operation_completed(entry):
            findings.extend(mission_slice_lane_consistency_findings(nodes_by_id, mission_id, mission_slice, source="mission_slice", blocking=True, path=str(slice_path)))
        control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
        slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
        active_slices.append({
            "mission_id": mission_id,
            "path": str(slice_path),
            "lane": control_plane.get("lane") or "",
            "stage": control_plane.get("stage") or "",
            "skill": (mission_slice.get("lane_action") or {}).get("skill") if isinstance(mission_slice.get("lane_action"), dict) else "",
            "primary_nodes": as_str_list(slice_graph.get("primary_nodes")),
            "related_nodes": as_str_list(slice_graph.get("related_nodes")),
        })

    nodes = list(nodes_by_id.values())
    mission_filter = set(open_ids)
    pending_gates = load_control_gate_reports(layout, mission_filter)
    required_approvals = collect_required_approvals(root, layout, status_doc, active_ids, active_slices, pending_gates)
    return {
        "status": status_from_findings(findings),
        "runtime_layout": layout,
        "missions": {
            "active": [mission_summary(mission_id, status_doc[mission_id]) for mission_id in active_ids if isinstance(status_doc.get(mission_id), dict)],
            "open": [mission_summary(mission_id, status_doc[mission_id]) for mission_id in open_ids if isinstance(status_doc.get(mission_id), dict)],
        },
        "slices": {"active": active_slices},
        "work_graph": {
            "ready_nodes": [node for node in nodes if node.get("status") == "ready"],
            "blocked_nodes": [node for node in nodes if node.get("status") == "blocked"],
        },
        "pending_gates": pending_gates,
        "required_approvals": required_approvals,
        "consistency_findings": findings,
    }
