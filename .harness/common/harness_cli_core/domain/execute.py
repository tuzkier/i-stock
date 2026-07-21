from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from harness_cli_core.domain.control_state import mission_slice_primary_nodes
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_paths import load_runtime_config


COMMON_ROOT = Path(__file__).resolve().parents[2]
SKILLS_ROOT = COMMON_ROOT / "skills"
WORK_GRAPH_SCRIPTS = SKILLS_ROOT / "work-graph" / "scripts"

OVERLAY_COMPLEX_GLOB_MARKERS = ("**", "!")
EFFECTIVE_OVERLAY_REL = "runtime/effective-overlay.json"
STOP_EVENT_KINDS = {
    "changes_outside_authorized_paths",
    "new_external_dependency",
    "design_constraint_conflict",
    "new_public_behavior_without_delta_spec",
}
EXECUTE_TDD_PHASES = ("red", "green", "regression", "toolchain")


def translate_execution_brief_to_overlay(execution_brief_contract: dict[str, Any], *, task_id: str | None = None) -> dict[str, Any]:
    contract = execution_brief_contract.get("control_contract")
    root = contract if isinstance(contract, dict) else execution_brief_contract
    tasks = root.get("tasks") if isinstance(root, dict) else None
    if not isinstance(tasks, list):
        tasks = []

    allow: list[str] = []
    deny: list[str] = []
    ask: list[str] = []
    stop_if_hooks: list[dict[str, Any]] = []
    fallback_log: list[dict[str, Any]] = []

    def emit_path(path: str, target_list: list[str], task: str, field: str) -> None:
        if not isinstance(path, str) or not path:
            return
        if any(marker in path for marker in OVERLAY_COMPLEX_GLOB_MARKERS):
            ask.append(f"Edit({path})")
            ask.append(f"Write({path})")
            fallback_log.append({"task_id": task, "field": field, "pattern": path, "reason": "complex_glob"})
            return
        target_list.append(f"Edit({path})")
        target_list.append(f"Write({path})")

    for task in tasks:
        if not isinstance(task, dict):
            continue
        current_task_id = task.get("id") or "<unknown>"
        if task_id is not None and current_task_id != task_id:
            continue
        for path in task.get("authorized_paths", []) or []:
            emit_path(path, allow, current_task_id, "authorized_paths")
        for path in task.get("prohibited_paths", []) or []:
            emit_path(path, deny, current_task_id, "prohibited_paths")
        stop_if = task.get("stop_if") or []
        if isinstance(stop_if, list):
            for flag in stop_if:
                if isinstance(flag, str) and flag:
                    stop_if_hooks.append(
                        {"task_id": current_task_id, "flag": flag, "fallback": "execute_postuse_hook_pending_m5"}
                    )

    return {
        "permissions": {
            "allow": dedupe(allow),
            "deny": dedupe(deny),
            "ask": dedupe(ask),
        },
        "stop_if_hooks": stop_if_hooks,
        "fallback_log": fallback_log,
    }


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def effective_overlay_path(root: Path, mission: str) -> Path:
    return root / "harness-runtime" / "harness" / "stages" / mission / EFFECTIVE_OVERLAY_REL


def build_effective_overlay_state(contract: dict[str, Any], mission: str, task_id: str | None) -> dict[str, Any]:
    overlay = translate_execution_brief_to_overlay({"control_contract": contract}, task_id=task_id)
    authorized: list[str] = []
    prohibited: list[str] = []
    stop_if_flags: set[str] = set()
    for task in contract.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        current_task_id = task.get("id")
        if task_id is not None and current_task_id != task_id:
            continue
        authorized.extend(path for path in (task.get("authorized_paths") or []) if isinstance(path, str))
        prohibited.extend(path for path in (task.get("prohibited_paths") or []) if isinstance(path, str))
        stop_if_flags.update(flag for flag in (task.get("stop_if") or []) if isinstance(flag, str))
    return {
        "mission": mission,
        "task_id": task_id,
        "authorized_paths": sorted(set(authorized)),
        "prohibited_paths": sorted(set(prohibited)),
        "stop_if": sorted(stop_if_flags),
        "overlay": overlay,
    }


