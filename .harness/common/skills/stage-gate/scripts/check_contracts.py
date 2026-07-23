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


# 稳定 ID 前缀 SSOT：复用 harness_cli_core.domain.closure.KNOWN_ID_PREFIXES（与
# rules/stage-doc-standard.md 同源），避免本文件另维护一份会漂移的前缀清单。
# 历史教训：界面 SURF- / 页面态 PS- / 系统用例 SUC- 曾只进下游覆盖门与 closure 白名单，
# 却漏进本文件的 ID_PREFIXES，导致 upstream_ids 抽不到 interaction 契约里的 SURF/PS/SUC，
# 触发「覆盖门要求 decisions[].traces_to 写 SURF、broken_decision_reference 又判 SURF 未知」
# 的死锁。这里从 SSOT 取前缀并去掉尾部 '-' 归一，import 不可用时回退到本地基线。
_ID_SSOT_COMMON = Path(__file__).resolve().parents[3]
if str(_ID_SSOT_COMMON) not in sys.path:
    sys.path.insert(0, str(_ID_SSOT_COMMON))
try:
    from harness_cli_core.domain.closure import KNOWN_ID_PREFIXES as _SSOT_ID_PREFIXES  # noqa: E402
    _SSOT_PREFIXES = tuple(p.rstrip("-") for p in _SSOT_ID_PREFIXES if str(p).strip())
except Exception:  # noqa: BLE001 — 渲染副本缺包时回退，至少保证 SURF/PS/SUC 被识别
    _SSOT_PREFIXES = ("SURF", "PS", "SUC", "UC", "CLAR")


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
    "US",
    "SC",
    "REQ",
    "CAP",
    "QRC",
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
# 并入稳定 ID 前缀 SSOT（closure.KNOWN_ID_PREFIXES），去重保序——把 SURF / PS / SUC /
# UC / CLAR 等纳入 ID_PATTERN，使 interaction 契约里的界面边界 / 页面态 / 系统用例 ID
# 经 ids_from_markdown 进入 upstream_ids 许可集，消除 SURF 覆盖门与 broken 门的死锁。
ID_PREFIXES = tuple(dict.fromkeys((*ID_PREFIXES, *_SSOT_PREFIXES)))
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

# 下游原型覆盖率门：复用 domain SSOT（behavior_graph）。优先正常 import；该脚本
# 位于 .harness/common/skills/stage-gate/scripts/，parents[3] = package/common，
# 把它挂到 sys.path 即可解析 harness_cli_core。import 不可用时整门静默跳过
# （零 finding），绝不因缺包让现有契约误 FAIL。
_HARNESS_CLI_COMMON = Path(__file__).resolve().parents[3]
if str(_HARNESS_CLI_COMMON) not in sys.path:
    sys.path.insert(0, str(_HARNESS_CLI_COMMON))
try:
    from harness_cli_core.domain import behavior_graph as _bg  # noqa: E402
except Exception:  # noqa: BLE001 — 缺包 / 渲染副本缺失时整门跳过，不影响既有校验
    _bg = None
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
    return contract if isinstance(contract, dict) else parsed


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
    if contract.get("version") not in (1, 2):
        add(findings, "FAIL", "unsupported_version", "Control Contract version must be 1 or 2")
    if contract.get("status") == "blocked":
        add(findings, "FAIL", "blocked_contract", "Control Contract status is blocked")
    if contract.get("status") not in {"draft", "ready", "blocked"}:
        add(findings, "FAIL", "invalid_status", "Control Contract status must be draft, ready, or blocked")
    if "upstream" in contract and not isinstance(contract.get("upstream"), list):
        add(findings, "FAIL", "invalid_upstream", "upstream must be a list")
    if "consumers" in contract and not isinstance(contract.get("consumers"), list):
        add(findings, "FAIL", "invalid_consumers", "consumers must be a list")


LEGACY_FINISHING_BRANCH_REQUIRED_FIELDS = (
    "stage",
    "mission_id",
    "branch_status",
    "release_readiness",
    "test_evidence",
    "close_choice",
    "git_ops",
    "pr_body",
    "mission_close",
    "effectiveness_review",
)


def is_legacy_finishing_branch_contract(contract: dict[str, Any]) -> bool:
    return contract.get("stage") == "finishing-branch" and "control_contract" not in contract


def check_legacy_finishing_branch_contract(contract: dict[str, Any], findings: list[Finding]) -> None:
    for field in LEGACY_FINISHING_BRANCH_REQUIRED_FIELDS:
        if field not in contract:
            add(findings, "FAIL", "missing_field", f"finishing-branch contract missing required field: {field}")

    if contract.get("mission_id") in (None, ""):
        add(findings, "FAIL", "missing_mission_id", "finishing-branch contract requires mission_id")

    test_evidence = contract.get("test_evidence") if isinstance(contract.get("test_evidence"), dict) else {}
    if test_evidence.get("exit_code") != 0:
        add(findings, "FAIL", "tests_not_passing", "finishing-branch test_evidence.exit_code must be 0")

    close_choice = contract.get("close_choice") if isinstance(contract.get("close_choice"), dict) else {}
    if close_choice.get("strategy") in (None, "", "pending_user_choice"):
        add(findings, "FAIL", "close_choice_pending", "finishing-branch close_choice.strategy must be finalized")

    git_ops = contract.get("git_ops")
    if not isinstance(git_ops, list) or not git_ops:
        add(findings, "FAIL", "missing_git_ops", "finishing-branch contract requires git_ops")
    elif not any(isinstance(op, dict) and op.get("executed") is True and op.get("exit_code") == 0 for op in git_ops):
        add(findings, "FAIL", "git_ops_not_executed", "finishing-branch git_ops must include a successful executed operation")

    mission_close = contract.get("mission_close") if isinstance(contract.get("mission_close"), dict) else {}
    if mission_close.get("close_strategy") in (None, "", "pending_user_choice"):
        add(findings, "FAIL", "mission_close_pending", "finishing-branch mission_close.close_strategy must be finalized")

    if has_placeholder(contract):
        add(findings, "FAIL", "placeholder_in_runtime_artifact", "finishing-branch contract still contains a template placeholder")


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
    reviewer_obligations = {
        str(item.get("id")): [
            str(role)
            for role in item.get("required_roles") or []
            if _is_reviewer_role(role)
        ]
        for item in graph_obligation_items(contract)
        if item.get("id") and any(_is_reviewer_role(role) for role in item.get("required_roles") or [])
    }
    for oid in fulfilled:
        reviewer_roles = reviewer_obligations.get(str(oid)) or []
        has_reviewer_verdict = any(
            verdict.get("role") in reviewer_roles
            and verdict.get("verdict") in {"PASS", "PASS_WITH_RISK"}
            and oid in (verdict.get("reviewed_obligations") or [])
            for verdict in all_role_verdicts(contract)
        )
        if reviewer_roles and not has_reviewer_verdict:
            add(
                findings,
                "FAIL",
                "execution_result_cannot_fulfill_reviewer_obligation",
                f"{field_label} cannot fulfill reviewer-owned obligation: {oid}",
            )
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


