from __future__ import annotations

import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import yaml

from harness_cli_core.app.output import finding, status_from_findings
from harness_cli_core.domain.approvals import mission_stage_completion_status
from harness_cli_core.domain.collections import unique
from harness_cli_core.domain.control_state import as_str_list, mission_slice_lane_consistency_findings
from harness_cli_core.domain.control_status import (
    active_mission_ids,
    mission_entry_operation_completed,
    open_mission_ids,
)
from harness_cli_core.domain.frame import build_lane_action_payload, load_mission_slice, mission_slice_path
from harness_cli_core.domain.graph_operations import graph_operation_input_nodes, graph_operation_output_nodes
from harness_cli_core.infra.io import load_yaml, write_yaml
from harness_cli_core.infra.runtime_paths import mission_status_path, relpath, runtime_harness_root


MISSION_ID_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
LEGACY_CLOSE_ALIAS_MAP: dict[str, str] = {
    "delivered": "merged",
    "cancelled": "discarded",
    "manual": "kept",
}
CLOSE_POLICY: dict[str, tuple[str, bool]] = {
    "merged": ("done", True),
    "pr": ("active", False),
    "kept": ("active", False),
    "discarded": ("cancelled", True),
}


@dataclass(frozen=True)
class MissionStatusFilters:
    mission: str | None = None
    active: bool = False
    open_only: bool = False
    status_filter: list[str] = field(default_factory=list)
    current_stage: list[str] = field(default_factory=list)
    stage: list[str] = field(default_factory=list)
    stage_status: list[str] = field(default_factory=list)
    ids_only: bool = False


ResolveLaneStage = Callable[[str], tuple[str, str, dict[str, Any] | None]]
ValidateGraphOperation = Callable[[dict[str, Any], dict[str, Any]], str | None]
WorkGraphNodesById = Callable[[], tuple[dict[str, dict[str, Any]], str | None]]
LoadGraph = Callable[[], tuple[Path, dict[str, dict[str, Any]], dict[str, Path], str | None]]
WriteViews = Callable[[Path, dict[str, dict[str, Any]]], None]
RunGraphCheck = Callable[[], tuple[int, str]]


def fail_payload(control: str, code: str, message: str) -> dict[str, Any]:
    return {"status": "FAIL", "control": control, "findings": [{"level": "FAIL", "code": code, "message": message}]}


def normalize_mission_slug(value: str) -> str | None:
    if not value:
        return None
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        return None
    return slug[:64]


def build_mission_new_id_payload(raw_slug: str, date_str: str) -> dict[str, Any]:
    slug = normalize_mission_slug(raw_slug)
    if not slug:
        return fail_payload(
            "mission.new-id",
            "INVALID_SLUG",
            f"slug must contain at least one ASCII letter/digit: received {raw_slug!r}",
        )
    if not re.fullmatch(r"\d{8}", date_str):
        return fail_payload(
            "mission.new-id",
            "INVALID_DATE",
            f"--date must be YYYYMMDD; received {date_str!r}",
        )
    return {
        "status": "PASS",
        "control": "mission.new-id",
        "mission_id": f"{date_str}-{slug}",
        "date": date_str,
        "slug": slug,
        "received_slug": raw_slug,
        "findings": [],
    }


def initialize_mission_runtime(root: Path, *, replace: bool) -> dict[str, Any]:
    status_path = mission_status_path(root)
    if status_path.exists() and not replace:
        status = load_yaml(status_path)
        if isinstance(status, dict):
            ensure_mission_runtime_dirs(root)
            return {
                "status": "PASS",
                "control": "mission.init",
                "mission_status_path": relpath(root, status_path),
                "noop": True,
                "findings": [
                    {
                        "level": "PASS",
                        "code": "mission_status_exists",
                        "message": "mission-status already initialized; no changes made",
                    }
                ],
            }
        return fail_payload("mission.init", "invalid_mission_status", f"mission-status exists but is not a mapping: {relpath(root, status_path)}")
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(
        "# HarnessV2 mission status — managed by harness-cli; do not hand-edit.\n"
        "# Each top-level key is a mission-id. Use 'harness mission create-slice' to populate.\n",
        encoding="utf-8",
    )
    ensure_mission_runtime_dirs(root)
    return {"status": "PASS", "control": "mission.init", "mission_status_path": relpath(root, status_path), "findings": []}


