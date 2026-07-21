#!/usr/bin/env python3
"""Runtime v1 Control Contract integrity checker.

This script intentionally performs deterministic checks only. It does not
judge whether a requirement is good or whether evidence is sufficient; the
stage-gate workflow handles that interpretation after this script reports
PASS / WARN / FAIL.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit("PyYAML is required to parse external Control Contract YAML") from exc

try:
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    import jsonschema
    from jsonschema import RefResolver
except ImportError:  # pragma: no cover - optional hardening dependency
    jsonschema = None
    RefResolver = None

WORK_GRAPH_SCRIPTS = Path(__file__).resolve().parents[2] / "work-graph" / "scripts"
if str(WORK_GRAPH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))

from work_graph_lib import (  # noqa: E402
    lane_action_registry_from_config as wg_lane_action_registry_from_config,
    lane_allowed_operations as wg_lane_allowed_operations,
    lane_stage_for_node as wg_lane_stage_for_node,
    validate_operation_against_profile as wg_validate_operation_against_profile,
)


REQUIRED_FIELDS = ("type", "version", "mission_id", "stage", "status", "upstream", "consumers")
REQUIRED_CONTRACT_BASENAMES = {
    "mission-contract.md",
    "product-definition.md",
    "product-evidence.md",
    "product-domain-model.md",
    "execution-brief.md",
    "verification-report.md",
    "solution.md",
    "tech-design.md",
    "code-review.md",
    "retrospective.md",
    "spec.md",
}
ID_PREFIXES = (
    "AC",
    "US",
    "SC",
    "FR",
    "NFR",
    "REQ",
    "SCN",
    "EV",
    "CMD",
    "OBJ",
    "SCOPE-IN",
    "SCOPE-OUT",
    "DEC",
    "RISK",
    "FB",
    "MOD",
    "IF",
    "INT",  # Stage-4 M1.4 typed interface_changes use INT-NN
    "DATA",
    "VS",
    "REV",
    "FND",
    "MEM",
    "OBL",
    "RVW",
    "EVD",
    "GATE",
    # Stage-4 M4.1: R-AGENT-* IDs surface from prd.contract.yaml
    # agent_capability_requirements[] and feed into solution.contract.yaml
    # agent_architecture[].traces_to_prd / tech-design.contract.yaml
    # agent_implementation[].traces_to_prd_capability cross-contract checks.
    "R-AGENT",
)
ID_PATTERN = re.compile(
    r"\b("
    + "|".join(rf"{re.escape(prefix)}-[A-Za-z0-9][A-Za-z0-9-]*" for prefix in ID_PREFIXES)
    + r"|T-?\d+"
    + r")\b"
)
PLACEHOLDER_PATTERN = re.compile(r"^\s*(\{\{.*\}\}|<.*>)\s*$")
CONTAINS_PLACEHOLDER_PATTERN = re.compile(r"(\{\{.*?\}\}|<[^>]+>)")
SCHEMA_DIR = Path(__file__).resolve().parents[3] / "schemas" / "control_contract.v1"
CODE_REVIEW_SCRIPT_DIR = Path(__file__).resolve().parents[2] / "code-review" / "scripts"
if str(CODE_REVIEW_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_REVIEW_SCRIPT_DIR))
try:
    from test_obligation_policy import is_obligation_complete, normalize_obligation
except ImportError:  # pragma: no cover - checker can still report schema errors
    is_obligation_complete = None
    normalize_obligation = None
try:
    from e2e_obligation_policy import is_e2e_obligation_complete, normalize_e2e_obligation
except ImportError:  # pragma: no cover - E2E policy may be introduced by another runtime layer
    is_e2e_obligation_complete = None
    normalize_e2e_obligation = None
SCHEMA_MAP = {
    ("intent_contract", None): "intent_contract.yaml",
    ("behaviour_contract", None): "behaviour_contract.yaml",
    ("behaviour_contract", "discovery_brief"): "discovery_brief_contract.yaml",
    ("action_contract", None): "action_contract.yaml",
    ("evidence_contract", "verification_evidence"): "evidence_contract.verification_evidence.yaml",
    ("evidence_contract", "review_evidence"): "evidence_contract.review_evidence.yaml",
    ("guide_contract", "solution_guide"): "guide_contract.solution_guide.yaml",
    ("guide_contract", "technical_guide"): "guide_contract.technical_guide.yaml",
    ("guide_contract", "interaction_guide"): "guide_contract.interaction_guide.yaml",
    ("memory_update_contract", None): "memory_update_contract.yaml",
}


@dataclass
class Finding:
    level: str
    code: str
    message: str


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# Contract reference may be written with or without backticks around the path.
# Both forms are valid Markdown for the same intent, and the artifact_gate /
# contract_check checks must not contradict each other (see test_framework_p1_regressions).
CONTRACT_REF_PATTERN = re.compile(
    r"^\s*[-*]?\s*(?:Contract|Control Contract)\s*:\s*`?([^\s`]+\.ya?ml)`?",
    re.MULTILINE,
)


def load_contract_yaml(path: Path) -> dict[str, Any] | None:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(parsed, dict):
        return None
    contract = parsed.get("control_contract")
    return contract if isinstance(contract, dict) else None


def find_contract_ref(text: str) -> str | None:
    match = CONTRACT_REF_PATTERN.search(text)
    return match.group(1) if match else None


def resolve_contract_artifact(root: Path, artifact: Path, findings: list[Finding]) -> tuple[Path, dict[str, Any] | None]:
    if artifact.suffix.lower() in {".yaml", ".yml"}:
        return artifact, load_contract_yaml(artifact)

    text = load_text(artifact)
    contract_ref = find_contract_ref(text)
    if not contract_ref:
        add(findings, "FAIL", "missing_contract_ref", f"Markdown artifact must reference an external contract YAML: {artifact}")
        return artifact, None
    contract_path = Path(contract_ref)
    if not contract_path.is_absolute():
        local_candidate = artifact.parent / contract_path
        root_candidate = root / contract_path
        contract_path = local_candidate if local_candidate.exists() else root_candidate
    if not contract_path.exists():
        add(findings, "FAIL", "missing_contract_artifact", f"Referenced contract YAML not found: {contract_ref}")
        return contract_path, None
    return contract_path, load_contract_yaml(contract_path)


def has_placeholder(value: Any) -> bool:
    for item in flatten(value):
        if isinstance(item, str) and PLACEHOLDER_PATTERN.match(item):
            return True
    return False


def contains_placeholder(value: str) -> bool:
    return bool(CONTAINS_PLACEHOLDER_PATTERN.search(value))


def boolish_true(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def markdown_heading_exists(text: str, heading: str, min_level: int = 1, max_level: int = 6) -> bool:
    escaped = re.escape(heading.strip())
    pattern = rf"(?m)^#{{{min_level},{max_level}}}\s+{escaped}(?:\s|$|:)"
    return bool(re.search(pattern, text))


def markdown_heading_section(text: str, heading: str, min_level: int = 1, max_level: int = 6) -> str:
    escaped = re.escape(heading.strip())
    pattern = rf"(?m)^(#{{{min_level},{max_level}}})\s+{escaped}(?:\s|$|:).*$"
    match = re.search(pattern, text)
    if not match:
        return ""
    level = len(match.group(1))
    rest = text[match.end() :]
    next_match = re.search(rf"(?m)^#{{1,{level}}}\s+", rest)
    if next_match:
        return rest[: next_match.start()]
    return rest


def flatten(value: Any) -> list[Any]:
    if isinstance(value, dict):
        items: list[Any] = []
        for nested in value.values():
            items.extend(flatten(nested))
        return items
    if isinstance(value, list):
        items = []
        for nested in value:
            items.extend(flatten(nested))
        return items
    return [value]


def referenced_ids(value: Any) -> set[str]:
    ids: set[str] = set()
    for item in flatten(value):
        if isinstance(item, str):
            ids.update(ID_PATTERN.findall(item))
    return ids


def ids_from_markdown(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(ID_PATTERN.findall(load_text(path)))


def agent_engineering_scope_from_yaml(path: Path) -> str | None:
    """Stage-4 M4.3 strict mode: read mission-contract.agent_engineering.scope
    from a YAML upstream contract. Returns the scope string (e.g. "core" /
    "experimental") or None when missing / malformed. The technical_guide
    check uses this to gate strict eval_scenarios coverage."""
    if not path.exists():
        return None
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(document, dict):
        return None
    contract = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else document
    if not isinstance(contract, dict):
        return None
    ae = contract.get("agent_engineering")
    if isinstance(ae, dict):
        scope = ae.get("scope")
        if isinstance(scope, str):
            return scope
    return None


def agent_architecture_components_from_yaml(path: Path) -> set[str]:
    """偏离修正3 (2026-05-15): structured-ID extractor.

    Pulls `agent_architecture[].component` strings out of a YAML upstream
    contract (e.g. solution.contract.yaml). Returned strings are the canonical
    target tokens for tech-design.contract.yaml's
    `agent_implementation[].traces_to_solution_arch` cross-reference.

    Returns empty set when the file is missing, not YAML, or has no
    agent_architecture[] entries — the caller falls back to permissive checks
    so contracts that opt out of agent design still pass.
    """
    if not path.exists():
        return set()
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return set()
    if not isinstance(document, dict):
        return set()
    contract = document.get("control_contract") if isinstance(document.get("control_contract"), dict) else document
    if not isinstance(contract, dict):
        return set()
    arch = contract.get("agent_architecture") or []
    if not isinstance(arch, list):
        return set()
    components: set[str] = set()
    for entry in arch:
        if isinstance(entry, dict):
            value = entry.get("component")
            if isinstance(value, str) and value.strip():
                components.add(value.strip())
    return components


def add(result: list[Finding], level: str, code: str, message: str) -> None:
    result.append(Finding(level=level, code=code, message=message))


def validate_schema(contract: dict[str, Any], findings: list[Finding]) -> None:
    if jsonschema is None or RefResolver is None:
        add(findings, "WARN", "schema_validator_unavailable", "jsonschema is unavailable; using semantic checks only")
        return
    schema_name = SCHEMA_MAP.get((contract.get("type"), contract.get("subtype"))) or SCHEMA_MAP.get((contract.get("type"), None))
    if not schema_name:
        add(findings, "WARN", "schema_not_found", f"No schema registered for {contract.get('type')} / {contract.get('subtype')}")
        return
    schema_path = SCHEMA_DIR / schema_name
    if not schema_path.exists():
        add(findings, "FAIL", "schema_file_missing", f"Schema file missing: {schema_path}")
        return
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    common_path = SCHEMA_DIR / "common.yaml"
    store = {f"file://{common_path.resolve()}": yaml.safe_load(common_path.read_text(encoding="utf-8"))}
    resolver = RefResolver(base_uri=f"file://{SCHEMA_DIR.resolve()}/", referrer=schema, store=store)
    try:
        jsonschema.Draft202012Validator(schema, resolver=resolver).validate(contract)
    except jsonschema.ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "<root>"
        add(findings, "FAIL", "schema_validation_failed", f"{schema_name}:{path}: {exc.message}")


def check_common(contract: dict[str, Any], findings: list[Finding]) -> None:
    for field in REQUIRED_FIELDS:
        if field not in contract:
            add(findings, "FAIL", "missing_field", f"Control Contract missing required field: {field}")
    if contract.get("version") != 1:
        add(findings, "FAIL", "unsupported_version", "Control Contract version must be 1")
    if contract.get("status") == "blocked":
        add(findings, "FAIL", "blocked_contract", "Control Contract status is blocked")
    if contract.get("status") not in {"draft", "ready", "blocked"}:
        add(findings, "FAIL", "invalid_status", "Control Contract status must be draft, ready, or blocked")
    if "upstream" in contract and not isinstance(contract.get("upstream"), list):
        add(findings, "FAIL", "invalid_upstream", "upstream must be a list")
    if "consumers" in contract and not isinstance(contract.get("consumers"), list):
        add(findings, "FAIL", "invalid_consumers", "consumers must be a list")


def contains_placeholder_any(value: Any) -> bool:
    return any(isinstance(item, str) and contains_placeholder(item) for item in flatten(value))


def template_prefilled_role_verdict(verdict: dict[str, Any]) -> bool:
    return str(verdict.get("verdict") or "") == "PASS" and contains_placeholder_any(verdict)


def check_contract_hygiene(contract: dict[str, Any], findings: list[Finding], allow_placeholders: bool) -> None:
    if allow_placeholders:
        return
    if contains_placeholder_any(contract):
        add(findings, "FAIL", "placeholder_in_runtime_artifact", "Contract still contains unresolved template placeholders")
        add(findings, "WARN", "manual_patch_required", "Materialized contract requires explicit patch/fill before it can pass hygiene")
    for verdict in contract.get("role_verdicts") or []:
        if isinstance(verdict, dict) and template_prefilled_role_verdict(verdict):
            add(findings, "FAIL", "prefilled_role_verdict", f"{verdict.get('id', '<role-verdict>')} pre-fills reviewer PASS from template placeholders")
    policy = contract.get("stage_participation_policy") if isinstance(contract.get("stage_participation_policy"), dict) else {}
    obligations = contract.get("entered_stage_obligations") if isinstance(contract.get("entered_stage_obligations"), dict) else {}
    policy_reviews = {str(item) for item in policy.get("required_review_roles") or [] if str(item).strip()}
    obligation_reviews = {str(item) for item in obligations.get("review_roles") or [] if str(item).strip()}
    if policy_reviews and obligation_reviews and policy_reviews != obligation_reviews:
        add(findings, "FAIL", "governance_conflict", "stage_participation_policy.required_review_roles conflicts with entered_stage_obligations.review_roles")


def graph_obligations(contract: dict[str, Any]) -> set[str]:
    obligations: set[str] = set()
    for item in contract.get("obligations") or []:
        if isinstance(item, dict) and item.get("id"):
            obligations.add(str(item["id"]))
    graph = contract.get("evidence_graph")
    if isinstance(graph, dict):
        nodes = graph.get("nodes") if isinstance(graph.get("nodes"), dict) else {}
        for item in nodes.get("obligations") or []:
            if isinstance(item, dict) and item.get("id"):
                obligations.add(str(item["id"]))
    return obligations


def graph_obligation_items(contract: dict[str, Any]) -> list[dict[str, Any]]:
    obligations = [item for item in contract.get("obligations") or [] if isinstance(item, dict)]
    graph = contract.get("evidence_graph")
    if isinstance(graph, dict):
        nodes = graph.get("nodes") if isinstance(graph.get("nodes"), dict) else {}
        obligations.extend(item for item in nodes.get("obligations") or [] if isinstance(item, dict))
    return obligations


def graph_gate_decisions(contract: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = [item for item in contract.get("gate_decisions") or [] if isinstance(item, dict)]
    graph = contract.get("evidence_graph")
    if isinstance(graph, dict):
        nodes = graph.get("nodes") if isinstance(graph.get("nodes"), dict) else {}
        decisions.extend(item for item in nodes.get("gate_decisions") or [] if isinstance(item, dict))
    return decisions


def graph_evidence(contract: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = [item for item in contract.get("evidence") or [] if isinstance(item, dict)]
    graph = contract.get("evidence_graph")
    if isinstance(graph, dict):
        nodes = graph.get("nodes") if isinstance(graph.get("nodes"), dict) else {}
        evidence.extend(item for item in nodes.get("evidence") or [] if isinstance(item, dict))
    return evidence


def check_role_policy_block(contract: dict[str, Any], findings: list[Finding]) -> None:
    policy = contract.get("role_policy") or contract.get("role_policy_override")
    if not isinstance(policy, dict):
        return
    for field in ("stage", "required_execution_roles", "required_review_roles"):
        if not policy.get(field):
            add(findings, "FAIL", "invalid_role_policy", f"role_policy missing {field}")
    for item in policy.get("conditional_roles") or []:
        if not isinstance(item, dict):
            add(findings, "FAIL", "invalid_role_policy", "conditional_roles entries must be objects")
            continue
        if not item.get("role") or not item.get("when"):
            add(findings, "FAIL", "invalid_role_policy", "conditional role requires role and when")


def all_execution_results(contract: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    legacy = contract.get("execution_result")
    if isinstance(legacy, dict):
        results.append(legacy)
    for item in contract.get("execution_results") or []:
        if isinstance(item, dict):
            results.append(item)
    return results


def validate_execution_result(contract: dict[str, Any], result: dict[str, Any], findings: list[Finding], root: Path, allow_placeholders: bool, field_label: str) -> None:
    status = result.get("status")
    if status not in {"DONE", "DONE_WITH_CONCERNS", "NEEDS_DECISION", "BLOCKED"}:
        add(findings, "FAIL", "invalid_execution_result_status", f"{field_label}.status is required and must be DONE, DONE_WITH_CONCERNS, NEEDS_DECISION, or BLOCKED")
    for field in ("id", "role"):
        if not result.get(field):
            add(findings, "FAIL", "invalid_execution_result", f"{field_label} missing {field}")
    for artifact in result.get("produced_artifacts") or []:
        if not isinstance(artifact, dict):
            add(findings, "FAIL", "invalid_execution_result_artifact", f"{field_label}.produced_artifacts entries must be objects")
            continue
        path = artifact.get("path")
        if not path:
            add(findings, "FAIL", "invalid_execution_result_artifact", f"{field_label} produced artifact missing path")
        elif not allow_placeholders and not contains_placeholder(str(path)) and not (root / str(path)).exists():
            add(findings, "FAIL", "execution_artifact_missing", f"Produced artifact path does not exist: {path}")
    known_obligations = graph_obligations(contract)
    fulfilled = result.get("fulfilled_obligations") or []
    if known_obligations:
        for oid in fulfilled:
            if oid not in known_obligations:
                add(findings, "FAIL", "unknown_fulfilled_obligation", f"{field_label} references unknown obligation: {oid}")
    if status == "DONE_WITH_CONCERNS" and not result.get("concerns"):
        add(findings, "FAIL", "concerns_required", "DONE_WITH_CONCERNS requires non-empty concerns")
    if status == "DONE_WITH_CONCERNS" and result.get("concerns"):
        has_consumer = bool(contract.get("role_verdicts") or graph_gate_decisions(contract))
        if not has_consumer:
            add(findings, "FAIL", "execution_concern_unconsumed", "DONE_WITH_CONCERNS requires a review verdict or Gate decision that consumes the concern")
    if status == "NEEDS_DECISION" and not (result.get("open_questions") or graph_gate_decisions(contract)):
        add(findings, "FAIL", "execution_decision_missing", "NEEDS_DECISION requires open_questions or a gate_decision")


def check_execution_result(contract: dict[str, Any], findings: list[Finding], root: Path, allow_placeholders: bool) -> None:
    result = contract.get("execution_result")
    results = contract.get("execution_results")
    if result is None and results is None:
        return
    if result is not None and not isinstance(result, dict):
        add(findings, "FAIL", "invalid_execution_result", "execution_result must be an object")
    if results is not None and not isinstance(results, list):
        add(findings, "FAIL", "invalid_execution_results", "execution_results must be a list")
    for index, item in enumerate(results or []):
        if not isinstance(item, dict):
            add(findings, "FAIL", "invalid_execution_results", f"execution_results[{index}] must be an object")
    for index, item in enumerate(all_execution_results(contract)):
        label = "execution_result" if item is result else f"execution_results[{index}]"
        validate_execution_result(contract, item, findings, root, allow_placeholders, label)


def list_strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def evidence_types(contract: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for field in ("tdd_evidence", "execution_evidence"):
        for item in contract.get(field) or []:
            if isinstance(item, dict):
                for key in ("type", "evidence_type", "capability"):
                    if item.get(key):
                        values.add(str(item[key]))
    for item in graph_evidence(contract):
        for key in ("type", "evidence_type", "capability"):
            if item.get(key):
                values.add(str(item[key]))
    return values


def has_content(value: Any, allow_placeholders: bool = False) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return False
        if not allow_placeholders and contains_placeholder(text):
            return False
        return True
    if isinstance(value, list):
        return any(has_content(item, allow_placeholders) for item in value)
    if isinstance(value, dict):
        return any(has_content(item, allow_placeholders) for item in value.values())
    return True


def check_tdd_scope(task: dict[str, Any], tid: str, findings: list[Finding], allow_placeholders: bool = False) -> None:
    scope = task.get("tdd_scope")
    if not isinstance(scope, dict):
        add(findings, "FAIL", "missing_tdd_scope", f"{tid} lacks tdd_scope planning contract")
        return
    required_fields = (
        "behavior_under_test",
        "red_scope",
        "green_scope",
        "refactor_scope",
        "out_of_scope",
        "required_assertions",
        "test_data_boundary",
        "test_doubles_boundary",
        "commands",
        "validity_probe",
    )
    for field in required_fields:
        if not has_content(scope.get(field), allow_placeholders):
            add(findings, "FAIL", "invalid_tdd_scope", f"{tid} tdd_scope requires non-empty {field}")
    commands = scope.get("commands") if isinstance(scope.get("commands"), dict) else {}
    for field in ("red", "green", "regression"):
        if not has_content(commands.get(field), allow_placeholders):
            add(findings, "FAIL", "invalid_tdd_scope_commands", f"{tid} tdd_scope.commands requires {field}")
    probe = scope.get("validity_probe") if isinstance(scope.get("validity_probe"), dict) else {}
    for field in ("method", "expected_signal"):
        if not has_content(probe.get(field), allow_placeholders):
            add(findings, "FAIL", "invalid_tdd_scope_probe", f"{tid} tdd_scope.validity_probe requires {field}")


def execute_expected_atomic_task_ids(contract: dict[str, Any], root: Path | None) -> set[str]:
    if root is None:
        return set()
    mission_id = str(contract.get("mission_id") or "")
    mission_slice = current_mission_slice(root, mission_id)
    slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    primary_nodes = [str(item) for item in slice_graph.get("primary_nodes") or []] if isinstance(slice_graph.get("primary_nodes"), list) else []
    if not primary_nodes:
        artifact = contract.get("work_graph_artifact") if isinstance(contract.get("work_graph_artifact"), dict) else {}
        node_id = str(artifact.get("node_id") or "")
        primary_nodes = [node_id] if node_id else []
    nodes = load_work_graph_nodes(root)
    expected: set[str] = set()
    for node_id in primary_nodes:
        node = nodes.get(node_id) or {}
        queue = node.get("parent_local_atomic_task_queue") if isinstance(node.get("parent_local_atomic_task_queue"), dict) else {}
        atomic_ids = queue.get("atomic_task_ids")
        if isinstance(atomic_ids, list):
            expected.update(str(item) for item in atomic_ids if item)
        execution_units = queue.get("execution_units")
        if isinstance(execution_units, list):
            for unit in execution_units:
                if isinstance(unit, dict) and unit.get("id"):
                    expected.add(str(unit["id"]))
    return expected


def is_single_atomic_execution_unit(value: str) -> bool:
    if not value.strip():
        return False
    if ".." in value or "," in value:
        return False
    return not bool(re.search(r"\s", value.strip()))


def evidence_covers_atomic_task(item: dict[str, Any], atomic_id: str) -> bool:
    covers = item.get("covers") if isinstance(item.get("covers"), dict) else {}
    candidates = []
    for key in ("atomic_tasks", "atomic_task_ids", "tasks", "execution_units"):
        value = covers.get(key)
        if isinstance(value, list):
            candidates.extend(str(entry) for entry in value)
    return atomic_id in candidates


def check_execute_atomic_task_control(contract: dict[str, Any], root: Path | None, findings: list[Finding]) -> None:
    expected_atomic_ids = execute_expected_atomic_task_ids(contract, root)
    if not expected_atomic_ids:
        return
    session = contract.get("execute_session") if isinstance(contract.get("execute_session"), dict) else {}
    plans = session.get("dispatch_plans") if isinstance(session.get("dispatch_plans"), list) else []
    seen_units: list[str] = []
    for index, plan in enumerate(plans):
        if not isinstance(plan, dict):
            continue
        unit = str(plan.get("execution_unit_id") or "")
        if not is_single_atomic_execution_unit(unit):
            add(
                findings,
                "FAIL",
                "invalid_execute_atomic_dispatch_unit",
                f"dispatch plan {index} execution_unit_id must be exactly one Atomic Task id from the current TASK node, got {unit!r}",
            )
            continue
        seen_units.append(unit)
        if unit not in expected_atomic_ids:
            add(findings, "FAIL", "unknown_execute_atomic_dispatch_unit", f"dispatch plan {index} references Atomic Task {unit!r} not bound to the current TASK node")
    seen_set = set(seen_units)
    for atomic_id in sorted(expected_atomic_ids - seen_set):
        add(findings, "FAIL", "missing_execute_atomic_dispatch_plan", f"current TASK node Atomic Task {atomic_id} has no dedicated execute dispatch plan")
    duplicates = sorted(unit for unit in seen_set if seen_units.count(unit) > 1)
    for unit in duplicates:
        add(findings, "FAIL", "duplicate_execute_atomic_dispatch_plan", f"Atomic Task {unit} has multiple execute dispatch plans")

    phase_types = {"red_report", "green_report", "regression_report"}
    phase_cover: dict[str, set[str]] = {phase: set() for phase in phase_types}
    for item in contract.get("tdd_evidence") or []:
        if not isinstance(item, dict):
            continue
        evidence_type = str(item.get("type") or item.get("evidence_type") or "")
        if evidence_type not in phase_types:
            continue
        for atomic_id in expected_atomic_ids:
            if evidence_covers_atomic_task(item, atomic_id):
                phase_cover[evidence_type].add(atomic_id)
    for evidence_type, covered in sorted(phase_cover.items()):
        for atomic_id in sorted(expected_atomic_ids - covered):
            add(findings, "FAIL", "missing_execute_atomic_tdd_evidence", f"{atomic_id} lacks {evidence_type} coverage in tdd_evidence")


def check_execute_implementation_contract(contract: dict[str, Any], findings: list[Finding], root: Path | None = None) -> None:
    if contract.get("stage") != "execute":
        return

    session = contract.get("execute_session")
    if not isinstance(session, dict):
        add(findings, "FAIL", "missing_execute_session", "execute contracts must include execute_session produced by the execute skill")
        return

    if session.get("carrier") != "execute" or session.get("skill") != "execute":
        add(findings, "FAIL", "invalid_execute_carrier", "execute_session must declare carrier=execute and skill=execute")
    if session.get("execute_mode") != "sdd":
        add(findings, "FAIL", "invalid_execute_mode", "execute implementation requires execute_mode=sdd")

    dispatch_plans = session.get("dispatch_plans")
    if not isinstance(dispatch_plans, list) or not dispatch_plans:
        add(findings, "FAIL", "missing_dispatch_plan", "execute_session.dispatch_plans must contain at least one execute dispatch plan")
        return

    required_executor_roles: set[str] = {"execute-control-plane-executor"}
    required_reviewer_roles: set[str] = set()
    for index, plan in enumerate(dispatch_plans):
        if not isinstance(plan, dict):
            add(findings, "FAIL", "invalid_dispatch_plan", f"execute_session.dispatch_plans[{index}] must be an object")
            continue
        primary = list_strings(plan.get("primary_executors"))
        reviewers = list_strings(plan.get("reviewers"))
        missing_surfaces = list_strings(plan.get("missing_surfaces"))
        if not primary:
            add(findings, "FAIL", "missing_primary_executor", f"dispatch plan {index} has no primary_executors")
        if "general-engineer" in primary:
            add(findings, "FAIL", "forbidden_general_executor", f"dispatch plan {index} uses general-engineer instead of a resolved specialist")
        if missing_surfaces:
            add(findings, "FAIL", "dispatch_has_missing_surfaces", f"dispatch plan {index} has unresolved surfaces: {', '.join(missing_surfaces)}")
        if plan.get("blocked") is True:
            add(findings, "FAIL", "blocked_dispatch_plan", f"dispatch plan {index} is blocked and cannot certify execute completion")
        if "spec-reviewer" not in reviewers:
            add(findings, "FAIL", "missing_spec_reviewer", f"dispatch plan {index} must include spec-reviewer")
        check_dispatch_execution_context(plan, index, findings)
        required_executor_roles.update(primary)
        required_reviewer_roles.update(reviewers)

    result_roles = {str(result.get("role")) for result in all_execution_results(contract) if result.get("role")}
    for role in sorted(required_executor_roles):
        if role not in result_roles:
            add(findings, "FAIL", "missing_execute_agent_result", f"execute contract missing execution result for role: {role}")

    verdict_roles = {str(verdict.get("role")) for verdict in all_role_verdicts(contract) if verdict.get("role")}
    for role in sorted(required_reviewer_roles):
        if role not in verdict_roles:
            add(findings, "FAIL", "missing_execute_reviewer_verdict", f"execute contract missing reviewer verdict for role: {role}")

    present_evidence = evidence_types(contract)
    required_evidence = {"red_report", "green_report", "regression_report", "toolchain_status"}
    missing_evidence = sorted(required_evidence - present_evidence)
    if missing_evidence:
        add(findings, "FAIL", "missing_tdd_evidence", f"execute contract missing TDD evidence types: {', '.join(missing_evidence)}")
    check_execute_atomic_task_control(contract, root, findings)
    check_tdd_phase_evidence(contract, findings)


def check_dispatch_execution_context(plan: dict[str, Any], index: int, findings: list[Finding]) -> None:
    context = plan.get("execution_context")
    if not isinstance(context, dict):
        add(findings, "FAIL", "missing_dispatch_execution_context", f"dispatch plan {index} must declare execution_context.skill=execute")
        context = {}
    if context.get("skill") != "execute":
        add(findings, "FAIL", "missing_dispatch_execution_context", f"dispatch plan {index} must declare execution_context.skill=execute")
    refs = context.get("role_package_refs")
    roles = [
        *list_strings(plan.get("primary_executors")),
        *list_strings(plan.get("supporting_executors")),
        *list_strings(plan.get("reviewers")),
    ]
    if not isinstance(refs, dict):
        add(findings, "FAIL", "missing_role_package_refs", f"dispatch plan {index} must declare execution_context.role_package_refs")
        return
    for role in sorted(set(roles)):
        ref = refs.get(role)
        if not has_content(ref):
            add(findings, "FAIL", "missing_role_package_ref", f"dispatch plan {index} missing role_package_refs.{role}")
            continue
        expected_suffix = f"common/agents/{role}.md"
        normalized = str(ref).replace("\\", "/")
        if not (normalized.endswith(f"package/{expected_suffix}") or normalized.endswith(f".harness/{expected_suffix}")):
            add(findings, "FAIL", "invalid_role_package_ref", f"dispatch plan {index} role_package_refs.{role} must point to .harness/common/agents/{role}.md or .harness/common/agents/{role}.md")
    material_contract = plan.get("material_package_contract")
    if isinstance(material_contract, dict):
        if material_contract.get("must_include_execution_context") is not True:
            add(findings, "FAIL", "invalid_material_package_contract", f"dispatch plan {index} material package must include execution_context")
        if material_contract.get("must_include_role_package_ref") is not True:
            add(findings, "FAIL", "invalid_material_package_contract", f"dispatch plan {index} material package must include role package refs")


def check_tdd_phase_evidence(contract: dict[str, Any], findings: list[Finding]) -> None:
    expected = {
        "red_report": "red",
        "green_report": "green",
        "regression_report": "regression",
    }
    for item in contract.get("tdd_evidence") or []:
        if not isinstance(item, dict):
            continue
        evidence_type = str(item.get("type") or item.get("evidence_type") or "")
        phase = expected.get(evidence_type)
        if not phase:
            continue
        eid = str(item.get("id") or evidence_type)
        if item.get("phase") != phase:
            add(findings, "FAIL", "invalid_tdd_evidence_phase", f"{eid} must declare phase={phase}")
        if not has_content(item.get("command")):
            add(findings, "FAIL", "invalid_tdd_evidence_command", f"{eid} must include the command that produced the evidence")
        if phase == "red":
            if item.get("exit_code") in (0, "0"):
                add(findings, "FAIL", "invalid_red_evidence", f"{eid} red evidence must record a failing exit_code")
            if not has_content(item.get("failure_signal")):
                add(findings, "FAIL", "invalid_red_evidence", f"{eid} red evidence must include failure_signal")
        else:
            if item.get("exit_code") not in (0, "0"):
                add(findings, "FAIL", "invalid_tdd_evidence_exit_code", f"{eid} {phase} evidence must record exit_code=0")


def execute_dispatch_executor_roles(contract: dict[str, Any]) -> set[str]:
    session = contract.get("execute_session")
    if not isinstance(session, dict):
        return set()
    roles: set[str] = set()
    for plan in session.get("dispatch_plans") or []:
        if not isinstance(plan, dict):
            continue
        roles.update(list_strings(plan.get("primary_executors")))
        roles.update(list_strings(plan.get("supporting_executors")))
    return roles


def legacy_role_verdicts(contract: dict[str, Any]) -> list[dict[str, Any]]:
    verdicts: list[dict[str, Any]] = []
    for reviewer in contract.get("reviewers") or []:
        if not isinstance(reviewer, dict):
            continue
        role = reviewer.get("role")
        reviewed = reviewer.get("reviewed_obligations") or reviewer.get("obligation_refs") or []
        verdicts.append(
            {
                "id": reviewer.get("id"),
                "role": role,
                "verdict": reviewer.get("verdict"),
                "reviewed_obligations": reviewed,
                "review_basis": reviewer.get("review_basis"),
                "blocking_gaps": reviewer.get("blocking_gaps", []),
            }
        )
    return verdicts


def all_role_verdicts(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *[item for item in contract.get("role_verdicts") or [] if isinstance(item, dict)],
        *legacy_role_verdicts(contract),
    ]


def check_declared_role_policy_coverage(contract: dict[str, Any], findings: list[Finding]) -> None:
    policy = contract.get("role_policy") or contract.get("role_policy_override")
    if not isinstance(policy, dict):
        return

    required_execution_roles = [str(role) for role in policy.get("required_execution_roles") or [] if role]
    if required_execution_roles:
        execution_results = all_execution_results(contract)
        if not execution_results:
            add(findings, "FAIL", "missing_execution_result_for_role_policy", "role_policy declares execution roles but execution_result(s) are missing")
        result_roles = {str(result.get("role")) for result in execution_results if result.get("role")}
        for role in required_execution_roles:
            if role not in result_roles:
                add(findings, "FAIL", "missing_required_execution_result", f"role_policy requires execution role without result: {role}")
        allowed_result_roles = set(required_execution_roles)
        if contract.get("stage") == "execute":
            allowed_result_roles.update(execute_dispatch_executor_roles(contract))
        for role in result_roles:
            if role not in allowed_result_roles:
                add(
                    findings,
                    "FAIL",
                    "execution_role_not_required_by_policy",
                    f"execution result role {role} is not in role_policy.required_execution_roles",
                )

    required_review_roles = [str(role) for role in policy.get("required_review_roles") or [] if role]
    verdicts = all_role_verdicts(contract)
    verdict_roles = {str(verdict.get("role")) for verdict in verdicts if verdict.get("role")}
    for role in required_review_roles:
        if role not in verdict_roles:
            add(findings, "FAIL", "missing_required_role_verdict", f"role_policy requires review role without verdict: {role}")


def check_obligation_role_coverage(contract: dict[str, Any], findings: list[Finding]) -> None:
    verdicts = all_role_verdicts(contract)
    for obligation in graph_obligation_items(contract):
        oid = obligation.get("id")
        if not oid:
            continue
        for role in obligation.get("required_roles") or []:
            matching = [
                verdict
                for verdict in verdicts
                if verdict.get("role") == role and oid in (verdict.get("reviewed_obligations") or [])
            ]
            if not matching:
                add(findings, "FAIL", "missing_obligation_role_verdict", f"{oid} requires {role} verdict")


_REVIEWER_ROLE_SUFFIXES = ("-reviewer", "-effectiveness-reviewer")


def _is_reviewer_role(role: Any) -> bool:
    return isinstance(role, str) and any(role.endswith(suffix) for suffix in _REVIEWER_ROLE_SUFFIXES)


def check_role_verdicts(contract: dict[str, Any], findings: list[Finding]) -> None:
    verdicts = [item for item in contract.get("role_verdicts") or [] if isinstance(item, dict)]
    if not verdicts:
        return
    known_obligations = graph_obligations(contract)
    failed_obligations: set[str] = set()
    for evidence in graph_evidence(contract):
        if evidence.get("status") != "FAIL":
            continue
        covers = evidence.get("covers") if isinstance(evidence.get("covers"), dict) else {}
        failed_obligations.update(str(oid) for oid in covers.get("obligations") or [])
    for verdict in verdicts:
        vid = verdict.get("id", "<role-verdict>")
        for field in ("id", "role", "verdict", "reviewed_obligations", "review_basis"):
            if not verdict.get(field):
                add(findings, "FAIL", "invalid_role_verdict", f"{vid} missing {field}")
        if verdict.get("verdict") not in {"PASS", "PASS_WITH_RISK", "HOLD", "BLOCKED"}:
            add(findings, "FAIL", "invalid_role_verdict_status", f"{vid} has invalid verdict: {verdict.get('verdict')}")
        reviewed = verdict.get("reviewed_obligations") or []
        if known_obligations:
            for oid in reviewed:
                if oid not in known_obligations:
                    add(findings, "FAIL", "role_verdict_unknown_obligation", f"{vid} reviews unknown obligation: {oid}")
        if verdict.get("verdict") in {"HOLD", "BLOCKED"} and not verdict.get("blocking_gaps"):
            add(findings, "FAIL", "hold_without_blocking_gaps", f"{vid} {verdict.get('verdict')} requires blocking_gaps")
        if verdict.get("verdict") == "PASS" and failed_obligations.intersection(reviewed):
            add(findings, "FAIL", "role_pass_over_programmatic_fail", f"{vid} PASS covers failed tool evidence")
        # M4.2 — reviewer dispatch evidence + no-main_agent_fallback enforcement.
        if _is_reviewer_role(verdict.get("role")):
            dispatch = verdict.get("dispatch")
            if not isinstance(dispatch, dict):
                add(
                    findings,
                    "FAIL",
                    "reviewer_missing_dispatch",
                    f"{vid} reviewer-class role {verdict.get('role')!r} must declare `dispatch` block",
                )
            else:
                missing = [
                    field
                    for field in ("subagent_id", "model", "execution_mode", "started_at", "completed_at")
                    if not dispatch.get(field)
                ]
                if missing:
                    add(
                        findings,
                        "FAIL",
                        "reviewer_dispatch_incomplete",
                        f"{vid} dispatch missing fields: {missing}",
                    )
                if dispatch.get("execution_mode") == "main_agent_fallback":
                    add(
                        findings,
                        "FAIL",
                        "reviewer_main_agent_fallback",
                        f"{vid} reviewer-class role {verdict.get('role')!r} cannot record execution_mode=main_agent_fallback",
                    )
    if any(item.get("verdict") == "PASS_WITH_RISK" for item in verdicts):
        decisions = graph_gate_decisions(contract)
        if not any(item.get("decision") in {"accept_risk", "accept_residual_risk"} or item.get("accepted_risk") for item in decisions):
            add(findings, "FAIL", "accepted_risk_without_decision", "PASS_WITH_RISK requires a user Decision Gate record")
    legacy = legacy_role_verdicts(contract)
    for verdict in verdicts:
        for item in legacy:
            if item.get("role") == verdict.get("role") and item.get("verdict") and item.get("verdict") != verdict.get("verdict"):
                add(findings, "FAIL", "role_verdict_legacy_mismatch", f"role_verdicts and reviewers disagree for role {verdict.get('role')}")


def check_effectiveness_review_rounds(
    contract: dict[str, Any], findings: list[Finding], root: Path
) -> None:
    """intake-improvement-plan M4.3 — when the reviewer loop exceeds its
    declared max_rounds AND no PASS verdict was reached, the mission must
    carry an approved `tradeoff` approval explaining why we accept the
    overflow. Without that, the contract is BLOCKED.
    """
    review = contract.get("effectiveness_review")
    if not isinstance(review, dict):
        return
    rounds_used = review.get("rounds_used")
    max_rounds = review.get("max_rounds")
    last_verdict = review.get("last_verdict", "")
    if not isinstance(rounds_used, int) or not isinstance(max_rounds, int):
        return
    if rounds_used <= max_rounds:
        return
    if isinstance(last_verdict, str) and last_verdict.upper() in {"PASS", "PASS_WITH_RISK"}:
        return

    mission_id = contract.get("mission_id")
    if not isinstance(mission_id, str) or not mission_id:
        # Without a mission_id we cannot locate the approvals.json scope —
        # warn rather than block.
        add(
            findings,
            "WARN",
            "rounds_overflow_unscoped",
            f"effectiveness_review.rounds_used ({rounds_used}) > max_rounds ({max_rounds}) but mission_id missing",
        )
        return

    approvals_path = root / "harness-runtime" / "harness" / "state" / "approvals.json"
    has_tradeoff = False
    if approvals_path.exists():
        try:
            data = json.loads(approvals_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = None
        entries = data.get("approvals") if isinstance(data, dict) else data
        if isinstance(entries, list):
            for entry in entries:
                if (
                    isinstance(entry, dict)
                    and entry.get("mission_id") == mission_id
                    and entry.get("type") == "tradeoff"
                    and entry.get("status") == "approved"
                ):
                    has_tradeoff = True
                    break

    if not has_tradeoff:
        add(
            findings,
            "FAIL",
            "rounds_overflow_without_approval",
            f"effectiveness_review.rounds_used ({rounds_used}) exceeds max_rounds ({max_rounds}) "
            f"with last_verdict={last_verdict!r}; requires `harness approval append "
            f"--mission {mission_id} --type tradeoff --status approved`",
        )


def _is_missing_story_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def check_intent(contract: dict[str, Any], findings: list[Finding]) -> None:
    # intake-improvement-plan M2.1 chunk B: fold Step 11 prose self-checks for
    # minimum intent structure into the CLI gate so `harness contract check`
    # is the single source of truth.
    objective = contract.get("objective")
    if not isinstance(objective, dict) or not objective.get("statement"):
        add(
            findings,
            "FAIL",
            "missing_objective_statement",
            "intent_contract must declare objective.statement so downstream stages can trace back to the framing goal",
        )
    user_stories = contract.get("user_stories")
    if not isinstance(user_stories, list) or not user_stories:
        add(
            findings,
            "FAIL",
            "missing_user_stories",
            "intent_contract must declare at least one user_story with a stable id (US-*)",
        )
    else:
        version = contract.get("version")
        requires_product_story = isinstance(version, int) and version >= 2
        for idx, story in enumerate(user_stories):
            if not isinstance(story, dict):
                add(
                    findings,
                    "FAIL",
                    "invalid_user_story",
                    f"user_stories[{idx}] must be an object with id/role/goal/value and story_context",
                )
                continue
            if not story.get("id"):
                add(
                    findings,
                    "FAIL",
                    "missing_user_story_id",
                    f"user_stories[{idx}] missing required field 'id' (stable US-* identifier)",
                )
            if requires_product_story:
                missing_fields: list[str] = []
                for field in ("role", "goal", "value"):
                    if _is_missing_story_value(story.get(field)):
                        missing_fields.append(field)
                story_context = story.get("story_context")
                if not isinstance(story_context, dict):
                    missing_fields.append("story_context")
                else:
                    for field in ("user", "problem", "scenario", "value"):
                        if _is_missing_story_value(story_context.get(field)):
                            missing_fields.append(f"story_context.{field}")
                    metrics = story_context.get("success_metrics")
                    if not isinstance(metrics, list) or not metrics:
                        missing_fields.append("story_context.success_metrics")
                    else:
                        for metric_idx, metric in enumerate(metrics):
                            if not isinstance(metric, dict):
                                missing_fields.append(f"story_context.success_metrics[{metric_idx}]")
                                continue
                            if _is_missing_story_value(metric.get("signal")):
                                missing_fields.append(f"story_context.success_metrics[{metric_idx}].signal")
                            if _is_missing_story_value(metric.get("target")):
                                missing_fields.append(f"story_context.success_metrics[{metric_idx}].target")
                if missing_fields:
                    add(
                        findings,
                        "FAIL",
                        "missing_user_story_product_context",
                        f"user_stories[{idx}] missing product story handoff fields: {', '.join(missing_fields)}",
                    )
    scope = contract.get("scope")
    if not isinstance(scope, dict):
        add(
            findings,
            "FAIL",
            "missing_scope",
            "intent_contract must declare scope.in and scope.out as lists",
        )
    else:
        for field in ("in", "out"):
            entries = scope.get(field)
            if entries is None:
                add(
                    findings,
                    "FAIL",
                    "missing_scope_field",
                    f"intent_contract scope.{field} must be present (empty list is allowed when intentional)",
                )
            elif not isinstance(entries, list):
                add(
                    findings,
                    "FAIL",
                    "invalid_scope_field",
                    f"intent_contract scope.{field} must be a list; received {type(entries).__name__}",
                )
    autonomy = contract.get("autonomy")
    if not isinstance(autonomy, dict) or not autonomy.get("level"):
        add(
            findings,
            "FAIL",
            "missing_autonomy_level",
            "intent_contract must declare autonomy.level (one of 快速执行 / 专家确认 / 受控推进)",
        )
    else:
        governance = autonomy.get("governance_assessment")
        if not isinstance(governance, dict) or not governance:
            add(
                findings,
                "WARN",
                "missing_governance_assessment",
                "intent_contract should declare autonomy.governance_assessment with hard_triggers, dimensions, scale_signals and decision_rule",
            )
        else:
            hard_triggers = governance.get("hard_triggers") if isinstance(governance.get("hard_triggers"), list) else []
            dimensions = governance.get("dimensions") if isinstance(governance.get("dimensions"), dict) else {}
            high_dimensions = [
                name for name, value in dimensions.items()
                if isinstance(value, dict) and str(value.get("level") or "").strip().lower() == "high"
            ]
            has_override = bool(
                governance.get("risk_acceptance_approval_id")
                or governance.get("override_approval_id")
                or governance.get("downgrade_approval_id")
            )
            if (hard_triggers or high_dimensions or str(autonomy.get("governance_risk") or "").strip().lower() == "high") and autonomy.get("level") != "受控推进" and not has_override:
                add(
                    findings,
                    "FAIL",
                    "governance_risk_requires_controlled",
                    "hard triggers, high governance dimensions, or governance_risk=high require autonomy.level=受控推进 unless a risk acceptance approval id is recorded",
                )

    acs = contract.get("acceptance_criteria") or []
    if not acs:
        add(findings, "FAIL", "missing_ac", "intent_contract must declare acceptance_criteria; see harness-runtime/templates/contracts/mission-contract.contract.yaml")
    for ac in acs:
        if not isinstance(ac, dict):
            add(findings, "FAIL", "invalid_ac", "acceptance_criteria entries must be objects (with id, statement, and either given/when/then or verification_method); see harness-runtime/templates/contracts/mission-contract.contract.yaml")
            continue
        ac_id = ac.get("id") or "<unknown>"
        for field in ("id", "statement"):
            if not ac.get(field):
                add(findings, "FAIL", "missing_ac_field", f"Acceptance criterion {ac_id} missing required field '{field}'")
        gwt_present = bool(ac.get("given") and ac.get("when") and ac.get("then"))
        vm_present = bool(ac.get("verification_method"))
        if not gwt_present and not vm_present:
            nested_gwt = ac.get("gwt")
            if isinstance(nested_gwt, dict) and nested_gwt.get("given") and nested_gwt.get("when") and nested_gwt.get("then"):
                add(
                    findings,
                    "FAIL",
                    "unverifiable_ac",
                    f"{ac_id} uses nested 'gwt:' block; given/when/then must be flat siblings of id/statement. Example in harness-runtime/templates/contracts/mission-contract.contract.yaml",
                )
            else:
                add(
                    findings,
                    "FAIL",
                    "unverifiable_ac",
                    f"{ac_id} must declare either flat given/when/then OR a 'verification_method' string. Example in harness-runtime/templates/contracts/mission-contract.contract.yaml",
                )

    scope_out = ((contract.get("scope") or {}).get("out")) or []
    for entry in scope_out:
        if isinstance(entry, dict) and not entry.get("reason"):
            add(findings, "FAIL", "scope_out_reason_missing", f"{entry.get('id', '<scope-out>')} lacks reason")


def check_behaviour(contract: dict[str, Any], findings: list[Finding], upstream_ids: set[str]) -> None:
    covers_intent = contract.get("covers_intent") or []
    if isinstance(covers_intent, dict):
        covered_acs = covers_intent.get("acceptance_criteria") or []
    else:
        covered_acs = covers_intent
    for ac in covered_acs:
        if upstream_ids and ac not in upstream_ids:
            add(findings, "FAIL", "broken_ac_reference", f"covers_intent references unknown AC: {ac}")

    frs = contract.get("functional_requirements") or []
    nfrs = contract.get("non_functional_requirements") or []
    capabilities = contract.get("capabilities") or []
    if not frs and not capabilities:
        add(findings, "FAIL", "missing_requirements", "behaviour_contract must declare FRs or capability requirements")
    for req in frs:
        if isinstance(req, dict) and not req.get("id"):
            add(findings, "FAIL", "missing_fr_id", "Functional requirement missing id")
    for nfr in nfrs:
        if isinstance(nfr, dict) and not (nfr.get("id") and nfr.get("verification_method")):
            add(findings, "FAIL", "invalid_nfr", "NFR entries require id and verification_method")
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        if not capability.get("id") or not capability.get("name"):
            add(findings, "FAIL", "invalid_capability", "Capability requires id and name")
        requirements = capability.get("requirements") or []
        for req in requirements:
            if not isinstance(req, dict):
                continue
            if not req.get("id") or not req.get("change_type"):
                add(findings, "FAIL", "invalid_requirement", "Capability requirement requires id and change_type")
            for scenario in req.get("scenarios") or []:
                if isinstance(scenario, dict) and not (scenario.get("id") and scenario.get("when") and scenario.get("then")):
                    add(findings, "FAIL", "invalid_scenario", f"Scenario in {req.get('id', '<req>')} requires id, when, and then")


def check_behaviour_discovery_brief(contract: dict[str, Any], findings: list[Finding], root: Path) -> None:
    """Discovery-stage-specific lint rules (discovery-improvement-plan M4.2).

    Three rule sets layered on top of the discovery_brief_contract.yaml
    structural schema:

    - W-spec-coverage: when spec.enabled=true, every capability under
      project-knowledge/specs/ must appear in contract.affected_capabilities (even
      if only as ASSUMED "not in scope"). Missing capability ⇒ FAIL so PRD
      cannot ship without a capability impact baseline.
    - W-discovery-contract: discovery-brief.md must not embed a fenced YAML
      control-contract island (duplicates the external contract.yaml).
    - W-gitnexus-source: brownfield missions (.gitnexus/ present) must have
      at least one gitnexus_symbol or gitnexus_query entry in
      existing_solutions[], otherwise the affected_capabilities chain leans on
      grep-only evidence.

    Each rule emits FAIL on violation (M4.2 strict mode); earlier milestones
    emitted WARN, but M4.2's whole point is upgrading to blocking severity.
    """
    mission_id = contract.get("mission_id")

    # --- W-spec-coverage --------------------------------------------------
    # spec.enabled is read from runtime config; default to True so a missing
    # config does not silently waive the rule.
    spec_enabled = True
    runtime_config_path = root / "harness-runtime" / "config" / "harness.yaml"
    if runtime_config_path.exists():
        try:
            runtime_cfg = yaml.safe_load(runtime_config_path.read_text(encoding="utf-8")) or {}
            spec_section = runtime_cfg.get("spec") if isinstance(runtime_cfg.get("spec"), dict) else {}
            spec_enabled = bool(spec_section.get("enabled", True))
        except yaml.YAMLError:
            pass

    if spec_enabled:
        specs_dir = root / "project-knowledge" / "specs"
        capability_dirs: list[str] = []
        if specs_dir.exists() and specs_dir.is_dir():
            for entry in sorted(specs_dir.iterdir()):
                if entry.is_dir():
                    capability_dirs.append(entry.name)
        affected = contract.get("affected_capabilities") or []
        affected_names = {
            str(item.get("capability"))
            for item in affected
            if isinstance(item, dict) and item.get("capability")
        }
        missing = [name for name in capability_dirs if name not in affected_names]
        if missing:
            add(
                findings, "FAIL", "discovery_spec_coverage_missing",
                f"W-spec-coverage: affected_capabilities[] missing entries for project-knowledge specs capabilities: {', '.join(missing)}. "
                f"Mark each as ASSUMED 'not in scope' if intentional.",
            )

    # --- W-discovery-contract --------------------------------------------
    # Sibling brief.md must not embed fenced YAML — the external contract is
    # the single source of truth for structured fields.
    if mission_id:
        brief_md = root / "harness-runtime" / "harness" / "stages" / str(mission_id) / "discovery-brief.md"
        if brief_md.exists():
            try:
                body = brief_md.read_text(encoding="utf-8")
                if "```yaml" in body:
                    add(
                        findings, "FAIL", "discovery_brief_embeds_fenced_yaml",
                        f"W-discovery-contract: discovery-brief.md contains a fenced YAML block; "
                        f"move structured fields to discovery-brief.contract.yaml. "
                        f"Path: {brief_md.relative_to(root) if brief_md.is_absolute() else brief_md}",
                    )
            except OSError:
                pass

    # --- W-gitnexus-source -----------------------------------------------
    # Brownfield = .gitnexus/ directory present (mirrors the gitnexus status
    # CLI's brownfield heuristic). When brownfield, existing_solutions[] must
    # carry at least one gitnexus_* source.
    gitnexus_dir = root / ".gitnexus"
    is_brownfield = gitnexus_dir.exists() and gitnexus_dir.is_dir() and any(gitnexus_dir.iterdir())
    if is_brownfield:
        existing = contract.get("existing_solutions") or []
        has_gitnexus = any(
            isinstance(item, dict) and str(item.get("source", "")).startswith("gitnexus")
            for item in existing
        )
        # Allow brownfield to opt out by recording a gitnexus degradation.
        degradations = contract.get("degradations") or []
        has_gitnexus_degradation = any(
            isinstance(item, dict) and str(item.get("kind", "")).startswith("gitnexus_")
            for item in degradations
        )
        if not has_gitnexus and not has_gitnexus_degradation:
            add(
                findings, "FAIL", "discovery_gitnexus_source_missing",
                "W-gitnexus-source: brownfield mission but existing_solutions[] has no "
                "gitnexus_symbol/gitnexus_query entry and degradations[] has no "
                "gitnexus_unavailable/gitnexus_stale entry. Either run gitnexus queries "
                "or record the degradation explicitly.",
            )


def check_behaviour_prd(contract: dict[str, Any], findings: list[Finding], root: Path) -> None:
    """PRD-stage-specific checks for behaviour_contract.

    Validates:
      1. capabilities[].confidence_from_discovery is present (UPSTREAM_SKIPPED if no discovery)
      2. agent_capability_requirements[] work_rights + eval_criteria when present
      3. capabilities[].requirement_ids ↔ specs/<cap>/spec.md name consistency
      4. effectiveness_review structure
    """
    # --- 1. confidence_from_discovery ---
    capabilities = contract.get("capabilities") or []
    for cap in capabilities:
        if not isinstance(cap, dict):
            continue
        cap_name = cap.get("capability") or cap.get("name") or "<unknown>"
        if "confidence_from_discovery" not in cap:
            add(findings, "WARN", "prd_missing_confidence_from_discovery",
                f"Capability '{cap_name}' missing confidence_from_discovery; set UPSTREAM_SKIPPED if discovery was skipped")

    # --- 2. agent_capability_requirements typed validation ---
    agent_reqs = contract.get("agent_capability_requirements") or []
    for req in agent_reqs:
        if not isinstance(req, dict):
            continue
        component = req.get("component") or "<unknown>"
        work_rights = req.get("work_rights") or []
        if not isinstance(work_rights, list):
            add(findings, "FAIL", "prd_invalid_work_rights",
                f"Agent capability '{component}' work_rights must be an array")
        eval_criteria = req.get("eval_criteria") or []
        if not isinstance(eval_criteria, list):
            add(findings, "FAIL", "prd_invalid_eval_criteria",
                f"Agent capability '{component}' eval_criteria must be an array")

    # --- 3. capabilities[].requirement_ids ↔ spec files consistency ---
    mission_id = contract.get("mission_id", "")
    for cap in capabilities:
        if not isinstance(cap, dict):
            continue
        cap_id = cap.get("capability") or cap.get("name") or ""
        if not cap_id:
            continue
        spec_path = root / "harness-runtime" / "harness" / "stages" / str(mission_id) / "specs" / cap_id / "spec.md"
        if spec_path.exists():
            spec_text = load_text(spec_path)
            spec_ids = set(ID_PATTERN.findall(spec_text))
            req_ids = set(cap.get("requirement_ids") or [])
            missing_in_spec = req_ids - spec_ids
            if missing_in_spec:
                add(findings, "WARN", "prd_spec_id_mismatch",
                    f"Capability '{cap_id}' requirement_ids {missing_in_spec} not found in {spec_path.name}")

    # --- 4. effectiveness_review structure ---
    eff = contract.get("effectiveness_review")
    if isinstance(eff, dict):
        if "rounds_used" not in eff:
            add(findings, "WARN", "prd_missing_rounds_used",
                "effectiveness_review missing rounds_used field")
        elif not isinstance(eff.get("rounds_used"), int):
            add(findings, "FAIL", "prd_invalid_rounds_used",
                "effectiveness_review.rounds_used must be an integer")
        if "max_rounds" not in eff:
            add(findings, "WARN", "prd_missing_max_rounds",
                "effectiveness_review missing max_rounds field")

        # M4.3: rounds_used > max_rounds requires tradeoff approval
        rounds_used = eff.get("rounds_used")
        max_rounds = eff.get("max_rounds")
        last_verdict = eff.get("last_verdict")
        if isinstance(rounds_used, int) and isinstance(max_rounds, int):
            if rounds_used >= max_rounds and last_verdict != "PASS":
                # Check for tradeoff approval
                approval_path = root / "harness-runtime" / "harness" / "state" / "approvals.json"
                has_tradeoff = False
                if approval_path.exists():
                    try:
                        approvals = json.loads(approval_path.read_text(encoding="utf-8"))
                        if isinstance(approvals, list):
                            for a in approvals:
                                if (isinstance(a, dict) and
                                    a.get("stage") == "prd" and
                                    a.get("type") in ("tradeoff", "prd_user_checkpoint") and
                                    a.get("status") == "approved"):
                                    has_tradeoff = True
                                    break
                    except (json.JSONDecodeError, OSError):
                        pass
                if not has_tradeoff:
                    add(findings, "FAIL", "prd_rounds_exceeded_without_approval",
                        f"rounds_used={rounds_used} >= max_rounds={max_rounds} with last_verdict={last_verdict}; "
                        "must have tradeoff/prd_user_checkpoint approval to proceed")

        # pending_reviewer_recheck must be false for advance
        if bool(eff.get("pending_reviewer_recheck")):
            add(findings, "FAIL", "prd_pending_recheck_not_cleared",
                "effectiveness_review.pending_reviewer_recheck=true; re-run product-definition-reviewer before advance")

    # --- 5. DDD domain_model structured fields ---
    domain_model = contract.get("domain_model")
    required_domain_model_keys = (
        "bounded_contexts",
        "aggregates",
        "commands",
        "events",
        "invariants",
        "state_machines",
        "permission_rules",
        "modeling_risks",
    )
    if domain_model is None:
        return
    if not isinstance(domain_model, dict):
        add(findings, "FAIL", "prd_invalid_domain_model",
            "domain_model must be an object")
    else:
        for key in required_domain_model_keys:
            if key not in domain_model:
                add(findings, "FAIL", "prd_domain_model_field_missing",
                    f"domain_model.{key} is required")
            elif not isinstance(domain_model.get(key), list):
                add(findings, "FAIL", "prd_domain_model_field_invalid",
                    f"domain_model.{key} must be an array")


def load_yaml_file(path: Path) -> dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def has_e2e_failure_signal(payload: dict[str, Any]) -> bool:
    if payload.get("missing_capabilities"):
        return True
    if payload.get("skipped_tests") or payload.get("flaky_signals"):
        return True
    for run in payload.get("runs") or []:
        if not isinstance(run, dict):
            continue
        status = run.get("status")
        result = run.get("result")
        if not status and isinstance(result, dict):
            status = result.get("status")
        if str(status).lower() in {"fail", "failed", "error", "timeout", "skipped", "flaky"}:
            return True
    return False


def has_e2e_obligations(payload: dict[str, Any]) -> bool:
    obligations = payload.get("obligations")
    return isinstance(obligations, list) and bool(obligations)


def is_e2e_enabled(config: dict[str, Any]) -> bool:
    e2e = config.get("e2e")
    if not isinstance(e2e, dict):
        return True
    return e2e.get("enabled", True) is not False


def check_action(contract: dict[str, Any], findings: list[Finding], upstream_ids: set[str], root: Path, allow_placeholders: bool = False) -> None:
    tasks = contract.get("tasks") or []
    if not tasks:
        add(findings, "FAIL", "missing_tasks", "action_contract must declare tasks")
    required_stop = {
        "changes_outside_authorized_paths",
        "new_public_behavior_without_delta_spec",
        "design_constraint_conflict",
        "new_external_dependency",
    }
    config = load_yaml_file(root / "harness-runtime/config/harness.yaml")
    policy = config.get("test_toolchain") if isinstance(config.get("test_toolchain"), dict) else {}
    e2e_policy = config.get("e2e") if isinstance(config.get("e2e"), dict) else {}
    e2e_enabled = is_e2e_enabled(config)
    queue_contract = contract.get("atomic_task_queue") if isinstance(contract.get("atomic_task_queue"), dict) else {}
    atomic_queue_required = boolish_true(queue_contract.get("required"))
    queue_artifact = str(queue_contract.get("artifact") or "")
    queue_text = ""
    if atomic_queue_required:
        if not queue_artifact:
            add(findings, "FAIL", "missing_atomic_task_queue_artifact", "atomic_task_queue.required=true requires atomic_task_queue.artifact")
        elif not allow_placeholders and not contains_placeholder(queue_artifact):
            queue_path = Path(queue_artifact)
            if not queue_path.is_absolute():
                queue_path = root / queue_path
            if not queue_path.exists():
                add(findings, "FAIL", "missing_atomic_task_queue", f"Required Atomic Task Queue artifact not found: {queue_artifact}")
            elif queue_path.suffix.lower() in {".md", ".markdown"}:
                queue_text = queue_path.read_text(encoding="utf-8")
                if "## Execution Units" not in queue_text or "atomic_task_queue:" not in queue_text:
                    add(
                        findings,
                        "FAIL",
                        "missing_atomic_task_queue_structure",
                        f"Required parent-local atomic_task_queue structure not found in {queue_artifact}",
                    )
                if "Atomic Task details" not in queue_text:
                    add(
                        findings,
                        "FAIL",
                        "missing_atomic_task_details_section",
                        f"Required Atomic Task details section not found in {queue_artifact}",
                    )
    for task in tasks:
        if not isinstance(task, dict):
            add(findings, "FAIL", "invalid_task", "Task entries must be objects")
            continue
        tid = task.get("id", "<unknown>")
        if not task.get("id"):
            add(findings, "FAIL", "missing_task_id", "Task missing id")
        traces = task.get("traces_to") or []
        if not traces:
            add(findings, "FAIL", "missing_task_trace", f"{tid} lacks traces_to")
        for ref in traces:
            if upstream_ids and ref not in upstream_ids:
                add(findings, "FAIL", "broken_task_reference", f"{tid} traces_to unknown ID: {ref}")
        if not task.get("required_evidence"):
            add(findings, "FAIL", "missing_required_evidence", f"{tid} lacks required_evidence")
        if contract.get("stage") == "breakdown":
            check_tdd_scope(task, str(tid), findings, allow_placeholders)
        task_queue = task.get("atomic_task_queue")
        if atomic_queue_required:
            if not isinstance(task_queue, dict):
                add(findings, "FAIL", "missing_parent_task_atomic_task_queue", f"{tid} lacks parent-local atomic_task_queue while Atomic Task Queue is required")
            else:
                status = str(task_queue.get("status") or "").strip().lower()
                if status != "ready":
                    add(findings, "FAIL", "invalid_parent_task_atomic_task_queue_status", f"{tid} atomic_task_queue.status must be ready")
                atomic_ids = task_queue.get("atomic_task_ids")
                execution_units = task_queue.get("execution_units")
                if atomic_ids is not None and not isinstance(atomic_ids, list):
                    add(findings, "FAIL", "invalid_parent_task_atomic_task_queue", f"{tid} atomic_task_queue.atomic_task_ids must be a list")
                if execution_units is not None and not isinstance(execution_units, list):
                    add(findings, "FAIL", "invalid_parent_task_atomic_task_queue", f"{tid} atomic_task_queue.execution_units must be a list")
                if atomic_ids is None and execution_units is None:
                    add(findings, "FAIL", "missing_parent_task_atomic_task_ids", f"{tid} atomic_task_queue must list Atomic Task ids or execution_units")
                if atomic_ids == [] or execution_units == []:
                    add(findings, "FAIL", "empty_parent_task_atomic_task_queue", f"{tid} atomic_task_queue must contain at least one Atomic Task")
                detail_ids: list[str] = []
                if isinstance(atomic_ids, list):
                    detail_ids.extend(str(item) for item in atomic_ids if isinstance(item, (str, int)))
                if isinstance(execution_units, list):
                    for unit in execution_units:
                        if isinstance(unit, dict) and unit.get("id"):
                            detail_ids.append(str(unit.get("id")))
                if queue_text and not allow_placeholders:
                    for atomic_id in sorted(set(detail_ids)):
                        if contains_placeholder(atomic_id):
                            continue
                        if not markdown_heading_exists(queue_text, atomic_id, min_level=4, max_level=6):
                            add(findings, "FAIL", "missing_atomic_task_detail", f"{tid} Atomic Task detail heading not found for {atomic_id}")
                            continue
                        detail_section = markdown_heading_section(queue_text, atomic_id, min_level=4, max_level=6)
                        required_detail_markers = {
                            "目标": "**目标",
                            "执行边界": "**执行边界",
                            "文件行动": "**文件行动",
                            "输入": "**输入",
                            "输出": "**输出",
                            "代码模式参考": "**代码模式参考",
                            "TDD 范围": "**TDD 范围",
                            "执行期验证命令": "**执行期验证命令",
                            "证据": "**证据",
                            "停止条件": "**停止条件",
                        }
                        for label, marker in required_detail_markers.items():
                            if marker not in detail_section:
                                add(findings, "FAIL", "missing_atomic_task_detail_field", f"{tid} {atomic_id} lacks Atomic Task detail field: {label}")
        readiness = task.get("atomic_task_readiness") or task.get("executor_readiness")
        if isinstance(readiness, dict):
            missing_readiness = readiness.get("atomic_task_gaps", readiness.get("missing_fields"))
            ready_fields = readiness.get("ready_fields")
            if missing_readiness is not None and not isinstance(missing_readiness, list):
                add(findings, "FAIL", "invalid_atomic_task_readiness", f"{tid} atomic_task_readiness.atomic_task_gaps must be a list")
            if ready_fields is not None and not isinstance(ready_fields, list):
                add(findings, "FAIL", "invalid_atomic_task_readiness", f"{tid} atomic_task_readiness.ready_fields must be a list")
        obligation = task.get("test_obligation")
        if not isinstance(obligation, dict):
            if normalize_obligation is None or is_obligation_complete is None:
                add(findings, "FAIL", "missing_test_obligation", f"{tid} lacks test_obligation and inference helper is unavailable")
            else:
                inferred = normalize_obligation(task, policy)
                if is_obligation_complete(inferred):
                    add(
                        findings,
                        "WARN",
                        "inferred_test_obligation",
                        f"{tid} lacks test_obligation; Harness inferred {inferred.get('risk_level')} / {', '.join(inferred.get('surfaces') or [])}",
                    )
                else:
                    add(findings, "FAIL", "missing_test_obligation", f"{tid} lacks test_obligation and Harness could not infer one")
        else:
            if normalize_obligation is not None and is_obligation_complete is not None:
                normalized = normalize_obligation(task, policy)
                inferred_fields = normalized.get("_harness_inferred_fields") or []
                if inferred_fields:
                    add(findings, "WARN", "partial_test_obligation_inferred", f"{tid} test_obligation missing fields inferred by Harness: {', '.join(inferred_fields)}")
            if obligation.get("risk_level") not in {"low", "medium", "high"}:
                add(findings, "FAIL", "invalid_test_obligation_risk", f"{tid} test_obligation risk_level must be low, medium, or high")
            for field in ("surfaces", "required_capabilities", "evidence_required"):
                values = obligation.get(field)
                if not isinstance(values, list) or not values:
                    add(findings, "FAIL", "invalid_test_obligation", f"{tid} test_obligation requires non-empty {field}")
        if e2e_enabled:
            e2e_obligation = task.get("e2e_obligation")
            if not isinstance(e2e_obligation, dict):
                if normalize_e2e_obligation is None or is_e2e_obligation_complete is None:
                    add(findings, "FAIL", "missing_e2e_obligation", f"{tid} lacks e2e_obligation and Harness could not infer one")
                else:
                    inferred_e2e = normalize_e2e_obligation(task, e2e_policy)
                    e2e_required = inferred_e2e.get("_harness_e2e_required", True)
                    if e2e_required and is_e2e_obligation_complete(inferred_e2e):
                        add(
                            findings,
                            "WARN",
                            "inferred_e2e_obligation",
                            f"{tid} lacks e2e_obligation; Harness inferred {inferred_e2e.get('risk_level')} / {', '.join(inferred_e2e.get('user_surfaces') or [])}",
                        )
                    elif e2e_required:
                        add(findings, "FAIL", "missing_e2e_obligation", f"{tid} lacks e2e_obligation and Harness could not infer one")
            else:
                if normalize_e2e_obligation is not None and is_e2e_obligation_complete is not None:
                    normalized_e2e = normalize_e2e_obligation(task, e2e_policy)
                    inferred_fields = normalized_e2e.get("_harness_inferred_fields") or []
                    if inferred_fields:
                        add(findings, "WARN", "partial_e2e_obligation_inferred", f"{tid} e2e_obligation missing fields inferred by Harness: {', '.join(inferred_fields)}")
                if e2e_obligation.get("risk_level") not in {"low", "medium", "high"}:
                    add(findings, "FAIL", "invalid_e2e_obligation_risk", f"{tid} e2e_obligation risk_level must be low, medium, or high")
                for field in ("user_surfaces", "required_capabilities", "evidence_required"):
                    values = e2e_obligation.get(field)
                    if not isinstance(values, list) or not values:
                        add(findings, "FAIL", "invalid_e2e_obligation", f"{tid} e2e_obligation requires non-empty {field}")
        stop_if = set(task.get("stop_if") or [])
        missing = sorted(required_stop - stop_if)
        if missing:
            add(findings, "WARN", "missing_stop_condition", f"{tid} stop_if lacks: {', '.join(missing)}")


def check_verification(contract: dict[str, Any], findings: list[Finding], upstream_ids: set[str]) -> None:
    evidence_ids = {entry.get("id") for entry in contract.get("command_evidence") or [] if isinstance(entry, dict)}
    result_evidence_ids = {entry.get("id") for entry in contract.get("result_evidence") or [] if isinstance(entry, dict)}
    if not result_evidence_ids:
        add(findings, "FAIL", "missing_result_evidence", "verification_evidence requires result_evidence")
    ac_trace = contract.get("ac_trace") or []
    if not ac_trace:
        add(findings, "FAIL", "missing_ac_trace", "verification_evidence requires ac_trace")
    for row in ac_trace:
        if not isinstance(row, dict):
            continue
        ac = row.get("ac", "<unknown>")
        conclusion = row.get("conclusion")
        if upstream_ids and ac not in upstream_ids:
            add(findings, "FAIL", "broken_ac_trace", f"ac_trace references unknown AC: {ac}")
        if conclusion == "pass":
            evidence = row.get("evidence") or []
            if not evidence:
                add(findings, "FAIL", "missing_pass_evidence", f"{ac} is pass but has no evidence")
            has_command = any(str(ev).startswith("CMD-") for ev in evidence)
            has_result = any(str(ev).startswith("EV-RESULT-") for ev in evidence)
            if not has_command:
                add(findings, "FAIL", "missing_command_evidence", f"{ac} is pass but has no command evidence")
            if not has_result:
                add(findings, "FAIL", "missing_result_evidence_reference", f"{ac} is pass but has no result evidence")
            for ev in evidence:
                if str(ev).startswith("CMD-") and ev not in evidence_ids:
                    add(findings, "FAIL", "broken_evidence_reference", f"{ac} references unknown command evidence: {ev}")
                if str(ev).startswith("EV-RESULT-") and ev not in result_evidence_ids:
                    add(findings, "FAIL", "broken_result_evidence_reference", f"{ac} references unknown result evidence: {ev}")
        elif conclusion == "blocked":
            for field in ("blocked_reason", "impact", "next_step"):
                if not row.get(field):
                    add(findings, "FAIL", "missing_blocked_detail", f"{ac} blocked lacks {field}")
        elif conclusion not in {"fail", "not_applicable"}:
            add(findings, "FAIL", "invalid_ac_conclusion", f"{ac} has invalid conclusion: {conclusion}")
    for evidence in contract.get("command_evidence") or []:
        if not isinstance(evidence, dict):
            continue
        artifact = evidence.get("artifact")
        if artifact and not contains_placeholder(str(artifact)):
            artifact_path = Path(artifact)
            if not artifact_path.is_absolute():
                artifact_path = Path.cwd() / artifact_path
            if not artifact_path.exists():
                add(findings, "FAIL", "evidence_artifact_missing", f"Evidence artifact not found: {artifact}")
    for evidence in contract.get("result_evidence") or []:
        if not isinstance(evidence, dict):
            continue
        eid = evidence.get("id", "<result-evidence>")
        for field in ("ac", "expected", "actual", "reproduce", "artifact", "result"):
            if not evidence.get(field):
                add(findings, "FAIL", "invalid_result_evidence", f"{eid} lacks {field}")


def check_solution_guide(contract: dict[str, Any], findings: list[Finding], upstream_ids: set[str]) -> None:
    decisions = contract.get("decisions") or []
    if not decisions:
        add(findings, "FAIL", "missing_decisions", "solution_guide requires at least one decision")
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        did = decision.get("id", "<decision>")
        for field in ("id", "chosen", "rationale", "traces_to"):
            if not decision.get(field):
                add(findings, "FAIL", "invalid_decision", f"{did} missing {field}")
        for ref in decision.get("traces_to") or []:
            if upstream_ids and ref not in upstream_ids:
                add(findings, "FAIL", "broken_decision_reference", f"{did} traces_to unknown ID: {ref}")
    for item in contract.get("forbidden_paths") or []:
        if isinstance(item, dict) and not item.get("reason"):
            add(findings, "FAIL", "forbidden_path_reason_missing", f"{item.get('id', '<forbidden>')} lacks reason")
    for risk in contract.get("risks") or []:
        if isinstance(risk, dict) and not risk.get("mitigation"):
            add(findings, "FAIL", "risk_mitigation_missing", f"{risk.get('id', '<risk>')} lacks mitigation")
    # Stage-4 M4.1: agent_architecture[].traces_to_prd cross-contract check.
    # Each entry must point to an R-AGENT-* ID present in upstream contracts
    # (typically prd.contract.yaml.agent_capability_requirements[].component
    # or behaviour_requirements). Skipped when agent_architecture is empty
    # (agent_engineering.enabled=false case).
    for entry in contract.get("agent_architecture") or []:
        if not isinstance(entry, dict):
            continue
        component = entry.get("component", "<agent_architecture>")
        traces = entry.get("traces_to_prd") or []
        for ref in traces:
            if upstream_ids and ref not in upstream_ids:
                add(
                    findings,
                    "FAIL",
                    "broken_agent_architecture_trace",
                    f"agent_architecture[{component}] traces_to_prd unknown ID: {ref}",
                )


_REQUIRED_EVAL_KINDS = frozenset({"normal", "boundary", "adversarial", "ambiguous"})


def check_technical_guide(
    contract: dict[str, Any],
    findings: list[Finding],
    upstream_ids: set[str],
    upstream_agent_architecture_components: set[str] | None = None,
    upstream_agent_engineering_scope: str | None = None,
) -> None:
    modules = contract.get("modules") or []
    if not modules:
        add(findings, "FAIL", "missing_modules", "technical_guide requires at least one module")
    for module in modules:
        if not isinstance(module, dict):
            continue
        mid = module.get("id", "<module>")
        if not module.get("responsibility"):
            add(findings, "FAIL", "module_responsibility_missing", f"{mid} lacks responsibility")
        for ref in module.get("traces_to") or []:
            if upstream_ids and ref not in upstream_ids:
                add(findings, "FAIL", "broken_module_reference", f"{mid} traces_to unknown ID: {ref}")
    # verification_strategy.target_ids may reference upstream requirement IDs
    # (AC / FR / NFR / DEC) OR this contract's own modules[].id — a VS that
    # targets a local module is a valid local reference, not a broken trace.
    local_module_ids = {
        module.get("id")
        for module in modules
        if isinstance(module, dict) and module.get("id")
    }
    for strategy in contract.get("verification_strategy") or []:
        if not isinstance(strategy, dict):
            continue
        sid = strategy.get("id", "<verification-strategy>")
        target_ids = strategy.get("target_ids") or []
        if not target_ids:
            add(findings, "FAIL", "verification_target_missing", f"{sid} lacks target_ids")
        for ref in target_ids:
            if upstream_ids and ref not in upstream_ids and ref not in local_module_ids:
                add(findings, "FAIL", "broken_verification_reference", f"{sid} targets unknown ID: {ref}")
    # Stage-4 M4.1: interface_changes[].traces_to + data_changes[].traces_to
    # cross-contract checks for the typed M1.4 fields.
    for ifc in contract.get("interface_changes") or []:
        if not isinstance(ifc, dict):
            continue
        ifc_id = ifc.get("id", "<interface_change>")
        for ref in ifc.get("traces_to") or []:
            if upstream_ids and ref not in upstream_ids:
                add(findings, "FAIL", "broken_interface_change_reference", f"{ifc_id} traces_to unknown ID: {ref}")
    for dc in contract.get("data_changes") or []:
        if not isinstance(dc, dict):
            continue
        dc_id = dc.get("id", "<data_change>")
        for ref in dc.get("traces_to") or []:
            if upstream_ids and ref not in upstream_ids:
                add(findings, "FAIL", "broken_data_change_reference", f"{dc_id} traces_to unknown ID: {ref}")
    # Stage-4 M4.1 + 偏离修正3: agent_implementation[] cross-contract checks.
    # traces_to_prd_capability must hit R-AGENT-* IDs in upstream (regex set).
    # traces_to_solution_arch is structured: each ref must equal a
    # solution.contract.yaml.agent_architecture[].component string. The
    # structured extractor (agent_architecture_components_from_yaml) supplies
    # this set; falling back to upstream_ids only when no structured set is
    # provided keeps backward compatibility for callers that didn't load
    # solution.contract.yaml as a YAML upstream.
    components_set = upstream_agent_architecture_components or set()
    strict_eval = upstream_agent_engineering_scope == "core"
    for ai in contract.get("agent_implementation") or []:
        if not isinstance(ai, dict):
            continue
        component = ai.get("component", "<agent_implementation>")
        # Stage-4 M4.3 strict mode: when mission-contract.agent_engineering.scope=core,
        # eval_scenarios must include all four canonical kinds. scope=experimental
        # or unset only triggers schema-level enum validation (M1.4).
        if strict_eval:
            scenarios = ai.get("eval_scenarios") or []
            kinds_present = {
                s.get("kind") for s in scenarios
                if isinstance(s, dict) and isinstance(s.get("kind"), str)
            }
            missing = _REQUIRED_EVAL_KINDS - kinds_present
            if missing:
                add(
                    findings,
                    "FAIL",
                    "agent_implementation_eval_kinds_incomplete",
                    f"agent_implementation[{component}] eval_scenarios missing kind(s): "
                    f"{sorted(missing)} (agent_engineering.scope=core requires all of "
                    f"{sorted(_REQUIRED_EVAL_KINDS)})",
                )
        for ref in ai.get("traces_to_prd_capability") or []:
            if upstream_ids and ref not in upstream_ids:
                add(
                    findings,
                    "FAIL",
                    "broken_agent_implementation_prd_trace",
                    f"agent_implementation[{component}] traces_to_prd_capability unknown ID: {ref}",
                )
        for ref in ai.get("traces_to_solution_arch") or []:
            # Strict mode: when an upstream solution.contract.yaml is supplied
            # with agent_architecture[] entries, validate against those
            # components. Permissive fallback only when no structured set is
            # available (e.g. caller didn't pass solution.contract.yaml).
            if components_set:
                if ref not in components_set:
                    add(
                        findings,
                        "FAIL",
                        "broken_agent_implementation_solution_trace",
                        f"agent_implementation[{component}] traces_to_solution_arch unknown component: {ref} (must match solution.contract.yaml.agent_architecture[].component)",
                    )
            elif upstream_ids and ref not in upstream_ids:
                add(
                    findings,
                    "FAIL",
                    "broken_agent_implementation_solution_trace",
                    f"agent_implementation[{component}] traces_to_solution_arch unknown ID: {ref}",
                )


def check_review_evidence(
    contract: dict[str, Any],
    findings: list[Finding],
    upstream_ids: set[str],
    root: Path,
    allow_placeholders: bool,
) -> None:
    reviewers = contract.get("reviewers") or []
    findings_list = contract.get("findings") or []
    allowed_verdicts = {"PASS", "HOLD", "PASS_WITH_RISK", "BLOCKED"}
    config = load_yaml_file(root / "harness-runtime/config/harness.yaml")
    e2e_enabled = is_e2e_enabled(config)
    if not reviewers:
        add(findings, "FAIL", "missing_reviewers", "review_evidence requires reviewers")
    roles = {reviewer.get("role") for reviewer in reviewers if isinstance(reviewer, dict)}
    if "tdd" not in roles:
        add(findings, "FAIL", "missing_tdd_reviewer", "code-review requires tdd reviewer verdict")
    for reviewer in reviewers:
        if not isinstance(reviewer, dict):
            continue
        rid = reviewer.get("id", "<reviewer>")
        verdict = reviewer.get("verdict")
        if not verdict:
            add(findings, "FAIL", "reviewer_verdict_missing", f"{rid} lacks verdict")
        elif verdict not in allowed_verdicts:
            add(findings, "FAIL", "reviewer_verdict_invalid", f"{rid} has invalid verdict: {verdict}")
        if not reviewer.get("role_boundary"):
            add(findings, "FAIL", "reviewer_boundary_missing", f"{rid} lacks role_boundary")
        if not reviewer.get("review_basis"):
            add(findings, "FAIL", "reviewer_basis_missing", f"{rid} lacks review_basis")
        if reviewer.get("role") == "e2e":
            if not reviewer.get("role_boundary"):
                add(findings, "FAIL", "e2e_reviewer_boundary_missing", f"{rid} e2e reviewer lacks role_boundary")
            if not reviewer.get("review_basis"):
                add(findings, "FAIL", "e2e_reviewer_basis_missing", f"{rid} e2e reviewer lacks review_basis")
    open_findings = [item for item in findings_list if isinstance(item, dict) and item.get("status") == "open"]
    if any(isinstance(reviewer, dict) and reviewer.get("verdict") == "HOLD" for reviewer in reviewers) and not open_findings:
        add(findings, "FAIL", "hold_without_open_finding", "Reviewer HOLD requires at least one open finding")
    tdd_reviewers = [reviewer for reviewer in reviewers if isinstance(reviewer, dict) and reviewer.get("role") == "tdd"]
    if tdd_reviewers:
        toolchain_probe = contract.get("toolchain_probe")
        if not isinstance(toolchain_probe, dict):
            add(findings, "FAIL", "missing_toolchain_probe", "tdd reviewer requires toolchain_probe block")
        else:
            probe_status = toolchain_probe.get("status")
            if probe_status not in {"PASS", "WARN", "FAIL"}:
                add(findings, "FAIL", "invalid_toolchain_probe_status", f"toolchain_probe has invalid status: {probe_status}")
            probe_artifact = toolchain_probe.get("artifact")
            if not probe_artifact:
                add(findings, "FAIL", "missing_toolchain_probe_artifact", "toolchain_probe requires artifact")
            elif not contains_placeholder(probe_artifact):
                probe_path = root / probe_artifact
                if not allow_placeholders and not probe_path.exists():
                    add(findings, "FAIL", "toolchain_probe_artifact_missing", f"Toolchain probe artifact not found: {probe_artifact}")
            if "signals" not in toolchain_probe:
                add(findings, "FAIL", "missing_toolchain_probe_signals", "toolchain_probe requires signals")
        toolchain_status_block = contract.get("toolchain_status")
        if not isinstance(toolchain_status_block, dict):
            add(findings, "FAIL", "missing_toolchain_status", "tdd reviewer requires toolchain_status block")
        else:
            toolchain_status = toolchain_status_block.get("status")
            if toolchain_status not in {"PASS", "WARN", "FAIL", "BLOCKED"}:
                add(findings, "FAIL", "invalid_toolchain_status", f"toolchain_status has invalid status: {toolchain_status}")
            status_payload: dict[str, Any] = {}
            for field in ("plan_artifact", "status_artifact"):
                artifact = toolchain_status_block.get(field)
                if not artifact:
                    add(findings, "FAIL", "missing_toolchain_status_artifact", f"toolchain_status requires {field}")
                elif not contains_placeholder(artifact):
                    artifact_path = root / artifact
                    if not allow_placeholders and not artifact_path.exists():
                        add(findings, "FAIL", "toolchain_status_artifact_missing", f"Toolchain status artifact not found: {artifact}")
                    elif field == "status_artifact" and artifact_path.exists():
                        status_payload = load_json_file(artifact_path)
            if toolchain_status == "BLOCKED" and not toolchain_status_block.get("decision_gate_reasons"):
                add(findings, "FAIL", "missing_toolchain_decision_gate_reason", "BLOCKED toolchain_status requires decision_gate_reasons")
            if status_payload:
                if status_payload.get("type") != "toolchain_status":
                    add(findings, "FAIL", "invalid_toolchain_status_payload", "toolchain-status artifact type must be toolchain_status")
                actual_status = status_payload.get("status")
                if actual_status and toolchain_status and actual_status != toolchain_status:
                    add(findings, "FAIL", "toolchain_status_mismatch", f"contract status {toolchain_status} differs from artifact status {actual_status}")
                actual_missing = status_payload.get("missing_capabilities") or []
                contract_missing = toolchain_status_block.get("missing_capabilities") or []
                if contract_missing != actual_missing:
                    add(findings, "FAIL", "toolchain_missing_capabilities_mismatch", "contract missing_capabilities differs from toolchain-status artifact")
                actual_reasons = status_payload.get("decision_gate_reasons") or []
                contract_reasons = toolchain_status_block.get("decision_gate_reasons") or []
                if contract_reasons != actual_reasons:
                    add(findings, "FAIL", "toolchain_decision_gate_reasons_mismatch", "contract decision_gate_reasons differs from toolchain-status artifact")
                if actual_status == "FAIL" and not actual_missing:
                    add(findings, "FAIL", "toolchain_fail_without_missing_capabilities", "toolchain-status FAIL requires missing_capabilities")
                if actual_status == "BLOCKED" and not actual_reasons:
                    add(findings, "FAIL", "toolchain_blocked_without_reasons", "toolchain-status BLOCKED requires decision_gate_reasons")
        tdd_review = contract.get("tdd_review")
        if not isinstance(tdd_review, dict):
            add(findings, "FAIL", "missing_tdd_review", "tdd reviewer requires tdd_review block")
        else:
            tdd_verdict = tdd_review.get("verdict")
            reviewer_verdict = tdd_reviewers[0].get("verdict")
            if not tdd_verdict:
                add(findings, "FAIL", "missing_tdd_verdict", "tdd_review lacks verdict")
            elif tdd_verdict not in {"PASS", "HOLD", "PASS_WITH_RISK"}:
                add(findings, "FAIL", "invalid_tdd_verdict", f"tdd_review has invalid verdict: {tdd_verdict}")
            elif reviewer_verdict and reviewer_verdict != tdd_verdict:
                add(findings, "FAIL", "tdd_verdict_mismatch", "tdd reviewer verdict and tdd_review.verdict differ")
            if not tdd_review.get("role_boundary"):
                add(findings, "FAIL", "missing_tdd_boundary", "tdd_review requires role_boundary")
            if toolchain_probe and isinstance(toolchain_probe, dict):
                probe_artifact = toolchain_probe.get("artifact")
                review_probe_artifact = tdd_review.get("probe_artifact")
                if probe_artifact and review_probe_artifact and probe_artifact != review_probe_artifact:
                    add(findings, "FAIL", "toolchain_probe_artifact_mismatch", "toolchain_probe.artifact and tdd_review.probe_artifact differ")
            if toolchain_status_block and isinstance(toolchain_status_block, dict):
                status_artifact = toolchain_status_block.get("status_artifact")
                review_status_artifact = tdd_review.get("toolchain_status_artifact")
                if status_artifact and review_status_artifact and status_artifact != review_status_artifact:
                    add(findings, "FAIL", "toolchain_status_artifact_mismatch", "toolchain_status.status_artifact and tdd_review.toolchain_status_artifact differ")
            if not tdd_review.get("toolchain_signal_handling"):
                add(findings, "FAIL", "missing_tdd_toolchain_signal_handling", "tdd_review requires toolchain_signal_handling")
            if not tdd_review.get("adequacy_matrix"):
                add(findings, "FAIL", "missing_tdd_matrix", "tdd_review requires non-empty adequacy_matrix")
            if tdd_verdict == "HOLD" and not tdd_review.get("blocking_gaps"):
                add(findings, "FAIL", "missing_tdd_blocking_gaps", "tdd_review HOLD requires blocking_gaps")
            if tdd_verdict == "PASS" and tdd_review.get("blocking_gaps"):
                add(findings, "FAIL", "pass_with_tdd_blocking_gaps", "tdd_review PASS cannot include blocking_gaps")
    e2e_reviewers = [reviewer for reviewer in reviewers if isinstance(reviewer, dict) and reviewer.get("role") == "e2e"]
    e2e_status_block = contract.get("e2e_status")
    e2e_review_required = False
    if e2e_enabled:
        if not isinstance(e2e_status_block, dict):
            add(findings, "FAIL", "missing_e2e_status", "e2e.enabled=true requires e2e_status block")
        else:
            e2e_status = e2e_status_block.get("status")
            if e2e_status not in {"PASS", "WARN", "FAIL", "BLOCKED"}:
                add(findings, "FAIL", "invalid_e2e_status", f"e2e_status has invalid status: {e2e_status}")
            e2e_payload: dict[str, Any] = {}
            e2e_status_artifact_loaded = False
            for field in ("plan_artifact", "status_artifact"):
                artifact = e2e_status_block.get(field)
                if not artifact:
                    add(findings, "FAIL", "missing_e2e_status_artifact", f"e2e_status requires {field}")
                elif not contains_placeholder(artifact):
                    artifact_path = root / artifact
                    if not allow_placeholders and not artifact_path.exists():
                        add(findings, "FAIL", "e2e_status_artifact_missing", f"E2E status artifact not found: {artifact}")
                    elif field == "status_artifact" and artifact_path.exists():
                        e2e_payload = load_json_file(artifact_path)
                        e2e_status_artifact_loaded = True
            if e2e_status == "BLOCKED" and not e2e_status_block.get("decision_gate_reasons"):
                add(findings, "FAIL", "missing_e2e_decision_gate_reason", "BLOCKED e2e_status requires decision_gate_reasons")
            if e2e_status_artifact_loaded and not e2e_payload:
                add(findings, "FAIL", "invalid_e2e_status_payload", "e2e-status artifact must be a non-empty JSON object")
            if has_e2e_obligations(e2e_status_block) or has_e2e_obligations(e2e_payload):
                e2e_review_required = True
            if e2e_payload:
                if e2e_payload.get("type") != "e2e_status":
                    add(findings, "FAIL", "invalid_e2e_status_payload", "e2e-status artifact type must be e2e_status")
                actual_status = e2e_payload.get("status")
                if actual_status and e2e_status and actual_status != e2e_status:
                    add(findings, "FAIL", "e2e_status_mismatch", f"contract status {e2e_status} differs from artifact status {actual_status}")
                actual_missing = e2e_payload.get("missing_capabilities") or []
                contract_missing = e2e_status_block.get("missing_capabilities") or []
                if contract_missing != actual_missing:
                    add(findings, "FAIL", "e2e_missing_capabilities_mismatch", "contract missing_capabilities differs from e2e-status artifact")
                actual_reasons = e2e_payload.get("decision_gate_reasons") or []
                contract_reasons = e2e_status_block.get("decision_gate_reasons") or []
                if contract_reasons != actual_reasons:
                    add(findings, "FAIL", "e2e_decision_gate_reasons_mismatch", "contract decision_gate_reasons differs from e2e-status artifact")
                if actual_status == "BLOCKED" and not actual_reasons:
                    add(findings, "FAIL", "e2e_blocked_without_reasons", "e2e-status BLOCKED requires decision_gate_reasons")
                if actual_status == "FAIL" and not has_e2e_failure_signal(e2e_payload):
                    add(findings, "FAIL", "e2e_fail_without_failure_signal", "e2e-status FAIL requires missing_capabilities, skipped_tests, flaky_signals, or failed runs")
    if e2e_review_required and not e2e_reviewers:
        add(findings, "FAIL", "missing_e2e_reviewer", "E2E obligations require e2e reviewer verdict")
    if e2e_reviewers or e2e_review_required:
        e2e_review = contract.get("e2e_review")
        if not isinstance(e2e_review, dict):
            add(findings, "FAIL", "missing_e2e_review", "e2e reviewer requires e2e_review block")
        else:
            e2e_verdict = e2e_review.get("verdict")
            reviewer_verdict = e2e_reviewers[0].get("verdict") if e2e_reviewers else None
            if not e2e_verdict:
                add(findings, "FAIL", "missing_e2e_verdict", "e2e_review lacks verdict")
            elif e2e_verdict not in {"PASS", "HOLD", "PASS_WITH_RISK"}:
                add(findings, "FAIL", "invalid_e2e_verdict", f"e2e_review has invalid verdict: {e2e_verdict}")
            elif reviewer_verdict and reviewer_verdict != e2e_verdict:
                add(findings, "FAIL", "e2e_verdict_mismatch", "e2e reviewer verdict and e2e_review.verdict differ")
            if not e2e_review.get("role_boundary"):
                add(findings, "FAIL", "missing_e2e_boundary", "e2e_review requires role_boundary")
            methodology_ref = e2e_review.get("methodology_ref")
            if methodology_ref != ".harness/docs/e2e-effectiveness-reviewer-methodology.md":
                add(
                    findings,
                    "FAIL",
                    "missing_e2e_methodology_ref",
                    "e2e_review requires methodology_ref .harness/docs/e2e-effectiveness-reviewer-methodology.md",
                )
            if not e2e_review.get("coverage_matrix"):
                add(findings, "FAIL", "missing_e2e_coverage_matrix", "e2e_review requires non-empty coverage_matrix")
            else:
                required_matrix_fields = {
                    "target",
                    "obligation_refs",
                    "e2e_test_refs",
                    "user_result_assertion",
                    "data_reality",
                    "negative_path",
                    "realtime_or_refresh",
                    "reliability",
                    "diagnostics",
                    "conclusion",
                }
                for index, row in enumerate(e2e_review.get("coverage_matrix") or [], start=1):
                    if not isinstance(row, dict):
                        add(findings, "FAIL", "invalid_e2e_coverage_row", f"e2e_review.coverage_matrix[{index}] must be an object")
                        continue
                    missing_fields = sorted(field for field in required_matrix_fields if field not in row)
                    if missing_fields:
                        add(
                            findings,
                            "FAIL",
                            "invalid_e2e_coverage_row",
                            f"e2e_review.coverage_matrix[{index}] missing fields: {', '.join(missing_fields)}",
                        )
            for field in ("blocking_gaps", "non_blocking_risks"):
                if field not in e2e_review or not isinstance(e2e_review.get(field), list):
                    add(findings, "FAIL", "invalid_e2e_review_field", f"e2e_review requires list field {field}")
            if e2e_status_block and isinstance(e2e_status_block, dict):
                status_artifact = e2e_status_block.get("status_artifact")
                review_status_artifact = e2e_review.get("e2e_status_artifact")
                if status_artifact and review_status_artifact and status_artifact != review_status_artifact:
                    add(findings, "FAIL", "e2e_status_artifact_mismatch", "e2e_status.status_artifact and e2e_review.e2e_status_artifact differ")
            if e2e_verdict == "HOLD":
                if not e2e_review.get("blocking_gaps"):
                    add(findings, "FAIL", "missing_e2e_blocking_gaps", "e2e_review HOLD requires blocking_gaps")
                if not open_findings:
                    add(findings, "FAIL", "e2e_hold_without_open_finding", "e2e_review HOLD requires at least one open finding")
            if e2e_verdict == "PASS" and e2e_review.get("blocking_gaps"):
                add(findings, "FAIL", "pass_with_e2e_blocking_gaps", "e2e_review PASS cannot include blocking_gaps")
    for item in findings_list:
        if not isinstance(item, dict):
            continue
        fid = item.get("id", "<finding>")
        for field in ("id", "severity", "category", "summary", "status"):
            if not item.get(field):
                add(findings, "FAIL", "invalid_finding", f"{fid} missing {field}")
        if item.get("severity") == "high" and item.get("status") == "open":
            add(findings, "FAIL", "unresolved_high_finding", f"{fid} is high and still open")
        for ref in item.get("traces_to") or []:
            if upstream_ids and ref not in upstream_ids:
                add(findings, "FAIL", "broken_finding_reference", f"{fid} traces_to unknown ID: {ref}")


def check_memory_update(contract: dict[str, Any], findings: list[Finding]) -> None:
    decisions = contract.get("decisions") or []
    if not decisions:
        add(findings, "FAIL", "missing_memory_decisions", "memory_update_contract requires decisions")
    sources = {"quality-control", "bug-fix", "retrospective"}
    targets = {"project-context", "project-knowledge", "review-checklist", "test-template", "runtime-asset"}
    change_types = {"applied", "proposed", "deferred"}
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        did = decision.get("id", "<memory-decision>")
        if decision.get("source") not in sources:
            add(findings, "FAIL", "invalid_memory_source", f"{did} has invalid source")
        if decision.get("target") not in targets:
            add(findings, "FAIL", "invalid_memory_target", f"{did} has invalid target")
        if decision.get("change_type") not in change_types:
            add(findings, "FAIL", "invalid_memory_change_type", f"{did} has invalid change_type")
        if decision.get("change_type") == "applied" and not decision.get("target_ref"):
            add(findings, "FAIL", "memory_target_ref_missing", f"{did} applied decision lacks target_ref")
        if decision.get("change_type") in {"proposed", "deferred"} and not decision.get("reason"):
            add(findings, "FAIL", "memory_reason_missing", f"{did} {decision.get('change_type')} decision lacks reason")


def work_graph_config(root: Path) -> dict[str, Any]:
    config = load_yaml_file(root / "harness-runtime/config/harness.yaml")
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    return work_graph


def current_mission_slice(root: Path, mission_id: str) -> dict[str, Any]:
    if not mission_id or contains_placeholder(mission_id):
        return {}
    candidates = [
        root / "harness-runtime" / "harness" / "work-graph" / "mission-slices" / f"{mission_id}.yaml",
        root / "harness" / "work-graph" / "mission-slices" / f"{mission_id}.yaml",
    ]
    for path in candidates:
        payload = load_yaml_file(path)
        if payload:
            return payload
    return {}


def load_work_graph_nodes(root: Path) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    candidates = [
        root / "harness-runtime" / "harness" / "work-graph" / "nodes",
        root / "harness" / "work-graph" / "nodes",
    ]
    for nodes_root in candidates:
        if not nodes_root.exists():
            continue
        for path in sorted(nodes_root.rglob("*.yaml")):
            node = load_yaml_file(path)
            node_id = str(node.get("id") or "")
            if node_id:
                nodes[node_id] = node
    return nodes


def has_gate_decision(contract: dict[str, Any]) -> bool:
    if contract.get("gate_decisions"):
        return True
    for decision in contract.get("decisions") or []:
        if isinstance(decision, dict) and decision.get("type") == "decision_gate":
            return True
    return False


def format_lane_value(value: Any, mission_id: str) -> Any:
    if isinstance(value, str):
        return value.replace("{mission_id}", mission_id)
    if isinstance(value, list):
        return [format_lane_value(item, mission_id) for item in value]
    return value


def normalize_runtime_artifact_ref(value: Any) -> Any:
    """Compare legacy workspace-relative and current runtime-relative artifact refs."""
    if isinstance(value, str):
        for prefix in ("harness-runtime/harness/", "./harness-runtime/harness/"):
            if value.startswith(prefix):
                return "harness" + "/" + value[len(prefix) :]
    if isinstance(value, list):
        return [normalize_runtime_artifact_ref(item) for item in value]
    return value


def relative_path_exists(root: Path, value: str) -> bool:
    path = Path(value)
    if path.is_absolute():
        return path.exists()
    return (root / path).exists()


def task_requires_spec_evidence(node: dict[str, Any], lane_action: dict[str, Any], mission_slice: dict[str, Any]) -> bool:
    if node.get("kind") != "task":
        return False
    stage = str((lane_action or {}).get("stage") or "")
    to_lane = str(mission_slice.get("to_lane") or (lane_action or {}).get("to_lane") or "")
    return stage in {"execute", "code-review", "verify", "delivery"} or to_lane in {"review", "verification", "delivery", "done"}


def check_task_spec_consumes(node_id: str, node: dict[str, Any], lane_action: dict[str, Any], mission_slice: dict[str, Any], findings: list[Finding], root: Path, allow_placeholders: bool) -> None:
    if not task_requires_spec_evidence(node, lane_action, mission_slice):
        return
    specs = node.get("specs") if isinstance(node.get("specs"), dict) else {}
    consumes = specs.get("consumes") if isinstance(specs.get("consumes"), list) else []
    if not consumes:
        add(findings, "FAIL", "task_spec_consumes_missing", f"{node_id} is a TASK completion slice and must declare specs.consumes")
        return
    for index, item in enumerate(consumes, start=1):
        if not isinstance(item, dict):
            add(findings, "FAIL", "invalid_task_spec_consumes", f"{node_id} specs.consumes[{index}] must be an object")
            continue
        missing = [field for field in ("path", "requirement", "scenario") if not item.get(field)]
        if missing:
            add(findings, "FAIL", "invalid_task_spec_consumes", f"{node_id} specs.consumes[{index}] missing {', '.join(missing)}")
            continue
        spec_path = str(item.get("path") or "")
        if not allow_placeholders and not contains_placeholder(spec_path) and not relative_path_exists(root, spec_path):
            add(findings, "FAIL", "task_spec_consumes_missing_path", f"{node_id} specs.consumes[{index}].path does not exist: {spec_path}")
        evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        implementation_refs = [str(ref) for ref in evidence.get("implementation_refs") or [] if str(ref)]
        test_refs = [str(ref) for ref in evidence.get("test_refs") or [] if str(ref)]
        if not implementation_refs or not test_refs:
            add(findings, "FAIL", "task_spec_evidence_missing", f"{node_id} specs.consumes[{index}] must include evidence.implementation_refs and evidence.test_refs")


def lane_allowed_operations(action: dict[str, Any]) -> list[str]:
    return wg_lane_allowed_operations(action)


def check_operation_tree_allowed(operation_payload: dict[str, Any], allowed: list[str], findings: list[Finding], path: str = "graph_operation") -> None:
    operation_type = str(operation_payload.get("type") or "")
    if not operation_type:
        add(findings, "FAIL", "missing_graph_operation_type", f"{path} missing type")
        return
    if allowed and operation_type not in allowed:
        add(findings, "FAIL", "mission_slice_operation_not_allowed", f"{path}.type {operation_type} is not allowed by lane action allowed operations")
        return
    if operation_type != "batch":
        return
    operations = operation_payload.get("operations")
    if not isinstance(operations, list) or not operations:
        add(findings, "FAIL", "invalid_batch_operation", f"{path}.operations must be a non-empty list")
        return
    for index, child in enumerate(operations, start=1):
        if not isinstance(child, dict):
            add(findings, "FAIL", "invalid_batch_operation", f"{path}.operations[{index}] must be an object")
            continue
        check_operation_tree_allowed(child, allowed, findings, f"{path}.operations[{index}]")


def check_lane_operation_allowed(expected_action: dict[str, Any], lane_action: dict[str, Any], mission_slice: dict[str, Any], findings: list[Finding], lane: str, stage: str) -> None:
    operation = str(mission_slice.get("operation") or "")
    if not operation:
        return
    expected_allowed = lane_allowed_operations(expected_action)
    actual_allowed = lane_allowed_operations(lane_action)
    if expected_allowed:
        if operation not in expected_allowed:
            add(findings, "FAIL", "mission_slice_operation_not_allowed", f"Mission Slice operation {operation} is not allowed by work_graph.lanes.{lane}/{stage}.operation_profiles")
        if actual_allowed and actual_allowed != expected_allowed:
            add(findings, "FAIL", "mission_slice_lane_action_mismatch", f"Mission Slice lane_action.allowed_graph_operations {actual_allowed!r} does not match operations derived from work_graph.lanes.{lane}/{stage}.operation_profiles {expected_allowed!r}")
        graph_operation = mission_slice.get("graph_operation")
        if isinstance(graph_operation, dict):
            check_operation_tree_allowed(graph_operation, expected_allowed, findings)
            wg_validate_operation_against_profile(graph_operation, expected_action, findings)
            payload_type = str(graph_operation.get("type") or "")
            if payload_type and payload_type != operation:
                add(findings, "FAIL", "graph_operation_type_mismatch", f"graph_operation.type {payload_type} does not match Mission Slice operation {operation}")
        elif operation in {"split_node", "merge_nodes", "supersede_node", "batch"}:
            add(findings, "FAIL", "missing_graph_operation_payload", f"Mission Slice operation {operation} requires graph_operation payload")
        return
    expected_operation = str(expected_action.get("graph_operation") or "")
    if expected_operation and operation != expected_operation:
        add(findings, "FAIL", "mission_slice_operation_mismatch", f"Mission Slice operation {operation} does not match work_graph.lanes.{lane}/{stage}.graph_operation {expected_operation}")
    graph_operation = mission_slice.get("graph_operation")
    if isinstance(graph_operation, dict):
        wg_validate_operation_against_profile(graph_operation, expected_action, findings)
        payload_type = str(graph_operation.get("type") or "")
        if payload_type and payload_type != operation:
            add(findings, "FAIL", "graph_operation_type_mismatch", f"graph_operation.type {payload_type} does not match Mission Slice operation {operation}")


def lane_actions_are_equivalent_for_role_policy(
    registry: dict[str, Any],
    declared_lane: str,
    current_lane: str,
    mission_id: str,
) -> bool:
    """Allow a stage artifact contract to be reused across equivalent lane actions.

    Some stages promote the same reviewed artifact through adjacent lanes. For
    example, PRD creation can run on the `requirements` lane, then the accepted
    PRD artifact is used to advance the same node from `prd` to `solution`.
    The role policy still describes the action that produced the artifact, so
    the checker should only fail when the role/output contract differs.
    """
    if not declared_lane or not current_lane or declared_lane == current_lane:
        return True
    declared = registry.get(declared_lane)
    current = registry.get(current_lane)
    if not isinstance(declared, dict) or not isinstance(current, dict):
        return False

    scalar_fields = ("stage", "graph_operation")
    for field in scalar_fields:
        if declared.get(field) != current.get(field):
            return False

    declared_artifact = normalize_runtime_artifact_ref(format_lane_value(declared.get("output_artifact"), mission_id))
    current_artifact = normalize_runtime_artifact_ref(format_lane_value(current.get("output_artifact"), mission_id))
    if declared_artifact != current_artifact:
        return False

    list_fields = ("required_execution_roles", "required_review_roles")
    for field in list_fields:
        if list(declared.get(field) or []) != list(current.get(field) or []):
            return False
    return True


def check_work_graph_mission_slice(contract: dict[str, Any], findings: list[Finding], root: Path, allow_placeholders: bool) -> None:
    mission_id = str(contract.get("mission_id") or "")
    if contains_placeholder(mission_id):
        return
    work_graph = work_graph_config(root)
    contract_graph = contract.get("work_graph") if isinstance(contract.get("work_graph"), dict) else {}
    artifact = contract.get("work_graph_artifact") if isinstance(contract.get("work_graph_artifact"), dict) else {}
    role_policy = contract.get("role_policy") if isinstance(contract.get("role_policy"), dict) else {}
    has_work_graph_binding = bool(contract_graph or artifact or role_policy.get("work_graph_lane"))
    if not has_work_graph_binding:
        return
    mission_slice = current_mission_slice(root, mission_id)
    if not mission_slice:
        add(findings, "FAIL", "missing_mission_slice", f"No Mission Slice found for {mission_id}")
        return

    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    lane_action = mission_slice.get("lane_action") if isinstance(mission_slice.get("lane_action"), dict) else {}
    slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    slice_lane = str(control_plane.get("lane") or lane_action.get("lane") or mission_slice.get("from_lane") or control_plane.get("from_lane") or lane_action.get("from_lane") or "")
    slice_stage = str(control_plane.get("stage") or lane_action.get("stage") or "")
    primary_nodes = [str(item) for item in slice_graph.get("primary_nodes") or []] if isinstance(slice_graph.get("primary_nodes"), list) else []
    registry = wg_lane_action_registry_from_config({"work_graph": work_graph})

    if control_plane.get("stage") and contract.get("stage") != control_plane.get("stage"):
        add(findings, "FAIL", "mission_slice_stage_mismatch", f"contract.stage {contract.get('stage')} does not match Mission Slice stage {control_plane.get('stage')}")

    if role_policy.get("stage") and role_policy.get("stage") != slice_stage:
        add(findings, "FAIL", "mission_slice_stage_mismatch", f"role_policy.stage {role_policy.get('stage')} does not match Mission Slice stage {slice_stage}")
    if (
        role_policy.get("work_graph_lane")
        and role_policy.get("work_graph_lane") != slice_lane
        and not lane_actions_are_equivalent_for_role_policy(registry, str(role_policy.get("work_graph_lane") or ""), slice_lane, mission_id)
    ):
        add(findings, "FAIL", "mission_slice_lane_mismatch", f"role_policy.work_graph_lane {role_policy.get('work_graph_lane')} does not match Mission Slice lane {slice_lane}")

    _lane, _stage, expected_action = wg_lane_stage_for_node({"work_graph": work_graph}, {"id": "<mission-slice>", "lane": slice_lane, "stage": slice_stage})
    if not expected_action:
        add(findings, "FAIL", "missing_lane_stage_registry_entry", f"work_graph.lanes has no entry for Mission Slice {slice_lane}/{slice_stage}")
    else:
        comparisons = {
            "lane": slice_lane,
            "stage": expected_action.get("stage"),
            "graph_operation": expected_action.get("graph_operation"),
            "output_artifact": format_lane_value(expected_action.get("output_artifact"), mission_id),
            "carrier": expected_action.get("carrier"),
            "skill": expected_action.get("skill"),
            "required_execution_roles": expected_action.get("required_execution_roles") or [],
            "required_review_roles": expected_action.get("required_review_roles") or [],
        }
        for field, expected in comparisons.items():
            actual = lane_action.get(field)
            comparable_actual = normalize_runtime_artifact_ref(actual) if field == "output_artifact" else actual
            comparable_expected = normalize_runtime_artifact_ref(expected) if field == "output_artifact" else expected
            if comparable_actual != comparable_expected:
                add(findings, "FAIL", "mission_slice_lane_action_mismatch", f"Mission Slice lane_action.{field} {actual!r} does not match work_graph.lanes.{slice_lane}/{slice_stage}.{field} {expected!r}")
        check_lane_operation_allowed(expected_action, lane_action, mission_slice, findings, slice_lane, slice_stage)

    if contract_graph.get("primary_nodes") and contract_graph.get("primary_nodes") != primary_nodes:
        add(findings, "FAIL", "mission_slice_primary_node_mismatch", "contract.work_graph.primary_nodes does not match Mission Slice primary_nodes")

    if artifact and primary_nodes and artifact.get("node_id") not in primary_nodes:
        add(findings, "FAIL", "mission_slice_artifact_node_mismatch", f"work_graph_artifact.node_id {artifact.get('node_id')} is not the Mission Slice primary node")

    output_artifact = lane_action.get("output_artifact")
    produced = []
    for result in all_execution_results(contract):
        produced.extend(result.get("produced_artifacts") or [])
    produced_paths = [item.get("path") for item in produced if isinstance(item, dict)]
    normalized_output_artifact = normalize_runtime_artifact_ref(output_artifact)
    normalized_produced_paths = [normalize_runtime_artifact_ref(path) for path in produced_paths]
    if output_artifact and not allow_placeholders and normalized_output_artifact not in normalized_produced_paths:
        add(findings, "FAIL", "mission_slice_output_artifact_missing", f"execution_result(s).produced_artifacts must include lane_action.output_artifact {output_artifact}")

    nodes = load_work_graph_nodes(root)
    for node_id in primary_nodes:
        node = nodes.get(node_id)
        if not node:
            continue
        relations = node.get("relations") if isinstance(node.get("relations"), dict) else {}
        conflicts = relations.get("conflicts_with") if isinstance(relations.get("conflicts_with"), list) else []
        duplicates = relations.get("duplicates") if isinstance(relations.get("duplicates"), list) else []
        supersedes = relations.get("supersedes") if isinstance(relations.get("supersedes"), list) else []
        if conflicts and not has_gate_decision(contract):
            add(findings, "FAIL", "work_graph_conflict_requires_decision", f"{node_id} conflicts_with requires a Decision Gate record")
        if duplicates and not has_gate_decision(contract):
            add(findings, "FAIL", "work_graph_duplicate_requires_resolution", f"{node_id} duplicates requires a resolution decision")
        if supersedes and not (artifact or has_gate_decision(contract)):
            add(findings, "FAIL", "work_graph_supersede_requires_trace", f"{node_id} supersedes requires artifact trace or Decision Gate record")
        check_task_spec_consumes(node_id, node, lane_action, mission_slice, findings, root, allow_placeholders)


def check_work_graph_accepted_upstreams(contract: dict[str, Any], findings: list[Finding], root: Path) -> None:
    nodes = load_work_graph_nodes(root)
    for upstream in contract.get("upstream") or []:
        if not isinstance(upstream, dict) or not upstream.get("path"):
            continue
        path_text = str(upstream.get("path") or "")
        prefix = "harness-runtime/harness/work-graph/artifacts/"
        if not path_text.startswith(prefix):
            continue
        parts = Path(path_text).parts
        try:
            node_id = parts[parts.index("artifacts") + 1]
        except (ValueError, IndexError):
            add(findings, "FAIL", "invalid_work_graph_artifact_upstream", f"Cannot resolve artifact node from upstream path: {path_text}")
            continue
        node = nodes.get(node_id)
        if not node:
            add(findings, "FAIL", "missing_work_graph_artifact_node", f"Upstream artifact node not found: {node_id}")
            continue
        artifact = node.get("artifact") if isinstance(node.get("artifact"), dict) else {}
        state = artifact.get("artifact_state") if isinstance(artifact.get("artifact_state"), dict) else {}
        if state.get("status") != "accepted":
            add(findings, "FAIL", "work_graph_upstream_not_accepted", f"{path_text} is not accepted; artifact_state.status={state.get('status')}")
        canonical = str(artifact.get("canonical_artifact") or "")
        if canonical and canonical != path_text:
            add(findings, "FAIL", "work_graph_upstream_not_current", f"{path_text} is not current canonical artifact for {node_id}")


def check_work_graph_artifact(contract: dict[str, Any], findings: list[Finding], root: Path) -> None:
    if contract.get("type") != "guide_contract":
        return
    if contract.get("subtype") not in {"solution_guide", "technical_guide", "interaction_guide"}:
        return
    artifact = contract.get("work_graph_artifact")
    if not isinstance(artifact, dict):
        add(findings, "FAIL", "missing_work_graph_artifact", "guide contract must declare work_graph_artifact")
        return
    for field in ("node_id", "artifact_version", "promoted_by_mission", "source_stage_artifact", "canonical_artifact"):
        if not artifact.get(field):
            add(findings, "FAIL", "invalid_work_graph_artifact", f"work_graph_artifact missing {field}")
    if any(item.level == "FAIL" and item.code in {"missing_work_graph_artifact", "invalid_work_graph_artifact"} for item in findings):
        return
    expected_file_by_subtype = {
        "solution_guide": "solution.md",
        "technical_guide": "tech-design.md",
        "interaction_guide": "interaction.md",
    }
    expected_file = expected_file_by_subtype[str(contract.get("subtype"))]
    node_id = str(artifact.get("node_id") or "")
    mission_id = str(contract.get("mission_id") or "")
    expected_source = f"harness-runtime/harness/stages/{mission_id}/{expected_file}"
    expected_canonical = f"harness-runtime/harness/work-graph/artifacts/{node_id}/{expected_file}"
    source_stage_artifact = str(artifact.get("source_stage_artifact") or "")
    canonical_artifact = str(artifact.get("canonical_artifact") or "")
    for field, value in (("source_stage_artifact", source_stage_artifact), ("canonical_artifact", canonical_artifact)):
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            add(findings, "FAIL", "work_graph_artifact_path_escape", f"work_graph_artifact.{field} must be a relative in-harness path")
    if source_stage_artifact != expected_source:
        add(findings, "FAIL", "work_graph_artifact_path_mismatch", f"source_stage_artifact must be {expected_source}")
    if canonical_artifact != expected_canonical:
        add(findings, "FAIL", "work_graph_artifact_path_mismatch", f"canonical_artifact must be {expected_canonical}")
    if artifact.get("promoted_by_mission") != contract.get("mission_id"):
        add(findings, "FAIL", "work_graph_artifact_mission_mismatch", "work_graph_artifact.promoted_by_mission must match mission_id")
    state = artifact.get("artifact_state") if isinstance(artifact.get("artifact_state"), dict) else {}
    if state and state.get("status") not in {"draft", "review", "accepted", "superseded", "archived"}:
        add(findings, "FAIL", "invalid_work_graph_artifact_state", "work_graph_artifact.artifact_state.status is invalid")
    changelog = root / str(Path(canonical_artifact).parent / "changelog.md")
    if not contains_placeholder(canonical_artifact) and changelog.exists() and artifact.get("artifact_version"):
        if str(artifact["artifact_version"]) not in changelog.read_text(encoding="utf-8"):
            add(findings, "FAIL", "work_graph_changelog_missing_version", f"changelog.md does not mention {artifact['artifact_version']}")
    for verdict in all_role_verdicts(contract):
        if verdict.get("verdict") not in {"PASS", "PASS_WITH_RISK"}:
            continue
        basis = verdict.get("review_basis") if isinstance(verdict.get("review_basis"), dict) else {}
        reviewed_artifact = basis.get("work_graph_artifact") if isinstance(basis.get("work_graph_artifact"), dict) else {}
        if not reviewed_artifact:
            add(findings, "FAIL", "role_verdict_missing_artifact_version", f"{verdict.get('id', '<role-verdict>')} must bind review_basis.work_graph_artifact")
            continue
        for field in ("node_id", "artifact_version"):
            if reviewed_artifact.get(field) != artifact.get(field):
                add(findings, "FAIL", "role_verdict_artifact_version_mismatch", f"{verdict.get('id', '<role-verdict>')} review_basis.work_graph_artifact.{field} does not match work_graph_artifact")


def run(args: argparse.Namespace) -> tuple[str, list[Finding], dict[str, Any] | None]:
    artifact = Path(args.artifact)
    root = Path(args.root)
    findings: list[Finding] = []
    if not artifact.exists():
        add(findings, "FAIL", "missing_artifact", f"Artifact not found: {artifact}")
        return "FAIL", findings, None

    contract_artifact, contract = resolve_contract_artifact(root, artifact, findings)
    if contract is None:
        if not any(f.code.startswith("missing_contract") for f in findings):
            add(findings, "FAIL", "invalid_contract_yaml", f"Control Contract YAML is missing `control_contract`: {contract_artifact}")
        return "FAIL" if any(f.level == "FAIL" for f in findings) else "WARN", findings, None

    check_common(contract, findings)
    check_contract_hygiene(contract, findings, args.allow_placeholders)
    check_role_policy_block(contract, findings)
    check_execution_result(contract, findings, root, args.allow_placeholders)
    check_execute_implementation_contract(contract, findings, Path(args.root))
    check_role_verdicts(contract, findings)
    check_effectiveness_review_rounds(contract, findings, root)
    if not args.allow_placeholders:
        check_declared_role_policy_coverage(contract, findings)
        check_obligation_role_coverage(contract, findings)
    check_work_graph_mission_slice(contract, findings, Path(args.root), args.allow_placeholders)
    check_work_graph_accepted_upstreams(contract, findings, Path(args.root))
    check_work_graph_artifact(contract, findings, Path(args.root))
    validate_schema(contract, findings)
    if not args.allow_placeholders:
        for field in ("mission_id", "stage"):
            if has_placeholder(contract.get(field)):
                add(findings, "FAIL", "placeholder_in_runtime_artifact", f"{field} still contains a template placeholder")

    upstream_ids: set[str] = set()
    # 偏离修正3: structured set for agent_architecture components — populated
    # whenever an upstream YAML contract supplies agent_architecture[] entries
    # (typically solution.contract.yaml).
    upstream_agent_arch_components: set[str] = set()
    # Stage-4 M4.3: agent_engineering.scope from mission-contract.contract.yaml
    # gates strict eval_scenarios completeness check. Last write wins when
    # multiple upstreams declare scope (mission-contract is canonical).
    upstream_agent_engineering_scope: str | None = None
    for upstream in args.upstream or []:
        upstream_path = Path(upstream)
        upstream_ids.update(ids_from_markdown(upstream_path))
        if upstream_path.suffix in {".yaml", ".yml"}:
            upstream_agent_arch_components.update(
                agent_architecture_components_from_yaml(upstream_path)
            )
            scope = agent_engineering_scope_from_yaml(upstream_path)
            if scope is not None:
                upstream_agent_engineering_scope = scope
    for upstream in contract.get("upstream") or []:
        if isinstance(upstream, dict) and upstream.get("path"):
            upstream_path = Path(args.root) / upstream["path"]
            path_text = upstream["path"]
            if contains_placeholder(path_text) and not args.allow_placeholders:
                add(findings, "FAIL", "placeholder_in_runtime_artifact", f"upstream path contains placeholder: {path_text}")
            elif not upstream_path.exists() and not contains_placeholder(path_text):
                add(findings, "FAIL", "missing_upstream", f"Upstream artifact not found: {path_text}")
            upstream_ids.update(ids_from_markdown(upstream_path))
            if upstream_path.suffix in {".yaml", ".yml"}:
                upstream_agent_arch_components.update(
                    agent_architecture_components_from_yaml(upstream_path)
                )
                scope = agent_engineering_scope_from_yaml(upstream_path)
                if scope is not None:
                    upstream_agent_engineering_scope = scope

    ctype = contract.get("type")
    subtype = contract.get("subtype")
    if ctype == "intent_contract":
        check_intent(contract, findings)
    elif ctype == "behaviour_contract":
        if subtype == "discovery_brief":
            # discovery-brief has its own structural rules (no FRs / capabilities
            # in the prd sense). Skip the prd-flavored check_behaviour /
            # check_behaviour_prd and run the discovery-specific rule set instead.
            check_behaviour_discovery_brief(contract, findings, Path(args.root))
        else:
            check_behaviour(contract, findings, upstream_ids)
            if contract.get("stage") == "prd":
                check_behaviour_prd(contract, findings, Path(args.root))
    elif ctype == "action_contract":
        check_action(contract, findings, upstream_ids, Path(args.root), args.allow_placeholders)
    elif ctype == "guide_contract" and subtype == "solution_guide":
        check_solution_guide(contract, findings, upstream_ids)
    elif ctype == "guide_contract" and subtype == "technical_guide":
        check_technical_guide(
            contract,
            findings,
            upstream_ids,
            upstream_agent_arch_components,
            upstream_agent_engineering_scope,
        )
    elif ctype == "evidence_contract" and subtype == "verification_evidence":
        check_verification(contract, findings, upstream_ids)
    elif ctype == "evidence_contract" and subtype == "review_evidence":
        check_review_evidence(contract, findings, upstream_ids, Path(args.root), args.allow_placeholders)
    elif ctype == "evidence_contract":
        add(findings, "WARN", "unsupported_evidence_subtype", f"Evidence subtype not checked in v1: {subtype}")
    elif ctype == "memory_update_contract":
        check_memory_update(contract, findings)
    elif ctype not in {"guide_contract", "memory_update_contract"}:
        add(findings, "FAIL", "unknown_contract_type", f"Unknown contract type: {ctype}")

    if not findings:
        add(findings, "PASS", "contract_valid", "Control Contract integrity checks passed")
    status = "FAIL" if any(f.level == "FAIL" for f in findings) else "WARN" if any(f.level == "WARN" for f in findings) else "PASS"
    return status, findings, contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, help="Stage artifact markdown file with Contract reference, or external contract YAML")
    parser.add_argument("--root", default=".", help="Workspace root used to resolve contract upstream paths")
    parser.add_argument("--upstream", action="append", default=[], help="Additional upstream markdown file")
    parser.add_argument("--allow-placeholders", action="store_true", help="Allow template placeholders in contract fields")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    status, findings, contract = run(args)
    payload = {
        "status": status,
        "artifact": args.artifact,
        "contract_type": contract.get("type") if contract else None,
        "findings": [finding.__dict__ for finding in findings],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Contract Check: {status}")
        print(f"Artifact: {args.artifact}")
        for finding in findings:
            print(f"[{finding.level}] {finding.code}: {finding.message}")
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
