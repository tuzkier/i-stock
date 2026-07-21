#!/usr/bin/env python3
"""Infer and normalize Harness test obligations from task intent and policy."""

from __future__ import annotations

from typing import Any


HIGH_RISK_SURFACES = {"state_machine", "concurrency", "auth", "permission", "migration", "data_model", "public_api"}

SURFACE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("auth", ("auth", "permission", "rbac", "role", "login", "token", "session", "security")),
    ("migration", ("migration", "migrations", "schema", "alembic", "prisma/migrations", "db/migrate")),
    ("concurrency", ("concurrency", "parallel", "queue", "worker", "daemon", "scheduler", "lock", "retry", "async")),
    ("state_machine", ("state", "status", "transition", "workflow", "fsm", "lifecycle")),
    ("accessibility", ("accessibility", "a11y", "aria")),
    ("public_api", ("openapi", "swagger", "public api", "api contract")),
    ("user_journey", ("e2e", "playwright", "user journey", "journey")),
    ("client_ui", ("mobile", "desktop", "native", "client ui", "simulator", "device", "ios", "android", "electron")),
    ("client_logic", ("client logic", "offline", "local cache", "sync", "platform api")),
    ("frontend_visual", ("visual", "responsive", "screenshot", "contrast", "layout", "css")),
    ("frontend_component", ("component", "components", ".tsx", ".jsx")),
    ("frontend_ui", ("frontend", "ui", "page", "screen", "view", "app/")),
    ("backend_api", ("api", "route", "routes", "controller", "endpoint", "handler")),
    ("backend_logic", ("service", "domain", "logic", "model", "repository", ".py", ".ts", ".js")),
)

CAPABILITY_EVIDENCE = {
    "test_result": ["red_report", "green_report", "regression_report"],
    "coverage": ["coverage_report"],
    "diff_coverage": ["diff_coverage_report"],
    "mutation_or_fault_injection": ["mutation_or_fault_report"],
    "ui_component_or_e2e": ["ui_component_or_e2e_report"],
    "client_run": ["client_run_report"],
    "visual_regression": ["screenshot_or_visual_report"],
    "e2e_ui": ["e2e_report"],
    "a11y": ["a11y_report"],
    "api_contract": ["api_contract_report"],
    "regression_report": ["regression_report"],
}

DEFAULT_ACCEPTED_ALTERNATIVES = {
    "mutation_or_fault_injection": ["mutation_report", "targeted_fault_injection_report", "equivalent_proof"],
    "ui_component_or_e2e": ["component_test_report", "e2e_report"],
}

DEFAULT_CAPABILITY_DEFAULTS = {
    "low": ["test_result", "regression_report"],
    "medium": ["test_result", "coverage", "diff_coverage"],
    "high": ["test_result", "coverage", "diff_coverage", "mutation_or_fault_injection"],
}

DEFAULT_SURFACE_DEFAULTS = {
    "backend_api": ["test_result", "coverage", "diff_coverage"],
    "backend_logic": ["test_result", "coverage", "diff_coverage"],
    "state_machine": ["mutation_or_fault_injection"],
    "concurrency": ["mutation_or_fault_injection"],
    "auth": ["mutation_or_fault_injection"],
    "migration": ["mutation_or_fault_injection"],
    "data_model": ["mutation_or_fault_injection"],
    "frontend_ui": ["ui_component_or_e2e"],
    "frontend_component": ["ui_component_or_e2e"],
    "frontend_visual": ["visual_regression"],
    "client_ui": ["client_run"],
    "client_logic": ["client_run"],
    "mobile": ["client_run"],
    "desktop": ["client_run"],
    "user_journey": ["e2e_ui"],
    "realtime": ["e2e_ui"],
    "accessibility": ["a11y"],
    "public_api": ["api_contract"],
}


