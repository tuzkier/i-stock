#!/usr/bin/env python3
"""Resolve execute-stage role and evidence expectations by task surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required to resolve execute role policy") from exc


SURFACE_POLICY: dict[str, dict[str, Any]] = {
    "backend_api": {
        "primary": "backend-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "api_result", "coverage"],
    },
    "public_api": {
        "primary": "backend-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "api_result", "coverage"],
    },
    "backend_logic": {
        "primary": "backend-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "coverage"],
    },
    "business_logic": {
        "primary": "backend-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "coverage"],
    },
    "state_machine": {
        "primary": "backend-engineer",
        "supporting": ["test-engineer", "debugging-expert"],
        "evidence": ["fault_evidence", "boundary_evidence", "test_result"],
    },
    "concurrency": {
        "primary": "backend-engineer",
        "supporting": ["test-engineer", "debugging-expert"],
        "evidence": ["race_or_boundary_evidence", "fault_evidence", "test_result"],
    },
    "auth": {
        "primary": "security-engineer",
        "supporting": ["test-engineer", "debugging-expert"],
        "reviewers": ["security-reviewer"],
        "evidence": ["negative_tests", "fault_evidence", "regression"],
    },
    "permission": {
        "primary": "security-engineer",
        "supporting": ["test-engineer", "debugging-expert"],
        "reviewers": ["security-reviewer"],
        "evidence": ["negative_tests", "fault_evidence", "regression"],
    },
    "authorization": {
        "primary": "security-engineer",
        "supporting": ["test-engineer", "debugging-expert"],
        "reviewers": ["security-reviewer"],
        "evidence": ["negative_tests", "fault_evidence", "regression"],
    },
    "authentication": {
        "primary": "security-engineer",
        "supporting": ["test-engineer", "debugging-expert"],
        "reviewers": ["security-reviewer"],
        "evidence": ["negative_tests", "fault_evidence", "regression"],
    },
    "payload_safety": {
        "primary": "security-engineer",
        "supporting": ["test-engineer", "debugging-expert"],
        "reviewers": ["security-reviewer"],
        "evidence": ["negative_tests", "fault_evidence", "regression"],
    },
    "frontend_interaction": {
        "primary": "frontend-engineer",
        "supporting": ["interaction-engineer", "test-engineer"],
        "evidence": ["component_or_e2e", "keyboard_focus", "user_visible_assertion"],
    },
    "frontend_ui": {
        "primary": "frontend-engineer",
        "supporting": ["interaction-engineer", "test-engineer"],
        "evidence": ["component_or_e2e", "keyboard_focus", "user_visible_assertion"],
    },
    "frontend_component": {
        "primary": "frontend-engineer",
        "supporting": ["interaction-engineer", "test-engineer"],
        "evidence": ["component_or_e2e", "user_visible_assertion"],
    },
    "web_ui": {
        "primary": "frontend-engineer",
        "supporting": ["interaction-engineer", "test-engineer"],
        "evidence": ["component_or_e2e", "keyboard_focus", "user_visible_assertion"],
    },
    "frontend_visual": {
        "primary": "frontend-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["screenshot", "responsive", "contrast"],
    },
    "client_ui": {
        "primary": "client-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["client_run", "user_visible_assertion", "screenshot_or_recording"],
    },
    "client_logic": {
        "primary": "client-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["client_run", "test_result"],
    },
    "mobile": {
        "primary": "client-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["simulator_or_device_run", "screenshot_or_recording"],
    },
    "desktop": {
        "primary": "client-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["client_run", "screenshot_or_recording"],
    },
    "integration": {
        "primary": "integration-engineer",
        "supporting": ["integration-impact-expert", "test-engineer"],
        "evidence": ["contract", "failure_path", "sandbox_or_mock"],
    },
    "external_api": {
        "primary": "integration-engineer",
        "supporting": ["integration-impact-expert", "test-engineer"],
        "evidence": ["contract", "failure_path", "sandbox_or_mock"],
    },
    "webhook": {
        "primary": "integration-engineer",
        "supporting": ["integration-impact-expert", "test-engineer"],
        "evidence": ["contract", "failure_path", "sandbox_or_mock"],
    },
    "sdk": {
        "primary": "integration-engineer",
        "supporting": ["integration-impact-expert", "test-engineer"],
        "evidence": ["contract", "failure_path", "sandbox_or_mock"],
    },
    "message_queue": {
        "primary": "integration-engineer",
        "supporting": ["integration-impact-expert", "test-engineer", "debugging-expert"],
        "evidence": ["contract", "failure_path", "replay_or_retry"],
    },
    "realtime": {
        "primary": "integration-engineer",
        "supporting": ["integration-impact-expert", "test-engineer", "debugging-expert"],
        "evidence": ["contract", "failure_path", "realtime_or_refresh"],
    },
    "data_model": {
        "primary": "data-engineer",
        "supporting": ["test-engineer"],
        "reviewers": ["data-migration-reviewer"],
        "evidence": ["schema_diff", "invariant", "rollback_or_recovery"],
    },
    "migration": {
        "primary": "data-engineer",
        "supporting": ["test-engineer"],
        "reviewers": ["data-migration-reviewer"],
        "evidence": ["dry_run", "rollback", "invariant"],
    },
    "data_consistency": {
        "primary": "data-engineer",
        "supporting": ["test-engineer", "debugging-expert"],
        "reviewers": ["data-migration-reviewer"],
        "evidence": ["dry_run", "recovery", "invariant"],
    },
    "refactor": {
        "primary": "refactoring-expert",
        "supporting": ["test-engineer"],
        "evidence": ["behavior_preserving", "regression"],
    },
    "bug_fix": {
        "primary": "debugging-expert",
        "supporting": ["test-engineer"],
        "evidence": ["reproduction", "root_cause", "regression"],
    },
    # Tooling / CLI / scripts / installers / build chain — covers harness's own infra-style work
    # (install.py, sync_adapters.py, harness CLI itself, project lint scripts, dev tooling).
    "cli": {
        "primary": "general-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "command_output"],
    },
    "tooling": {
        "primary": "general-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "command_output"],
    },
    "installer": {
        "primary": "general-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "command_output", "dry_run"],
    },
    "script": {
        "primary": "general-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "command_output"],
    },
    "developer_tooling": {
        "primary": "general-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "command_output"],
    },
    "build_pipeline": {
        "primary": "general-engineer",
        "supporting": ["test-engineer"],
        "evidence": ["test_result", "command_output"],
    },
    # Documentation / rules / skills authoring — for Harness's own template content edits.
    "documentation": {
        "primary": "general-engineer",
        "supporting": [],
        "evidence": ["doc_diff", "lint_result"],
    },
    "harness_rule": {
        "primary": "general-engineer",
        "supporting": [],
        "evidence": ["doc_diff", "lint_result"],
    },
    "harness_skill": {
        "primary": "general-engineer",
        "supporting": [],
        "evidence": ["doc_diff", "lint_result"],
    },
}


def resolve(surfaces: list[str]) -> dict[str, Any]:
    primary_executors: list[str] = []
    supporting_executors: list[str] = []
    reviewers: list[str] = []
    evidence: list[str] = []
    missing_surfaces: list[str] = []
    for surface in surfaces:
        policy = SURFACE_POLICY.get(surface)
        if not policy:
            missing_surfaces.append(surface)
            continue
        primary = policy["primary"]
        if primary not in primary_executors:
            primary_executors.append(primary)
        for role in policy.get("supporting", []):
            if role not in supporting_executors and role not in primary_executors:
                supporting_executors.append(role)
        for role in policy.get("reviewers", []):
            if role not in reviewers:
                reviewers.append(role)
        for item in policy["evidence"]:
            if item not in evidence:
                evidence.append(item)
    if "spec-reviewer" not in reviewers:
        reviewers.append("spec-reviewer")
    supporting_executors = [role for role in supporting_executors if role not in primary_executors]
    executors = [*primary_executors, *[role for role in supporting_executors if role not in primary_executors]]
    rationale: list[str] = []
    for surface in surfaces:
        policy = SURFACE_POLICY.get(surface)
        if not policy:
            rationale.append(f"{surface} is unknown; execute dispatch is blocked until the task declares a supported surface")
            continue
        rationale.append(f"{surface} -> primary {policy['primary']}")
        if policy.get("supporting"):
            rationale.append(f"{surface} -> supporting {', '.join(policy['supporting'])}")
        if policy.get("reviewers"):
            rationale.append(f"{surface} -> reviewers {', '.join(policy['reviewers'])}")
    blockers: list[str] = []
    if missing_surfaces:
        blockers.append("unknown_surface")
    if not surfaces:
        blockers.append("missing_surface")
    if not primary_executors:
        blockers.append("missing_primary_executor")
    return {
        "surfaces": surfaces,
        "primary_executors": primary_executors,
        "supporting_executors": supporting_executors,
        "executors": executors,
        "reviewers": reviewers,
        "required_evidence": evidence,
        "missing_surfaces": missing_surfaces,
        "blocked": bool(blockers),
        "blockers": blockers,
        "rationale": rationale,
    }


def dedupe_preserve_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--surface", action="append", default=[])
    parser.add_argument("--task-json", help="Optional task JSON containing surfaces/test_obligation/e2e_obligation")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    surfaces = list(args.surface)
    if args.task_json:
        task = json.loads(Path(args.task_json).read_text(encoding="utf-8"))
        for key in ("surfaces", "user_surfaces"):
            values = task.get(key)
            if isinstance(values, list):
                surfaces.extend(str(value) for value in values)
        for block_name in ("test_obligation", "e2e_obligation"):
            block = task.get(block_name)
            if isinstance(block, dict):
                for key in ("surfaces", "user_surfaces"):
                    values = block.get(key)
                    if isinstance(values, list):
                        surfaces.extend(str(value) for value in values)
    result = resolve(dedupe_preserve_order(surfaces))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else yaml.safe_dump(result, sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