def build_create_mission_slice_payload(
    *,
    mission_id: str,
    lane_action_name: str,
    primary_nodes: list[str],
    related_nodes: list[str],
    input_nodes: list[str],
    output_nodes: list[str],
    graph_operation: dict[str, Any] | None,
    requested_operation: str = "",
    objective: str = "",
    resolve_lane_stage: ResolveLaneStage,
    validate_graph_operation: ValidateGraphOperation,
    work_graph_nodes_by_id: WorkGraphNodesById,
) -> tuple[dict[str, Any] | None, str | None]:
    lane, stage, action = resolve_lane_stage(lane_action_name)
    if not action:
        return None, f"work_graph.lanes has no lane or stage entry for {lane_action_name}"
    lane_action = build_lane_action_payload(lane, action, mission_id)
    operation = str(lane_action.get("graph_operation") or "")
    if requested_operation and requested_operation != operation:
        profiles = lane_action.get("operation_profiles") if isinstance(lane_action.get("operation_profiles"), dict) else {}
        if requested_operation not in profiles:
            return None, f"requested operation {requested_operation} is not allowed by work_graph.lanes.{lane}/{stage}.operation_profiles"
        operation = requested_operation
    if graph_operation:
        error = validate_graph_operation(graph_operation, action)
        if error:
            return None, error
        operation = str(graph_operation.get("type") or operation)
        input_nodes = unique([*input_nodes, *graph_operation_input_nodes(graph_operation)])
        output_nodes = unique([*output_nodes, *graph_operation_output_nodes(graph_operation)])
    if not operation:
        return None, f"work_graph.lanes.{lane}/{stage}.graph_operation is required"
    nodes_by_id, load_error = work_graph_nodes_by_id()
    if load_error:
        return None, load_error
    for node_id in primary_nodes:
        node = nodes_by_id.get(node_id)
        if node is None:
            return None, f"primary node not found: {node_id}"
        node_lane = str(node.get("lane") or "")
        node_stage = str(node.get("stage") or "")
        if node_lane != lane or node_stage != stage:
            return None, f"{node_id} lane/stage is {node_lane}/{node_stage}, expected {lane}/{stage}"
    primary_nodes = unique([*primary_nodes, *output_nodes])
    if not primary_nodes:
        return None, "at least one --primary-node or graph_operation output node is required"
    payload: dict[str, Any] = {
        "mission_id": mission_id,
        "objective": objective or f"Mission Slice {mission_id}",
        "control_plane": {"lane": lane, "stage": lane_action["stage"]},
        "lane_action": lane_action,
        "work_graph": {
            "primary_nodes": primary_nodes,
            "related_nodes": unique(related_nodes),
            "input_nodes": unique(input_nodes),
            "output_nodes": unique(output_nodes),
        },
        "operation": operation,
        "acceptance_scenarios": [
            "graph operation applied by work-graph script",
            "board/index/tree regenerated from nodes",
        ],
    }
    if graph_operation:
        payload["graph_operation"] = graph_operation
    return payload, None