def write_effective_overlay_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def execution_result_contract_path(root: Path, mission: str) -> Path:
    return root / "harness-runtime" / "harness" / "stages" / mission / "contracts" / "execution-result.contract.yaml"


def execution_result_markdown_path(root: Path, mission: str) -> Path:
    return root / "harness-runtime" / "harness" / "stages" / mission / "execution-result.md"


def resolve_execution_result_contract(root: Path, mission: str) -> tuple[Path, dict[str, Any] | None, str | None]:
    artifact = execution_result_contract_path(root, mission)
    if not artifact.exists():
        return artifact, None, "execution_result_contract_missing"
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return artifact, None, "execution_result_contract_invalid_yaml"
    if not isinstance(document, dict):
        return artifact, None, "execution_result_contract_invalid_root"
    contract = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else document
    if not isinstance(contract, dict):
        return artifact, None, "execution_result_contract_invalid_shape"
    return artifact, contract, None


def append_stop_event(artifact: Path, *, kind: str, task_id: str | None, affected_paths: list[str], hook_source: str) -> tuple[dict[str, Any], int]:
    document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        document = {}
    contract_block = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else document
    if not isinstance(contract_block, dict):
        document["control_contract"] = {}
        contract_block = document["control_contract"]
    execute_session = contract_block.get("execute_session")
    if not isinstance(execute_session, dict):
        execute_session = {}
        contract_block["execute_session"] = execute_session
    events = execute_session.get("stop_events")
    if not isinstance(events, list):
        events = []
        execute_session["stop_events"] = events
    event = {
        "kind": kind,
        "task_id": task_id,
        "affected_paths": affected_paths,
        "hook_source": hook_source,
    }
    events.append(event)
    artifact.write_text(yaml.dump(document, default_flow_style=False, allow_unicode=True, sort_keys=False) + "\n", encoding="utf-8")
    return event, len(events)


def check_execute_tdd_evidence(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    tdd = contract.get("tdd_evidence")
    present_phases: set[str] = set()
    if isinstance(tdd, list):
        for entry in tdd:
            if isinstance(entry, dict) and isinstance(entry.get("phase"), str):
                present_phases.add(entry["phase"])
    for phase in EXECUTE_TDD_PHASES:
        if phase not in present_phases:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_tdd_evidence_phase",
                    "phase": phase,
                    "message": f"tdd_evidence missing phase {phase!r}",
                }
            )
    return findings


def check_execute_dispatch_coverage(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    session = contract.get("execute_session") if isinstance(contract.get("execute_session"), dict) else {}
    plans = session.get("dispatch_plans") if isinstance(session.get("dispatch_plans"), list) else []
    result_roles = {
        entry["role"]
        for entry in (contract.get("execution_results") or [])
        if isinstance(entry, dict) and isinstance(entry.get("role"), str)
    }
    verdict_roles = {
        entry["role"]
        for entry in (contract.get("role_verdicts") or [])
        if isinstance(entry, dict) and isinstance(entry.get("role"), str)
    }
    covered = result_roles | verdict_roles
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        plan_id = plan.get("id") or "<unknown>"
        planned: list[str] = []
        for key in ("primary_executors", "supporting_executors", "reviewers"):
            value = plan.get(key)
            if isinstance(value, list):
                planned.extend(role for role in value if isinstance(role, str))
        for role in planned:
            if role not in covered:
                findings.append(
                    {
                        "level": "FAIL",
                        "code": "dispatch_role_not_covered",
                        "dispatch_plan": plan_id,
                        "role": role,
                        "message": f"dispatch plan {plan_id} role {role!r} has no execution_results / role_verdicts entry",
                    }
                )
    return findings


def work_graph_nodes_by_id(root: Path) -> tuple[dict[str, dict[str, Any]], str | None]:
    if str(WORK_GRAPH_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))
    from work_graph_lib import load_nodes, resolve_graph_root

    nodes, _paths, findings = load_nodes(resolve_graph_root(root))
    if findings:
        return nodes, "; ".join(item.message for item in findings)
    return nodes, None


