"""Handlers for `harness prototype-as-frontend ...` commands."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
from pathlib import Path
from typing import Any

from harness_cli_core.app.commands.alignment_handlers import cmd_alignment_check
from harness_cli_core.app.commands.interaction_handlers import (
    cmd_interaction_spec_check,
    cmd_interaction_ux_quality_check,
)
from harness_cli_core.app.output import emit_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.approvals import approval_matches, load_approvals
from harness_cli_core.domain.findings import (
    apply_compat_warning,
    finding,
    is_placeholder_text,
)
from harness_cli_core.domain.interaction import (
    contains_any,
    contract_feedback_sync_findings,
)
from harness_cli_core.domain.prototype_as_frontend import (
    contract_e2e_obligations,
    frontend_changeset_path,
    frontend_flowstep_obligation_coverage,
    frontend_na_stale_findings,
    frontend_project_root_from_contract,
    frontend_upstream_completeness_findings,
    parse_frontend_changeset_surfaces,
    parse_frontend_na_flowsteps,
    prd_flowsteps_for_mission,
    prototype_as_frontend_contract,
    prototype_as_frontend_contract_path,
)
from harness_cli_core.infra.runtime_paths import (
    mission_stage_dir,
    read_text_if_exists,
    relpath,
)


def cmd_prototype_as_frontend_changeset_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    changeset = frontend_changeset_path(root, mission)
    text = read_text_if_exists(changeset)
    findings: list[dict[str, object]] = []
    if not changeset.exists():
        findings.append(
            finding(
                "FAIL",
                "FRONTEND_CHANGESET_MISSING",
                "frontend_engineering route must produce frontend-changeset.md.",
                path=relpath(root, changeset),
            )
        )
    required_tokens = [
        ("INTERACTION_SPEC_REF_MISSING", ("interaction_spec_ref", "interaction-spec", "spec_ref")),
        ("SPEC_CONFORMANCE_MISSING", ("spec_conformance", "frontend_vs_spec", "conformance")),
        ("SURFACE_BASELINE_MISSING", ("baseline_ref", "baseline")),
        ("TRACEABILITY_INCOMPLETE", ("traces_to", "SCN-", "SUC-")),
        ("DOMAIN_REFS_MISSING", ("domain_refs", "ENT-", "CMD-", "STM-", "Permission", "权限")),
        ("E2E_LOCATOR_OBLIGATION_MISSING", ("data-testid", "locator", "aria", "e2e_locator")),
    ]
    for code, tokens in required_tokens:
        if not contains_any(text, tokens):
            findings.append(
                finding(
                    "FAIL",
                    code,
                    f"frontend-changeset.md must include {code.lower().replace('_', ' ')}.",
                    path=relpath(root, changeset),
                )
            )

    contract = prototype_as_frontend_contract(root, mission)
    interaction_spec = (
        contract.get("interaction_spec")
        if isinstance(contract.get("interaction_spec"), dict)
        else {}
    )
    if not interaction_spec:
        findings.append(
            finding(
                "FAIL",
                "INTERACTION_SPEC_CONTRACT_MISSING",
                "prototype-as-frontend contract must include interaction_spec.",
                path=relpath(root, prototype_as_frontend_contract_path(root, mission)),
            )
        )

    # 门A：结构化上游覆盖（frontend 版 UPSTREAM_SUC_NOT_IN_GRAPH）。
    # PRD flow-step 全集 ⊆ 所有 changeset surface 的 traces_to 并集（∪ 结构化 N/A 豁免）。
    if changeset.exists():
        surfaces = parse_frontend_changeset_surfaces(text)
        if not surfaces:
            findings.append(
                finding(
                    "FAIL",
                    "FRONTEND_CHANGESET_SURFACES_UNPARSEABLE",
                    "frontend-changeset.md 存在但未解析出任何 SURF 机器表行：散文无法对账上游覆盖。",
                    path=relpath(root, changeset),
                )
            )
        prd_flowsteps = prd_flowsteps_for_mission(root, mission)
        na_flowsteps, _exemptions = parse_frontend_na_flowsteps(text, prd_flowsteps)
        findings.extend(
            frontend_upstream_completeness_findings(
                changeset_surfaces=surfaces,
                prd_flowsteps=prd_flowsteps,
                na_flowsteps=na_flowsteps,
            )
        )
        findings.extend(
            frontend_na_stale_findings(na_flowsteps=na_flowsteps, changeset_surfaces=surfaces)
        )

    status, failed_checks = apply_compat_warning(args, findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "prototype-as-frontend.changeset-check",
            "mission_id": mission,
            "frontend_changeset": relpath(root, changeset),
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def cmd_prototype_as_frontend_path_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    project_root = frontend_project_root_from_contract(root, mission)
    findings: list[dict[str, object]] = []
    if project_root is None:
        findings.append(
            finding(
                "FAIL",
                "FRONTEND_PROJECT_ROOT_MISSING",
                "prototype-as-frontend contract must resolve frontend_project.root.",
                path=relpath(root, prototype_as_frontend_contract_path(root, mission)),
            )
        )
    else:
        for rel, code in (
            ("app", "FRONTEND_APP_DIR_MISSING"),
            ("mocks", "MSW_MOCKS_DIR_MISSING"),
            ("lib/types", "SHARED_TYPES_DRAFT_MISSING"),
        ):
            path = project_root / rel
            if not path.exists():
                findings.append(
                    finding(
                        "FAIL",
                        code,
                        f"frontend project path missing: {rel}",
                        path=relpath(root, path),
                    )
                )

    changeset_text = read_text_if_exists(frontend_changeset_path(root, mission))
    if not contains_any(
        changeset_text, ("happy", "错误", "error", "empty", "空态", "permission", "权限")
    ):
        findings.append(
            finding(
                "FAIL",
                "USER_PATH_STATE_COVERAGE_MISSING",
                "frontend-changeset.md must cover happy / error / empty / permission paths or explicit N/A reasons.",
                path=relpath(root, frontend_changeset_path(root, mission)),
            )
        )

    # 门B（可达性下沉 E2E）：frontend_engineering 路线下，PRD 每条流步骤都必须有
    # 一条 e2e_obligation（status=required，或 status=accepted_alternative 且写明理由），
    # 让“每条用户路径可达”的证明落到 verify 阶段的 E2E 上而非靠人肉走查。
    contract = prototype_as_frontend_contract(root, mission)
    prd_flowsteps = prd_flowsteps_for_mission(root, mission)
    coverage = frontend_flowstep_obligation_coverage(
        prd_flowsteps, contract_e2e_obligations(contract)
    )
    for flow_step in coverage["uncovered_flowsteps"]:
        findings.append(
            finding(
                "FAIL",
                "FLOWSTEP_E2E_OBLIGATION_MISSING",
                f"PRD 流步骤 {flow_step} 缺少 e2e_obligation（required 或带理由的 "
                "accepted_alternative）：frontend_engineering 路线的可达性须下沉到 E2E 证明。",
                path=relpath(root, prototype_as_frontend_contract_path(root, mission)),
            )
        )

    status, failed_checks = apply_compat_warning(args, findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "prototype-as-frontend.path-check",
            "mission_id": mission,
            "frontend_project_root": relpath(root, project_root) if project_root else None,
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def cmd_prototype_as_frontend_drift_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    contract_path = prototype_as_frontend_contract_path(root, mission)
    contract = prototype_as_frontend_contract(root, mission)
    findings: list[dict[str, object]] = []

    interaction_spec = (
        contract.get("interaction_spec")
        if isinstance(contract.get("interaction_spec"), dict)
        else {}
    )
    drift_checks = (
        interaction_spec.get("drift_checks")
        if isinstance(interaction_spec.get("drift_checks"), dict)
        else {}
    )
    for key in ("spec_vs_prd_drift", "frontend_vs_spec_drift", "feedback_not_synced"):
        value = drift_checks.get(key)
        if is_placeholder_text(value):
            findings.append(
                finding(
                    "FAIL",
                    "DRIFT_CHECK_UNRESOLVED",
                    f"{key} must be explicitly resolved to none / not_applicable before gate.",
                    path=relpath(root, contract_path),
                    drift_key=key,
                )
            )
        elif str(value).strip().lower() not in {"none", "0", "无", "not_applicable", "n/a"}:
            findings.append(
                finding(
                    "FAIL",
                    "DRIFT_DETECTED",
                    f"{key} is not resolved.",
                    path=relpath(root, contract_path),
                    drift_key=key,
                    value=value,
                )
            )

    findings.extend(
        contract_feedback_sync_findings(root, mission, "prototype-as-frontend.contract.yaml")
    )
    status, failed_checks = apply_compat_warning(args, findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "prototype-as-frontend.drift-check",
            "mission_id": mission,
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def _prototype_as_frontend_user_walkthrough_check(root: Path, mission: str, args: argparse.Namespace) -> dict[str, Any]:
    walkthrough_path = (
        root
        / "harness-runtime"
        / "harness"
        / "traces"
        / mission
        / "user-walkthrough.md"
    )
    findings: list[dict[str, object]] = []
    if not walkthrough_path.exists():
        findings.append(
            finding(
                "FAIL",
                "USER_WALKTHROUGH_MISSING",
                "prototype-as-frontend route requires a user browser walkthrough record before gate PASS.",
                path=relpath(root, walkthrough_path),
            )
        )

    _document, approvals = load_approvals(root)
    matches = [
        record
        for record in approvals
        if approval_matches(
            record,
            mission=mission,
            approval_type="checkpoint",
            stage="interaction",
            status="approved",
        )
    ]
    if not matches:
        findings.append(
            finding(
                "FAIL",
                "USER_WALKTHROUGH_APPROVAL_MISSING",
                "prototype-as-frontend route requires `harness approval append --type checkpoint --stage interaction --status approved` after user walkthrough.",
            )
        )

    status, failed_checks = apply_compat_warning(args, findings)
    return {
        "status": status,
        "control": "prototype-as-frontend.user-walkthrough-check",
        "mission_id": mission,
        "walkthrough_path": relpath(root, walkthrough_path),
        "approval": matches[-1] if matches else None,
        "findings": findings,
        "failed_checks": failed_checks,
    }


def cmd_prototype_as_frontend_gate_run(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    checks: dict[str, dict[str, Any]] = {}
    failed_checks: list[dict[str, Any]] = []
    for name, handler, extra in (
        ("interaction_spec_check", cmd_interaction_spec_check, {}),
        ("interaction_ux_quality_check", cmd_interaction_ux_quality_check, {}),
        ("changeset_check", cmd_prototype_as_frontend_changeset_check, {}),
        ("path_check", cmd_prototype_as_frontend_path_check, {}),
        ("alignment_check", cmd_alignment_check, {"stage": "interaction"}),
        ("drift_check", cmd_prototype_as_frontend_drift_check, {}),
    ):
        check_args = argparse.Namespace(**vars(args))
        for key, value in extra.items():
            setattr(check_args, key, value)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            handler(check_args)
        try:
            result = json.loads(buf.getvalue())
        except json.JSONDecodeError:
            result = {"status": "BLOCKED", "failed_checks": [{"check": name, "status": "BLOCKED"}]}
        checks[name] = result
        if result.get("status") not in {"PASS", "WARN"}:
            for item in result.get("failed_checks") or result.get("findings") or []:
                if isinstance(item, dict):
                    failed_checks.append({"check": name, **item})
            if not (result.get("failed_checks") or result.get("findings")):
                failed_checks.append({"check": name, "status": result.get("status")})

    walkthrough_result = _prototype_as_frontend_user_walkthrough_check(root, mission, args)
    checks["user_walkthrough_check"] = walkthrough_result
    if walkthrough_result.get("status") not in {"PASS", "WARN"}:
        for item in walkthrough_result.get("failed_checks") or walkthrough_result.get("findings") or []:
            if isinstance(item, dict):
                failed_checks.append({"check": "user_walkthrough_check", **item})

    status = (
        "FAIL"
        if failed_checks
        else (
            "WARN"
            if any(r.get("status") == "WARN" for r in checks.values())
            else "PASS"
        )
    )
    payload = {
        "status": status,
        "control": "prototype-as-frontend.gate-run",
        "mission_id": mission,
        "checks": checks,
        "failed_checks": failed_checks,
    }
    reports_dir = mission_stage_dir(root, mission) / "gate-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "prototype-as-frontend-gate.json"
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["report_path"] = relpath(root, report_path)
    return emit_payload(args, payload)


__all__ = [
    "cmd_prototype_as_frontend_changeset_check",
    "cmd_prototype_as_frontend_path_check",
    "cmd_prototype_as_frontend_drift_check",
    "cmd_prototype_as_frontend_gate_run",
]