def write_mission_status_for_slice(
    root: Path,
    mission_id: str,
    slice_payload: dict[str, Any],
    slice_path: Path,
    *,
    today_value: str,
) -> dict[str, Any]:
    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    control_plane = slice_payload.get("control_plane") if isinstance(slice_payload.get("control_plane"), dict) else {}
    work_graph_payload = slice_payload.get("work_graph") if isinstance(slice_payload.get("work_graph"), dict) else {}
    stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
    stage = str(control_plane.get("stage") or "")
    if stage:
        stages.setdefault(stage, "pending")
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    work_graph.update(
        {
            "mission_slice": relpath(root, slice_path),
            "primary_nodes": work_graph_payload.get("primary_nodes") or [],
            "related_nodes": work_graph_payload.get("related_nodes") or [],
            "input_nodes": work_graph_payload.get("input_nodes") or [],
            "output_nodes": work_graph_payload.get("output_nodes") or [],
            "lane": control_plane.get("lane"),
            "stage": stage,
            "operation": slice_payload.get("operation"),
            "lane_action": slice_payload.get("lane_action"),
            "last_gate_report": "",
            "last_operation_manifest": "",
            "last_operation_status": "",
        }
    )
    objective = str(slice_payload.get("objective") or mission_id)
    existing_title = str(entry.get("title") or "")
    generic_title = f"Mission Slice {mission_id}"
    entry.update(
        {
            "title": objective if not existing_title or existing_title == generic_title else existing_title,
            "status": entry.get("status") or "active",
            "started_at": entry.get("started_at") or today_value,
            "completed_at": entry.get("completed_at") or "",
            "current_stage": stage,
            "current_lane": control_plane.get("lane"),
            "stages": stages,
            "work_graph": work_graph,
            "checkpoints_passed": entry.get("checkpoints_passed") if isinstance(entry.get("checkpoints_passed"), list) else [],
        }
    )
    status[mission_id] = entry
    write_yaml(status_path, status)
    return entry


def remove_node_references(node: dict[str, Any], removed: set[str]) -> None:
    for key in ("inputs", "outputs"):
        node[key] = [item for item in as_str_list(node.get(key)) if item not in removed]
    relations = node.get("relations") if isinstance(node.get("relations"), dict) else {}
    for key, value in list(relations.items()):
        if isinstance(value, list):
            relations[key] = [str(item) for item in value if str(item) not in removed]
        elif str(value) in removed:
            relations[key] = None
    node["relations"] = relations


