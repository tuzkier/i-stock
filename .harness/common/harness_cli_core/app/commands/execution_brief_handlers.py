from __future__ import annotations

import argparse
from pathlib import Path

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.breakdown import (
    artifact_gate_findings,
    persist_last_gate_run_status,
    quality_check_findings,
    resolve_execution_brief_contract,
    self_check_findings,
    status_from_fail_findings,
    trace_ids_from_contract,
    uncovered_delta_scenarios,
)
from harness_cli_core.infra.runtime_paths import relpath


def cmd_execution_brief_self_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact, contract, error_code = resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execution-brief.self-check",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )
    findings = self_check_findings(contract)
    return emit_payload(
        args,
        {
            "status": status_from_fail_findings(findings),
            "control": "execution-brief.self-check",
            "mission": args.mission,
            "artifact": relpath(root, artifact),
            "findings": findings,
        },
    )


def cmd_execution_brief_gate_run(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact, contract, error_code = resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execution-brief.gate-run",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )

    quality_findings = quality_check_findings(contract)
    quality_status = status_from_fail_findings(quality_findings)
    gate_findings = artifact_gate_findings(root, args.mission, relpath)
    gate_status = status_from_fail_findings(gate_findings)
    status = "PASS" if quality_status == "PASS" and gate_status == "PASS" else "FAIL"
    failed_checks = [finding["code"] for finding in (quality_findings + gate_findings) if finding.get("level") == "FAIL"]
    persist_last_gate_run_status(artifact, status)

    return emit_payload(
        args,
        {
            "status": status,
            "control": "execution-brief.gate-run",
            "mission": args.mission,
            "artifact": relpath(root, artifact),
            "phase_results": [
                {"name": "quality_check", "status": quality_status, "findings": quality_findings},
                {"name": "artifact_gate", "status": gate_status, "findings": gate_findings},
            ],
            "failed_checks": failed_checks,
        },
    )


def cmd_execution_brief_check_coverage(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    spec_mode = args.spec_mode or "strict"
    artifact, contract, error_code = resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execution-brief.check-coverage",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )
    total_scenarios, uncovered = uncovered_delta_scenarios(root, args.mission, trace_ids_from_contract(contract))
    status = "FAIL" if uncovered and spec_mode == "strict" else "PASS"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "execution-brief.check-coverage",
            "mission": args.mission,
            "spec_mode": spec_mode,
            "total_scenarios": total_scenarios,
            "uncovered": uncovered,
        },
    )
