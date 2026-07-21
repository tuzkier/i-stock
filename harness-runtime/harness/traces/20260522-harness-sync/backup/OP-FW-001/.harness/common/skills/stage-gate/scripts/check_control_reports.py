#!/usr/bin/env python3
"""Check control-plane reports for Stage Gate consumption."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str = ""


def add(findings: list[Finding], level: str, code: str, message: str, path: str = "") -> None:
    findings.append(Finding(level, code, message, path))


def load_report(path: Path, findings: list[Finding]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(findings, "FAIL", "invalid_control_report_json", f"{path}: {exc}", str(path))
        return None
    if not isinstance(data, dict):
        add(findings, "FAIL", "invalid_control_report", f"{path}: root must be an object", str(path))
        return None
    return data


def validate_report(path: Path, report: dict[str, Any], findings: list[Finding]) -> None:
    for field in ("schema_version", "control", "status", "gate_effect", "findings"):
        if field not in report:
            add(findings, "FAIL", "invalid_control_report", f"{path}: missing {field}", str(path))
    if report.get("schema_version") != 1:
        add(findings, "FAIL", "invalid_control_report", f"{path}: schema_version must be 1", str(path))
    if report.get("status") not in {"PASS", "WARN", "FAIL"}:
        add(findings, "FAIL", "invalid_control_report", f"{path}: invalid status {report.get('status')}", str(path))
    if report.get("gate_effect") not in {"allow", "warn", "block"}:
        add(findings, "FAIL", "invalid_control_report", f"{path}: invalid gate_effect {report.get('gate_effect')}", str(path))
    if not isinstance(report.get("findings"), list):
        add(findings, "FAIL", "invalid_control_report", f"{path}: findings must be a list", str(path))


def discover_reports(root: Path, mission_id: str | None, explicit: list[str]) -> list[Path]:
    reports = [Path(item) if Path(item).is_absolute() else root / item for item in explicit]
    if mission_id:
        traces = root / "harness-runtime" / "harness" / "traces" / mission_id
        reports.extend(sorted((traces / "controls").glob("*/*.json")))
        reports.extend(sorted((traces / "project-lint").glob("project-lint-report.json")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for report in reports:
        resolved = report.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(report)
    return unique


def check(root: Path, mission_id: str | None, reports: list[str], required_controls: list[str]) -> dict[str, Any]:
    findings: list[Finding] = []
    report_paths = discover_reports(root, mission_id, reports)
    seen_controls: set[str] = set()
    controls: list[dict[str, Any]] = []
    for path in report_paths:
        if not path.exists():
            add(findings, "FAIL", "missing_control_report", f"Control report not found: {path}", str(path))
            continue
        report = load_report(path, findings)
        if report is None:
            continue
        validate_report(path, report, findings)
        control_name = str(report.get("control") or "")
        if control_name:
            seen_controls.add(control_name)
        gate_effect = report.get("gate_effect")
        if gate_effect == "block":
            add(findings, "FAIL", "control_report_blocks_gate", f"{control_name or path.name} gate_effect=block", str(path))
        elif gate_effect == "warn":
            add(findings, "WARN", "control_report_warns_gate", f"{control_name or path.name} gate_effect=warn", str(path))
        controls.append({"path": str(path), "control": control_name, "status": report.get("status"), "gate_effect": gate_effect})

    for control in required_controls:
        if control and control not in seen_controls:
            add(findings, "FAIL", "missing_required_control_report", f"Required control report missing: {control}")

    if not findings:
        add(findings, "PASS", "control_reports_valid", "Control-plane reports allow Stage Gate to continue")
    status = "FAIL" if any(item.level == "FAIL" for item in findings) else "WARN" if any(item.level == "WARN" for item in findings) else "PASS"
    return {"status": status, "controls": controls, "findings": [item.__dict__ for item in findings]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mission-id")
    parser.add_argument("--report", action="append", default=[])
    parser.add_argument("--required-control", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = check(Path(args.root).resolve(), args.mission_id, args.report, args.required_control)
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else payload["status"])
    return 1 if payload["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