def execute_batch_key(node: dict[str, Any]) -> tuple[str, str]:
    batch_id = str(node.get("execution_batch_id") or "").strip()
    if batch_id:
        return "execution_batch_id", batch_id
    brief = str(node.get("execution_brief_artifact") or "").strip()
    if brief:
        return "execution_brief_artifact", brief
    return "", ""


def check_execute_batch_sibling_coverage(contract: dict[str, Any], root: Path | None, findings: list[Finding]) -> None:
    if root is None:
        return
    mission_id = str(contract.get("mission_id") or "")
    mission_slice = current_mission_slice(root, mission_id)
    slice_graph = mission_slice.get("work_graph") if isinstance(mission_slice.get("work_graph"), dict) else {}
    primary_nodes = [str(item) for item in slice_graph.get("primary_nodes") or []] if isinstance(slice_graph.get("primary_nodes"), list) else []
    if not primary_nodes:
        return
    control_plane = mission_slice.get("control_plane") if isinstance(mission_slice.get("control_plane"), dict) else {}
    slice_lane = str(control_plane.get("lane") or "")
    slice_stage = str(control_plane.get("stage") or "")
    if slice_stage != "execute":
        return
    nodes = load_work_graph_nodes(root)
    work_graph = work_graph_config(root)
    primary_set = set(primary_nodes)
    primary_keys = {execute_batch_key(nodes.get(node_id) or {}) for node_id in primary_nodes}
    primary_keys = {key for key in primary_keys if key != ("", "")}
    if not primary_keys:
        return
    for node_id, node in sorted(nodes.items()):
        if node_id in primary_set:
            continue
        if execute_batch_key(node) not in primary_keys:
            continue
        node_lane, node_stage, _action = wg_lane_stage_for_node({"work_graph": work_graph}, node)
        if node_lane != slice_lane or node_stage != slice_stage:
            continue
        if str(node.get("status") or "") not in {"ready", "active"}:
            continue
        add(
            findings,
            "FAIL",
            "mission_slice_missing_execution_batch_sibling",
            f"Execute Mission Slice omits sibling TASK node {node_id} from the same execution batch",
        )


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
    check_execute_batch_sibling_coverage(contract, root, findings)
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
                f"dispatch plan {index} execution_unit_id must be exactly one Atomic Task id from the current Mission Slice primary TASK nodes, got {unit!r}",
            )
            continue
        seen_units.append(unit)
        if unit not in expected_atomic_ids:
            add(findings, "FAIL", "unknown_execute_atomic_dispatch_unit", f"dispatch plan {index} references Atomic Task {unit!r} not bound to the current Mission Slice primary TASK nodes")
    seen_set = set(seen_units)
    for atomic_id in sorted(expected_atomic_ids - seen_set):
        add(findings, "FAIL", "missing_execute_atomic_dispatch_plan", f"current Mission Slice batch Atomic Task {atomic_id} has no dedicated execute dispatch plan")
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


def _review_basis_values(value: Any) -> set[str]:
    values: set[str] = set()
    if isinstance(value, str):
        values.add(value)
    elif isinstance(value, list):
        for item in value:
            values.update(_review_basis_values(item))
    elif isinstance(value, dict):
        for item in value.values():
            values.update(_review_basis_values(item))
    return values


def _basis_matches_artifact(root: Path, basis: Any, artifact: str) -> bool:
    expected = str(artifact)
    expected_path = Path(expected)
    expected_abs = expected_path if expected_path.is_absolute() else root / expected
    candidates = _review_basis_values(basis)
    for candidate in candidates:
        candidate_path = Path(candidate)
        candidate_abs = candidate_path if candidate_path.is_absolute() else root / candidate
        if candidate == expected or str(candidate_abs) == str(expected_abs):
            return True
    return False


def check_dependency_impact(contract: dict[str, Any], findings: list[Finding], root: Path) -> None:
    dependency = contract.get("dependency_impact")
    if not isinstance(dependency, dict) or not dependency.get("required"):
        return
    claims = dependency.get("claims")
    if not isinstance(claims, list) or not claims:
        add(findings, "FAIL", "invalid_dependency_impact_claim", "dependency_impact.required=true requires non-empty claims")
    for index, claim in enumerate(claims or []):
        if not isinstance(claim, dict):
            add(findings, "FAIL", "invalid_dependency_impact_claim", f"dependency_impact.claims[{index}] must be an object")
            continue
        missing = [
            field
            for field in ("id", "claim", "confidence", "source_evidence", "failure_mode", "validation_action")
            if not claim.get(field)
        ]
        if missing:
            add(
                findings,
                "FAIL",
                "invalid_dependency_impact_claim",
                f"dependency_impact.claims[{index}] missing fields: {missing}",
            )
    review_role = dependency.get("review_role")
    artifact = dependency.get("artifact")
    if not review_role or not artifact:
        add(findings, "FAIL", "missing_dependency_impact_review", "dependency_impact requires review_role and artifact")
        return
    has_review = any(
        verdict.get("role") == review_role
        and verdict.get("verdict") in {"PASS", "PASS_WITH_RISK"}
        and _basis_matches_artifact(root, verdict.get("review_basis"), str(artifact))
        for verdict in all_role_verdicts(contract)
    )
    if not has_review:
        add(
            findings,
            "FAIL",
            "missing_dependency_impact_review",
            f"dependency_impact artifact requires {review_role} verdict: {artifact}",
        )