def reset_mission_stage(
    root: Path,
    mission_id: str,
    stage: str,
    primary_nodes: list[str],
    related_nodes: list[str],
    output_node_policy: str,
    preserve_stage_history: bool,
    preserve_checkpoints: bool,
    reason: str,
    *,
    resolve_lane_stage: ResolveLaneStage,
    load_graph: LoadGraph,
    write_views: WriteViews,
    run_graph_check: RunGraphCheck,
    now_value: str,
    today_value: str,
) -> dict[str, Any]:
    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    if not entry:
        return fail_payload("mission.reset_stage", "missing_mission", f"mission not found: {mission_id}")

    target_lane, target_stage, action = resolve_lane_stage(stage)
    if not action:
        return fail_payload("mission.reset_stage", "unknown_stage", f"work_graph.lanes has no lane or stage entry for {stage}")

    slice_path, old_slice = load_mission_slice(root, mission_id, entry)
    old_slice_graph = old_slice.get("work_graph") if isinstance(old_slice.get("work_graph"), dict) else {}
    entry_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    selected_primary_nodes = unique(
        primary_nodes
        or as_str_list(old_slice_graph.get("primary_nodes"))
        or as_str_list(entry_graph.get("primary_nodes"))
    )
    if not selected_primary_nodes:
        return fail_payload("mission.reset_stage", "missing_primary_node", "at least one --primary-node or existing Mission Slice primary node is required")

    graph_root, nodes, paths, load_error = load_graph()
    if load_error:
        return fail_payload("mission.reset_stage", "invalid_work_graph_nodes", load_error)
    missing = [node_id for node_id in selected_primary_nodes if node_id not in nodes]
    if missing:
        return fail_payload("mission.reset_stage", "primary_node_missing", f"primary node not found: {', '.join(missing)}")

    output_nodes = unique(
        [
            *as_str_list(entry_graph.get("output_nodes")),
            *as_str_list(old_slice_graph.get("output_nodes")),
            *(item for node_id in selected_primary_nodes for item in as_str_list(nodes[node_id].get("outputs"))),
        ]
    )
    output_nodes = [node_id for node_id in output_nodes if node_id not in selected_primary_nodes]
    changed_nodes: set[str] = set()

    for node_id in selected_primary_nodes:
        node = nodes[node_id]
        node["lane"] = target_lane
        node["stage"] = target_stage
        node["status"] = "ready"
        node["updated_at"] = now_value
        trace = node.get("trace") if isinstance(node.get("trace"), dict) else {}
        trace.update({"reset_by_mission": mission_id, "reset_to_stage": target_stage, "reset_reason": reason})
        node["trace"] = trace
        changed_nodes.add(node_id)

    existing_output_nodes = [node_id for node_id in output_nodes if node_id in nodes]
    pruned_nodes: list[str] = []
    deferred_nodes: list[str] = []
    if output_node_policy == "prune":
        removed = set(existing_output_nodes)
        for node_id in existing_output_nodes:
            path = paths.get(node_id)
            if path and path.exists():
                path.unlink()
            nodes.pop(node_id, None)
            pruned_nodes.append(node_id)
        for node_id, node in nodes.items():
            remove_node_references(node, removed)
            changed_nodes.add(node_id)
    elif output_node_policy == "defer":
        for node_id in existing_output_nodes:
            node = nodes[node_id]
            node["status"] = "deferred"
            node["updated_at"] = now_value
            trace = node.get("trace") if isinstance(node.get("trace"), dict) else {}
            trace.update({"defer_reason": reason, "reset_by_mission": mission_id, "reset_to_stage": target_stage})
            node["trace"] = trace
            changed_nodes.add(node_id)
            deferred_nodes.append(node_id)

    for node_id in sorted(changed_nodes):
        if node_id in nodes and node_id in paths:
            write_yaml(paths[node_id], nodes[node_id])
    write_views(graph_root, nodes)

    lane_action = build_lane_action_payload(target_lane, action, mission_id)
    slice_payload = {
        "mission_id": mission_id,
        "objective": f"Mission Slice {mission_id}",
        "control_plane": {"lane": target_lane, "stage": target_stage},
        "lane_action": lane_action,
        "work_graph": {
            "primary_nodes": selected_primary_nodes,
            "related_nodes": unique(related_nodes),
            "input_nodes": [],
            "output_nodes": [],
        },
        "operation": lane_action.get("graph_operation") or "",
        "acceptance_scenarios": [
            "mission stage reset by harness mission reset-stage",
            "work graph views regenerated from nodes",
        ],
    }
    write_yaml(slice_path, slice_payload)
    entry = write_mission_status_for_slice(root, mission_id, slice_payload, slice_path, today_value=today_value)
    if preserve_stage_history:
        stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
        entry["stages"] = {**stages, target_stage: "in-progress"}
    else:
        entry["stages"] = {target_stage: "in-progress"}
    if not preserve_checkpoints:
        entry["checkpoints_passed"] = []
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    work_graph.update(
        {
            "last_transaction_id": "",
            "last_transaction_journal": "",
            "reset_stage": target_stage,
            "reset_reason": reason,
            "reset_at": now_value,
            "reset_output_node_policy": output_node_policy,
        }
    )
    entry["work_graph"] = work_graph
    status[mission_id] = entry
    write_yaml(status_path, status)

    log_path = graph_root / "operations.log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "applied_at": now_value,
            "operation": {
                "operation_id": f"{mission_id}__reset_stage__{target_stage}",
                "type": "reset_stage",
                "mission_id": mission_id,
                "to_lane": target_lane,
                "to_stage": target_stage,
                "primary_nodes": selected_primary_nodes,
                "deferred_nodes": deferred_nodes,
                "pruned_nodes": pruned_nodes,
                "reason": reason,
            },
        }, ensure_ascii=False) + "\n")

    graph_check_returncode, graph_check_stdout = run_graph_check()
    graph_check_payload: dict[str, Any] = {}
    if graph_check_stdout.strip().startswith("{"):
        graph_check_payload = json.loads(graph_check_stdout)
    return {
        "status": graph_check_payload.get("status") or ("PASS" if graph_check_returncode == 0 else "FAIL"),
        "control": "mission.reset_stage",
        "mission_id": mission_id,
        "mission_status": entry,
        "mission_slice_path": relpath(root, slice_path),
        "mission_slice": slice_payload,
        "output_node_policy": output_node_policy,
        "deferred_nodes": deferred_nodes,
        "pruned_nodes": pruned_nodes,
        "graph_check": graph_check_payload,
        "findings": graph_check_payload.get("findings") or [],
    }