def task_text(task: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("id", "objective", "title", "summary", "description"):
        value = task.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("authorized_paths", "prohibited_paths", "traces_to"):
        value = task.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
    for evidence in task.get("required_evidence") or []:
        if isinstance(evidence, dict):
            parts.extend(str(evidence.get(key, "")) for key in ("id", "type", "description"))
        else:
            parts.append(str(evidence))
    return "\n".join(parts).lower()


def infer_surfaces(task: dict[str, Any]) -> list[str]:
    text = task_text(task)
    surfaces = [surface for surface, patterns in SURFACE_PATTERNS if any(pattern in text for pattern in patterns)]
    if surfaces:
        return list(dict.fromkeys(surfaces))
    paths = [str(path) for path in task.get("authorized_paths") or []]
    if any(path.endswith((".md", ".mdx", ".txt")) for path in paths) and not any(path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")) for path in paths):
        return ["documentation"]
    return ["backend_logic"]


def infer_risk_level(task: dict[str, Any], surfaces: list[str]) -> str:
    text = task_text(task)
    if any(surface in HIGH_RISK_SURFACES for surface in surfaces):
        return "high"
    if any(word in text for word in ("payment", "money", "credential", "secret", "privacy", "data consistency", "rollback")):
        return "high"
    if surfaces == ["documentation"] or any(word in text for word in ("copy", "style", "css", "readme", "docs")):
        return "low"
    return "medium"


def capabilities_for(policy: dict[str, Any], risk_level: str, surfaces: list[str]) -> list[str]:
    capabilities: list[str] = []
    defaults = policy.get("capability_defaults") if isinstance(policy.get("capability_defaults"), dict) else {}
    surface_defaults = policy.get("surface_defaults") if isinstance(policy.get("surface_defaults"), dict) else {}
    defaults = {**DEFAULT_CAPABILITY_DEFAULTS, **defaults}
    surface_defaults = {**DEFAULT_SURFACE_DEFAULTS, **surface_defaults}
    for capability in defaults.get(risk_level) or []:
        capabilities.append(str(capability))
    for surface in surfaces:
        for capability in surface_defaults.get(surface) or []:
            capabilities.append(str(capability))
    if not capabilities:
        capabilities.extend(["test_result", "regression_report"])
    return list(dict.fromkeys(capabilities))


def evidence_for(capabilities: list[str]) -> list[str]:
    evidence = ["red_report", "green_report", "regression_report"]
    for capability in capabilities:
        evidence.extend(CAPABILITY_EVIDENCE.get(capability, []))
    return list(dict.fromkeys(evidence))


def normalize_obligation(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    explicit = task.get("test_obligation") if isinstance(task.get("test_obligation"), dict) else {}
    inferred_surfaces = infer_surfaces(task)
    surfaces = explicit.get("surfaces") if isinstance(explicit.get("surfaces"), list) and explicit.get("surfaces") else inferred_surfaces
    surfaces = [str(surface) for surface in surfaces]
    risk_level = explicit.get("risk_level") if explicit.get("risk_level") in {"low", "medium", "high"} else infer_risk_level(task, surfaces)
    capabilities = explicit.get("required_capabilities") if isinstance(explicit.get("required_capabilities"), list) and explicit.get("required_capabilities") else capabilities_for(policy, risk_level, surfaces)
    capabilities = [str(capability) for capability in capabilities]
    evidence_required = explicit.get("evidence_required") if isinstance(explicit.get("evidence_required"), list) and explicit.get("evidence_required") else evidence_for(capabilities)
    evidence_required = [str(evidence) for evidence in evidence_required]
    accepted_alternatives = explicit.get("accepted_alternatives") if isinstance(explicit.get("accepted_alternatives"), dict) else DEFAULT_ACCEPTED_ALTERNATIVES
    inferred_fields = []
    if "risk_level" not in explicit:
        inferred_fields.append("risk_level")
    if "surfaces" not in explicit:
        inferred_fields.append("surfaces")
    if "required_capabilities" not in explicit:
        inferred_fields.append("required_capabilities")
    if "evidence_required" not in explicit:
        inferred_fields.append("evidence_required")
    return {
        "risk_level": risk_level,
        "surfaces": surfaces,
        "required_capabilities": list(dict.fromkeys(capabilities)),
        "evidence_required": list(dict.fromkeys(evidence_required)),
        "accepted_alternatives": accepted_alternatives,
        "_harness_source": "explicit" if not inferred_fields else "inferred" if not explicit else "explicit_plus_inferred",
        "_harness_inferred_fields": inferred_fields,
    }


def is_obligation_complete(obligation: dict[str, Any]) -> bool:
    return (
        obligation.get("risk_level") in {"low", "medium", "high"}
        and isinstance(obligation.get("surfaces"), list)
        and bool(obligation.get("surfaces"))
        and isinstance(obligation.get("required_capabilities"), list)
        and bool(obligation.get("required_capabilities"))
        and isinstance(obligation.get("evidence_required"), list)
        and bool(obligation.get("evidence_required"))
    )
