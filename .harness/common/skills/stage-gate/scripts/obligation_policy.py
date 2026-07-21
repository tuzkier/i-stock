#!/usr/bin/env python3
"""Infer minimal delivery obligations from mission/task surfaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to infer obligations") from exc


SURFACE_RULES: list[tuple[set[str], list[dict[str, Any]]]] = [
    (
        {"backend_logic", "business_logic", "public_api", "backend_api"},
        [
            {"type": "tdd", "required_evidence": ["test_result"], "required_roles": ["tdd-reviewer"]},
            {"type": "correctness", "required_evidence": ["reviewer_verdict"], "required_roles": ["correctness-reviewer"]},
        ],
    ),
    (
        {"frontend_ui", "frontend_component", "web_ui", "user_journey"},
        [
            {"type": "tdd", "required_evidence": ["test_result"], "required_roles": ["tdd-reviewer"]},
            {"type": "e2e", "required_evidence": ["e2e_trace"], "required_roles": ["e2e-reviewer"]},
            {"type": "acceptance", "required_evidence": ["manual_acceptance"], "required_roles": ["verification-effectiveness-reviewer"]},
        ],
    ),
    (
        {"auth", "permission", "workspace_boundary"},
        [
            {"type": "security", "required_evidence": ["negative_test"], "required_roles": ["security-reviewer"]},
            {"type": "e2e", "required_evidence": ["negative_path"], "required_roles": ["e2e-reviewer"]},
        ],
    ),
    (
        {"migration", "data_consistency"},
        [
            {"type": "integration", "required_evidence": ["integration_result"], "required_roles": ["dependency-validity-reviewer"]},
            {"type": "rollback", "required_evidence": ["rollback_or_recovery"], "required_roles": ["data-migration-reviewer"]},
        ],
    ),
]


def normalize_surfaces(task: dict[str, Any]) -> list[str]:
    surfaces: list[str] = []
    for key in ("surfaces", "user_surfaces"):
        values = task.get(key)
        if isinstance(values, list):
            surfaces.extend(str(value) for value in values)
    for block_name in ("test_obligation", "e2e_obligation"):
        block = task.get(block_name)
        if not isinstance(block, dict):
            continue
        for key in ("surfaces", "user_surfaces"):
            values = block.get(key)
            if isinstance(values, list):
                surfaces.extend(str(value) for value in values)
    return sorted(set(surfaces))


ACCEPTANCE_TRACE_PREFIXES = ("SCN-", "REQ-", "US-", "UC-")


def infer_obligations(mission_id: str, acceptance_scenarios: list[str], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []

    def add_obligation(kind: str, acceptance_refs: list[str], task_refs: list[str], surfaces: list[str], evidence: list[str], roles: list[str], risk: str = "medium") -> None:
        key = (kind, tuple(acceptance_refs), tuple(task_refs))
        if any((item["type"], tuple(item["traces_to"].get("acceptance") or []), tuple(item["traces_to"].get("task") or [])) == key for item in obligations):
            return
        obligations.append(
            {
                "id": f"OBL-{len(obligations) + 1:03d}",
                "mission_id": mission_id,
                "type": kind,
                "risk": risk,
                "surfaces": surfaces,
                "traces_to": {"acceptance": acceptance_refs, "task": task_refs},
                "required_evidence": evidence,
                "required_roles": roles,
                "blocking": True,
                "source": "inferred",
            }
        )

    if acceptance_scenarios:
        add_obligation("correctness", acceptance_scenarios, [], [], ["reviewer_verdict"], ["correctness-reviewer"])
        add_obligation("verification", acceptance_scenarios, [], [], ["command_result", "result_evidence"], ["verification-effectiveness-reviewer"])

    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = str(task.get("id", ""))
        acceptance_refs = [
            str(ref)
            for ref in task.get("traces_to") or []
            if str(ref).startswith(ACCEPTANCE_TRACE_PREFIXES)
        ]
        surfaces = normalize_surfaces(task)
        for trigger_surfaces, rules in SURFACE_RULES:
            if not trigger_surfaces.intersection(surfaces):
                continue
            for rule in rules:
                add_obligation(
                    rule["type"],
                    acceptance_refs,
                    [task_id] if task_id else [],
                    surfaces,
                    rule["required_evidence"],
                    rule["required_roles"],
                    risk="high" if {"auth", "permission", "migration"}.intersection(surfaces) else "medium",
                )
    return obligations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--acceptance-scenario", action="append", dest="acceptance_scenarios", default=[])
    parser.add_argument("--acceptance-criteria", action="append", dest="legacy_acceptance_scenarios", default=[], help=argparse.SUPPRESS)
    parser.add_argument("--tasks-json", help="Path to a JSON file containing a task list")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    tasks: list[dict[str, Any]] = []
    if args.tasks_json:
        data = json.loads(Path(args.tasks_json).read_text(encoding="utf-8"))
        tasks = data if isinstance(data, list) else data.get("tasks", [])
    acceptance_scenarios = [*args.acceptance_scenarios, *args.legacy_acceptance_scenarios]
    obligations = infer_obligations(args.mission_id, acceptance_scenarios, tasks)
    payload = {"obligations": obligations}
    print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else yaml.safe_dump(payload, sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
