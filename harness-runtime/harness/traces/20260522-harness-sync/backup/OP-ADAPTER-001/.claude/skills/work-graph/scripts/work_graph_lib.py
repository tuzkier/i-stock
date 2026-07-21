#!/usr/bin/env python3
"""Shared helpers for deterministic Harness Work Graph scripts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to manage Work Graph files") from exc


LANES = [
    "requirement-lane",
    "product-definition-lane",
    "solution-lane",
    "technical-analysis-lane",
    "breakdown-lane",
    "development-lane",
    "verification-lane",
    "delivery-lane",
]

STATUSES = ["ready", "active", "blocked", "deferred", "done"]

LEGACY_LANE_STAGE = {
    "intake": ("requirement-lane", "intake"),
    "discovery": ("requirement-lane", "discovery"),
    "requirements": ("product-definition-lane", "prd"),
    "prd": ("product-definition-lane", "prd"),
    "solution": ("solution-lane", "solution"),
    "interaction": ("product-definition-lane", "interaction"),
    "technical_analysis": ("technical-analysis-lane", "technical_analysis"),
    "breakdown": ("breakdown-lane", "breakdown"),
    "ready_for_dev": ("development-lane", "execute"),
    "in_progress": ("development-lane", "code-review"),
    "review": ("development-lane", "code-review"),
    "verification": ("verification-lane", "verify"),
    "delivery": ("delivery-lane", "delivery"),
    "blocked": ("development-lane", "execute"),
    "deferred": ("delivery-lane", "delivery"),
    "done": ("delivery-lane", "finishing-branch"),
}


@dataclass
class Finding:
    level: str
    code: str
    message: str


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def resolve_graph_root(root: Path) -> Path:
    candidates = [
        root / "harness-runtime" / "harness" / "work-graph",
        root / "package" / "harness-runtime" / "harness" / "work-graph",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def node_files(graph_root: Path) -> list[Path]:
    nodes_root = graph_root / "nodes"
    if not nodes_root.exists():
        return []
    return sorted(path for path in nodes_root.rglob("*.yaml") if path.is_file())


def load_nodes(graph_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Path], list[Finding]]:
    nodes: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    findings: list[Finding] = []
    for path in node_files(graph_root):
        node = load_yaml(path)
        node_id = str(node.get("id") or "")
        if not node_id:
            findings.append(Finding("FAIL", "missing_node_id", f"Node file lacks id: {path}"))
            continue
        if node_id in nodes:
            findings.append(Finding("FAIL", "duplicate_node_id", f"Duplicate node id: {node_id}"))
            continue
        nodes[node_id] = node
        paths[node_id] = path
        for field in ("kind", "title", "lane", "status"):
            if not node.get(field):
                findings.append(Finding("FAIL", "missing_node_field", f"{node_id} missing required field: {field}"))
        legacy_lane = str(node.get("lane") or "")
        legacy_stage = str(node.get("stage") or "")
        if not legacy_stage and legacy_lane in LANES:
            node["stage"] = ""
        if legacy_lane in LEGACY_LANE_STAGE:
            mapped_lane, mapped_stage = LEGACY_LANE_STAGE[legacy_lane]
            node["lane"] = mapped_lane
            node["stage"] = legacy_stage or mapped_stage
    return nodes, paths, findings


def as_str_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def load_runtime_config(root: Path) -> dict[str, Any]:
    for path in (
        root / "harness-runtime" / "config" / "harness.yaml",
        root / "package" / "harness-runtime" / "config" / "harness.yaml",
    ):
        config = load_yaml(path)
        if config:
            return config
    return {}


def work_graph_config(root: Path) -> dict[str, Any]:
    config = load_runtime_config(root)
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    return work_graph


def lane_registry_from_config(config: dict[str, Any], findings: list[Finding] | None = None) -> dict[str, dict[str, Any]]:
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    lanes = work_graph.get("lanes") if isinstance(work_graph.get("lanes"), dict) else {}
    if not lanes:
        if findings is not None:
            findings.append(Finding("FAIL", "missing_lanes", "work_graph.lanes is required; the legacy lane action registry is no longer supported"))
        return {}
    lane_ids = [str(item) for item in lanes]
    stage_ids: list[str] = []
    normalized: dict[str, dict[str, Any]] = {}
    for lane_id, lane in lanes.items():
        lane_id = str(lane_id)
        if not isinstance(lane, dict):
            if findings is not None:
                findings.append(Finding("FAIL", "invalid_lane", f"work_graph.lanes.{lane_id} must be an object"))
            continue
        stages = lane.get("stages")
        if not isinstance(stages, list) or not stages:
            if findings is not None:
                findings.append(Finding("FAIL", "invalid_lane", f"work_graph.lanes.{lane_id}.stages must be a non-empty list"))
            continue
        normalized_stages: list[dict[str, Any]] = []
        for index, stage in enumerate(stages):
            if not isinstance(stage, dict) or not stage.get("stage"):
                if findings is not None:
                    findings.append(Finding("FAIL", "invalid_stage", f"work_graph.lanes.{lane_id}.stages[{index}] must declare stage"))
                continue
            stage_id = str(stage["stage"])
            stage_ids.append(stage_id)
            normalized_stages.append({**stage, "stage": stage_id})
        normalized[lane_id] = {**lane, "stages": normalized_stages}
    overlap = sorted(set(lane_ids) & set(stage_ids))
    if overlap and findings is not None:
        findings.append(Finding("FAIL", "lane_stage_name_overlap", f"lane ids and stage ids must be disjoint: {', '.join(overlap)}"))
    return normalized


def lane_registry(root: Path, findings: list[Finding] | None = None) -> dict[str, dict[str, Any]]:
    return lane_registry_from_config(load_runtime_config(root), findings)


def lane_order_from_config(config: dict[str, Any], findings: list[Finding] | None = None) -> list[str]:
    return list(lane_registry_from_config(config, findings))


def stage_ids_from_lanes(lanes: dict[str, dict[str, Any]]) -> list[str]:
    return [str(stage.get("stage") or "") for lane in lanes.values() for stage in lane.get("stages", []) if isinstance(stage, dict)]


def stage_entry(lanes: dict[str, dict[str, Any]], lane_id: str, stage_id: str) -> tuple[dict[str, Any], int]:
    lane = lanes.get(lane_id) if isinstance(lanes.get(lane_id), dict) else {}
    stages = lane.get("stages") if isinstance(lane.get("stages"), list) else []
    for index, stage in enumerate(stages):
        if isinstance(stage, dict) and str(stage.get("stage") or "") == stage_id:
            return stage, index
    return {}, -1


def prototype_delivery_mode(config: dict[str, Any]) -> str:
    prototype = config.get("prototype") if isinstance(config.get("prototype"), dict) else {}
    mode = str(prototype.get("delivery_mode") or "interactive_prototype")
    return mode if mode else "interactive_prototype"


def frontend_project_root(config: dict[str, Any]) -> str:
    prototype = config.get("prototype") if isinstance(config.get("prototype"), dict) else {}
    frontend = prototype.get("frontend_engineering") if isinstance(prototype.get("frontend_engineering"), dict) else {}
    return str(frontend.get("frontend_project_root") or "apps/web")


def format_config_value(value: Any, config: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return value.replace("{frontend_project_root}", frontend_project_root(config))
    if isinstance(value, list):
        return [format_config_value(item, config) for item in value]
    if isinstance(value, dict):
        return {key: format_config_value(item, config) for key, item in value.items()}
    return value


def apply_stage_mode_variant(stage: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    variants = stage.get("mode_variants")
    if not isinstance(variants, dict):
        return stage
    mode = prototype_delivery_mode(config)
    variant = variants.get(mode)
    if not isinstance(variant, dict):
        return stage
    merged = {**stage, **format_config_value(variant, config)}
    merged["mode_variant"] = mode
    merged["mode_variants"] = variants
    return merged


def lane_of_stage(config: dict[str, Any], stage_id: str) -> str:
    lanes = lane_registry_from_config(config)
    for lane_id, lane in lanes.items():
        if stage_id in [str(stage.get("stage") or "") for stage in lane.get("stages", []) if isinstance(stage, dict)]:
            return lane_id
    return ""


def stages_in_lane(config: dict[str, Any], lane_id: str) -> list[str]:
    lane = lane_registry_from_config(config).get(lane_id, {})
    return [str(stage.get("stage") or "") for stage in lane.get("stages", []) if isinstance(stage, dict)]


def next_lane(config: dict[str, Any], lane_id: str) -> str:
    lane_ids = lane_order_from_config(config)
    try:
        index = lane_ids.index(lane_id)
    except ValueError:
        return ""
    return lane_ids[index + 1] if index + 1 < len(lane_ids) else ""


def next_stage(config: dict[str, Any], lane_id: str, stage_id: str) -> tuple[str, str]:
    lanes = lane_registry_from_config(config)
    lane = lanes.get(lane_id, {})
    stage_entries = [stage for stage in lane.get("stages", []) if isinstance(stage, dict)]
    stages = [str(stage.get("stage") or "") for stage in stage_entries]
    try:
        index = stages.index(stage_id)
    except ValueError:
        return "", ""
    for next_entry in stage_entries[index + 1:]:
        return lane_id, str(next_entry.get("stage") or "")
    target_lane = next_lane(config, lane_id)
    target_stages = stages_in_lane(config, target_lane) if target_lane else []
    return target_lane, target_stages[0] if target_stages else ""


def default_operation_profiles(config: dict[str, Any], lane_id: str, stage_id: str) -> tuple[str, dict[str, dict[str, Any]]]:
    target_lane, target_stage = next_stage(config, lane_id, stage_id)
    if target_lane == lane_id and target_stage:
        profiles = {"advance_stage": {"to_stage": target_stage}}
        default_operation = "advance_stage"
        lanes = lane_registry_from_config(config)
        stage_entries = [stage for stage in (lanes.get(lane_id, {}) or {}).get("stages", []) if isinstance(stage, dict)]
        stages = [str(stage.get("stage") or "") for stage in stage_entries]
        try:
            current_index = stages.index(stage_id)
        except ValueError:
            current_index = -1
        next_entry = stage_entries[current_index + 1] if current_index >= 0 and current_index + 1 < len(stage_entries) else {}
        if isinstance(next_entry, dict) and next_entry.get("condition"):
            fallback_lane = next_lane(config, lane_id)
            fallback_stages = stages_in_lane(config, fallback_lane) if fallback_lane else []
            fallback_stage = fallback_stages[0] if fallback_stages else ""
            if fallback_lane and fallback_stage:
                profiles["advance_lane"] = {"to_lane": fallback_lane, "to_stage": fallback_stage}
    elif target_lane and target_stage:
        profiles = {"advance_lane": {"to_lane": target_lane, "to_stage": target_stage}}
        default_operation = "advance_lane"
    else:
        profiles = {}
        default_operation = "advance_stage"

    if stage_id == "technical_analysis":
        profiles["merge_nodes"] = {
            "default_target_lane": "breakdown-lane",
            "default_target_stage": "breakdown",
            "allowed_target_kinds": ["technical_design", "task"],
        }
        profiles["batch"] = {"allowed_operations": ["advance_lane", "merge_nodes"]}
    if stage_id == "solution":
        # Compatibility for existing solution-stage graph slicing. New task
        # planning should prefer breakdown, but accepted solution updates can
        # still split follow-up work without a second registry.
        profiles["split_node"] = {
            "default_child_lane": "development-lane",
            "default_child_stage": "execute",
            "allowed_child_kinds": ["task", "bug"],
        }
        profiles["batch"] = {"allowed_operations": ["advance_lane", "split_node"]}
    if stage_id == "breakdown":
        profiles["split_node"] = {
            "default_child_lane": "development-lane",
            "default_child_stage": "execute",
            "allowed_child_kinds": ["task", "bug"],
        }
        profiles["batch"] = {"allowed_operations": ["advance_lane", "split_node"]}

    if profiles:
        return default_operation, profiles
    if target_lane and target_stage:
        return "advance_lane", {"advance_lane": {"to_lane": target_lane, "to_stage": target_stage}}
    return "advance_stage", {}


def lane_stage_for_node(config: dict[str, Any], node: dict[str, Any], findings: list[Finding] | None = None) -> tuple[str, str, dict[str, Any]]:
    lanes = lane_registry_from_config(config, findings)
    lane_id = str(node.get("lane") or "")
    stage_id = str(node.get("stage") or "")
    if lane_id in LEGACY_LANE_STAGE:
        mapped_lane, mapped_stage = LEGACY_LANE_STAGE[lane_id]
        lane_id = mapped_lane
        stage_id = stage_id or mapped_stage
    stage, _index = stage_entry(lanes, lane_id, stage_id)
    if not stage and findings is not None:
        findings.append(Finding("FAIL", "stage_not_in_lane", f"node {node.get('id') or '<unknown>'} stage {stage_id or '<missing>'} is not registered in lane {lane_id or '<missing>'}"))
    stage = apply_stage_mode_variant(stage, config)
    graph_operation, profiles = default_operation_profiles(config, lane_id, stage_id)
    action = {
        **stage,
        "stage": stage_id,
        "graph_operation": str(stage.get("graph_operation") or graph_operation),
        "operation_profiles": stage.get("operation_profiles") if isinstance(stage.get("operation_profiles"), dict) else profiles,
        "accepts_kinds": as_str_list((lanes.get(lane_id) or {}).get("accepts_kinds")),
    }
    return lane_id, stage_id, action


def format_control_value(value: Any, mission_id: str) -> Any:
    if isinstance(value, str):
        return value.replace("{mission_id}", mission_id)
    if isinstance(value, list):
        return [format_control_value(item, mission_id) for item in value]
    if isinstance(value, dict):
        return {key: format_control_value(item, mission_id) for key, item in value.items()}
    return value


def operation_profiles(action: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles = action.get("operation_profiles")
    if not isinstance(profiles, dict):
        return {}
    return {str(name): payload for name, payload in profiles.items() if isinstance(payload, dict)}


def lane_allowed_operations(action: dict[str, Any]) -> list[str]:
    profiles = operation_profiles(action)
    return list(profiles)


def lane_action_to_lane(action: dict[str, Any]) -> str:
    if action.get("to_lane"):
        return str(action.get("to_lane"))
    default_operation = str(action.get("graph_operation") or "")
    profile = operation_profiles(action).get(default_operation, {})
    if profile.get("to_lane"):
        return str(profile["to_lane"])
    return ""


def lane_action_snapshot(lane: str, action: dict[str, Any], mission_id: str) -> dict[str, Any]:
    profiles = operation_profiles(action)
    default_operation = str(action.get("graph_operation") or "")
    snapshot = {
        "lane": str(lane),
        "stage": str(action.get("stage") or ""),
        "graph_operation": default_operation,
        "operation_profiles": format_control_value(profiles, mission_id),
        "allowed_graph_operations": lane_allowed_operations(action),
        "output_artifact": format_control_value(action.get("output_artifact"), mission_id),
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


def lane_action_registry_from_config(config: dict[str, Any], findings: list[Finding] | None = None) -> dict[str, dict[str, Any]]:
    # Compatibility shim for callers that still ask for a lane-action registry.
    # The persisted source of truth is work_graph.lanes; this function exposes
    # the first stage in each lane under the lane id.
    lanes = lane_registry_from_config(config, findings)
    actions: dict[str, dict[str, Any]] = {}
    for lane_id, lane in lanes.items():
        stages = lane.get("stages") if isinstance(lane.get("stages"), list) else []
        if not stages:
            continue
        action = {**stages[0], "accepts_kinds": as_str_list(lane.get("accepts_kinds"))}
        graph_operation, profiles = default_operation_profiles(config, lane_id, str(action.get("stage") or ""))
        action.setdefault("graph_operation", graph_operation)
        action.setdefault("operation_profiles", profiles)
        validate_lane_action(lane_id, action, findings)
        normalized = {**action}
        normalized["allowed_graph_operations"] = lane_allowed_operations(normalized)
        actions[lane_id] = normalized
    return actions


def lane_action_registry(root: Path, findings: list[Finding] | None = None) -> dict[str, dict[str, Any]]:
    return lane_action_registry_from_config(load_runtime_config(root), findings)


def validate_lane_action(lane: str, action: dict[str, Any], findings: list[Finding] | None = None) -> bool:
    valid = True

    def fail(message: str) -> None:
        nonlocal valid
        valid = False
        if findings is not None:
            findings.append(Finding("FAIL", "invalid_lane_action", message))

    for field in ("stage", "graph_operation"):
        if action.get(field) in (None, ""):
            fail(f"work_graph.lanes.{lane}.stage missing {field}")

    profiles = operation_profiles(action)
    allowed = lane_allowed_operations(action)
    default_operation = str(action.get("graph_operation") or "")
    if not allowed:
        fail(f"work_graph.lanes.{lane}.stage.operation_profiles is required")
    if default_operation and default_operation not in allowed:
        fail(f"work_graph.lanes.{lane}.stage.operation_profiles must include graph_operation")
    if action.get("allowed_graph_operations") is not None:
        fail(f"work_graph.lanes.{lane}.stage.allowed_graph_operations is derived from operation_profiles and must not be configured")

    accepts_kinds = action.get("accepts_kinds")
    if accepts_kinds is not None and not as_str_list(accepts_kinds):
        fail(f"work_graph.lanes.{lane}.accepts_kinds must be a non-empty string list")
    for operation_name, profile in profiles.items():
        if operation_name == "split_node" and profile.get("allowed_child_kinds") is not None and not as_str_list(profile.get("allowed_child_kinds")):
            fail(f"work_graph.lanes.{lane}.operation_profiles.split_node.allowed_child_kinds must be a non-empty string list")
        if operation_name == "merge_nodes" and profile.get("allowed_target_kinds") is not None and not as_str_list(profile.get("allowed_target_kinds")):
            fail(f"work_graph.lanes.{lane}.operation_profiles.merge_nodes.allowed_target_kinds must be a non-empty string list")
        if operation_name == "batch" and profile.get("allowed_child_operations") is not None and not as_str_list(profile.get("allowed_child_operations")):
            fail(f"work_graph.lanes.{lane}.operation_profiles.batch.allowed_child_operations must be a non-empty string list")
    return valid


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def operation_type_tree(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    values = [operation_type] if operation_type else []
    if operation_type == "batch" and isinstance(operation.get("operations"), list):
        for child in operation["operations"]:
            if isinstance(child, dict):
                values.extend(operation_type_tree(child))
    return values


def validate_graph_operation_structure(operation: dict[str, Any], path: str = "graph_operation") -> list[str]:
    operation_type = str(operation.get("type") or "")
    if not operation_type:
        return [f"{path}.type is required"]
    if operation_type != "batch":
        return []
    operations = operation.get("operations")
    if not isinstance(operations, list) or not operations:
        return [f"{path}.operations must be a non-empty list"]
    errors: list[str] = []
    for index, child in enumerate(operations, start=1):
        if not isinstance(child, dict):
            errors.append(f"{path}.operations[{index}] must be an object")
            continue
        errors.extend(validate_graph_operation_structure(child, f"{path}.operations[{index}]"))
    return errors


def graph_operation_output_nodes(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    outputs: list[str] = []
    if operation_type == "create_node":
        target = operation.get("target")
        if isinstance(target, dict):
            outputs.append(str(target.get("id") or ""))
    elif operation_type == "split_node":
        children = operation.get("children")
        if isinstance(children, list):
            outputs.extend(str(item.get("id") or "") for item in children if isinstance(item, dict))
    elif operation_type == "merge_nodes":
        target = operation.get("target")
        if isinstance(target, dict):
            outputs.append(str(target.get("id") or ""))
    elif operation_type == "batch":
        for child in operation.get("operations") or []:
            if isinstance(child, dict):
                outputs.extend(graph_operation_output_nodes(child))
    return unique([item for item in outputs if item])


def graph_operation_input_nodes(operation: dict[str, Any]) -> list[str]:
    operation_type = str(operation.get("type") or "")
    inputs: list[str] = []
    if operation_type in {"advance_stage", "advance_lane", "split_node", "block_node", "defer_node", "supersede_node"}:
        inputs.append(str(operation.get("node_id") or ""))
    if operation_type in {"merge_nodes", "supersede_node"}:
        inputs.extend(str(item) for item in operation.get("node_ids") or [])
    if operation_type == "batch":
        for child in operation.get("operations") or []:
            if isinstance(child, dict):
                inputs.extend(graph_operation_input_nodes(child))
    return unique([item for item in inputs if item])


def validate_operation_against_profile(operation: dict[str, Any], action: dict[str, Any], findings: list[Finding], path: str = "graph_operation") -> None:
    operation_type = str(operation.get("type") or "")
    if not operation_type:
        findings.append(Finding("FAIL", "missing_graph_operation_type", f"{path} missing type"))
        return
    allowed = lane_allowed_operations(action)
    if allowed and operation_type not in allowed:
        findings.append(Finding("FAIL", "slice_lane_operation_not_allowed", f"{path}.type {operation_type} is not allowed by lane action operation profiles: {', '.join(allowed)}"))
        return
    profiles = operation_profiles(action)
    profile = profiles.get(operation_type, {}) if profiles else {}

    if operation_type == "advance_stage":
        expected_to_stage = str(profile.get("to_stage") or "")
        actual_to_stage = str(operation.get("to_stage") or "")
        if expected_to_stage and actual_to_stage and actual_to_stage != expected_to_stage:
            findings.append(Finding("FAIL", "graph_operation_stage_mismatch", f"{path}.to_stage {actual_to_stage} does not match lane stage profile to_stage {expected_to_stage}"))
        return

    if operation_type == "advance_lane":
        expected_to_lane = str(profile.get("to_lane") or action.get("to_lane") or "")
        actual_to_lane = str(operation.get("to_lane") or "")
        if expected_to_lane and actual_to_lane and actual_to_lane != expected_to_lane:
            findings.append(Finding("FAIL", "graph_operation_lane_mismatch", f"{path}.to_lane {actual_to_lane} does not match lane action profile to_lane {expected_to_lane}"))
        return

    if operation_type == "split_node":
        allowed_child_kinds = as_str_list(profile.get("allowed_child_kinds"))
        default_child_lane_by_kind = profile.get("default_child_lane_by_kind") if isinstance(profile.get("default_child_lane_by_kind"), dict) else {}
        default_child_lane = str(profile.get("default_child_lane") or "")
        children = operation.get("children")
        if not isinstance(children, list) or not children:
            return
        for index, child in enumerate(children, start=1):
            if not isinstance(child, dict):
                continue
            child_kind = str(child.get("kind") or "")
            child_lane = str(child.get("lane") or "")
            if allowed_child_kinds and child_kind not in allowed_child_kinds:
                findings.append(Finding("FAIL", "graph_operation_child_kind_not_allowed", f"{path}.children[{index}].kind {child_kind} is not allowed; expected one of {', '.join(allowed_child_kinds)}"))
            expected_lane = str(default_child_lane_by_kind.get(child_kind) or default_child_lane or "")
            if expected_lane and child_lane and child_lane != expected_lane:
                findings.append(Finding("FAIL", "graph_operation_child_lane_mismatch", f"{path}.children[{index}].lane {child_lane} does not match default lane {expected_lane} for kind {child_kind}"))
        return

    if operation_type == "merge_nodes":
        target = operation.get("target")
        if not isinstance(target, dict):
            return
        target_kind = str(target.get("kind") or "")
        target_lane = str(target.get("lane") or "")
        allowed_target_kinds = as_str_list(profile.get("allowed_target_kinds"))
        if allowed_target_kinds and target_kind not in allowed_target_kinds:
            findings.append(Finding("FAIL", "graph_operation_target_kind_not_allowed", f"{path}.target.kind {target_kind} is not allowed; expected one of {', '.join(allowed_target_kinds)}"))
        default_target_lane_by_kind = profile.get("default_target_lane_by_kind") if isinstance(profile.get("default_target_lane_by_kind"), dict) else {}
        expected_lane = str(default_target_lane_by_kind.get(target_kind) or profile.get("default_target_lane") or "")
        if expected_lane and target_lane and target_lane != expected_lane:
            findings.append(Finding("FAIL", "graph_operation_target_lane_mismatch", f"{path}.target.lane {target_lane} does not match default lane {expected_lane} for kind {target_kind}"))
        return

    if operation_type in {"block_node", "defer_node"}:
        expected_lane = str(profile.get("target_lane") or "")
        actual_lane = str(operation.get("to_lane") or "")
        if expected_lane and actual_lane and actual_lane != expected_lane:
            findings.append(Finding("FAIL", "graph_operation_lane_mismatch", f"{path}.to_lane {actual_lane} does not match lane action profile target_lane {expected_lane}"))
        return

    if operation_type == "supersede_node":
        expected_lane = str(profile.get("target_lane") or "")
        actual_lane = str(operation.get("to_lane") or "")
        if expected_lane and actual_lane and actual_lane != expected_lane:
            findings.append(Finding("FAIL", "graph_operation_lane_mismatch", f"{path}.to_lane {actual_lane} does not match lane action profile target_lane {expected_lane}"))
        return

    if operation_type == "batch":
        operations = operation.get("operations")
        if not isinstance(operations, list) or not operations:
            findings.append(Finding("FAIL", "invalid_batch_operation", f"{path}.operations must be a non-empty list"))
            return
        child_allowed = as_str_list(profile.get("allowed_child_operations")) or as_str_list(profile.get("allowed_operations")) or [item for item in allowed if item != "batch"]
        for index, child in enumerate(operations, start=1):
            if not isinstance(child, dict):
                findings.append(Finding("FAIL", "invalid_batch_operation", f"{path}.operations[{index}] must be an object"))
                continue
            child_type = str(child.get("type") or "")
            if child_allowed and child_type not in child_allowed:
                findings.append(Finding("FAIL", "slice_lane_operation_not_allowed", f"{path}.operations[{index}].type {child_type} is not allowed by batch profile: {', '.join(child_allowed)}"))
                continue
            validate_operation_against_profile(child, action, findings, f"{path}.operations[{index}]")


def sorted_node_ids(nodes: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(nodes)


def build_views(nodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lanes: dict[str, list[str]] = {lane: [] for lane in LANES}
    by_kind: dict[str, list[str]] = {}
    by_status: dict[str, list[str]] = {}
    index_nodes: dict[str, dict[str, Any]] = {}
    relation_inputs: dict[str, list[str]] = {}
    relation_outputs: dict[str, list[str]] = {}
    relation_summary: dict[str, dict[str, list[str]]] = {
        "depends_on": {},
        "conflicts_with": {},
        "duplicates": {},
        "supersedes": {},
    }

    for node_id in sorted_node_ids(nodes):
        node = nodes[node_id]
        lane = str(node.get("lane") or "")
        lanes.setdefault(lane, []).append(node_id)
        kind = str(node.get("kind") or "")
        status = str(node.get("status") or "")
        by_kind.setdefault(kind, []).append(node_id)
        by_status.setdefault(status, []).append(node_id)
        inputs = as_str_list(node.get("inputs"))
        outputs = as_str_list(node.get("outputs"))
        relation_inputs[node_id] = inputs
        relation_outputs[node_id] = outputs
        relations = node.get("relations") if isinstance(node.get("relations"), dict) else {}
        for key in relation_summary:
            values = as_str_list(relations.get(key))
            if values:
                relation_summary[key][node_id] = values
        index_nodes[node_id] = {
            "kind": kind,
            "title": str(node.get("title") or ""),
            "lane": lane,
            "status": status,
            "priority": node.get("priority"),
            "updated_at": node.get("updated_at"),
            "inputs": inputs,
            "outputs": outputs,
        }
    return {
        "index": {"schema_version": 1, "generated": True, "generated_at": now(), "nodes": index_nodes},
        "board": {"schema_version": 1, "generated": True, "generated_at": now(), "lanes": lanes},
        "by_lane": {"schema_version": 1, "generated": True, "lanes": lanes},
        "by_kind": {"schema_version": 1, "generated": True, "kinds": {key: sorted(value) for key, value in sorted(by_kind.items())}},
        "by_status": {"schema_version": 1, "generated": True, "statuses": {key: sorted(value) for key, value in sorted(by_status.items())}},
        "by_relation": {
            "schema_version": 1,
            "generated": True,
            "inputs": relation_inputs,
            "outputs": relation_outputs,
            "relations": relation_summary,
        },
    }


def build_tree(nodes: dict[str, dict[str, Any]], root_id: str, stack: tuple[str, ...] = ()) -> dict[str, Any]:
    node = nodes[root_id]
    children: list[dict[str, Any]] = []
    if root_id not in stack:
        for child_id in as_str_list(node.get("outputs")):
            if child_id in nodes:
                children.append(build_tree(nodes, child_id, (*stack, root_id)))
    return {
        "id": root_id,
        "kind": node.get("kind"),
        "title": node.get("title"),
        "lane": node.get("lane"),
        "status": node.get("status"),
        "children": children,
    }


def tree_roots(nodes: dict[str, dict[str, Any]]) -> list[str]:
    roots = [node_id for node_id, node in nodes.items() if str(node.get("kind")) == "epic"]
    if roots:
        return sorted(roots)
    return sorted(node_id for node_id, node in nodes.items() if not as_str_list(node.get("inputs")))


def write_views(graph_root: Path, nodes: dict[str, dict[str, Any]]) -> None:
    views = build_views(nodes)
    write_yaml(graph_root / "_index.yaml", views["index"])
    write_yaml(graph_root / "boards" / "main.yaml", views["board"])
    write_yaml(graph_root / "indexes" / "by-lane.yaml", views["by_lane"])
    write_yaml(graph_root / "indexes" / "by-kind.yaml", views["by_kind"])
    write_yaml(graph_root / "indexes" / "by-status.yaml", views["by_status"])
    write_yaml(graph_root / "indexes" / "by-relation.yaml", views["by_relation"])
    for root_id in tree_roots(nodes):
        write_yaml(
            graph_root / "trees" / f"{root_id}.yaml",
            {"schema_version": 1, "generated": True, "root": root_id, "tree": [build_tree(nodes, root_id)]},
        )


def finding_dict(item: Finding) -> dict[str, str]:
    return {"level": item.level, "code": item.code, "message": item.message}


def status_from_findings(findings: list[Finding]) -> str:
    if any(item.level == "FAIL" for item in findings):
        return "FAIL"
    if any(item.level == "WARN" for item in findings):
        return "WARN"
    return "PASS"