def create_mission_slice(
    root: Path,
    *,
    mission_id: str,
    lane_action_name: str,
    primary_nodes: list[str],
    related_nodes: list[str],
    input_nodes: list[str],
    output_nodes: list[str],
    graph_operation: dict[str, Any] | None,
    requested_operation: str,
    objective: str,
    replace: bool,
    resolve_lane_stage: ResolveLaneStage,
    validate_graph_operation: ValidateGraphOperation,
    work_graph_nodes_by_id: WorkGraphNodesById,
    today_value: str,
) -> dict[str, Any]:
    status = load_yaml(mission_status_path(root))
    path = mission_slice_path(root, mission_id)
    if not replace and (path.exists() or mission_id in status):
        return fail_payload("mission.create_slice", "mission_slice_exists", f"Mission Slice or mission status already exists for {mission_id}; pass --replace to overwrite")
    payload, error = build_create_mission_slice_payload(
        mission_id=mission_id,
        lane_action_name=lane_action_name,
        primary_nodes=primary_nodes,
        related_nodes=related_nodes,
        input_nodes=input_nodes,
        output_nodes=output_nodes,
        graph_operation=graph_operation,
        requested_operation=requested_operation,
        objective=objective,
        resolve_lane_stage=resolve_lane_stage,
        validate_graph_operation=validate_graph_operation,
        work_graph_nodes_by_id=work_graph_nodes_by_id,
    )
    if error or not payload:
        return fail_payload("mission.create_slice", "invalid_mission_slice", error or "invalid Mission Slice")
    write_yaml(path, payload)
    entry = write_mission_status_for_slice(root, mission_id, payload, path, today_value=today_value)
    return {
        "status": "PASS",
        "control": "mission.create_slice",
        "mission_id": mission_id,
        "mission_slice_path": relpath(root, path),
        "mission_slice": payload,
        "mission_status": entry,
        "findings": [],
    }


def ensure_mission_runtime_dirs(root: Path) -> None:
    for relative in ("missions", "stages", "deliveries", "memory", "traces", "state", "work-graph/nodes", "work-graph/mission-slices"):
        (runtime_harness_root(root) / relative).mkdir(parents=True, exist_ok=True)


def lower_filter(values: list[str] | None) -> set[str]:
    return {str(item).lower() for item in values or [] if str(item)}


def mission_matches_status_filters(entry: dict[str, Any], filters: MissionStatusFilters) -> bool:
    status_filter = lower_filter(filters.status_filter)
    if status_filter and str(entry.get("status") or "").lower() not in status_filter:
        return False
    current_stage_filter = lower_filter(filters.current_stage)
    if current_stage_filter and str(entry.get("current_stage") or "").lower() not in current_stage_filter:
        return False
    stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
    stage_filter = lower_filter(filters.stage)
    stage_status_filter = lower_filter(filters.stage_status)
    if stage_filter:
        matched_stage_values = [str(value).lower() for key, value in stages.items() if str(key).lower() in stage_filter]
        if not matched_stage_values:
            return False
        if stage_status_filter and not any(value in stage_status_filter for value in matched_stage_values):
            return False
    elif stage_status_filter and not any(str(value).lower() in stage_status_filter for value in stages.values()):
        return False
    return True


