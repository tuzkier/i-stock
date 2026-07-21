#!/usr/bin/env python3
"""Deterministic Evidence Graph Gate checks."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to check Evidence Graphs") from exc


@dataclass
class Finding:
    level: str
    code: str
    message: str


def add(findings: list[Finding], level: str, code: str, message: str) -> None:
    findings.append(Finding(level, code, message))


def load_graph(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.suffix in {".yaml", ".yml"} else json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "evidence_graph" in data:
        graph = data["evidence_graph"]
    else:
        graph = data
    return graph if isinstance(graph, dict) else {}


def ids(items: list[Any]) -> set[str]:
    return {str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")}


def path_is_placeholder(path: str) -> bool:
    return "{{" in path or "}}" in path or path.startswith("<")


def check_graph(graph: dict[str, Any], root: Path, current_git_ref: str | None = None) -> list[Finding]:
    findings: list[Finding] = []
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), dict) else {}
    obligations = [item for item in nodes.get("obligations") or [] if isinstance(item, dict)]
    evidence = [item for item in nodes.get("evidence") or [] if isinstance(item, dict)]
    verdicts = [item for item in nodes.get("role_verdicts") or [] if isinstance(item, dict)]
    gate_decisions = [item for item in nodes.get("gate_decisions") or [] if isinstance(item, dict)]

    obligation_ids = ids(obligations)
    evidence_by_obligation: dict[str, list[dict[str, Any]]] = {oid: [] for oid in obligation_ids}
    for item in evidence:
        eid = item.get("id", "<evidence>")
        for field in ("id", "type", "status", "observed_at", "git_ref", "covers"):
            if not item.get(field):
                add(findings, "FAIL", "invalid_evidence", f"{eid} lacks {field}")
        path = item.get("path")
        if path and not path_is_placeholder(str(path)) and not (root / str(path)).exists():
            add(findings, "FAIL", "evidence_path_missing", f"Evidence path does not exist: {path}")
        git_ref = item.get("git_ref")
        if current_git_ref and git_ref and git_ref != current_git_ref:
            add(findings, "FAIL", "stale_evidence", f"{eid} git_ref {git_ref} does not match {current_git_ref}")
        covers = item.get("covers") if isinstance(item.get("covers"), dict) else {}
        for oid in covers.get("obligations") or []:
            if oid not in obligation_ids:
                add(findings, "FAIL", "evidence_unknown_obligation", f"{eid} covers unknown obligation: {oid}")
            else:
                evidence_by_obligation.setdefault(oid, []).append(item)

    for obligation in obligations:
        oid = obligation.get("id", "<obligation>")
        for field in ("id", "type", "risk", "traces_to", "required_evidence", "required_roles"):
            if not obligation.get(field):
                add(findings, "FAIL", "invalid_obligation", f"{oid} lacks {field}")
        if obligation.get("blocking") is not False:
            covered_types = {item.get("type") for item in evidence_by_obligation.get(oid, [])}
            missing = [kind for kind in obligation.get("required_evidence") or [] if kind not in covered_types]
            if missing:
                add(findings, "FAIL", "missing_blocking_obligation_evidence", f"{oid} missing evidence: {', '.join(missing)}")

    tool_fail_obligations: set[str] = set()
    for item in evidence:
        if item.get("status") == "FAIL":
            covers = item.get("covers") if isinstance(item.get("covers"), dict) else {}
            tool_fail_obligations.update(str(oid) for oid in covers.get("obligations") or [])

    for verdict in verdicts:
        rid = verdict.get("id", "<role-verdict>")
        reviewed = verdict.get("reviewed_obligations") or []
        if not reviewed:
            add(findings, "FAIL", "empty_reviewed_obligations", f"{rid} has no reviewed_obligations")
        for oid in reviewed:
            if oid not in obligation_ids:
                add(findings, "FAIL", "role_verdict_unknown_obligation", f"{rid} reviews unknown obligation: {oid}")
        if verdict.get("verdict") in {"HOLD", "BLOCKED"} and not verdict.get("blocking_gaps"):
            add(findings, "FAIL", "hold_without_blocking_gaps", f"{rid} {verdict.get('verdict')} requires blocking_gaps")
        if verdict.get("verdict") == "PASS" and tool_fail_obligations.intersection(reviewed):
            add(findings, "FAIL", "role_pass_over_programmatic_fail", f"{rid} PASS covers failed tool evidence")

    accepted_risks = [item for item in verdicts if item.get("verdict") == "PASS_WITH_RISK"]
    decisions = [item for item in gate_decisions if item.get("decision") in {"accept_risk", "accept_residual_risk"} or item.get("accepted_risk")]
    if accepted_risks and not decisions:
        add(findings, "FAIL", "accepted_risk_without_decision", "PASS_WITH_RISK requires a user Decision Gate record")

    if not findings:
        add(findings, "PASS", "evidence_graph_valid", "Evidence Graph checks passed")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--current-git-ref")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    graph = load_graph(Path(args.graph))
    findings = check_graph(graph, Path(args.root).resolve(), args.current_git_ref)
    status = "FAIL" if any(item.level == "FAIL" for item in findings) else "WARN" if any(item.level == "WARN" for item in findings) else "PASS"
    payload = {"status": status, "findings": [item.__dict__ for item in findings]}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
