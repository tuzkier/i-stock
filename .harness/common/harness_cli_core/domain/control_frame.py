from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from harness_cli_core.app.output import fail_payload, finding
from harness_cli_core.domain.control_context import control_relpath, selected_mission_slice
from harness_cli_core.domain.control_state import as_str_list, mission_summary
from harness_cli_core.domain.control_status import collect_control_status, gate_report_paths
from harness_cli_core.infra.runtime_paths import load_runtime_config, resolve_path


COMMON_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = COMMON_ROOT / "skills"
WORK_GRAPH_SCRIPTS = SKILLS_ROOT / "work-graph" / "scripts"
if str(WORK_GRAPH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))

from work_graph_lib import lane_stage_for_node as wg_lane_stage_for_node  # noqa: E402


def latest_gate_report_for_mission(layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    reports: list[tuple[float, Path, dict[str, Any]]] = []
    for path in gate_report_paths(layout):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(report, dict) or str(report.get("mission_id") or "") != mission_id:
            continue
        reports.append((path.stat().st_mtime, path, report))
    if not reports:
        return {"latest_gate_report": "", "gate_effect": "", "decision": "", "exists": False}
    _mtime, path, report = sorted(reports, key=lambda item: item[0])[-1]
    return {
        "latest_gate_report": str(path),
        "gate_effect": str(report.get("gate_effect") or ""),
        "decision": str(report.get("decision") or ""),
        "exists": True,
    }


def load_advance_after_gate_module() -> Any | None:
    path = SKILLS_ROOT / "board-router" / "scripts" / "advance_after_gate.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("harness_advance_after_gate", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def next_graph_operation_for_frame(root: Path, mission_id: str, mission_slice: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    module = load_advance_after_gate_module()
    if module is None:
        return {}, [finding("WARN", "resolved_graph_operation_unavailable", "board-router advance_after_gate resolver is unavailable", source="control.frame")]
    resolver_findings: list[Any] = []
    try:
        operation = module.operation_from_slice(root, mission_id, mission_slice, resolver_findings)
    except Exception as exc:  # pragma: no cover - defensive boundary for read-only control query
        return {}, [finding("WARN", "resolved_graph_operation_failed", f"failed to resolve next graph operation: {exc}", source="control.frame")]
    findings = [
        finding(
            "WARN" if str(getattr(item, "level", "")).upper() == "FAIL" else str(getattr(item, "level", "WARN") or "WARN"),
            str(getattr(item, "code", "resolved_graph_operation_finding") or "resolved_graph_operation_finding"),
            str(getattr(item, "message", "") or "resolved graph operation finding"),
            source="control.frame",
        )
        for item in resolver_findings
    ]
    return (operation if isinstance(operation, dict) else {}), findings


def build_control_frame(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    _status_doc, entry, slice_path, mission_slice = selected_mission_slice(root, layout, mission_id)
    if not entry:
        payload = fail_payload("control.frame", "missing_mission", f"mission not found: {mission_id}")
        payload["runtime_layout"] = layout
        return payload
    if not mission_slice:
        payload = fail_payload("control.frame", "missing_mission_slice", f"Mission Slice not found: {slice_path}")
        payload["runtime_layout"] = layout
        return payload

    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    lane_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    lane = str(control_plane.get("lane") or lane_action.get("lane") or mission_slice.get("from_lane") or "")
    stage = str(control_plane.get("stage") or lane_action.get("stage") or "")
    registry_action: dict[str, Any] = {}
    if lane and stage:
        _lane, _stage, resolved = wg_lane_stage_for_node(load_runtime_config(root), {"id": "<control-frame>", "lane": lane, "stage": stage})
        registry_action = resolved if isinstance(resolved, dict) else {}
    action = {**registry_action, **lane_action} if registry_action else lane_action
    findings: list[dict[str, Any]] = []
    legacy_action_field = "stage" + "_action"
    legacy_control_fields = [field for field in ("skill", "carrier", legacy_action_field, "from_lane", "to_lane") if control_plane.get(field) not in (None, "")]
    if legacy_control_fields:
        findings.append(finding(
            "WARN",
            "legacy_control_plane_fields",
            "Mission Slice control_plane contains legacy dispatch fields; new control_plane only owns lane/stage",
            source="mission_slice",
            path=str(slice_path),
            legacy_fields=legacy_control_fields,
        ))
    control_skill = str(control_plane.get("skill") or "")
    action_skill = str(action.get("skill") or "")
    if control_skill and action_skill and control_skill != action_skill:
        payload = fail_payload(
            "control.frame",
            "control_plane_skill_conflict",
            f"legacy control_plane dispatch skill {control_skill!r} conflicts with lane_action.skill {action_skill!r}",
        )
        payload["runtime_layout"] = layout
        payload["mission_id"] = mission_id
        payload["mission_slice_path"] = control_relpath(root, slice_path)
        return payload
    output_artifact = str(action.get("output_artifact") or "")
    artifact_path = resolve_path(root, output_artifact)
    status_payload = collect_control_status(root, layout, mission=mission_id)
    required_approvals = status_payload.get("required_approvals") if isinstance(status_payload.get("required_approvals"), list) else []
    gate_state = latest_gate_report_for_mission(layout, mission_id)
    if status_payload.get("pending_gates"):
        gate_state["pending_gates"] = status_payload["pending_gates"]
    raw_allowed_graph_operations = as_str_list(action.get("allowed_graph_operations")) or list((action.get("operation_profiles") or {}).keys())
    resolved_graph_operation, resolver_findings = next_graph_operation_for_frame(root, mission_id, mission_slice)
    findings.extend(resolver_findings)
    allowed_graph_operations = [str(resolved_graph_operation["type"])] if resolved_graph_operation.get("type") else raw_allowed_graph_operations
    return {
        "status": "PASS",
        "runtime_layout": layout,
        "mission_id": mission_id,
        "mission_status": mission_summary(mission_id, entry),
        "mission_slice_path": control_relpath(root, slice_path),
        "lane": lane,
        "stage": stage,
        "skill": str(action.get("skill") or stage or ""),
        "carrier": str(action.get("carrier") or action.get("skill") or stage or ""),
        "output_artifact": output_artifact,
        "required_execution_roles": as_str_list(action.get("required_execution_roles")),
        "required_review_roles": as_str_list(action.get("required_review_roles")),
        "allowed_graph_operations": allowed_graph_operations,
        "raw_allowed_graph_operations": raw_allowed_graph_operations,
        "resolved_graph_operation": resolved_graph_operation,
        "artifact_state": {"path": output_artifact, "exists": bool(artifact_path and artifact_path.exists())},
        "gate_state": gate_state,
        "next_required_controls": ["approval.require"] if required_approvals else [],
        "required_approvals": required_approvals,
        "work_graph": mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {},
        "findings": findings,
    }