def build_mission_status_payload(
    root: Path,
    status: dict[str, Any],
    filters: MissionStatusFilters,
    work_graph_nodes_by_id: Callable[[], tuple[dict[str, dict[str, Any]], str | None]],
) -> dict[str, Any]:
    active_ids = active_mission_ids(status)
    open_ids = open_mission_ids(status)
    if filters.mission:
        entry = status.get(filters.mission) if isinstance(status.get(filters.mission), dict) else {}
        if not entry:
            return fail_payload("mission.status", "missing_mission", f"mission not found: {filters.mission}")
        slice_path, mission_slice = load_mission_slice(root, filters.mission, entry)
        nodes_by_id, load_error = work_graph_nodes_by_id()
        findings: list[dict[str, Any]] = []
        if load_error:
            findings.append(finding("BLOCKED", "invalid_work_graph_nodes", load_error, source="work_graph", blocking=True))
        if mission_slice and not mission_entry_operation_completed(entry):
            findings.extend(
                mission_slice_lane_consistency_findings(
                    nodes_by_id,
                    filters.mission,
                    mission_slice,
                    source="mission_slice",
                    blocking=True,
                    path=relpath(root, slice_path),
                )
            )
        return {
            "status": status_from_findings(findings),
            "control": "mission.status",
            "mission_id": filters.mission,
            "mission_status": entry,
            "mission_slice_path": relpath(root, slice_path),
            "mission_slice": mission_slice,
            "findings": findings,
        }

    ids = [mission_id for mission_id, entry in status.items() if isinstance(entry, dict)]
    if filters.active:
        active_set = set(active_ids)
        ids = [mission_id for mission_id in ids if mission_id in active_set]
    if filters.open_only:
        open_set = set(open_ids)
        ids = [mission_id for mission_id in ids if mission_id in open_set]
    ids = [mission_id for mission_id in ids if mission_matches_status_filters(status[mission_id], filters)]
    ids = sorted(ids, key=lambda item: str((status.get(item) or {}).get("started_at") or ""))
    return {
        "status": "PASS",
        "control": "mission.status",
        "missions": {} if filters.ids_only else {mission_id: status[mission_id] for mission_id in ids},
        "mission_ids": ids,
        "active_missions": active_ids,
        "open_missions": open_ids,
        "filters": {
            "active": filters.active,
            "open": filters.open_only,
            "status": filters.status_filter,
            "current_stage": filters.current_stage,
            "stage": filters.stage,
            "stage_status": filters.stage_status,
            "ids_only": filters.ids_only,
        },
        "findings": [],
    }


def update_mission_stage(
    root: Path,
    mission_id: str,
    stage: str,
    stage_status: str,
    work_graph_nodes_by_id: Callable[[], tuple[dict[str, dict[str, Any]], str | None]],
) -> dict[str, Any]:
    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    if not entry:
        return fail_payload("mission.stage", "missing_mission", f"mission not found: {mission_id}")
    slice_path, mission_slice = load_mission_slice(root, mission_id, entry)
    if not mission_slice and (entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}).get("mission_slice"):
        return fail_payload("mission.stage", "missing_mission_slice", f"Mission Slice not found: {relpath(root, slice_path)}")
    if mission_slice:
        control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
        slice_stage = str(control_plane.get("stage") or "")
        if slice_stage and stage != slice_stage:
            return fail_payload(
                "mission.stage",
                "mission_stage_not_current_slice",
                f"mission stage {stage} does not match active Mission Slice {slice_stage}; use gate.advance and create-slice to change lane/stage",
            )
        nodes_by_id, load_error = work_graph_nodes_by_id()
        if load_error:
            return fail_payload("mission.stage", "invalid_work_graph_nodes", load_error)
        consistency = mission_slice_lane_consistency_findings(nodes_by_id, mission_id, mission_slice, source="mission_slice", blocking=True, path=relpath(root, slice_path))
        if consistency:
            return {"status": status_from_findings(consistency), "control": "mission.stage", "mission_id": mission_id, "findings": consistency}
    stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
    stages[stage] = stage_status
    entry.update({"status": entry.get("status") or "active", "current_stage": stage, "stages": stages})
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    work_graph.update({"stage": stage})
    entry["work_graph"] = work_graph
    status[mission_id] = entry
    write_yaml(status_path, status)
    return {"status": "PASS", "control": "mission.stage", "mission_id": mission_id, "mission_status": entry, "findings": []}