_REVIEWER_ROLE_SUFFIXES = ("-reviewer", "-effectiveness-reviewer")

# 横切 gap category SSOT（开放枚举）。
# 权威定义在 harness_cli_core.domain.contracts.CROSSCUTTING_GAP_CATEGORIES；
# 该脚本位于 skills/ 下，跨包 import domain 路径脆弱，故在此保留一份镜像。
# 修改时两处必须同步。这里只用于横切 category 的最小 WARN 校验，
# 阶段特有 / 未知 category 一律放行。
_CROSSCUTTING_GAP_CATEGORIES = {
    "reasoning_chain_open",
    "internal_contradiction",
    "needs_user_clarification",
}


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
        # 横切 category 最小校验（仅 WARN，加性、非破坏）：
        # 当某 blocking_gap 标注了横切 category，却缺少 detail/required_fix 这类
        # 必要描述时给 WARN，提醒补全可消费的修复信息；
        # 未知 / 阶段特有 category 一律放行，不报任何 finding。
        for gap in verdict.get("blocking_gaps") or []:
            if not isinstance(gap, dict):
                continue
            category = gap.get("category")
            if category not in _CROSSCUTTING_GAP_CATEGORIES:
                continue
            if not any(gap.get(field) for field in ("detail", "required_fix", "description", "message")):
                add(
                    findings,
                    "WARN",
                    "crosscutting_gap_missing_detail",
                    f"{vid} blocking_gap category={category!r} 缺少 detail/required_fix 描述，"
                    "横切类别应提供可消费的修复说明",
                )
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
    """严格审查不变量（core.md「严格审查不变量」）— 审查轮次只记录修复历史，
    永不构成放行阈值。任何已记录的开放（非通过）verdict（HOLD / BLOCKED）在 gate
    时都必须 carry 一条 approved `tradeoff` approval（用户在 Decision Gate 上显式
    拥有已披露的残留风险）才能放行；否则 BLOCKED。本判定与 rounds_used / max_rounds
    无关——`rounds_used` 仅供记录，达到任何轮次都不会自动放行或降级通过。
    """
    review = contract.get("effectiveness_review")
    if not isinstance(review, dict):
        return
    last_verdict = review.get("last_verdict", "")
    if not isinstance(last_verdict, str) or not last_verdict.strip():
        # 尚未记录 verdict（审查未跑 / 未记）——交由其它检查负责，本检查不发信号。
        return
    if last_verdict.upper() in {"PASS", "PASS_WITH_RISK"}:
        return

    mission_id = contract.get("mission_id")
    if not isinstance(mission_id, str) or not mission_id:
        # Without a mission_id we cannot locate the approvals.json scope —
        # warn rather than block.
        add(
            findings,
            "WARN",
            "open_verdict_unscoped",
            f"effectiveness_review.last_verdict={last_verdict!r} 非通过，但 mission_id 缺失，无法定位 approvals.json",
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
            "open_verdict_without_approval",
            f"effectiveness_review.last_verdict={last_verdict!r} 非通过；审查循环不得因轮次放行，"
            f"放行必须由用户在 Decision Gate 上显式拥有残留风险："
            f"`harness approval append --mission {mission_id} --type tradeoff --status approved`",
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

    scenarios = contract.get("acceptance_scenarios") or []
    if not scenarios:
        add(findings, "FAIL", "missing_acceptance_scenario", "intent_contract must declare acceptance_scenarios; see harness-runtime/templates/contracts/mission-contract.contract.yaml")
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            add(findings, "FAIL", "invalid_acceptance_scenario", "acceptance_scenarios entries must be objects (with id, statement, and either given/when/then or verification_method); see harness-runtime/templates/contracts/mission-contract.contract.yaml")
            continue
        scenario_id = scenario.get("id") or "<unknown>"
        for field in ("id", "statement"):
            if not scenario.get(field):
                add(findings, "FAIL", "missing_acceptance_scenario_field", f"Acceptance scenario {scenario_id} missing required field '{field}'")
        gwt_present = bool(scenario.get("given") and scenario.get("when") and scenario.get("then"))
        vm_present = bool(scenario.get("verification_method"))
        if not gwt_present and not vm_present:
            nested_gwt = scenario.get("gwt")
            if isinstance(nested_gwt, dict) and nested_gwt.get("given") and nested_gwt.get("when") and nested_gwt.get("then"):
                add(
                    findings,
                    "FAIL",
                    "unverifiable_acceptance_scenario",
                    f"{scenario_id} uses nested 'gwt:' block; given/when/then must be flat siblings of id/statement. Example in harness-runtime/templates/contracts/mission-contract.contract.yaml",
                )
            else:
                add(
                    findings,
                    "FAIL",
                    "unverifiable_acceptance_scenario",
                    f"{scenario_id} must declare either flat given/when/then OR a 'verification_method' string. Example in harness-runtime/templates/contracts/mission-contract.contract.yaml",
                )

    scope_out = ((contract.get("scope") or {}).get("out")) or []
    for entry in scope_out:
        if isinstance(entry, dict) and not entry.get("reason"):
            add(findings, "FAIL", "scope_out_reason_missing", f"{entry.get('id', '<scope-out>')} lacks reason")


def check_behaviour(contract: dict[str, Any], findings: list[Finding], upstream_ids: set[str]) -> None:
    covers_intent = contract.get("covers_intent") or []
    if isinstance(covers_intent, dict):
        covered_acceptance = covers_intent.get("acceptance_scenarios") or []
    else:
        covered_acceptance = covers_intent
    for acceptance_id in covered_acceptance:
        if upstream_ids and acceptance_id not in upstream_ids:
            add(findings, "FAIL", "broken_acceptance_reference", f"covers_intent references unknown acceptance scenario: {acceptance_id}")

    behavior_specs = contract.get("behavior_specs") or []
    quality_constraints = contract.get("quality_runtime_constraints") or []
    capabilities = contract.get("capabilities") or []
    if not behavior_specs and not capabilities:
        add(findings, "FAIL", "missing_behavior_specs", "behaviour_contract must declare behavior_specs or capabilities")
    for spec in behavior_specs:
        if isinstance(spec, dict) and not spec.get("id"):
            add(findings, "FAIL", "missing_behavior_spec_id", "Behavior spec missing id")
    for constraint in quality_constraints:
        if isinstance(constraint, dict) and not (constraint.get("id") and constraint.get("verification_method")):
            add(findings, "FAIL", "invalid_quality_constraint", "Quality/runtime constraint entries require id and verification_method")
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
    - W-graphify-source: brownfield missions (graphify-out/ present) must have
      at least one graphify_symbol or graphify_query entry in
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

    # --- W-graphify-source -----------------------------------------------
    # Brownfield = graphify-out/ directory present (mirrors the graphify status
    # CLI's brownfield heuristic). When brownfield, existing_solutions[] must
    # carry at least one graphify_* source.
    graphify_dir = root / "graphify-out"
    is_brownfield = graphify_dir.exists() and graphify_dir.is_dir() and any(graphify_dir.iterdir())
    if is_brownfield:
        existing = contract.get("existing_solutions") or []
        has_graphify = any(
            isinstance(item, dict) and str(item.get("source", "")).startswith("graphify")
            for item in existing
        )
        # Allow brownfield to opt out by recording a graphify degradation.
        degradations = contract.get("degradations") or []
        has_graphify_degradation = any(
            isinstance(item, dict) and str(item.get("kind", "")).startswith("graphify_")
            for item in degradations
        )
        if not has_graphify and not has_graphify_degradation:
            add(
                findings, "FAIL", "discovery_graphify_source_missing",
                "W-graphify-source: brownfield mission but existing_solutions[] has no "
                "graphify_symbol/graphify_query entry and degradations[] has no "
                "graphify_unavailable/graphify_stale entry. Either run graphify queries "
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

        # 严格审查不变量（core.md）：轮次只记录修复历史，永不构成放行阈值。
        # 任何已记录的非通过 verdict 都必须 carry 用户显式 tradeoff approval 才能放行，
        # 与 rounds_used / max_rounds 无关。
        last_verdict = eff.get("last_verdict")
        if isinstance(last_verdict, str) and last_verdict.strip() and last_verdict.upper() not in ("PASS", "PASS_WITH_RISK"):
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
                add(findings, "FAIL", "prd_open_verdict_without_approval",
                    f"effectiveness_review.last_verdict={last_verdict} 非通过；审查循环不得因轮次放行，"
                    "放行必须由用户在 Decision Gate 上显式拥有残留风险（tradeoff/prd_user_checkpoint approval）")

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

    # 下游原型覆盖率门（breakdown 阶段，卡 PS 级）。承载来源 = 各父/原子任务 tasks[].traces_to
    # 里出现的 PS- ref；分母 = mission-local 图的 page_state id 全集。非破坏（无图跳过）。
    if contract.get("stage") == "breakdown":
        _apply_prototype_coverage_gate(
            contract, findings, root, stage="breakdown", carried_sections=("tasks",),
        )


def check_verification(contract: dict[str, Any], findings: list[Finding], upstream_ids: set[str]) -> None:
    evidence_ids = {entry.get("id") for entry in contract.get("command_evidence") or [] if isinstance(entry, dict)}
    result_evidence_ids = {entry.get("id") for entry in contract.get("result_evidence") or [] if isinstance(entry, dict)}
    if not result_evidence_ids:
        add(findings, "FAIL", "missing_result_evidence", "verification_evidence requires result_evidence")
    acceptance_trace = contract.get("acceptance_trace") or []
    if not acceptance_trace:
        add(findings, "FAIL", "missing_acceptance_trace", "verification_evidence requires acceptance_trace")
    for row in acceptance_trace:
        if not isinstance(row, dict):
            continue
        acceptance_id = row.get("acceptance_id") or row.get("id") or "<unknown>"
        conclusion = row.get("conclusion")
        if upstream_ids and acceptance_id not in upstream_ids:
            add(findings, "FAIL", "broken_acceptance_trace", f"acceptance_trace references unknown acceptance scenario: {acceptance_id}")
        if conclusion == "pass":
            evidence = row.get("evidence") or []
            if not evidence:
                add(findings, "FAIL", "missing_pass_evidence", f"{acceptance_id} is pass but has no evidence")
            has_command = any(str(ev).startswith("CMD-") for ev in evidence)
            has_result = any(str(ev).startswith("EV-RESULT-") for ev in evidence)
            if not has_command:
                add(findings, "FAIL", "missing_command_evidence", f"{acceptance_id} is pass but has no command evidence")
            if not has_result:
                add(findings, "FAIL", "missing_result_evidence_reference", f"{acceptance_id} is pass but has no result evidence")
            for ev in evidence:
                if str(ev).startswith("CMD-") and ev not in evidence_ids:
                    add(findings, "FAIL", "broken_evidence_reference", f"{acceptance_id} references unknown command evidence: {ev}")
                if str(ev).startswith("EV-RESULT-") and ev not in result_evidence_ids:
                    add(findings, "FAIL", "broken_result_evidence_reference", f"{acceptance_id} references unknown result evidence: {ev}")
        elif conclusion == "blocked":
            for field in ("blocked_reason", "impact", "next_step"):
                if not row.get(field):
                    add(findings, "FAIL", "missing_blocked_detail", f"{acceptance_id} blocked lacks {field}")
        elif conclusion not in {"fail", "not_applicable"}:
            add(findings, "FAIL", "invalid_acceptance_conclusion", f"{acceptance_id} has invalid conclusion: {conclusion}")
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
        for field in ("acceptance_id", "expected", "actual", "reproduce", "artifact", "result"):
            if not evidence.get(field):
                add(findings, "FAIL", "invalid_result_evidence", f"{eid} lacks {field}")


# 下游契约里携带 SURF- / PS- trace 的字段段（traces_to 列表所在处）。SURF- 是覆盖率
# 分子的主载体；PS- 在 breakdown 阶段才卡（solution/tech 只卡 SURF）。
_PROTOTYPE_REF_RE = re.compile(r"\b(?:SURF|PS)-[A-Za-z0-9][A-Za-z0-9_-]*\b")


def _collect_carried_refs(contract: dict[str, Any], sections: tuple[str, ...]) -> set[str]:
    """从契约指定段的每条 ``traces_to`` 里抽出 SURF- / PS- ref 集合（覆盖率分子）。"""
    refs: set[str] = set()
    for section in sections:
        for entry in contract.get(section) or []:
            if not isinstance(entry, dict):
                continue
            for ref in entry.get("traces_to") or []:
                refs.update(_PROTOTYPE_REF_RE.findall(str(ref)))
    return refs


def _prototype_coverage_exemptions(contract: dict[str, Any]) -> dict[str, str]:
    """读契约可选字段 ``prototype_coverage_exemptions``（列表 of {id, reason}）→
    ``{id: reason}``。缺字段 / 形态不符 → 空 dict（无豁免）。"""
    out: dict[str, str] = {}
    for item in contract.get("prototype_coverage_exemptions") or []:
        if not isinstance(item, dict):
            continue
        eid = str(item.get("id") or "")
        if eid:
            out[eid] = str(item.get("reason") or "")
    return out


def _load_prototype_coverage_inputs(
    root: Path | None, mission: str | None,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """定位并加载 **mission-local** behavior-graph + 本 mission 的 surface catalog，
    返回 ``(mission_graph, surface_catalog)``。任一前置不满足（domain 不可用 / 无
    root / 无 mission / mission 没有 behavior-graph）→ 返回 None，调用方据此整门跳过。

    分母刻意只取 mission-local 图（不再 ``merge_graphs(project, mission)``）：下游
    solution / tech / breakdown 只对【本 mission 原型定义的】SURF / PS 负责，不该为
    项目历史沉淀（项目累积图）里的 surface / page_state 承载，否则会对历史 SURF / PS
    误报 SURFACE_NOT_CARRIED / PAGESTATE_NOT_COVERED。"""
    if _bg is None or root is None or not mission:
        return None
    _path, mission_graph = _bg.load_behavior_graph(root, mission)
    if not mission_graph:
        # 非 UI 任务 / 未跑 interaction：无 mission 行为图 → 整门跳过，零 finding。
        return None
    # surface catalog：优先 surface-model.md 机器表；补充 mission 图内联 surfaces。
    catalog = _bg.parse_surface_catalog(_bg.read_text_if_exists(_bg.surface_model_path(root, mission)))
    catalog = {**_bg.surfaces_from_graph(mission_graph), **catalog}
    return mission_graph, catalog


def _apply_prototype_coverage_gate(
    contract: dict[str, Any],
    findings: list[Finding],
    root: Path | None,
    stage: str,
    carried_sections: tuple[str, ...],
) -> None:
    """把 domain 的 ``downstream_prototype_coverage_findings`` 并入下游 gate。

    **非破坏铁律**：behavior-graph 不存在（非 UI / 未跑 interaction）→ 直接跳过，
    零 finding；只有 mission 真有行为图且下游真漏承载 surface / page_state 才 FAIL。
    """
    mission = contract.get("mission_id")
    loaded = _load_prototype_coverage_inputs(root, str(mission) if mission else None)
    if loaded is None:
        return
    merged_graph, surface_catalog = loaded
    carried_refs = _collect_carried_refs(contract, carried_sections)
    exemptions = _prototype_coverage_exemptions(contract)
    for f in _bg.downstream_prototype_coverage_findings(
        merged_graph=merged_graph,
        surface_catalog=surface_catalog,
        carried_refs=carried_refs,
        stage=stage,
        exemptions=exemptions,
    ):
        add(findings, str(f.get("level", "FAIL")), str(f.get("code", "")), str(f.get("message", "")))


def check_solution_guide(
    contract: dict[str, Any],
    findings: list[Finding],
    upstream_ids: set[str],
    root: Path | None = None,
) -> None:
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
    # 下游原型覆盖率门（solution 阶段，卡 SURF 级）。承载来源 = decisions[].traces_to。
    _apply_prototype_coverage_gate(
        contract, findings, root, stage="solution", carried_sections=("decisions",),
    )


_REQUIRED_EVAL_KINDS = frozenset({"normal", "boundary", "adversarial", "ambiguous"})


def check_technical_guide(
    contract: dict[str, Any],
    findings: list[Finding],
    upstream_ids: set[str],
    upstream_agent_architecture_components: set[str] | None = None,
    upstream_agent_engineering_scope: str | None = None,
    root: Path | None = None,
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
    # (Scenario / Rule / Decision) OR this contract's own modules[].id — a VS that
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
    # 下游原型覆盖率门（technical_analysis 阶段，卡 SURF 级）。承载来源 =
    # modules / interface_changes / data_changes 的 traces_to。
    _apply_prototype_coverage_gate(
        contract, findings, root, stage="technical_analysis",
        carried_sections=("modules", "interface_changes", "data_changes"),
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
                normalized = "harness" + "/" + value[len(prefix) :]
                return legacy_stage_artifact_to_current_ref(normalized)
        return legacy_stage_artifact_to_current_ref(value)
    if isinstance(value, list):
        return [normalize_runtime_artifact_ref(item) for item in value]
    return value


LEGACY_STAGE_ARTIFACT_MAP = {
    "discovery-brief.md": "discovery/discovery-brief.md",
    "product/product-definition.md": "product/product-definition.md",
    "product-definition.md": "product/product-definition.md",
    "product-evidence.md": "product/product-evidence.md",
    "product-domain-model.md": "product/product-domain-model.md",
    "scope-strategy.md": "product/scope-strategy.md",
    "use-case-model.md": "product/use-case-model.md",
    "acceptance-scenarios.md": "product/acceptance-scenarios.md",
    "interaction.md": "interaction/interaction.md",
    "solution.md": "solution/solution.md",
    "tech-design.md": "technical-analysis/tech-design.md",
    "execution-brief.md": "breakdown/execution-brief.md",
    "execution-result.md": "execute/execution-result.md",
    "code-review.md": "code-review/code-review.md",
    "verification-report.md": "verify/verification-report.md",
    "delivery-package.md": "delivery/delivery-package.md",
    "retrospective.md": "retrospective/retrospective.md",
}


def legacy_stage_artifact_to_current_ref(value: str) -> str:
    normalized = value[2:] if value.startswith("./") else value
    prefix = "harness-runtime/harness/stages/"
    runtime_prefix = "harness-runtime/harness/stages/"
    if normalized.startswith(runtime_prefix):
        normalized = "harness-runtime/harness/stages/" + normalized[len(runtime_prefix) :]
    if not normalized.startswith(prefix):
        return value
    parts = normalized.split("/")
    if len(parts) < 4:
        return value
    mission_id = parts[2]
    suffix = "/".join(parts[3:])
    if suffix.startswith("specs/"):
        mapped = "product/" + suffix
    else:
        mapped = LEGACY_STAGE_ARTIFACT_MAP.get(suffix)
    if not mapped:
        return value
    return f"harness-runtime/harness/artifacts/{mission_id}/{mapped}"


def artifact_ref_path_candidates(value: str) -> list[str]:
    normalized = value[2:] if value.startswith("./") else value
    candidates = [value]
    runtime_prefix = "harness-runtime/harness/"
    if normalized.startswith("harness-runtime/harness/"):
        candidates.append("harness-runtime/" + normalized)
    if normalized.startswith(runtime_prefix):
        candidates.append("harness-runtime/harness/" + normalized[len(runtime_prefix) :])

    current_ref = normalize_runtime_artifact_ref(normalized)
    if current_ref not in candidates:
        candidates.append(current_ref)
    if current_ref.startswith("harness-runtime/harness/artifacts/"):
        parts = current_ref.split("/")
        if len(parts) >= 5:
            mission_id = parts[2]
            suffix = "/".join(parts[3:])
            reverse = {v: k for k, v in LEGACY_STAGE_ARTIFACT_MAP.items()}
            legacy_suffix = reverse.get(suffix)
            if suffix.startswith("product/specs/"):
                legacy_suffix = suffix[len("product/") :]
            elif suffix.startswith("product/"):
                legacy_suffix = suffix
            if legacy_suffix:
                candidates.extend(
                    [
                        f"harness-runtime/harness/stages/{mission_id}/{legacy_suffix}",
                        f"harness-runtime/harness/stages/{mission_id}/{legacy_suffix}",
                    ]
                )
    return list(dict.fromkeys(candidates))


def relative_path_exists(root: Path, value: str) -> bool:
    for candidate in artifact_ref_path_candidates(value):
        path = Path(candidate)
        if path.is_absolute() and path.exists():
            return True
        if not path.is_absolute() and (root / path).exists():
            return True
    return False


def first_existing_relative_path(root: Path, value: str) -> Path:
    for candidate in artifact_ref_path_candidates(value):
        path = Path(candidate)
        resolved = path if path.is_absolute() else root / path
        if resolved.exists():
            return resolved
    path = Path(value)
    return path if path.is_absolute() else root / path


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
    example, PRD creation can run on the `product-definition-lane`, then the accepted
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
    for field in ("node_id", "artifact_version", "promoted_by_mission"):
        if not artifact.get(field):
            add(findings, "FAIL", "invalid_work_graph_artifact", f"work_graph_artifact missing {field}")
    uses_artifact_refs = isinstance(artifact.get("artifact_refs"), list)
    uses_legacy_paths = bool(artifact.get("source_stage_artifact") or artifact.get("canonical_artifact"))
    if uses_artifact_refs:
        if not artifact.get("artifact_set_id"):
            add(findings, "FAIL", "invalid_work_graph_artifact", "work_graph_artifact missing artifact_set_id")
        if not artifact.get("artifact_refs"):
            add(findings, "FAIL", "invalid_work_graph_artifact", "work_graph_artifact.artifact_refs must be non-empty")
    elif uses_legacy_paths:
        for field in ("source_stage_artifact", "canonical_artifact"):
            if not artifact.get(field):
                add(findings, "FAIL", "invalid_work_graph_artifact", f"work_graph_artifact missing {field}")
    else:
        add(findings, "FAIL", "invalid_work_graph_artifact", "work_graph_artifact must declare artifact_refs or legacy source_stage_artifact/canonical_artifact")
    if any(item.level == "FAIL" and item.code in {"missing_work_graph_artifact", "invalid_work_graph_artifact"} for item in findings):
        return
    expected_by_subtype = {
        "solution_guide": ("solution", "solution.md"),
        "technical_guide": ("technical-analysis", "tech-design.md"),
        "interaction_guide": ("interaction", "interaction.md"),
    }
    expected_dir, expected_file = expected_by_subtype[str(contract.get("subtype"))]
    node_id = str(artifact.get("node_id") or "")
    mission_id = str(contract.get("mission_id") or "")
    expected_artifact_path = f"harness-runtime/harness/artifacts/{mission_id}/{expected_dir}/{expected_file}"
    expected_source = f"harness-runtime/harness/stages/{mission_id}/{expected_file}"
    expected_canonical = f"harness-runtime/harness/work-graph/artifacts/{node_id}/{expected_file}"
    if uses_artifact_refs:
        matching_ref = False
        for index, ref in enumerate(artifact.get("artifact_refs") or []):
            if not isinstance(ref, dict):
                add(findings, "FAIL", "invalid_work_graph_artifact", f"work_graph_artifact.artifact_refs[{index}] must be an object")
                continue
            path_value = str(ref.get("path") or "")
            if not path_value:
                add(findings, "FAIL", "invalid_work_graph_artifact", f"work_graph_artifact.artifact_refs[{index}] missing path")
                continue
            path = Path(path_value)
            if path.is_absolute() or ".." in path.parts:
                add(findings, "FAIL", "work_graph_artifact_path_escape", f"work_graph_artifact.artifact_refs[{index}].path must be a relative in-harness path")
            if normalize_runtime_artifact_ref(path_value) == normalize_runtime_artifact_ref(expected_artifact_path):
                matching_ref = True
        if not matching_ref:
            add(findings, "FAIL", "work_graph_artifact_path_mismatch", f"artifact_refs must include {expected_artifact_path}")
    else:
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
    if uses_legacy_paths:
        canonical_artifact = str(artifact.get("canonical_artifact") or "")
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


def check_delivery(contract: dict[str, Any], findings: list[Finding]) -> None:
    """delivery_contract checker (delivery-improvement-plan M1.1 / M4.2).

    Implements the informal rule spec in
    schemas/control_contract.v1/delivery_contract.yaml (required_fields +
    GR-DL-001..007) — that file is a design spec, not a jsonschema document,
    so it is enforced here rather than through validate_schema().
    """
    for field in ("mission_id", "stage", "artifact"):
        if not contract.get(field):
            add(findings, "FAIL", "missing_field", f"delivery_contract missing required field: {field}")
    if contract.get("stage") not in (None, "delivery"):
        add(findings, "FAIL", "invalid_stage", "delivery_contract.stage must be 'delivery'")
    if contract.get("artifact") not in (None, "delivery"):
        add(findings, "FAIL", "invalid_artifact", "delivery_contract.artifact must be 'delivery'")

    acceptance_result = contract.get("acceptance_result") if isinstance(contract.get("acceptance_result"), dict) else {}
    if not acceptance_result:
        add(findings, "FAIL", "missing_acceptance_result", "delivery_contract requires acceptance_result section")
    else:
        for field in ("mission_id", "stage", "artifact"):
            if not acceptance_result.get(field):
                add(findings, "FAIL", "missing_field", f"acceptance_result missing required field: {field}")

        acceptance_trace = acceptance_result.get("acceptance_trace") or []
        if not acceptance_trace:
            add(findings, "FAIL", "missing_acceptance_trace", "acceptance_result requires non-empty acceptance_trace")
        for row in acceptance_trace:
            if not isinstance(row, dict):
                add(findings, "FAIL", "invalid_acceptance_trace_item", "acceptance_trace entries must be objects")
                continue
            aid = row.get("acceptance_id", "<unknown>")
            for field in ("acceptance_id", "expected", "actual", "reproduce_steps", "result_status"):
                if not row.get(field):
                    add(findings, "FAIL", "invalid_acceptance_trace_item", f"{aid} missing {field}")
            status = row.get("result_status")
            if status not in {"pass", "fail", "accepted_risk", "blocked"}:
                add(findings, "FAIL", "invalid_result_status", f"{aid} has invalid result_status: {status}")
            if status == "pass":
                if not row.get("verify_command_evidence_id"):
                    add(findings, "FAIL", "GR-DL-001", f"{aid} result_status=pass requires verify_command_evidence_id")
                if not row.get("acceptance_result_evidence_path"):
                    add(findings, "FAIL", "GR-DL-002", f"{aid} result_status=pass requires acceptance_result_evidence_path")

        risk_acceptance = acceptance_result.get("risk_acceptance") or []
        for item in risk_acceptance:
            if not isinstance(item, dict):
                add(findings, "FAIL", "invalid_risk_acceptance_item", "risk_acceptance entries must be objects")
                continue
            for field in ("risk_id", "approval_id", "approval_type", "source"):
                if not item.get(field):
                    add(findings, "FAIL", "invalid_risk_acceptance_item", f"risk_acceptance entry missing {field}")

        user_checkpoint = acceptance_result.get("user_checkpoint") if isinstance(acceptance_result.get("user_checkpoint"), dict) else {}
        uc_status = user_checkpoint.get("status")
        if uc_status not in {"pending_user_acceptance", "approved", "accepted_risk", "continue_fix", "blocked"}:
            add(findings, "FAIL", "invalid_user_checkpoint_status", f"user_checkpoint has invalid status: {uc_status}")
        if uc_status in {"approved", "accepted_risk"}:
            if not user_checkpoint.get("approval_id"):
                add(findings, "FAIL", "missing_user_checkpoint_approval", "user_checkpoint requires approval_id when status is approved/accepted_risk")
            if not user_checkpoint.get("original_user_text_ref"):
                add(findings, "FAIL", "missing_user_checkpoint_text_ref", "user_checkpoint requires original_user_text_ref when status is approved/accepted_risk")
        if uc_status == "accepted_risk" and not user_checkpoint.get("risk_summary"):
            add(findings, "FAIL", "missing_risk_summary", "user_checkpoint requires risk_summary when status is accepted_risk")
        if uc_status not in {"approved", "accepted_risk"}:
            add(findings, "FAIL", "GR-DL-005", "acceptance_result.user_checkpoint.status must be approved or accepted_risk")

    delivery_package = contract.get("delivery_package") if isinstance(contract.get("delivery_package"), dict) else {}
    if not delivery_package:
        add(findings, "FAIL", "missing_delivery_package", "delivery_contract requires delivery_package section")
    else:
        if not delivery_package.get("acceptance_state_ref"):
            add(findings, "FAIL", "GR-DL-003", "delivery_package.acceptance_state_ref is required")
        if not delivery_package.get("scope_summary"):
            add(findings, "FAIL", "missing_scope_summary", "delivery_package requires scope_summary")
        if not delivery_package.get("evidence_links"):
            add(findings, "FAIL", "missing_evidence_links", "delivery_package requires non-empty evidence_links")

        for fu in delivery_package.get("follow_ups") or []:
            if not isinstance(fu, dict):
                add(findings, "FAIL", "invalid_follow_up", "follow_ups entries must be objects")
                continue
            fid = fu.get("id", "<unknown>")
            for field in ("id", "description", "severity", "graph_op"):
                if not fu.get(field):
                    add(findings, "FAIL", "invalid_follow_up", f"{fid} missing {field}")
            severity = fu.get("severity")
            if severity not in {"blocking", "advisory", "can_ignore"}:
                add(findings, "FAIL", "invalid_follow_up_severity", f"{fid} has invalid severity: {severity}")
            graph_op = fu.get("graph_op")
            if graph_op not in {"split_node", "defer_node", "block_node", "none"}:
                add(findings, "FAIL", "invalid_follow_up_graph_op", f"{fid} has invalid graph_op: {graph_op}")
            if severity in {"blocking", "advisory"} and graph_op == "none":
                add(findings, "FAIL", "GR-DL-006", f"{fid} severity={severity} cannot have graph_op=none")
            if graph_op == "none" and severity == "can_ignore" and not fu.get("none_reason"):
                add(findings, "FAIL", "missing_none_reason", f"{fid} graph_op=none requires none_reason")

        handoff = delivery_package.get("handoff_evidence") if isinstance(delivery_package.get("handoff_evidence"), dict) else {}
        if not handoff:
            add(findings, "FAIL", "missing_handoff_evidence", "delivery_package requires handoff_evidence")
        elif handoff.get("pause_required") is not True:
            add(findings, "FAIL", "GR-DL-004", "delivery_package.handoff_evidence.pause_required must be true")

    for dispatch in contract.get("dispatches") or []:
        if not isinstance(dispatch, dict):
            add(findings, "FAIL", "invalid_dispatch", "dispatches entries must be objects")
            continue
        role = dispatch.get("role", "<unknown>")
        for field in ("role", "execution_mode", "model", "started_at", "completed_at", "verdict"):
            if not dispatch.get(field):
                add(findings, "FAIL", "invalid_dispatch", f"{role} dispatch missing {field}")
        if dispatch.get("execution_mode") == "main_agent_fallback" and dispatch.get("verdict") == "PASS":
            add(findings, "FAIL", "GR-DL-007", f"{role} dispatch cannot be main_agent_fallback with verdict=PASS")


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

    if is_legacy_finishing_branch_contract(contract):
        check_legacy_finishing_branch_contract(contract, findings)
        if not findings:
            add(findings, "PASS", "contract_valid", "Legacy finishing-branch contract integrity checks passed")
        status = "FAIL" if any(f.level == "FAIL" for f in findings) else "WARN" if any(f.level == "WARN" for f in findings) else "PASS"
        return status, findings, contract

    check_common(contract, findings)
    check_contract_hygiene(contract, findings, args.allow_placeholders)
    check_role_policy_block(contract, findings)
    check_execution_result(contract, findings, root, args.allow_placeholders)
    check_execute_implementation_contract(contract, findings, Path(args.root))
    check_role_verdicts(contract, findings)
    check_effectiveness_review_rounds(contract, findings, root)
    check_dependency_impact(contract, findings, root)
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
            path_text = upstream["path"]
            upstream_path = first_existing_relative_path(Path(args.root), str(path_text))
            if contains_placeholder(path_text) and not args.allow_placeholders:
                add(findings, "FAIL", "placeholder_in_runtime_artifact", f"upstream path contains placeholder: {path_text}")
            elif (
                not relative_path_exists(Path(args.root), str(path_text))
                and not contains_placeholder(path_text)
                and not upstream.get("optional")
            ):
                # optional 上游（如 interaction 原型契约）不存在时不报 missing_upstream，
                # 支持"非 UI / 未跑 interaction 的 mission 自动跳过"的非破坏语义；
                # 若存在则其 SURF-/PS- id 照常进入 upstream_ids 许可集。
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
        check_solution_guide(contract, findings, upstream_ids, Path(args.root))
    elif ctype == "guide_contract" and subtype == "technical_guide":
        check_technical_guide(
            contract,
            findings,
            upstream_ids,
            upstream_agent_arch_components,
            upstream_agent_engineering_scope,
            Path(args.root),
        )
    elif ctype == "evidence_contract" and subtype == "verification_evidence":
        check_verification(contract, findings, upstream_ids)
    elif ctype == "evidence_contract" and subtype == "review_evidence":
        check_review_evidence(contract, findings, upstream_ids, Path(args.root), args.allow_placeholders)
    elif ctype == "evidence_contract":
        add(findings, "WARN", "unsupported_evidence_subtype", f"Evidence subtype not checked in v1: {subtype}")
    elif ctype == "memory_update_contract":
        check_memory_update(contract, findings)
    elif ctype == "delivery_contract":
        check_delivery(contract, findings)
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
