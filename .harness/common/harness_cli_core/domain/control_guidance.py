from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_cli_core.domain.collections import unique
from harness_cli_core.domain.control_context import build_context_index, control_relpath
from harness_cli_core.domain.control_frame import build_control_frame
from harness_cli_core.domain.control_state import as_str_list
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_layout import control_runtime_root


GUIDANCE_CATEGORIES = {
    "ready_for_execution",
    "needs_context",
    "needs_artifact",
    "needs_review",
    "needs_gate",
    "needs_approval",
    "blocked",
}


def guidance_required_controls(
    *,
    missing_context: list[dict[str, Any]],
    missing_artifacts: list[dict[str, Any]],
    required_approvals: list[dict[str, Any]],
    missing_evidence: list[dict[str, Any]],
    pending_gates: list[dict[str, Any]],
) -> list[str]:
    controls = ["control.context-index"]
    if missing_context:
        controls.append("context.check")
    if missing_artifacts:
        controls.append("execute.produce-stage-artifact")
    if required_approvals:
        controls.append("approval.require")
    if missing_evidence:
        controls.append("contract.add-verdict")
    if pending_gates:
        controls.append("gate.run")
    return unique(controls)


def stage_participation_policy_payload(frame: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "role_policy_and_lane_action",
        "skippable": False,
        "conditional_entry": bool(frame.get("required_approvals")),
        "human_checkpoints": frame.get("required_approvals") or [],
        "required_review_roles": frame.get("required_review_roles") or [],
    }


def entered_stage_obligations_payload(frame: dict[str, Any], required_controls: list[str]) -> dict[str, Any]:
    return {
        "execution_roles": frame.get("required_execution_roles") or [],
        "review_roles": frame.get("required_review_roles") or [],
        "gate_controls": ["gate.run", "gate.advance"],
        "evidence": ["red_report", "green_report", "regression_report"],
        "required_controls": required_controls,
    }


def missing_review_evidence(root: Path, layout: dict[str, Any], mission_id: str, required_review_roles: list[str]) -> list[dict[str, Any]]:
    if not required_review_roles:
        return []
    contract_path = control_runtime_root(layout) / "stages" / mission_id / "contracts" / "execution-result.contract.yaml"
    contract_doc = load_yaml(contract_path) if contract_path.exists() else {}
    contract = contract_doc.get("control_contract") if isinstance(contract_doc.get("control_contract"), dict) else {}
    role_verdicts = contract.get("role_verdicts") if isinstance(contract.get("role_verdicts"), list) else []
    passed_roles = {
        str(item.get("role") or "")
        for item in role_verdicts
        if isinstance(item, dict) and str(item.get("verdict") or "") == "PASS"
    }
    missing: list[dict[str, Any]] = []
    for role in required_review_roles:
        if role in passed_roles:
            continue
        missing.append({
            "kind": "review_evidence",
            "role": role,
            "path": control_relpath(root, contract_path),
            "required": True,
            "exists": False,
            "source": "contract",
        })
    return missing


def blocked_guidance_payload(root: Path, layout: dict[str, Any], mission_id: str, frame: dict[str, Any]) -> dict[str, Any]:
    findings = frame.get("findings") if isinstance(frame.get("findings"), list) else []
    if not findings and frame.get("error"):
        findings = [{
            "level": "BLOCKED",
            "code": str(frame.get("error") or "blocked"),
            "message": str(frame.get("message") or "control frame is blocked"),
            "blocking": True,
            "source": "control.frame",
        }]
    required_controls = ["control.frame"]
    return {
        "status": "BLOCKED",
        "runtime_layout": layout,
        "mission_id": mission_id,
        "lane": frame.get("lane") or "",
        "stage": frame.get("stage") or "",
        "state": {"category": "blocked"},
        "required_controls": required_controls,
        "allowed_actions": ["fix_blocker", "rerun_required_controls"],
        "disallowed_actions": [
            {"action": "select_mission_without_selector", "reason": "control frame requires explicit --mission"},
            {"action": "emit_final_decision", "reason": "guidance is non-decisional"},
        ],
        "missing_context": [],
        "missing_artifacts": [],
        "missing_approvals": [],
        "missing_evidence": [],
        "stage_participation_policy": stage_participation_policy_payload(frame),
        "entered_stage_obligations": entered_stage_obligations_payload(frame, required_controls),
        "findings": findings,
    }


def build_control_guidance(root: Path, layout: dict[str, Any], mission_id: str) -> dict[str, Any]:
    frame = build_control_frame(root, layout, mission_id)
    if frame.get("status") != "PASS":
        return blocked_guidance_payload(root, layout, mission_id, frame)
    context_index = build_context_index(root, layout, mission_id)
    missing_context = context_index.get("missing_context") if isinstance(context_index.get("missing_context"), list) else []
    missing_artifacts = []
    artifact_state = frame.get("artifact_state") if isinstance(frame.get("artifact_state"), dict) else {}
    if artifact_state.get("path") and not artifact_state.get("exists"):
        missing_artifacts.append({
            "kind": "output_artifact",
            "path": artifact_state["path"],
            "required": True,
            "exists": False,
            "source": "lane_action",
        })
    required_approvals = frame.get("required_approvals") if isinstance(frame.get("required_approvals"), list) else []
    required_reviews = as_str_list(frame.get("required_review_roles"))
    missing_evidence = [] if missing_artifacts else missing_review_evidence(root, layout, mission_id, required_reviews)
    gate_state = frame.get("gate_state") if isinstance(frame.get("gate_state"), dict) else {}
    pending_gates = gate_state.get("pending_gates") if isinstance(gate_state.get("pending_gates"), list) else []
    if missing_context:
        category = "needs_context"
    elif required_approvals:
        category = "needs_approval"
    elif missing_artifacts:
        category = "needs_artifact"
    elif missing_evidence:
        category = "needs_review"
    elif gate_state.get("pending_gates"):
        category = "needs_gate"
    else:
        category = "ready_for_execution"
    required_controls = guidance_required_controls(
        missing_context=missing_context,
        missing_artifacts=missing_artifacts,
        required_approvals=required_approvals,
        missing_evidence=missing_evidence,
        pending_gates=pending_gates,
    )
    return {
        "status": "PASS",
        "runtime_layout": layout,
        "mission_id": mission_id,
        "lane": frame.get("lane") or "",
        "stage": frame.get("stage") or "",
        "state": {"category": category},
        "required_controls": required_controls,
        "allowed_actions": ["read_context", "run_required_controls", "produce_stage_artifact"],
        "disallowed_actions": [
            {"action": "select_mission_without_selector", "reason": "control frame requires explicit --mission"},
            {"action": "emit_final_decision", "reason": "guidance is non-decisional"},
        ],
        "missing_context": missing_context,
        "missing_artifacts": missing_artifacts,
        "missing_approvals": required_approvals,
        "missing_evidence": missing_evidence,
        "next_graph_operation": frame.get("resolved_graph_operation") if isinstance(frame.get("resolved_graph_operation"), dict) else {},
        "stage_participation_policy": stage_participation_policy_payload(frame),
        "entered_stage_obligations": entered_stage_obligations_payload(frame, required_controls),
        "findings": [],
    }