def record_translation_warning(root: Path, legacy_value: str, translated_to: str, *, today_value: str) -> None:
    warn_dir = root / "harness-runtime" / "runtime"
    warn_dir.mkdir(parents=True, exist_ok=True)
    warn_path = warn_dir / "translation-warning.yaml"
    existing: list[dict] = []
    if warn_path.exists():
        try:
            data = yaml.safe_load(warn_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                existing = data
        except Exception:
            pass
    existing.append({"legacy_value": legacy_value, "translated_to": translated_to, "recorded_at": today_value})
    warn_path.write_text(yaml.dump(existing, allow_unicode=True), encoding="utf-8")


def close_mission(
    root: Path,
    mission_id: str,
    strategy: str,
    *,
    today_value: str,
    pr_url: str | None = None,
    kept_reason: str | None = None,
) -> dict[str, Any]:
    legacy_alias_used = strategy in LEGACY_CLOSE_ALIAS_MAP
    findings: list[dict] = []
    if legacy_alias_used:
        translated = LEGACY_CLOSE_ALIAS_MAP[strategy]
        findings.append({
            "level": "WARN",
            "code": "legacy_alias_translated",
            "message": (
                f"Legacy close strategy '{strategy}' is deprecated. "
                f"Translated to '{translated}'. "
                "Update your workflow to use the new value directly."
            ),
        })
        record_translation_warning(root, strategy, translated, today_value=today_value)
        strategy = translated

    status_path = mission_status_path(root)
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    if not entry:
        return fail_payload("mission.close", "missing_mission", f"mission not found: {mission_id}")

    mission_status_value, branch_closed = CLOSE_POLICY[strategy]
    entry.update({"status": mission_status_value, "completed_at": today_value, "close_strategy": strategy})
    git_sub = entry.get("git") if isinstance(entry.get("git"), dict) else {}
    git_sub["branch_closed"] = branch_closed
    git_sub["close_strategy"] = strategy
    if strategy == "pr":
        git_sub["pending_pr"] = True
        if pr_url:
            git_sub["pr_url"] = pr_url
    if strategy == "kept" and kept_reason:
        git_sub["kept_reason"] = kept_reason
    entry["git"] = git_sub
    status[mission_id] = entry
    write_yaml(status_path, status)
    return {
        "status": "PASS",
        "control": "mission.close",
        "mission_id": mission_id,
        "strategy": strategy,
        "legacy_alias_used": legacy_alias_used,
        "mission_status": entry,
        "findings": findings,
    }


def complete_mission_stage(
    root: Path,
    mission_id: str,
    stage: str,
    work_graph_nodes_by_id: Callable[[], tuple[dict[str, dict[str, Any]], str | None]],
) -> dict[str, Any]:
    payload = update_mission_stage(root, mission_id, stage, "done", work_graph_nodes_by_id)
    if payload.get("status") == "PASS":
        payload["stage_completion"] = mission_stage_completion_status(root, stage, payload.get("mission_status"))
    return payload
