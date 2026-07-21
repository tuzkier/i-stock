#!/usr/bin/env python3
"""Render machine-readable and human-readable stage-gate reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_control_reports import check as check_control_reports


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        return {}
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def as_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


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


def normalize_checkpoint_name(name: str) -> str:
    stripped = name.strip()
    return CHECKPOINT_ALIASES.get(stripped, stripped)


def approvals_path(root: Path) -> Path:
    runtime_path = root / "harness-runtime" / "harness" / "state" / "approvals.json"
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
        if data.get("mission_id"):
            return [data]
    return []


def normalize_checkpoint_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [normalize_checkpoint_name(value)] if value else []
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            names.append(normalize_checkpoint_name(item))
        elif isinstance(item, dict):
            name = str(item.get("stage") or item.get("checkpoint") or item.get("id") or "")
            if name:
                names.append(normalize_checkpoint_name(name))
    return unique(names)


def human_checkpoints(args: argparse.Namespace, mission_slice: dict[str, Any]) -> list[str]:
    names: list[str] = []
    names.extend(normalize_checkpoint_names(as_str_list(args.human_checkpoint)))
    names.extend(normalize_checkpoint_names(mission_slice.get("human_checkpoints")))
    return unique(names)


def required_checkpoints(args: argparse.Namespace, mission_slice: dict[str, Any], humans: list[str]) -> list[str]:
    names: list[str] = []
    names.extend(normalize_checkpoint_names(as_str_list(args.required_checkpoint)))
    names.extend(humans)
    names.extend(normalize_checkpoint_names(mission_slice.get("required_checkpoints")))
    return unique(names)


def approval_status(root: Path, mission_id: str, required: list[str]) -> dict[str, Any]:
    approvals = load_approvals(root)
    approved: list[str] = []
    approval_ids: dict[str, str] = {}
    for item in approvals:
        if str(item.get("mission_id") or mission_id) != mission_id:
            continue
        if str(item.get("type") or "") != "checkpoint":
            continue
        if str(item.get("status") or "") != "approved":
            continue
        checkpoint = str(item.get("stage") or item.get("checkpoint") or item.get("id") or "")
        if checkpoint and checkpoint not in approved:
            approved.append(checkpoint)
            approval_ids[checkpoint] = str(item.get("approval_id") or "")
    missing = [checkpoint for checkpoint in required if checkpoint not in approved]
    return {
        "required_checkpoints": required,
        "approved_checkpoints": approved,
        "missing_checkpoints": missing,
        "approval_ids": approval_ids,
        "status": "PASS" if not missing else "BLOCKED",
    }


def gate_effect_from_inputs(contract_check: dict[str, Any], control_check: dict[str, Any], approval_check: dict[str, Any]) -> str:
    if contract_check.get("status") == "FAIL" or control_check.get("status") == "FAIL":
        return "block"
    if approval_check.get("status") == "BLOCKED":
        return "pause"
    if contract_check.get("status") == "WARN" or control_check.get("status") == "WARN":
        return "warn"
    return "allow"


def decision_from_gate_effect(gate_effect: str) -> str:
    if gate_effect == "allow":
        return "continue"
    if gate_effect == "warn":
        return "continue_with_warnings"
    return "cannot_continue"


def render_markdown(payload: dict[str, Any]) -> str:
    work_graph = payload.get("work_graph") if isinstance(payload.get("work_graph"), dict) else {}
    lines = [
        "# Stage Gate Report",
        "",
        f"**Mission:** {payload.get('mission_id', '')}",
        f"**Stage:** {payload.get('stage') or work_graph.get('stage') or ''}",
        f"**Operation:** {payload.get('operation') or work_graph.get('operation') or ''}",
        f"**Decision:** {payload.get('decision', '')}",
        f"**Gate Effect:** {payload.get('gate_effect', '')}",
        "",
        "## Programmatic Contract Check",
        "",
        "| Level | Code | Message |",
        "|-------|------|---------|",
    ]
    for finding in (payload.get("contract_check") or {}).get("findings", []):
        lines.append(f"| {finding.get('level')} | {finding.get('code')} | {finding.get('message')} |")
    if payload.get("work_graph"):
        work_graph = payload["work_graph"]
        lines.extend(
            [
                "",
                "## Work Graph",
                "",
                f"- Mission Slice: `{work_graph.get('mission_slice', '')}`",
                f"- Primary Nodes: `{', '.join(work_graph.get('primary_nodes') or [])}`",
                f"- Lane/Stage: `{work_graph.get('lane', '')}/{work_graph.get('stage', '')}`",
                f"- Operation: `{work_graph.get('operation', '')}`",
            ]
        )
    approval = payload.get("approval_status") if isinstance(payload.get("approval_status"), dict) else {}
    if approval:
        lines.extend(
            [
                "",
                "## Approvals",
                "",
                f"- Required Checkpoints: `{', '.join(approval.get('required_checkpoints') or [])}`",
                f"- Approved Checkpoints: `{', '.join(approval.get('approved_checkpoints') or [])}`",
                f"- Missing Checkpoints: `{', '.join(approval.get('missing_checkpoints') or [])}`",
            ]
        )
    interpretation = (payload.get("ai_interpretation") or "").strip()
    if interpretation:
        lines.extend(["", "## AI Interpretation", "", interpretation])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--contract-check-json", required=True)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--from-stage", required=True)
    parser.add_argument("--to-stage", required=True)
    parser.add_argument("--mission-slice")
    parser.add_argument("--control-report", action="append", default=[])
    parser.add_argument("--required-control", action="append", default=[])
    parser.add_argument("--required-checkpoint", action="append", default=[])
    parser.add_argument("--human-checkpoint", action="append", default=[])
    parser.add_argument("--ai-interpretation", default="")
    parser.add_argument("--stage-artifact")
    parser.add_argument("--contract-artifact")
    parser.add_argument("--output-dir", default="harness-runtime/harness/state/gate-reports")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    contract_check = load_json(Path(args.contract_check_json))
    mission_slice = load_yaml(Path(args.mission_slice)) if args.mission_slice else {}
    slice_control = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    humans = human_checkpoints(args, mission_slice)
    required = required_checkpoints(args, mission_slice, humans)
    approvals = approval_status(root, args.mission_id, required)
    control_check = check_control_reports(root, args.mission_id, args.control_report, args.required_control)
    gate_effect = gate_effect_from_inputs(contract_check, control_check, approvals)
    decision = decision_from_gate_effect(gate_effect)
    payload = {
        "schema_version": 1,
        "mission_id": args.mission_id,
        "stage": slice_control.get("stage") or args.from_stage,
        "operation": mission_slice.get("operation") if mission_slice else None,
        "from_stage": args.from_stage,
        "to_stage": args.to_stage,
        "decision": decision,
        "gate_effect": gate_effect,
        "contract_check": contract_check,
        "artifacts": {
            "stage_artifact": args.stage_artifact,
            "contract_artifact": args.contract_artifact,
        },
        "control_reports": control_check,
        "required_checkpoints": required,
        "human_checkpoints": humans,
        "approval_status": approvals,
        "work_graph": {
            "mission_slice": args.mission_slice,
            "primary_nodes": slice_graph.get("primary_nodes") or [],
            "related_nodes": slice_graph.get("related_nodes") or [],
            "lane": slice_control.get("lane"),
            "stage": slice_control.get("stage"),
            "operation": mission_slice.get("operation"),
        } if mission_slice else None,
        "ai_interpretation": args.ai_interpretation,
    }
    out_dir = Path(args.output_dir) / args.mission_id
    out_dir.mkdir(parents=True, exist_ok=True)
    if mission_slice:
        stem_parts = [
            str(slice_control.get("stage") or args.from_stage or "stage"),
            str(mission_slice.get("operation") or "operation"),
        ]
        stem = "__".join(part.replace("/", "-") for part in stem_parts)
    else:
        stem = f"{args.from_stage}__to__{args.to_stage}"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "decision": decision, "gate_effect": gate_effect}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