def execution_expected_atomic_task_ids(root: Path, mission: str, contract: dict[str, Any]) -> set[str]:
    mission_slice = load_yaml(root / "harness-runtime" / "harness" / "work-graph" / "mission-slices" / f"{mission}.yaml")
    primary_nodes = mission_slice_primary_nodes(mission_slice) if mission_slice else []
    if not primary_nodes:
        artifact = contract.get("work_graph_artifact") if isinstance(contract.get("work_graph_artifact"), dict) else {}
        node_id = str(artifact.get("node_id") or "")
        primary_nodes = [node_id] if node_id else []
    nodes_by_id, _load_error = work_graph_nodes_by_id(root)
    expected: set[str] = set()
    for node_id in primary_nodes:
        node = nodes_by_id.get(node_id) or {}
        queue = node.get("parent_local_atomic_task_queue") if isinstance(node.get("parent_local_atomic_task_queue"), dict) else {}
        atomic_ids = queue.get("atomic_task_ids")
        if isinstance(atomic_ids, list):
            expected.update(str(item) for item in atomic_ids if item)
        execution_units = queue.get("execution_units")
        if isinstance(execution_units, list):
            for unit in execution_units:
                if isinstance(unit, dict) and unit.get("id"):
                    expected.add(str(unit["id"]))
    return expected


def execute_batch_key(node: dict[str, Any]) -> tuple[str, str]:
    batch_id = str(node.get("execution_batch_id") or "").strip()
    if batch_id:
        return "execution_batch_id", batch_id
    brief = str(node.get("execution_brief_artifact") or "").strip()
    if brief:
        return "execution_brief_artifact", brief
    return "", ""


def check_execute_batch_sibling_coverage(root: Path, mission: str) -> list[dict[str, Any]]:
    mission_slice = load_yaml(root / "harness-runtime" / "harness" / "work-graph" / "mission-slices" / f"{mission}.yaml")
    primary_nodes = mission_slice_primary_nodes(mission_slice) if mission_slice else []
    if not primary_nodes:
        return []
    control = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    slice_lane = str(control.get("lane") or "")
    slice_stage = str(control.get("stage") or "")
    if slice_stage != "execute":
        return []
    nodes_by_id, _load_error = work_graph_nodes_by_id(root)
    primary_set = set(primary_nodes)
    primary_keys = {execute_batch_key(nodes_by_id.get(node_id) or {}) for node_id in primary_nodes}
    primary_keys = {key for key in primary_keys if key != ("", "")}
    if not primary_keys:
        return []
    if str(WORK_GRAPH_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))
    from work_graph_lib import lane_stage_for_node

    findings: list[dict[str, Any]] = []
    config = load_runtime_config(root)
    for node_id, node in sorted(nodes_by_id.items()):
        if node_id in primary_set:
            continue
        if execute_batch_key(node) not in primary_keys:
            continue
        node_lane, node_stage, _action = lane_stage_for_node(config, node)
        if node_lane != slice_lane or node_stage != slice_stage:
            continue
        if str(node.get("status") or "") not in {"ready", "active"}:
            continue
        findings.append(
            {
                "level": "FAIL",
                "code": "mission_slice_missing_execution_batch_sibling",
                "node_id": node_id,
                "message": f"Execute Mission Slice omits sibling TASK node {node_id} from the same execution batch",
            }
        )
    return findings


def single_atomic_execution_unit(value: str) -> bool:
    text = value.strip()
    return bool(text) and ".." not in text and "," not in text and not re.search(r"\s", text)


def evidence_covers_atomic(entry: dict[str, Any], atomic_id: str) -> bool:
    covers = entry.get("covers") if isinstance(entry.get("covers"), dict) else {}
    candidates: list[str] = []
    for key in ("atomic_tasks", "atomic_task_ids", "tasks", "execution_units"):
        value = covers.get(key)
        if isinstance(value, list):
            candidates.extend(str(item) for item in value)
    return atomic_id in candidates


