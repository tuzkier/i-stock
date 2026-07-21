from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from harness_cli_core.domain.control_state import as_str_list
from harness_cli_core.domain.control_status import active_mission_ids, open_mission_ids
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_paths import relpath, resolve_path, work_graph_root


def fail_payload(control: str, code: str, message: str) -> dict[str, Any]:
    return {"status": "FAIL", "control": control, "findings": [{"level": "FAIL", "code": code, "message": message}]}


def mission_slice_path(root: Path, mission_id: str) -> Path:
    return work_graph_root(root) / "mission-slices" / f"{mission_id}.yaml"


def load_mission_slice(root: Path, mission_id: str, entry: dict[str, Any] | None = None) -> tuple[Path, dict[str, Any]]:
    path: Path | None = None
    if entry and isinstance(entry.get("work_graph"), dict):
        path = resolve_path(root, str(entry["work_graph"].get("mission_slice") or ""))
    path = path or mission_slice_path(root, mission_id)
    return path, load_yaml(path)


def format_lane_value(value: Any, mission_id: str) -> Any:
    if isinstance(value, str):
        return value.replace("{mission_id}", mission_id)
    if isinstance(value, list):
        return [format_lane_value(item, mission_id) for item in value]
    if isinstance(value, dict):
        return {key: format_lane_value(item, mission_id) for key, item in value.items()}
    return value


def operation_profiles(action: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles = action.get("operation_profiles")
    if not isinstance(profiles, dict):
        return {}
    return {str(name): payload for name, payload in profiles.items() if isinstance(payload, dict)}


def build_lane_action_payload(action_name: str, action: dict[str, Any], mission_id: str) -> dict[str, Any]:
    profiles = operation_profiles(action)
    default_operation = str(action.get("graph_operation") or "")
    snapshot: dict[str, Any] = {
        "lane": str(action_name),
        "stage": str(action.get("stage") or ""),
        "graph_operation": default_operation,
        "operation_profiles": format_lane_value(profiles, mission_id),
        "allowed_graph_operations": list(profiles),
        "output_artifact": format_lane_value(action.get("output_artifact"), mission_id),
        "required_execution_roles": as_str_list(action.get("required_execution_roles")),
        "required_review_roles": as_str_list(action.get("required_review_roles")),
    }
    advance_stage = profiles.get("advance_stage") if isinstance(profiles.get("advance_stage"), dict) else {}
    advance_lane = profiles.get("advance_lane") if isinstance(profiles.get("advance_lane"), dict) else {}
    if default_operation == "advance_stage" and advance_stage.get("to_stage"):
        snapshot["to_stage"] = str(advance_stage["to_stage"])
    if default_operation == "advance_lane" and advance_lane.get("to_lane"):
        snapshot["to_lane"] = str(advance_lane["to_lane"])
    if default_operation == "advance_lane" and advance_lane.get("to_stage"):
        snapshot["to_stage"] = str(advance_lane["to_stage"])
    if action.get("carrier"):
        snapshot["carrier"] = str(action.get("carrier"))
    if action.get("skill"):
        snapshot["skill"] = str(action.get("skill"))
    if isinstance(action.get("role_carriers"), dict):
        snapshot["role_carriers"] = dict(action["role_carriers"])
    return snapshot


def build_frame_current_payload(
    root: Path,
    status: dict[str, Any],
    requested_mission_id: str | None,
    lane_actions: dict[str, dict[str, Any]],
    board_select: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    mission_id = requested_mission_id
    active_ids = active_mission_ids(status)
    open_ids = open_mission_ids(status)
    if not mission_id and active_ids:
        mission_id = active_ids[0]
    if mission_id and isinstance(status.get(mission_id), dict) and mission_id in open_ids:
        entry = status[mission_id]
        slice_path, mission_slice = load_mission_slice(root, mission_id, entry)
        if mission_slice:
            control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
            from_lane = str(mission_slice.get("from_lane") or control_plane.get("from_lane") or "")
            registry_action = lane_actions.get(from_lane) or {}
            return {
                "status": "PASS",
                "control": "frame.current",
                "resume_source": "mission_slice",
                "mission_id": mission_id,
                "mission_status": entry,
                "mission_slice_path": relpath(root, slice_path),
                "mission_slice": mission_slice,
                "lane_action": build_lane_action_payload(from_lane, registry_action, mission_id) if registry_action else mission_slice.get("lane_action"),
                "control_plane": mission_slice.get("control_plane"),
                "work_graph": mission_slice.get("work_graph"),
                "findings": [],
            }
        if (entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}).get("mission_slice"):
            return fail_payload("frame.current", "missing_mission_slice", f"Mission Slice not found: {relpath(root, slice_path)}")
        return fail_payload(
            "frame.current",
            "missing_mission_slice",
            f"mission {mission_id} has no Mission Slice; legacy stage-mode resume is no longer supported. Recreate Mission Slice via board-router.",
        )
    selection_mission_id = mission_id or (open_ids[0] if open_ids else "FRAME-CURRENT")
    return {
        "status": "PASS",
        "control": "frame.current",
        "resume_source": "board",
        "mission_id": mission_id,
        "selection_mission_id": selection_mission_id,
        "active_missions": active_ids,
        "open_missions": open_ids,
        "board_selection": board_select(selection_mission_id) or None,
        "findings": [],
    }


def build_frame_explain_payload(
    root: Path,
    status: dict[str, Any],
    mission_id: str,
    node: str | None,
) -> dict[str, Any]:
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    if not entry:
        return fail_payload("frame.explain", "missing_mission", f"mission not found: {mission_id}")
    slice_path, mission_slice = load_mission_slice(root, mission_id, entry)
    slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    node_ids = set(
        as_str_list(slice_graph.get("primary_nodes"))
        + as_str_list(slice_graph.get("related_nodes"))
        + as_str_list(slice_graph.get("input_nodes"))
        + as_str_list(slice_graph.get("output_nodes"))
    )
    if node and node not in node_ids:
        return fail_payload("frame.explain", "node_not_in_mission_slice", f"{node} is not referenced by Mission Slice {mission_id}")
    return {
        "status": "PASS",
        "control": "frame.explain",
        "mission_id": mission_id,
        "node": node,
        "mission_status": entry,
        "mission_slice_path": relpath(root, slice_path),
        "mission_slice": mission_slice,
        "findings": [],
    }
