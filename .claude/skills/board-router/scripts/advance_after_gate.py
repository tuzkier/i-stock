#!/usr/bin/env python3
"""Apply a Mission Slice graph operation after Stage Gate allows continuation."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

WORK_GRAPH_SCRIPTS = Path(__file__).resolve().parents[2] / "work-graph" / "scripts"
if str(WORK_GRAPH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))

# package/common 根：用于导入 harness_cli_core 的 domain SSOT（reviewer 上游归因信号、
# reset_mission_stage 回退原语等）。board-router 脚本默认只把 work-graph scripts 入 path，
# 这里防御性地补上 common 根，保证脚本独立执行时也能消费 domain 函数。
COMMON_ROOT = Path(__file__).resolve().parents[3]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from apply_graph_operation import run as apply_graph_operation
from work_graph_lib import Finding, as_str_list, finding_dict, load_yaml, resolve_graph_root, status_from_findings, write_yaml
from work_graph_lib import lane_allowed_operations, operation_profiles, lane_stage_for_node, validate_operation_against_profile

# reviewer 上游归因信号（domain SSOT，见 harness_cli_core/domain/contracts.py）。
# 跨包 import 不稳时降级为 None，gate-block 出口据此完全保持原有死路行为（非破坏）。
try:
    from harness_cli_core.domain.contracts import reviewer_upstream_rollback_signal as _reviewer_upstream_rollback_signal
except Exception:  # pragma: no cover - 跨包 import 兜底，绝不影响既有路径
    _reviewer_upstream_rollback_signal = None  # type: ignore[assignment]

# reviewer 澄清归因信号（domain SSOT）：根因是"人从未提供的事实"，任何重导补不出，
# 必须暂停问人。与 upstream 回退正交；同时存在时先问人（信息缺口是回退的前提）。
try:
    from harness_cli_core.domain.contracts import reviewer_clarification_signal as _reviewer_clarification_signal
except Exception:  # pragma: no cover - 跨包 import 兜底，绝不影响既有路径
    _reviewer_clarification_signal = None  # type: ignore[assignment]

# 原型必要性判定模型（2026-06 重设计）：interaction 默认进入、阶段内判定，ui_task 默认 True，
# 跳过由阶段内 not_needed 轻产物 + gate 豁免承载。不再在此前置读 PRD UIC 做门控。


CONTINUE_DECISIONS = {"continue"}
# reset_stage 纳入受支持的 Mission Slice operation 集合：携带 target_stage 的回退操作
# 不再被判为 unsupported_slice_operation。它由 reset_mission_stage 原语执行（独立于
# apply_graph_operation 的 create/advance/split/merge 处理链），见 build_reset_stage_operation。
SUPPORTED_SLICE_OPERATIONS = {"advance_stage", "advance_lane", "split_node", "merge_nodes", "block_node", "defer_node", "supersede_node", "batch", "reset_stage"}
# ui_task 条件（是否进 interaction / 原型阶段）不再用关键词扫描判定——改读 PRD 用例模型
# 界面承载要求(UIC) 的 reasoned 结论，见 condition_met + harness_cli_core.domain.interaction
# .interaction_required_decision。关键词表已退役。


def load_payload(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return load_yaml(path)
        return data if isinstance(data, dict) else {}
    return load_yaml(path)


def load_control_contract(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    payload = load_yaml(path)
    contract = payload.get("control_contract")
    return contract if isinstance(contract, dict) else {}


def load_runtime_config(root: Path) -> dict[str, Any]:
    return load_yaml(root / "harness-runtime" / "config" / "harness.yaml") or load_yaml(root / "package" / "harness-runtime" / "config" / "harness.yaml")


def as_str_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def artifact_text(root: Path, mission_id: str) -> str:
    paths = [
        root / "harness-runtime" / "harness" / "missions" / mission_id / "mission-contract.md",
        root / "harness-runtime" / "harness" / "stages" / mission_id / "product" / "product-definition.md",
        root / "harness-runtime" / "harness" / "stages" / mission_id / "product" / "product-domain-model.md",
        root / "harness-runtime" / "harness" / "stages" / mission_id / "product" / "product-evidence.md",
        root / "harness-runtime" / "harness" / "stages" / mission_id / "solution.md",
        root / "harness-runtime" / "harness" / "stages" / mission_id / "tech-design.md",
        root / "harness-runtime" / "harness" / "stages" / mission_id / "contracts" / "prd.contract.yaml",
        root / "harness-runtime" / "harness" / "stages" / mission_id / "contracts" / "tech-design.contract.yaml",
    ]
    chunks: list[str] = []
    for path in paths:
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def condition_flags(mission_slice: dict[str, Any], contract: dict[str, Any] | None) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    for source in (mission_slice, contract or {}):
        raw = source.get("conditions") if isinstance(source, dict) else None
        if isinstance(raw, dict):
            flags.update({str(key): bool(value) for key, value in raw.items()})
        elif isinstance(raw, list):
            flags.update({str(item): True for item in raw})
        raw = source.get("condition_flags") if isinstance(source, dict) else None
        if isinstance(raw, dict):
            flags.update({str(key): bool(value) for key, value in raw.items()})
    return flags


def condition_met(root: Path, mission_id: str, condition: str, mission_slice: dict[str, Any], contract: dict[str, Any] | None) -> bool:
    # 显式覆盖优先（Mission Slice / 契约的 conditions / condition_flags 是合法人工口子）。
    flags = condition_flags(mission_slice, contract)
    if condition in flags:
        return flags[condition]
    if condition == "ui_task":
        # 原型必要性判定模型（2026-06 重设计）：每个 mission **默认进入 interaction 阶段**，
        # 由 interaction-designer 在阶段内 Step 0 判断要不要原型；不再用 PRD 用例模型 UIC
        # 前置门控、不扫关键词。因此 ui_task 默认 True（进入）；显式 conditions/condition_flags
        # 仍可人工覆盖（上面已优先处理）。判"否"的跳过由阶段内 not_needed 轻产物 + gate 豁免承载。
        return True
    return False


def satisfied_conditional_stage(
    root: Path,
    mission_id: str,
    lane: str,
    stage: str,
    mission_slice: dict[str, Any],
    contract: dict[str, Any] | None,
) -> str:
    config = load_runtime_config(root)
    lanes = ((config.get("work_graph") or {}).get("lanes") or {}) if isinstance(config.get("work_graph"), dict) else {}
    lane_config = lanes.get(lane) if isinstance(lanes.get(lane), dict) else {}
    stages = lane_config.get("stages") if isinstance(lane_config.get("stages"), list) else []
    stage_ids = [str(item.get("stage") or "") for item in stages if isinstance(item, dict)]
    try:
        index = stage_ids.index(stage)
    except ValueError:
        return ""
    for entry in stages[index + 1:]:
        if not isinstance(entry, dict):
            continue
        next_stage = str(entry.get("stage") or "")
        condition = str(entry.get("condition") or "")
        if not condition:
            return ""
        if condition_met(root, mission_id, condition, mission_slice, contract):
            return next_stage
    return ""


def configured_next_conditional_stage(root: Path, lane: str, stage: str) -> str:
    config = load_runtime_config(root)
    lanes = ((config.get("work_graph") or {}).get("lanes") or {}) if isinstance(config.get("work_graph"), dict) else {}
    lane_config = lanes.get(lane) if isinstance(lanes.get(lane), dict) else {}
    stages = lane_config.get("stages") if isinstance(lane_config.get("stages"), list) else []
    stage_ids = [str(item.get("stage") or "") for item in stages if isinstance(item, dict)]
    try:
        index = stage_ids.index(stage)
    except ValueError:
        return ""
    for entry in stages[index + 1:]:
        if not isinstance(entry, dict):
            continue
        if entry.get("condition"):
            return str(entry.get("stage") or "")
        return ""
    return ""


def normalize_checkpoint_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value else []
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            names.append(item)
        elif isinstance(item, dict):
            name = str(item.get("stage") or item.get("checkpoint") or item.get("id") or "")
            if name:
                names.append(name)
    result: list[str] = []
    for name in names:
        if name not in result:
            result.append(name)
    return result


def registry_lane_action(root: Path, mission_slice: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    slice_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    lane = str(control_plane.get("lane") or slice_action.get("lane") or "")
    stage = str(control_plane.get("stage") or slice_action.get("stage") or "")
    node = {"id": "<mission-slice>", "lane": lane, "stage": stage}
    config = load_runtime_config(root)
    lane, stage, action = lane_stage_for_node(config, node, findings)
    if not action:
        findings.append(Finding("FAIL", "missing_lane_stage_registry_entry", f"work_graph.lanes has no entry for Mission Slice {lane}/{stage}"))
        return {}
    return {
        **action,
        "stage": action.get("stage"),
        "lane": lane,
        "graph_operation": action.get("graph_operation"),
        "allowed_graph_operations": action.get("allowed_graph_operations"),
    }


def apply_conditional_stage_override(
    root: Path,
    mission_id: str,
    mission_slice: dict[str, Any],
    lane_action: dict[str, Any],
    operation_type: str,
    contract: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    slice_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    lane = str(lane_action.get("lane") or control_plane.get("lane") or slice_action.get("lane") or "")
    stage = str(lane_action.get("stage") or control_plane.get("stage") or slice_action.get("stage") or "")
    conditional_stage = satisfied_conditional_stage(root, mission_id, lane, stage, mission_slice, contract)
    if not conditional_stage or operation_type not in {"advance_lane", "advance_stage"}:
        if operation_type == "advance_stage":
            profiles = operation_profiles(lane_action)
            advance_stage_profile = profiles.get("advance_stage") if isinstance(profiles.get("advance_stage"), dict) else {}
            advance_lane_profile = profiles.get("advance_lane") if isinstance(profiles.get("advance_lane"), dict) else {}
            configured_stage = configured_next_conditional_stage(root, lane, stage)
            if (
                configured_stage
                and str(advance_stage_profile.get("to_stage") or "") == configured_stage
                and advance_lane_profile.get("to_lane")
                and advance_lane_profile.get("to_stage")
            ):
                return {**lane_action, "graph_operation": "advance_lane"}, "advance_lane"
        return lane_action, operation_type
    overridden = {
        **lane_action,
        "graph_operation": "advance_stage",
        "allowed_graph_operations": ["advance_stage"],
        "operation_profiles": {"advance_stage": {"to_stage": conditional_stage}},
    }
    return overridden, "advance_stage"


def lane_allows_operation(lane_action: dict[str, Any], operation_type: str) -> bool:
    allowed = lane_allowed_operations(lane_action)
    if allowed:
        return operation_type in allowed
    lane_operation = str(lane_action.get("graph_operation") or "")
    return not lane_operation or lane_operation == operation_type


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def lane_action_with_implicit_batch(lane_action: dict[str, Any], child_operation: str) -> dict[str, Any]:
    profiles = operation_profiles(lane_action)
    batch_profile = profiles.get("batch") if isinstance(profiles.get("batch"), dict) else {}
    child_allowed = unique([
        *as_str_list(batch_profile.get("allowed_operations")),
        *as_str_list(batch_profile.get("allowed_child_operations")),
        child_operation,
    ])
    next_profiles = {**profiles, "batch": {**batch_profile, "allowed_operations": child_allowed}}
    allowed = lane_allowed_operations(lane_action)
    next_action = {**lane_action, "operation_profiles": next_profiles}
    if allowed:
        next_action["allowed_graph_operations"] = unique([*allowed, "batch"])
    return next_action


def validate_operation_tree(operation: dict[str, Any], lane_action: dict[str, Any], findings: list[Finding], path: str = "graph_operation") -> None:
    validate_operation_against_profile(operation, lane_action, findings, path)


def attach_contract_artifact(operation: dict[str, Any], artifact: dict[str, Any], findings: list[Finding]) -> None:
    if not artifact:
        return
    if operation.get("type") != "batch":
        operation.setdefault("work_graph_artifact", artifact)
        return
    node_id = str(artifact.get("node_id") or "")
    operations = operation.get("operations")
    if not isinstance(operations, list) or not node_id:
        findings.append(Finding("FAIL", "ambiguous_batch_artifact", "Cannot attach work_graph_artifact to batch operation without child operations and artifact node_id"))
        return

    def operation_node_ids(child: dict[str, Any]) -> set[str]:
        ids = {str(child.get("node_id") or "")}
        children = child.get("children")
        if isinstance(children, list):
            ids.update(str(item.get("id") or "") for item in children if isinstance(item, dict))
        target = child.get("target")
        if isinstance(target, dict):
            ids.add(str(target.get("id") or ""))
        return {item for item in ids if item}

    matches = [child for child in operations if isinstance(child, dict) and node_id in operation_node_ids(child)]
    if len(matches) != 1:
        findings.append(Finding("FAIL", "ambiguous_batch_artifact", f"Cannot map work_graph_artifact.node_id {node_id} to exactly one batch child operation"))
        return
    matches[0].setdefault("work_graph_artifact", artifact)


def runtime_harness_root(root: Path) -> Path:
    candidate = root / "harness-runtime" / "harness"
    if candidate.exists():
        return candidate
    return root / "harness-runtime" / "harness"


def relpath(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def approvals_path(root: Path) -> Path:
    runtime_path = runtime_harness_root(root) / "state" / "approvals.json"
    if runtime_path.exists():
        return runtime_path
    legacy_path = root / "harness" / "state" / "approvals.json"
    if legacy_path.exists():
        return legacy_path
    return runtime_path


def load_approvals(root: Path) -> list[dict[str, Any]]:
    path = approvals_path(root)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        approvals = data.get("approvals")
        if isinstance(approvals, list):
            return [item for item in approvals if isinstance(item, dict)]
        return [data]
    return []


def required_checkpoints(gate_report: dict[str, Any], mission_slice: dict[str, Any]) -> list[str]:
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    names: list[str] = []
    for payload in (mission_slice, gate_report):
        names.extend(normalize_checkpoint_names(payload.get("required_checkpoints")))
        names.extend(normalize_checkpoint_names(payload.get("human_checkpoints")))
    if gate_report.get("requires_approval") is True:
        names.append(str(gate_report.get("stage") or gate_report.get("from_stage") or control_plane.get("stage") or ""))
    result: list[str] = []
    for name in names:
        if name and name not in result:
            result.append(name)
    return result


def approved_checkpoints(root: Path, mission_id: str) -> set[str]:
    approved: set[str] = set()
    for item in load_approvals(root):
        if str(item.get("mission_id") or mission_id) != mission_id:
            continue
        if str(item.get("status") or "") != "approved":
            continue
        if item.get("type") and str(item.get("type")) != "checkpoint":
            continue
        name = str(item.get("stage") or item.get("checkpoint") or item.get("id") or "")
        if name:
            approved.add(name)
    return approved


def check_checkpoint_approvals(root: Path, mission_id: str, gate_report: dict[str, Any], mission_slice: dict[str, Any], findings: list[Finding]) -> list[str]:
    required = required_checkpoints(gate_report, mission_slice)
    if not required:
        return []
    approved = approved_checkpoints(root, mission_id)
    missing = [name for name in required if name not in approved]
    for name in missing:
        findings.append(Finding("BLOCKED", "checkpoint_approval_missing", f"Checkpoint {name} requires approved record in approvals.json"))
    return required if not missing else []


def check_gate_matches_slice(gate_report: dict[str, Any], mission_slice: dict[str, Any], findings: list[Finding]) -> None:
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    gate_stage = str(gate_report.get("stage") or gate_report.get("from_stage") or "")
    slice_stage = str(control_plane.get("stage") or "")
    if gate_stage == "design" and slice_stage in {"solution", "interaction", "technical_analysis"}:
        return
    if gate_stage and slice_stage and gate_stage != slice_stage:
        findings.append(Finding("FAIL", "gate_slice_stage_mismatch", f"Gate stage {gate_stage} does not match Mission Slice stage {slice_stage}"))


def operation_from_slice(root: Path, mission_id: str, mission_slice: dict[str, Any], findings: list[Finding], contract: dict[str, Any] | None = None) -> dict[str, Any] | None:
    primary_nodes = ((mission_slice.get("work_graph") or {}).get("primary_nodes")) if isinstance(mission_slice.get("work_graph"), dict) else []
    if not isinstance(primary_nodes, list) or not primary_nodes:
        findings.append(Finding("FAIL", "invalid_primary_nodes", "Mission Slice must contain at least one work_graph.primary_nodes entry"))
        return None
    operation_type = str(mission_slice.get("operation") or "")
    if operation_type not in SUPPORTED_SLICE_OPERATIONS:
        findings.append(Finding("FAIL", "unsupported_slice_operation", f"Unsupported Mission Slice operation: {operation_type}"))
        return None
    lane_action = registry_lane_action(root, mission_slice, findings)
    if findings:
        return None
    if not isinstance(mission_slice.get("graph_operation"), dict):
        lane_action, operation_type = apply_conditional_stage_override(root, mission_id, mission_slice, lane_action, operation_type, contract)
    lane_operation = str(lane_action.get("graph_operation") or "")
    if not lane_allows_operation(lane_action, operation_type):
        allowed = lane_allowed_operations(lane_action)
        if allowed:
            findings.append(Finding("FAIL", "slice_lane_operation_not_allowed", f"Mission Slice operation {operation_type} is not allowed by lane action operation profiles: {', '.join(allowed)}"))
        else:
            findings.append(Finding("FAIL", "slice_lane_operation_mismatch", f"Mission Slice operation {operation_type} does not match lane_action.graph_operation {lane_operation}"))
        return None

    explicit_operation = mission_slice.get("graph_operation")
    if isinstance(explicit_operation, dict):
        payload_type = str(explicit_operation.get("type") or "")
        if payload_type and payload_type != operation_type:
            findings.append(Finding("FAIL", "graph_operation_type_mismatch", f"graph_operation.type {payload_type} does not match Mission Slice operation {operation_type}"))
            return None
        operation = {**explicit_operation}
        operation.setdefault("operation_id", f"{mission_id}__{operation_type}")
        operation.setdefault("type", operation_type)
        operation.setdefault("mission_id", mission_id)
        if operation.get("type") != operation_type:
            findings.append(Finding("FAIL", "graph_operation_type_mismatch", f"graph_operation.type {operation.get('type')} does not match Mission Slice operation {operation_type}"))
            return None
        validate_operation_tree(operation, lane_action, findings)
        if findings:
            return None
        if isinstance(contract, dict) and isinstance(contract.get("work_graph_artifact"), dict):
            attach_contract_artifact(operation, contract["work_graph_artifact"], findings)
            if findings:
                return None
        return operation

    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    slice_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    lane = str(control_plane.get("lane") or slice_action.get("lane") or "")
    stage = str(control_plane.get("stage") or slice_action.get("stage") or "")
    profiles = operation_profiles(lane_action)
    advance_stage_profile = profiles.get("advance_stage") if isinstance(profiles.get("advance_stage"), dict) else {}
    advance_lane_profile = profiles.get("advance_lane") if isinstance(profiles.get("advance_lane"), dict) else {}
    if operation_type == "advance_stage":
        # advance_stage (including a conditional-stage override of advance_lane)
        # must resolve to_stage from the advance_stage profile first; the raw
        # slice_action.to_stage may carry a stale advance_lane target that points
        # to a stage outside the current lane.
        to_stage = str(advance_stage_profile.get("to_stage") or slice_action.get("to_stage") or "")
    else:
        to_stage = str(advance_lane_profile.get("to_stage") or slice_action.get("to_stage") or advance_stage_profile.get("to_stage") or "")
    to_lane = str(slice_action.get("to_lane") or advance_lane_profile.get("to_lane") or "")
    if operation_type in {"split_node", "merge_nodes", "supersede_node", "batch"}:
        findings.append(Finding("FAIL", "missing_graph_operation_payload", f"Mission Slice operation {operation_type} requires graph_operation payload"))
        return None
    if operation_type == "advance_stage" and not to_stage:
        findings.append(Finding("FAIL", "missing_to_stage", "Mission Slice must provide lane_action.to_stage for advance_stage"))
        return None
    if operation_type == "advance_lane" and not to_lane:
        findings.append(Finding("FAIL", "missing_to_lane", "Mission Slice must provide to_lane for advance_lane"))
        return None

    if operation_type in {"advance_stage", "advance_lane"} and len(primary_nodes) > 1:
        child_operations: list[dict[str, Any]] = []
        for node_id in primary_nodes:
            if operation_type == "advance_stage":
                child_operations.append(
                    {
                        "type": "advance_stage",
                        "node_id": str(node_id),
                        "lane": lane,
                        "from_stage": stage,
                        "to_stage": to_stage,
                    }
                )
            else:
                child_operations.append(
                    {
                        "type": "advance_lane",
                        "node_id": str(node_id),
                        "from_lane": lane,
                        "to_lane": to_lane,
                        "to_stage": to_stage,
                        "status": "ready",
                    }
                )
        operation = {
            "operation_id": f"{mission_id}__batch_{operation_type}",
            "type": "batch",
            "mission_id": mission_id,
            "operations": child_operations,
        }
        validate_operation_tree(operation, lane_action_with_implicit_batch(lane_action, operation_type), findings)
        if findings:
            return None
        if isinstance(contract, dict) and isinstance(contract.get("work_graph_artifact"), dict):
            attach_contract_artifact(operation, contract["work_graph_artifact"], findings)
            if findings:
                return None
        return operation

    node_id = str(primary_nodes[0])
    operation = {
        "operation_id": f"{mission_id}__{node_id}__{operation_type}",
        "type": operation_type,
        "node_id": node_id,
        "mission_id": mission_id,
    }
    if operation_type == "advance_stage":
        operation.update({"lane": lane, "from_stage": stage, "to_stage": to_stage})
    if operation_type == "advance_lane":
        operation.update({"from_lane": lane, "to_lane": to_lane, "to_stage": to_stage, "status": "ready"})
    if operation_type in {"block_node", "defer_node"} and mission_slice.get("reason"):
        operation["reason"] = mission_slice.get("reason")
    if operation_type in {"block_node", "defer_node"}:
        target_lane = operation_profiles(lane_action).get(operation_type, {}).get("target_lane")
        if target_lane:
            operation["to_lane"] = str(target_lane)
    if isinstance(contract, dict) and isinstance(contract.get("work_graph_artifact"), dict):
        attach_contract_artifact(operation, contract["work_graph_artifact"], findings)
        if findings:
            return None
    return operation


def update_mission_status(root: Path, mission_id: str, mission_slice: dict[str, Any], gate_report_ref: str, operation_ref: str, apply_result: dict[str, Any], checkpoints_passed: list[str] | None = None) -> None:
    status_path = runtime_harness_root(root) / "mission-status.yaml"
    status = load_yaml(status_path)
    entry = status.get(mission_id) if isinstance(status.get(mission_id), dict) else {}
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    stages = entry.get("stages") if isinstance(entry.get("stages"), dict) else {}
    stage = str(control_plane.get("stage") or "")
    if stage:
        stages[stage] = "done"
    work_graph = entry.get("work_graph") if isinstance(entry.get("work_graph"), dict) else {}
    work_graph.update(
        {
            "last_gate_report": gate_report_ref,
            "last_operation_manifest": operation_ref,
            "last_operation_status": apply_result.get("status"),
            "last_transaction_id": apply_result.get("transaction_id") or "",
            "last_transaction_journal": apply_result.get("transaction_journal") or "",
        }
    )
    current_checkpoints = as_str_list(entry.get("checkpoints_passed"))
    for checkpoint in checkpoints_passed or []:
        if checkpoint not in current_checkpoints:
            current_checkpoints.append(checkpoint)
    entry.update({"stages": stages, "work_graph": work_graph, "checkpoints_passed": current_checkpoints})
    status[mission_id] = entry
    write_yaml(status_path, status)


def advance_status(findings: list[Finding]) -> str:
    if any(item.level == "BLOCKED" for item in findings):
        return "BLOCKED"
    return status_from_findings(findings)


def check_gate_effect(gate_report: dict[str, Any], allow_warnings: bool, findings: list[Finding]) -> bool:
    gate_effect = str(gate_report.get("gate_effect") or "")
    if not gate_effect:
        return False
    if gate_effect == "allow":
        return True
    if gate_effect == "warn":
        if allow_warnings:
            return True
        findings.append(Finding("FAIL", "gate_effect_warn_requires_allow_warnings", "Gate effect warn requires --allow-warnings before applying graph operation"))
        return True
    if gate_effect == "block":
        findings.append(Finding("FAIL", "gate_effect_blocks", "Gate effect block does not allow graph operation"))
        return True
    if gate_effect == "pause":
        findings.append(Finding("BLOCKED", "gate_effect_pauses", "Gate effect pause requires checkpoint or human approval before applying graph operation"))
        return True
    findings.append(Finding("FAIL", "invalid_gate_effect", f"Unsupported gate_effect: {gate_effect}"))
    return True


# 标准阶段顺序——镜像自 harness_cli_core/domain/contracts.STANDARD_STAGE_ORDER（SSOT）。
# 仅用于 checkpoint-crossing 判定（target_stage 是否“早于”某个已 approval 的 checkpoint）。
# 跨包 import 不稳时此镜像保证脚本独立运行；新增阶段以 domain SSOT 为准同步。
_STANDARD_STAGE_ORDER = (
    "intake",
    "prd",
    "solution",
    "technical_analysis",
    "interaction",
    "breakdown",
    "execute",
    "verify",
    "delivery",
)


def _stage_index(stage: str) -> int:
    try:
        return _STANDARD_STAGE_ORDER.index(stage)
    except ValueError:
        return len(_STANDARD_STAGE_ORDER)


def build_reset_stage_operation(mission_id: str, target_stage: str, primary_nodes: list[str], signal: dict[str, Any]) -> dict[str, Any]:
    """装配 reset_stage operation profile（Task 2）。

    reset_stage 由 reset_mission_stage 原语执行，不走 apply_graph_operation 处理链；
    这里产出一个可审计、可执行的 payload，默认携带 output_node_policy=keep
    （产物全留盘、绝不作废下游），并记录上游归因来源与 gap 标识。
    """
    return {
        "operation_id": f"{mission_id}__reset_stage__{target_stage}",
        "type": "reset_stage",
        "mission_id": mission_id,
        "to_stage": target_stage,
        "target_stage": target_stage,
        "primary_nodes": list(primary_nodes),
        "output_node_policy": "keep",
        "reason": "upstream_incomplete",
        "trigger": {
            "kind": "reviewer_upstream_rollback",
            "source_role": signal.get("source_role"),
            "gap_ids": signal.get("gap_ids") or [],
        },
    }


def block_is_reviewer_hold(gate_report: dict[str, Any], contract: dict[str, Any]) -> bool:
    """判断 gate block 是否源于 reviewer HOLD/BLOCKED verdict。

    依据：control contract 携带 reviewer-class 角色且最新 verdict ∈ {HOLD, BLOCKED}。
    只要 reviewer_upstream_rollback_signal 能从 contract 取到 upstream 信号，
    本质上就已蕴含 reviewer HOLD；此函数保留为显式可读的前置闸（非破坏）。
    """
    raw = contract.get("role_verdicts") if isinstance(contract, dict) else None
    if not isinstance(raw, list):
        return False
    return bool(raw)


def rollback_crosses_approved_checkpoint(root: Path, mission_id: str, gate_report: dict[str, Any], mission_slice: dict[str, Any], target_stage: str) -> str | None:
    """判断回退目标是否跨越了「已被用户 approval 的 checkpoint」。

    若 target_stage 早于（_stage_index 更小或相等）任一已 approved 的 checkpoint 阶段，
    则回退会越过用户已确认的关口——此时不应静默自动回退，应降级为 Decision Gate（pause）。
    返回越过的 checkpoint 名（触发降级）；不跨越则返回 None（允许自动回退）。
    """
    approved = approved_checkpoints(root, mission_id)
    if not approved:
        return None
    target_index = _stage_index(target_stage)
    for name in sorted(approved):
        # checkpoint 名通常就是阶段名；非阶段名 _stage_index 落到末尾，不会误判。
        if _stage_index(name) >= target_index and _stage_index(name) < len(_STANDARD_STAGE_ORDER):
            return name
    return None


def attempt_upstream_rollback(
    root: Path,
    mission_id: str,
    gate_report: dict[str, Any],
    contract: dict[str, Any],
    mission_slice: dict[str, Any],
    findings: list[Finding],
) -> dict[str, Any] | None:
    """gate-block 出口的上游归因自动回退（Task 3）。

    仅当以下全部成立时触发回退（否则返回 None，调用方完全保持原有死路行为）：
    - domain 信号函数可用（跨包 import 成功）；
    - gate block 源于 reviewer HOLD/BLOCKED（block_is_reviewer_hold）；
    - reviewer_upstream_rollback_signal 返回非空 upstream 信号。

    触发后：装配 reset_stage operation（output_node_policy=keep）→ 调用
    reset_mission_stage 执行回退（产物留盘）→ reset_mission_stage 自身写 operations.log。
    若回退目标跨越已 approved checkpoint，则降级为 Decision Gate（pause），不静默回退。
    """
    if _reviewer_upstream_rollback_signal is None:
        return None
    if not isinstance(contract, dict) or not block_is_reviewer_hold(gate_report, contract):
        return None
    signal = _reviewer_upstream_rollback_signal(contract)
    if not signal:
        return None
    target_stage = str(signal.get("target_stage") or "")
    if not target_stage:
        return None

    # checkpoint-crossing 降级：跨越用户已确认关口 → pause（发起 Decision Gate），不自动回退。
    crossed = rollback_crosses_approved_checkpoint(root, mission_id, gate_report, mission_slice, target_stage)
    if crossed:
        findings.append(
            Finding(
                "BLOCKED",
                "upstream_rollback_crosses_checkpoint",
                (
                    f"reviewer 上游归因要求回退到 {target_stage}，但该回退会跨越已 approval 的 "
                    f"checkpoint {crossed}；降级为 Decision Gate（pause），需用户确认后再回退"
                ),
            )
        )
        return {
            "rollback": "pause_decision_gate",
            "target_stage": target_stage,
            "crossed_checkpoint": crossed,
            "signal": signal,
        }

    # 装配 reset_stage operation（携带 target_stage + output_node_policy=keep）。
    slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    primary_nodes = as_str_list(slice_graph.get("primary_nodes"))
    operation = build_reset_stage_operation(mission_id, target_stage, primary_nodes, signal)

    # 执行回退（产物留盘）。复用 mission_handlers 的 domain 接线（reset_mission_stage SSOT）。
    try:
        from harness_cli_core.domain.mission import reset_mission_stage
        from harness_cli_core.app.commands.mission_handlers import (
            load_graph as _load_graph,
            resolve_lane_stage as _resolve_lane_stage,
            run_graph_check as _run_graph_check,
            write_graph_views as _write_graph_views,
        )
        import datetime as _dt
        from zoneinfo import ZoneInfo as _ZoneInfo
    except Exception as exc:  # pragma: no cover - 跨包 import 兜底
        findings.append(Finding("FAIL", "upstream_rollback_import_failed", f"自动回退依赖导入失败：{exc}"))
        return None

    now = _dt.datetime.now(_ZoneInfo("Asia/Shanghai"))
    reason = (
        f"upstream_incomplete: reviewer {signal.get('source_role')} 判定缺口根因在前序阶段 "
        f"{target_stage}（gap_ids={signal.get('gap_ids')}）"
    )
    reset_result = reset_mission_stage(
        root,
        mission_id,
        target_stage,
        primary_nodes,
        [],
        "keep",  # output_node_policy=keep —— 产物留盘，绝不作废/删除/defer 下游
        True,    # preserve_stage_history —— 保留历史，重入各阶段自然对齐
        False,   # preserve_checkpoints —— 回退后下游 checkpoint 需重新过
        reason,
        resolve_lane_stage=lambda stage: _resolve_lane_stage(root, stage),
        load_graph=lambda: _load_graph(root),
        write_views=_write_graph_views,
        run_graph_check=lambda: _run_graph_check(root),
        now_value=now.isoformat(),
        today_value=now.strftime("%Y-%m-%d"),
    )

    return {
        "rollback": "auto_reset_stage",
        "target_stage": target_stage,
        "operation": operation,
        "signal": signal,
        "reset_result": reset_result,
    }


def attempt_clarification_gate(
    gate_report: dict[str, Any],
    contract: dict[str, Any],
    findings: list[Finding],
) -> dict[str, Any] | None:
    """gate-block 出口的"需用户澄清"汇总暂停（与 upstream 回退正交、优先于它）。

    仅当以下全部成立时触发（否则返回 None，调用方落回 upstream / 原有逻辑）：
    - domain 信号函数可用（跨包 import 成功）；
    - gate block 源于 reviewer HOLD/BLOCKED（block_is_reviewer_hold）；
    - reviewer_clarification_signal 返回非空澄清批次。

    触发后：**不 reset、不强制本阶段自修复**，而是把分散在多个 reviewer / 多条 gap 的
    澄清需求汇总成一个批次，发起澄清 Decision Gate（pause）。主 Agent 据此一次性问人
    （AskUserQuestion），人答复后由 `harness clarification record` 沉淀回
    `materials/clarifications/`（进文档集完备性基线），再回退/重推自然对齐。

    优先级：本函数在 run() 中先于 attempt_upstream_rollback 调用——根因是"人没给信息"时，
    任何 agent 重导都补不出，必须先补信息再决定是否回退。
    """
    if _reviewer_clarification_signal is None:
        return None
    if not isinstance(contract, dict) or not block_is_reviewer_hold(gate_report, contract):
        return None
    signal = _reviewer_clarification_signal(contract)
    if not signal:
        return None
    items = signal.get("clarification_items") or []
    findings.append(
        Finding(
            "BLOCKED",
            "needs_user_clarification_batch",
            (
                f"reviewer 判定 {len(items)} 条缺口根因是缺失的输入信息（gap_root=clarification），"
                "任何重导都补不出；汇总成澄清批次暂停（pause Decision Gate），"
                "需主 Agent 一次性向用户澄清后由 harness clarification record 沉淀回文档集"
            ),
        )
    )
    return {
        "rollback": "pause_clarification_gate",
        "clarification_batch": signal,
        "signal": signal,
    }


def run(root: Path, mission_id: str, gate_report_path: Path, allow_warnings: bool = False, contract_artifact: Path | None = None) -> dict[str, Any]:
    graph_root = resolve_graph_root(root)
    findings: list[Finding] = []
    gate_report = load_payload(gate_report_path)
    decision = str(gate_report.get("decision") or "")
    gate_effect = str(gate_report.get("gate_effect") or "")
    slice_path = graph_root / "mission-slices" / f"{mission_id}.yaml"
    mission_slice = load_yaml(slice_path)
    contract = load_control_contract(contract_artifact)

    # ── gate-block 出口的上游归因自动回退（Task 3）──────────────────────────────
    # 原本 gate_effect=block 是死路（gate_effect_blocks FAIL）。当 block 源于
    # reviewer HOLD 且存在 upstream 归因信号时，改为自动回退到该前序阶段重推。
    # 无信号 / gap_root=self / 旧契约 / 跨包 import 失败时，本分支一律不触发，
    # 控制流落回下方原有逻辑，行为完全不变（非破坏铁律）。
    if gate_effect == "block" and mission_slice:
        # ① 先查"需用户澄清"批次（优先于 upstream 回退）：根因是人从未提供的事实时，
        #    任何 agent 重导都补不出，必须先暂停问人，不能 reset 空转。
        clar_findings: list[Finding] = []
        clarification = attempt_clarification_gate(gate_report, contract, clar_findings)
        if clarification is not None:
            findings.extend(clar_findings)
            status = advance_status(findings)
            return {
                "status": status,
                "control": "board_router_advance_after_gate",
                "mission_id": mission_id,
                "gate_decision": decision,
                "mission_slice": str(slice_path),
                "operation_manifest": None,
                "apply_result": None,
                "clarification_gate": clarification,
                "findings": [finding_dict(item) for item in findings],
            }
        # ② 无澄清需求时，再查 upstream 归因自动回退（原有逻辑）。
        rollback_findings: list[Finding] = []
        rollback = attempt_upstream_rollback(root, mission_id, gate_report, contract, mission_slice, rollback_findings)
        if rollback is not None:
            findings.extend(rollback_findings)
            status = advance_status(findings)
            return {
                "status": status,
                "control": "board_router_advance_after_gate",
                "mission_id": mission_id,
                "gate_decision": decision,
                "mission_slice": str(slice_path),
                "operation_manifest": None,
                "apply_result": None,
                "upstream_rollback": rollback,
                "findings": [finding_dict(item) for item in findings],
            }
    # ── 上游回退/澄清分支结束；以下为原有 gate 流程，保持不变 ──────────────────────

    if not check_gate_effect(gate_report, allow_warnings, findings):
        allowed_decisions = CONTINUE_DECISIONS | ({"continue_with_warnings"} if allow_warnings else set())
        if decision not in allowed_decisions:
            findings.append(Finding("FAIL", "gate_not_continue", f"Gate decision does not allow graph operation: {decision or '<missing>'}"))

    if not mission_slice:
        findings.append(Finding("FAIL", "missing_mission_slice", f"Mission Slice not found: {slice_path}"))
    if not findings:
        check_gate_matches_slice(gate_report, mission_slice, findings)
    checkpoints_passed: list[str] = []
    if not findings:
        checkpoints_passed = check_checkpoint_approvals(root, mission_id, gate_report, mission_slice, findings)

    operation: dict[str, Any] | None = None
    operation_path: Path | None = None
    apply_result: dict[str, Any] | None = None
    if not findings:
        operation = operation_from_slice(root, mission_id, mission_slice, findings, contract=contract)
    if operation and not findings:
        operation_path = graph_root / "operations" / f"{operation['operation_id']}.yaml"
        gate_report_ref = relpath(root, gate_report_path)
        operation_ref = relpath(root, operation_path)

        def after_stage(staging_root: Path, _staged_operation: Path, staged_payload: dict[str, Any]) -> list[Finding]:
            update_mission_status(staging_root, mission_id, mission_slice, gate_report_ref, operation_ref, staged_payload, checkpoints_passed=checkpoints_passed)
            return []

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml", delete=False) as handle:
            temp_operation_path = Path(handle.name)
        try:
            write_yaml(temp_operation_path, operation)
            apply_result = apply_graph_operation(
                root,
                temp_operation_path,
                staged=True,
                operation_commit_rel=Path(operation_ref),
                extra_rel_roots=[Path("harness-runtime") / "harness" / "mission-status.yaml"],
                after_stage=after_stage,
            )
        finally:
            temp_operation_path.unlink(missing_ok=True)
        for item in apply_result.get("findings") or []:
            if isinstance(item, dict) and item.get("level") in {"FAIL", "BLOCKED"}:
                findings.append(Finding("FAIL", str(item.get("code") or "apply_operation_failed"), str(item.get("message") or "")))

    status = advance_status(findings)
    return {
        "status": status,
        "control": "board_router_advance_after_gate",
        "mission_id": mission_id,
        "gate_decision": decision,
        "mission_slice": str(slice_path),
        "operation_manifest": str(operation_path) if operation_path else None,
        "apply_result": apply_result,
        "findings": [finding_dict(item) for item in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--gate-report", required=True)
    parser.add_argument("--contract-artifact")
    parser.add_argument("--allow-warnings", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    gate_report = Path(args.gate_report)
    if not gate_report.is_absolute():
        gate_report = root / gate_report
    contract_artifact = Path(args.contract_artifact) if args.contract_artifact else None
    if contract_artifact and not contract_artifact.is_absolute():
        contract_artifact = root / contract_artifact
    payload = run(root, args.mission_id, gate_report, allow_warnings=args.allow_warnings, contract_artifact=contract_artifact)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Board Router advance after gate: {payload['status']}")
        for item in payload["findings"]:
            print(f"[{item['level']}] {item['code']}: {item['message']}")
    return 0 if payload["status"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    sys.exit(main())
