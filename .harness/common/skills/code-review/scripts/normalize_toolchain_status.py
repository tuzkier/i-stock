#!/usr/bin/env python3
"""Normalize Harness test-toolchain plan/run artifacts into toolchain-status.json."""

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


def normalize(plan: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    run_by_tool: dict[str, list[dict[str, Any]]] = {}
    for item in run.get("tool_runs") or []:
        if isinstance(item, dict):
            run_by_tool.setdefault(str(item.get("tool")), []).append(item)

    obligations = []
    for task in plan.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        satisfied = []
        missing = []
        if task.get("missing_obligation"):
            missing.append(
                {
                    "capability": "test_obligation",
                    "reason": "task_lacks_test_obligation",
                    "selected_tool": None,
                }
            )
        for capability, detail in (task.get("capabilities") or {}).items():
            tool = (detail or {}).get("selected_tool")
            runs = run_by_tool.get(str(tool), [])
            has_pass = any(((entry.get("result") or {}).get("status") == "pass") for entry in runs)
            has_planned = any(((entry.get("result") or {}).get("status") == "planned") for entry in runs)
            configured = bool((detail or {}).get("configured"))
            if has_pass or (configured and not runs):
                satisfied.append(capability)
            elif has_planned:
                missing.append(
                    {
                        "capability": capability,
                        "reason": "tool_command_planned_not_run",
                        "selected_tool": tool,
                    }
                )
            else:
                missing.append(
                    {
                        "capability": capability,
                        "reason": "tool_missing_or_failed",
                        "selected_tool": tool,
                    }
                )
        obligations.append(
            {
                "task_id": task.get("task_id"),
                "obligation_source": task.get("obligation_source"),
                "inferred_fields": task.get("inferred_fields") or [],
                "risk_level": task.get("risk_level"),
                "surfaces": task.get("surfaces") or [],
                "required_capabilities": task.get("required_capabilities") or [],
                "satisfied_capabilities": satisfied,
                "missing_capabilities": missing,
                "evidence_required": task.get("evidence_required") or [],
            }
        )

    reports: dict[str, list[dict[str, Any]]] = {
        "test_result": [],
        "coverage": [],
        "diff_coverage": [],
        "mutation": [],
        "ui_e2e": [],
        "a11y": [],
        "api_contract": [],
    }
    category_map = {
        "test_result": "test_result",
        "coverage": "coverage",
        "diff_coverage": "diff_coverage",
        "mutation": "mutation",
        "frontend_unit_component": "ui_e2e",
        "e2e_ui": "ui_e2e",
    }
    for tool in plan.get("toolchain") or []:
        if not isinstance(tool, dict):
            continue
        category = category_map.get(str(tool.get("category")))
        if not category:
            continue
        reports.setdefault(category, []).append(
            {
                "tool": tool.get("tool"),
                "configured": tool.get("configured"),
                "available": tool.get("available"),
                "report_paths": tool.get("report_paths") or [],
                "runs": run_by_tool.get(str(tool.get("tool")), []),
            }
        )

    missing_capabilities = [
        {"task_id": item["task_id"], **missing}
        for item in obligations
        for missing in item.get("missing_capabilities") or []
    ]
    decision_gate_reasons = plan.get("decision_gate_reasons") or []
    inferred_obligations = [
        {"task_id": item.get("task_id"), "source": item.get("obligation_source"), "inferred_fields": item.get("inferred_fields") or []}
        for item in obligations
        if item.get("obligation_source") != "explicit"
    ]
    status = "BLOCKED" if decision_gate_reasons else "FAIL" if missing_capabilities else "PASS"
    probe = plan.get("probe") or {}
    return {
        "schema_version": 1,
        "type": "toolchain_status",
        "mission_id": plan.get("mission_id"),
        "status": status,
        "changed_files": probe.get("changed_files") or {},
        "test_inventory": probe.get("test_inventory") or {},
        "obligations": obligations,
        "reports": reports,
        "required_evidence": probe.get("required_evidence") or {},
        "trace_artifacts": probe.get("trace_artifacts") or [],
        "toolchain_signals": probe.get("signals") or [],
        "missing_capabilities": missing_capabilities,
        "inferred_obligations": inferred_obligations,
        "decision_gate_reasons": decision_gate_reasons,
        "toolchain_plan_status": plan.get("status"),
        "toolchain_run_status": run.get("status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--run")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = normalize(load_json(Path(args.plan)), load_json(Path(args.run)) if args.run else {})
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] in {"FAIL", "BLOCKED"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
