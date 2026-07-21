#!/usr/bin/env python3
"""Normalize Harness E2E plan/run artifacts into e2e-status.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def run_status(entry: dict[str, Any]) -> str:
    result = entry.get("result")
    if isinstance(result, dict) and result.get("status"):
        return str(result.get("status"))
    return str(entry.get("status") or "")


def normalize_status(value: Any) -> str:
    status = str(value or "").upper().replace("-", "_")
    aliases = {
        "PASS": "PASS",
        "PASSED": "PASS",
        "FAIL": "FAIL",
        "FAILED": "FAIL",
        "BLOCKED": "BLOCKED",
        "WARN": "WARN",
        "WARNING": "WARN",
        "PLANNED": "PLANNED",
        "PLAN_ONLY": "PLANNED",
        "PLANNED_NOT_RUN": "PLANNED_NOT_RUN",
        "NOT_RUN": "PLANNED_NOT_RUN",
    }
    return aliases.get(status, status)


def normalize(plan: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    run_by_tool: dict[str, list[dict[str, Any]]] = {}
    run_entries = run.get("tool_runs") or run.get("runs") or []
    for item in run_entries:
        if isinstance(item, dict):
            run_by_tool.setdefault(str(item.get("tool")), []).append(item)

    obligations: list[dict[str, Any]] = []
    for task in plan.get("obligations") or plan.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        satisfied: list[str] = []
        missing: list[dict[str, Any]] = []
        for capability, detail in (task.get("capabilities") or {}).items():
            if not isinstance(detail, dict):
                continue
            tool = detail.get("selected_tool")
            tool_runs = run_by_tool.get(str(tool), [])
            statuses = {normalize_status(run_status(entry)) for entry in tool_runs}
            has_pass = "PASS" in statuses
            has_failed = bool(statuses & {"FAIL", "BLOCKED"})
            has_planned = bool(statuses & {"PLANNED", "PLANNED_NOT_RUN"})
            configured = bool(detail.get("configured"))
            if has_pass:
                satisfied.append(str(capability))
            elif has_failed:
                missing.append({
                    "capability": capability,
                    "reason": "e2e_tool_not_run_or_failed",
                    "selected_tool": tool,
                })
            elif not configured:
                missing.append({
                    "capability": capability,
                    "reason": "e2e_tool_missing_or_unconfigured",
                    "selected_tool": tool,
                })
            elif has_planned:
                missing.append({
                    "capability": capability,
                    "reason": "e2e_command_planned_not_run",
                    "selected_tool": tool,
                })
            else:
                missing.append({
                    "capability": capability,
                    "reason": "e2e_tool_not_run_or_failed",
                    "selected_tool": tool,
                })
        obligations.append({
            "task_id": task.get("task_id"),
            "obligation_source": task.get("obligation_source"),
            "inferred_fields": task.get("inferred_fields") or [],
            "risk_level": task.get("risk_level"),
            "user_surfaces": task.get("user_surfaces") or [],
            "required_capabilities": task.get("required_capabilities") or [],
            "satisfied_capabilities": satisfied,
            "missing_capabilities": missing,
            "evidence_required": task.get("evidence_required") or [],
            "accepted_alternatives": task.get("accepted_alternatives") or {},
        })

    missing_capabilities = [
        {"task_id": obligation.get("task_id"), **missing}
        for obligation in obligations
        for missing in obligation.get("missing_capabilities") or []
    ]
    missing_capabilities.extend(
        item for item in run.get("missing_capabilities") or [] if isinstance(item, dict)
    )
    decision_gate_reasons = plan.get("decision_gate_reasons") or []
    artifacts = run.get("artifacts") if isinstance(run.get("artifacts"), dict) else {}
    if not artifacts:
        artifacts = ((plan.get("artifact_policy") or {}).get("collect") or {}) if isinstance(plan.get("artifact_policy"), dict) else {}
    artifacts = {
        "html_report": artifacts.get("html_report", ""),
        "trace": artifacts.get("trace") or [],
        "video": artifacts.get("video") or [],
        "screenshots": artifacts.get("screenshots") or [],
    }
    flaky_signals = [
        item for item in run.get("flaky_signals") or []
    ] + [
        item for entry in run_entries if isinstance(entry, dict) for item in entry.get("flaky_signals") or []
    ]
    skipped_tests = [
        item for item in run.get("skipped_tests") or []
    ] + [
        item for entry in run_entries if isinstance(entry, dict) for item in entry.get("skipped_tests") or []
    ]

    run_status_value = normalize_status(run.get("status"))
    plan_status_value = normalize_status(plan.get("status"))
    failed_runs = [
        entry for entry in run_entries
        if isinstance(entry, dict)
        and (normalize_status(run_status(entry)) in {"FAIL", "BLOCKED"} or int(entry.get("failed") or 0) > 0)
    ]
    planned_not_run = [
        entry for entry in run_entries
        if isinstance(entry, dict)
        and normalize_status(run_status(entry)) in {"PLANNED", "PLANNED_NOT_RUN"}
    ]

    if planned_not_run and not any(item.get("reason") == "e2e_command_planned_not_run" for item in missing_capabilities):
        for obligation in obligations:
            for capability in obligation.get("required_capabilities") or []:
                missing_capabilities.append({
                    "task_id": obligation.get("task_id"),
                    "capability": capability,
                    "reason": "e2e_command_planned_not_run",
                    "selected_tool": None,
                })

    if decision_gate_reasons:
        status = "BLOCKED"
    elif missing_capabilities or failed_runs or planned_not_run or run_status_value in {"FAIL", "BLOCKED", "PLANNED_NOT_RUN"}:
        status = "FAIL"
    elif skipped_tests or flaky_signals:
        status = "WARN"
    elif run_status_value in {"PLANNED", "WARN"}:
        status = "WARN"
    elif plan_status_value in {"FAIL", "BLOCKED", "WARN"} and not run_entries:
        status = plan_status_value
    else:
        status = "PASS"

    return {
        "schema_version": 1,
        "type": "e2e_status",
        "mission_id": plan.get("mission_id") or run.get("mission_id"),
        "status": status,
        "obligations": obligations,
        "runs": run_entries,
        "artifacts": artifacts,
        "missing_capabilities": missing_capabilities,
        "decision_gate_reasons": decision_gate_reasons,
        "flaky_signals": flaky_signals,
        "skipped_tests": skipped_tests,
        "e2e_plan_status": plan.get("status"),
        "e2e_run_status": run.get("status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mission-id")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--run")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = normalize(load_json(Path(args.plan)), load_json(Path(args.run)) if args.run else {})
    if args.mission_id and not result.get("mission_id"):
        result["mission_id"] = args.mission_id
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] in {"FAIL", "BLOCKED"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