def check_execute_atomic_control(root: Path, mission: str, contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = check_execute_batch_sibling_coverage(root, mission)
    expected = execution_expected_atomic_task_ids(root, mission, contract)
    if not expected:
        return findings
    session = contract.get("execute_session") if isinstance(contract.get("execute_session"), dict) else {}
    plans = session.get("dispatch_plans") if isinstance(session.get("dispatch_plans"), list) else []
    seen: list[str] = []
    for index, plan in enumerate(plans):
        if not isinstance(plan, dict):
            continue
        plan_id = str(plan.get("id") or f"dispatch[{index}]")
        unit = str(plan.get("execution_unit_id") or "")
        if not single_atomic_execution_unit(unit):
            findings.append(
                {
                    "level": "FAIL",
                    "code": "invalid_execute_atomic_dispatch_unit",
                    "dispatch_plan": plan_id,
                    "message": f"dispatch plan {plan_id} execution_unit_id must be one Atomic Task id, got {unit!r}",
                }
            )
            continue
        seen.append(unit)
        if unit not in expected:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "unknown_execute_atomic_dispatch_unit",
                    "dispatch_plan": plan_id,
                    "atomic_task_id": unit,
                    "message": f"dispatch plan {plan_id} references Atomic Task {unit!r} outside the current Mission Slice primary TASK nodes",
                }
            )
    seen_set = set(seen)
    for atomic_id in sorted(expected - seen_set):
        findings.append(
            {
                "level": "FAIL",
                "code": "missing_execute_atomic_dispatch_plan",
                "atomic_task_id": atomic_id,
                "message": f"current Mission Slice batch Atomic Task {atomic_id} has no dedicated dispatch plan",
            }
        )
    for atomic_id in sorted(unit for unit in seen_set if seen.count(unit) > 1):
        findings.append(
            {
                "level": "FAIL",
                "code": "duplicate_execute_atomic_dispatch_plan",
                "atomic_task_id": atomic_id,
                "message": f"Atomic Task {atomic_id} has multiple dispatch plans",
            }
        )

    phase_cover: dict[str, set[str]] = {"red": set(), "green": set(), "regression": set()}
    for entry in contract.get("tdd_evidence") or []:
        if not isinstance(entry, dict):
            continue
        phase = str(entry.get("phase") or "")
        if phase not in phase_cover:
            continue
        for atomic_id in expected:
            if evidence_covers_atomic(entry, atomic_id):
                phase_cover[phase].add(atomic_id)
    for phase, covered in sorted(phase_cover.items()):
        for atomic_id in sorted(expected - covered):
            findings.append(
                {
                    "level": "FAIL",
                    "code": "missing_execute_atomic_tdd_evidence",
                    "phase": phase,
                    "atomic_task_id": atomic_id,
                    "message": f"Atomic Task {atomic_id} lacks {phase} TDD evidence coverage",
                }
            )
    return findings


def execute_quality_findings(root: Path, mission: str, contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(check_execute_tdd_evidence(contract))
    findings.extend(check_execute_dispatch_coverage(contract))
    findings.extend(check_execute_atomic_control(root, mission, contract))
    return findings


def execute_artifact_gate_findings(root: Path, mission: str, relpath_fn) -> list[dict[str, Any]]:
    md_path = execution_result_markdown_path(root, mission)
    if not md_path.exists():
        return [
            {
                "level": "FAIL",
                "code": "execution_result_md_missing",
                "message": f"execution-result.md not found at {relpath_fn(root, md_path)}",
            }
        ]
    md_text = md_path.read_text(encoding="utf-8")
    findings: list[dict[str, Any]] = []
    for marker in ("Execute Session", "TDD Evidence", "Contract: contracts/execution-result.contract.yaml"):
        if marker not in md_text:
            findings.append(
                {
                    "level": "FAIL",
                    "code": "execution_result_md_section_missing",
                    "section": marker,
                    "message": f"execution-result.md missing section/marker: {marker!r}",
                }
            )
    return findings


def status_from_fail_findings(findings: list[dict[str, Any]]) -> str:
    return "PASS" if not any(finding.get("level") == "FAIL" for finding in findings) else "FAIL"


def persist_last_gate_run_status(artifact: Path, status: str) -> None:
    try:
        document = yaml.safe_load(artifact.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            return
        contract_block = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else document
        if not isinstance(contract_block, dict):
            return
        effectiveness = contract_block.get("effectiveness_review")
        if not isinstance(effectiveness, dict):
            effectiveness = {}
            contract_block["effectiveness_review"] = effectiveness
        effectiveness["last_gate_run_status"] = status
        artifact.write_text(yaml.dump(document, default_flow_style=False, allow_unicode=True, sort_keys=False) + "\n", encoding="utf-8")
    except (OSError, yaml.YAMLError):
        return
