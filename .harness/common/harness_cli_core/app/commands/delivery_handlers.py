"""Handlers for `harness delivery ...` commands.

delivery-improvement-plan M2.1 — 6 real-new commands: summarize /
compute-follow-ups / check-followups / compute-conclusion / handoff /
agent-capability-status. Each returns the typed JSON envelope via
``emit_payload``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.contracts import load_control_contract
from harness_cli_core.domain.delivery import (
    delivery_contract_path,
    tech_design_contract_path,
)
from harness_cli_core.domain.verification import verify_report_path
from harness_cli_core.infra.runtime_paths import relpath


def cmd_delivery_summarize(args: argparse.Namespace) -> int:
    """Produce a typed delivery summary from the verification-report contract."""
    root = Path(root_arg(args))
    vr_path = verify_report_path(root, args.mission)
    contract = load_control_contract(vr_path)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "delivery.summarize",
                "verification_report_missing",
                f"verification-report contract not found at {relpath(root, vr_path)}",
            ),
        )
    acceptance_trace = (
        contract.get("acceptance_trace")
        if isinstance(contract.get("acceptance_trace"), list)
        else []
    )
    total = len(acceptance_trace)
    passed = sum(1 for e in acceptance_trace if isinstance(e, dict) and e.get("conclusion") == "pass")
    failed = sum(1 for e in acceptance_trace if isinstance(e, dict) and e.get("conclusion") == "fail")
    findings: list[dict] = []
    if failed:
        findings.append(
            {
                "level": "WARN",
                "code": "acceptance_trace_has_failures",
                "message": f"{failed} acceptance scenario(s) concluded fail in verification-report",
            }
        )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "delivery.summarize",
            "mission": args.mission,
            "summary": {
                "acceptance_trace": {
                    "total": total,
                    "pass": passed,
                    "fail": failed,
                }
            },
            "findings": findings,
        },
    )


def cmd_delivery_compute_follow_ups(args: argparse.Namespace) -> int:
    """Generate follow-up candidates from failed / accepted-risk acceptance scenarios."""
    root = Path(root_arg(args))
    vr_path = verify_report_path(root, args.mission)
    contract = load_control_contract(vr_path)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "delivery.compute-follow-ups",
                "verification_report_missing",
                f"verification-report contract not found at {relpath(root, vr_path)}",
            ),
        )
    acceptance_trace = (
        contract.get("acceptance_trace")
        if isinstance(contract.get("acceptance_trace"), list)
        else []
    )
    candidates: list[dict] = []
    for entry in acceptance_trace:
        if not isinstance(entry, dict):
            continue
        acceptance_id = entry.get("acceptance_id") or entry.get("id") or "<unknown>"
        conclusion = entry.get("conclusion")
        if conclusion == "fail":
            candidates.append(
                {
                    "id": f"FU-{acceptance_id}",
                    "acceptance_id": acceptance_id,
                    "severity": "blocking",
                    "source": "failed_acceptance",
                    "reason": f"Acceptance scenario {acceptance_id} concluded fail; must be resolved before close",
                }
            )
        elif conclusion == "accepted_risk":
            candidates.append(
                {
                    "id": f"FU-{acceptance_id}",
                    "acceptance_id": acceptance_id,
                    "severity": "advisory",
                    "source": "accepted_risk_acceptance",
                    "reason": f"Acceptance scenario {acceptance_id} accepted with risk; track as advisory follow-up",
                }
            )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "delivery.compute-follow-ups",
            "mission": args.mission,
            "follow_ups_candidates": candidates,
            "findings": [],
        },
    )


def cmd_delivery_check_followups(args: argparse.Namespace) -> int:
    """Verify every follow-up has a graph operation or a documented none reason."""
    root = Path(root_arg(args))
    dc_path = delivery_contract_path(root, args.mission)
    contract = load_control_contract(dc_path)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "delivery.check-followups",
                "delivery_contract_missing",
                f"delivery contract not found at {relpath(root, dc_path)}",
            ),
        )
    package = (
        contract.get("delivery_package")
        if isinstance(contract.get("delivery_package"), dict)
        else {}
    )
    follow_ups = (
        package.get("follow_ups") if isinstance(package.get("follow_ups"), list) else []
    )
    findings: list[dict] = []
    for fu in follow_ups:
        if not isinstance(fu, dict):
            continue
        fu_id = fu.get("id") or "<unknown>"
        severity = fu.get("severity")
        graph_op = fu.get("graph_op")
        has_op = bool(graph_op) and graph_op != "none"
        if severity in {"blocking", "advisory"}:
            if not has_op:
                findings.append(
                    {
                        "level": "FAIL",
                        "code": "follow_up_missing_graph_op",
                        "follow_up": fu_id,
                        "message": f"follow-up {fu_id} ({severity}) must declare a graph operation; got {graph_op!r}",
                    }
                )
        elif severity == "can_ignore":
            if not has_op and not fu.get("none_reason"):
                findings.append(
                    {
                        "level": "FAIL",
                        "code": "follow_up_missing_none_reason",
                        "follow_up": fu_id,
                        "message": f"follow-up {fu_id} (can_ignore) with graph_op=none must declare none_reason",
                    }
                )
    status = "PASS" if not any(f["level"] == "FAIL" for f in findings) else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "delivery.check-followups",
            "mission": args.mission,
            "follow_ups_checked": len(follow_ups),
            "findings": findings,
        },
    )


def cmd_delivery_compute_conclusion(args: argparse.Namespace) -> int:
    """Compute the typed delivery conclusion: delivered / continue_fix / blocked."""
    root = Path(root_arg(args))
    dc_path = delivery_contract_path(root, args.mission)
    contract = load_control_contract(dc_path)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "delivery.compute-conclusion",
                "delivery_contract_missing",
                f"delivery contract not found at {relpath(root, dc_path)}",
            ),
        )
    package = (
        contract.get("delivery_package")
        if isinstance(contract.get("delivery_package"), dict)
        else {}
    )
    acceptance = (
        contract.get("acceptance_result")
        if isinstance(contract.get("acceptance_result"), dict)
        else {}
    )
    findings: list[dict] = []

    if not package.get("acceptance_state_ref"):
        findings.append(
            {
                "level": "FAIL",
                "code": "acceptance_state_ref_missing",
                "message": "delivery_package.acceptance_state_ref is missing",
            }
        )
    handoff = (
        package.get("handoff_evidence")
        if isinstance(package.get("handoff_evidence"), dict)
        else {}
    )
    if handoff.get("pause_required") is not True:
        findings.append(
            {
                "level": "FAIL",
                "code": "handoff_pause_required_missing",
                "message": "delivery_package.handoff_evidence.pause_required must be true",
            }
        )
    checkpoint = (
        acceptance.get("user_checkpoint")
        if isinstance(acceptance.get("user_checkpoint"), dict)
        else {}
    )
    ckpt_status = checkpoint.get("status")
    if ckpt_status == "pending_user_acceptance":
        findings.append(
            {
                "level": "FAIL",
                "code": "user_checkpoint_pending",
                "message": "acceptance_result.user_checkpoint.status is still pending_user_acceptance",
            }
        )
    acceptance_trace = (
        acceptance.get("acceptance_trace")
        if isinstance(acceptance.get("acceptance_trace"), list)
        else []
    )
    for entry in acceptance_trace:
        if not isinstance(entry, dict):
            continue
        if entry.get("result_status") == "pass" and not entry.get("verify_command_evidence_id"):
            findings.append(
                {
                    "level": "FAIL",
                    "code": "acceptance_trace_missing_verify_evidence",
                    "acceptance_id": entry.get("acceptance_id"),
                    "message": f"Acceptance scenario {entry.get('acceptance_id')} concluded pass but lacks verify_command_evidence_id",
                }
            )

    if ckpt_status == "continue_fix":
        conclusion = "continue_fix"
    elif ckpt_status == "pending_user_acceptance":
        conclusion = "blocked"
    elif any(f["level"] == "FAIL" for f in findings):
        conclusion = "blocked"
    else:
        conclusion = "delivered"
    status = "PASS" if conclusion == "delivered" and not findings else "FAIL"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "delivery.compute-conclusion",
            "mission": args.mission,
            "conclusion": conclusion,
            "findings": findings,
        },
    )


def cmd_delivery_handoff(args: argparse.Namespace) -> int:
    """Write handoff evidence declaring a pause boundary after delivery."""
    root = Path(root_arg(args))
    dc_path = delivery_contract_path(root, args.mission)
    if not dc_path.exists():
        return emit_payload(
            args,
            fail_payload(
                "delivery.handoff",
                "delivery_contract_missing",
                f"delivery contract not found at {relpath(root, dc_path)}",
            ),
        )
    try:
        doc = yaml.safe_load(dc_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return emit_payload(
            args,
            fail_payload(
                "delivery.handoff",
                "delivery_contract_invalid_yaml",
                f"{exc}",
            ),
        )
    if not isinstance(doc, dict):
        doc = {}
    block = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    if not isinstance(block, dict):
        doc["control_contract"] = {}
        block = doc["control_contract"]
    package = block.get("delivery_package")
    if not isinstance(package, dict):
        package = {}
        block["delivery_package"] = package
    approval_id = getattr(args, "approval_id", None)
    handoff_evidence = {
        "pause_required": True,
        "requires_user_resume": True,
        "next_stage_candidate": "finishing-branch",
        "approval_id": approval_id,
    }
    package["handoff_evidence"] = handoff_evidence
    dc_path.write_text(
        yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "delivery.handoff",
            "mission": args.mission,
            "pause_required": True,
            "requires_user_resume": True,
            "next_stage_candidate": "finishing-branch",
            "handoff_evidence": handoff_evidence,
            "findings": [],
        },
    )


def cmd_delivery_agent_capability_status(args: argparse.Namespace) -> int:
    """Report agent-capability delivery status, or not_applicable when the
    mission has no Agent implementation in tech-design."""
    root = Path(root_arg(args))
    dc_path = delivery_contract_path(root, args.mission)
    if load_control_contract(dc_path) is None:
        return emit_payload(
            args,
            fail_payload(
                "delivery.agent-capability-status",
                "delivery_contract_missing",
                f"delivery contract not found at {relpath(root, dc_path)}",
            ),
        )
    td_path = tech_design_contract_path(root, args.mission)
    td = load_control_contract(td_path)
    has_agent = bool(td) and bool(td.get("agent_architecture") or td.get("agent_implementation"))
    overall = "delivered" if has_agent else "not_applicable"
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "delivery.agent-capability-status",
            "mission": args.mission,
            "agent_capability_status": {"overall_status": overall},
            "findings": [],
        },
    )


__all__ = [
    "cmd_delivery_summarize",
    "cmd_delivery_compute_follow_ups",
    "cmd_delivery_check_followups",
    "cmd_delivery_compute_conclusion",
    "cmd_delivery_handoff",
    "cmd_delivery_agent_capability_status",
]
