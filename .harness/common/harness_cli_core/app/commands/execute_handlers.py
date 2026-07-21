from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from harness_cli_core.app.output import emit_payload, fail_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.breakdown import resolve_execution_brief_contract
from harness_cli_core.domain.execute import (
    STOP_EVENT_KINDS,
    append_stop_event,
    build_effective_overlay_state,
    effective_overlay_path,
    execute_artifact_gate_findings,
    execute_quality_findings,
    persist_last_gate_run_status,
    resolve_execution_result_contract,
    status_from_fail_findings,
    write_effective_overlay_state,
)
from harness_cli_core.infra.runtime_paths import relpath


def cmd_execute_apply_overlay(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact, contract, error_code = resolve_execution_brief_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execute.apply-overlay",
                error_code or "execution_brief_contract_unloadable",
                f"Cannot load execution-brief contract at {relpath(root, artifact)}",
            ),
        )
    state = build_effective_overlay_state(contract, args.mission, args.task)
    state_path = effective_overlay_path(root, args.mission)
    if not args.dry_run:
        write_effective_overlay_state(state_path, state)
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "execute.apply-overlay",
            "mission": args.mission,
            "task_id": args.task,
            "dry_run": bool(args.dry_run),
            "effective_overlay": state,
            "state_path": relpath(root, state_path) if not args.dry_run else None,
        },
    )


def cmd_execute_revoke_overlay(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    state_path = effective_overlay_path(root, args.mission)
    existed = state_path.exists()
    if existed:
        try:
            state_path.unlink()
        except OSError as exc:
            return emit_payload(
                args,
                fail_payload("execute.revoke-overlay", "revoke_failed", f"Failed to remove {state_path}: {exc}"),
            )
    return emit_payload(args, {"status": "PASS", "control": "execute.revoke-overlay", "mission": args.mission, "existed": existed})


def cmd_execute_stop_event_record(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    if args.kind not in STOP_EVENT_KINDS:
        return emit_payload(
            args,
            fail_payload(
                "execute.stop-event.record",
                "invalid_stop_event_kind",
                f"--kind must be one of {sorted(STOP_EVENT_KINDS)}; got {args.kind!r}",
            ),
        )
    artifact, contract, error_code = resolve_execution_result_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execute.stop-event.record",
                error_code or "execution_result_contract_unloadable",
                f"Cannot load execution-result contract at {relpath(root, artifact)}",
            ),
        )
    try:
        event, event_count = append_stop_event(
            artifact,
            kind=args.kind,
            task_id=args.task,
            affected_paths=list(args.path or []),
            hook_source=args.hook_source or "manual",
        )
    except yaml.YAMLError as exc:
        return emit_payload(
            args,
            fail_payload("execute.stop-event.record", "execution_result_contract_invalid_yaml", f"Failed to parse {artifact}: {exc}"),
        )
    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "execute.stop-event.record",
            "mission": args.mission,
            "event": event,
            "stop_events_count": event_count,
        },
    )


def cmd_execute_check_ready(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact, contract, error_code = resolve_execution_result_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execute.check-ready",
                error_code or "execution_result_contract_unloadable",
                f"Cannot load execution-result contract at {relpath(root, artifact)}",
            ),
        )
    findings = execute_quality_findings(root, args.mission, contract)
    return emit_payload(
        args,
        {
            "status": status_from_fail_findings(findings),
            "control": "execute.check-ready",
            "mission": args.mission,
            "artifact": relpath(root, artifact),
            "findings": findings,
        },
    )


def cmd_execute_gate_run(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    artifact, contract, error_code = resolve_execution_result_contract(root, args.mission)
    if contract is None:
        return emit_payload(
            args,
            fail_payload(
                "execute.gate-run",
                error_code or "execution_result_contract_unloadable",
                f"Cannot load execution-result contract at {relpath(root, artifact)}",
            ),
        )
    quality_findings = execute_quality_findings(root, args.mission, contract)
    quality_status = status_from_fail_findings(quality_findings)
    gate_findings = execute_artifact_gate_findings(root, args.mission, relpath)
    gate_status = status_from_fail_findings(gate_findings)
    status = "PASS" if quality_status == "PASS" and gate_status == "PASS" else "FAIL"
    failed_checks = [finding["code"] for finding in (quality_findings + gate_findings) if finding.get("level") == "FAIL"]
    persist_last_gate_run_status(artifact, status)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "execute.gate-run",
            "mission": args.mission,
            "artifact": relpath(root, artifact),
            "phase_results": [
                {"name": "quality_check", "status": quality_status, "findings": quality_findings},
                {"name": "artifact_gate", "status": gate_status, "findings": gate_findings},
            ],
            "failed_checks": failed_checks,
        },
    )
