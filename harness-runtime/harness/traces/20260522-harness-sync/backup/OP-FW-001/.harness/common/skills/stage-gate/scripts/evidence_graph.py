#!/usr/bin/env python3
"""Build and normalize minimal Harness Evidence Graph slices."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to build Evidence Graph slices") from exc


def empty_graph(mission_id: str) -> dict[str, Any]:
    return {
        "mission_id": mission_id,
        "nodes": {
            "acceptance_criteria": [],
            "tasks": [],
            "obligations": [],
            "evidence": [],
            "role_verdicts": [],
            "gate_decisions": [],
            "acceptance_results": [],
        },
        "edges": [],
    }


def find_control_contract(path: Path) -> dict[str, Any]:
    if path.suffix.lower() not in {".yaml", ".yml"}:
        text = path.read_text(encoding="utf-8")
        match = re.search(r"(?:Contract|Control Contract): `([^`]+\.ya?ml)`", text)
        if not match:
            return {}
        candidate = path.parent / match.group(1)
        path = candidate if candidate.exists() else path.parents[0] / match.group(1)
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if isinstance(parsed, dict):
        contract = parsed.get("control_contract")
        if isinstance(contract, dict):
            return contract
    return {}


def append_unique(items: list[dict[str, Any]], item: dict[str, Any]) -> None:
    item_id = item.get("id")
    if item_id and any(existing.get("id") == item_id for existing in items):
        return
    items.append(item)


def normalize_legacy_reviewers(contract: dict[str, Any]) -> list[dict[str, Any]]:
    verdicts: list[dict[str, Any]] = []
    for reviewer in contract.get("reviewers") or []:
        if not isinstance(reviewer, dict):
            continue
        rid = reviewer.get("id") or f"RVW-{len(verdicts) + 1:03d}"
        reviewed = reviewer.get("reviewed_obligations") or reviewer.get("obligation_refs") or ["OBL-LEGACY-REVIEW"]
        verdicts.append(
            {
                "id": rid if str(rid).startswith("RVW-") else f"RVW-{rid}",
                "role": reviewer.get("role", "reviewer"),
                "verdict": reviewer.get("verdict", "BLOCKED"),
                "reviewed_obligations": reviewed,
                "review_basis": reviewer.get("review_basis", {}),
                "matrix": reviewer.get("matrix", []),
                "findings": reviewer.get("findings", []),
                "blocking_gaps": reviewer.get("blocking_gaps", []),
                "non_blocking_risks": reviewer.get("non_blocking_risks", []),
            }
        )
    return verdicts


def merge_contract(graph: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    nodes = graph["nodes"]
    mission_id = contract.get("mission_id") or graph["mission_id"]
    graph["mission_id"] = mission_id

    for ac in contract.get("acceptance_criteria") or []:
        if isinstance(ac, dict):
            append_unique(nodes["acceptance_criteria"], ac)
    for task in contract.get("tasks") or []:
        if isinstance(task, dict):
            append_unique(nodes["tasks"], task)
    for obligation in contract.get("obligations") or []:
        if isinstance(obligation, dict):
            append_unique(nodes["obligations"], obligation)
    for evidence in [*(contract.get("command_evidence") or []), *(contract.get("result_evidence") or []), *(contract.get("evidence") or [])]:
        if isinstance(evidence, dict):
            append_unique(nodes["evidence"], evidence)
    for verdict in [*(contract.get("role_verdicts") or []), *normalize_legacy_reviewers(contract)]:
        if isinstance(verdict, dict):
            append_unique(nodes["role_verdicts"], verdict)
    for decision in contract.get("gate_decisions") or []:
        if isinstance(decision, dict):
            append_unique(nodes["gate_decisions"], decision)
    for result in contract.get("acceptance_results") or []:
        if isinstance(result, dict):
            append_unique(nodes["acceptance_results"], result)

    for obligation in nodes["obligations"]:
        oid = obligation.get("id")
        traces = obligation.get("traces_to") or {}
        for ac in traces.get("ac") or []:
            graph["edges"].append({"from": ac, "to": oid, "type": "requires"})
        for task in traces.get("task") or []:
            graph["edges"].append({"from": task, "to": oid, "type": "requires"})
    for evidence in nodes["evidence"]:
        eid = evidence.get("id")
        covers = evidence.get("covers") or {}
        for oid in covers.get("obligations") or evidence.get("obligation_refs") or []:
            graph["edges"].append({"from": oid, "to": eid, "type": "supported_by"})
    for verdict in nodes["role_verdicts"]:
        rid = verdict.get("id")
        for oid in verdict.get("reviewed_obligations") or []:
            graph["edges"].append({"from": oid, "to": rid, "type": "reviewed_by"})
    return graph


def load_structured(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def merge_evidence_store(graph: dict[str, Any], store: dict[str, Any]) -> dict[str, Any]:
    nodes = graph["nodes"]
    for evidence in store.get("evidence") or []:
        if isinstance(evidence, dict):
            append_unique(nodes["evidence"], evidence)
    for link in store.get("links") or []:
        if isinstance(link, dict) and link.get("from") and link.get("to"):
            graph["edges"].append({"from": link.get("to"), "to": link.get("from"), "type": link.get("type") or "supported_by"})
    return graph


def graph_from_artifacts(paths: list[Path], mission_id: str | None = None, evidence_stores: list[Path] | None = None) -> dict[str, Any]:
    graph: dict[str, Any] | None = None
    for path in paths:
        contract = find_control_contract(path)
        if not contract:
            continue
        if graph is None:
            graph = empty_graph(mission_id or contract.get("mission_id", "UNKNOWN"))
        merge_contract(graph, contract)
    graph = graph or empty_graph(mission_id or "UNKNOWN")
    for store_path in evidence_stores or []:
        if store_path.exists():
            merge_evidence_store(graph, load_structured(store_path))
    return graph


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", required=True)
    parser.add_argument("--mission-id")
    parser.add_argument("--evidence-store", action="append", default=[])
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    graph = graph_from_artifacts([Path(path) for path in args.artifact], mission_id=args.mission_id, evidence_stores=[Path(path) for path in args.evidence_store])
    payload = {"evidence_graph": graph}
    text = json.dumps(payload, ensure_ascii=False, indent=2) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
