#!/usr/bin/env python3
"""Infer and normalize Harness E2E obligations from task intent and policy."""

from __future__ import annotations

from typing import Any


__all__ = ["normalize_e2e_obligation", "is_e2e_obligation_complete"]


HIGH_RISK_SURFACES = {"auth", "permission", "workspace_boundary", "critical_flow"}
E2E_RISK_WORDS = (
    "payment",
    "money",
    "credential",
    "secret",
    "privacy",
    "tenant",
    "workspace",
    "permission",
    "rbac",
    "auth",
    "login",
)

USER_SURFACE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("auth", ("auth", "login", "logout", "session", "token", "credential", "sso")),
    ("permission", ("permission", "rbac", "role", "forbidden", "unauthorized", "access denied")),
    ("workspace_boundary", ("workspace", "tenant", "organization", "org boundary", "multi-tenant")),
    ("realtime", ("realtime", "real-time", "websocket", "sse", "subscription", "live update")),
    ("query_invalidation", ("invalidate", "refetch", "refresh", "cache", "query", "stale")),
    ("accessibility", ("accessibility", "a11y", "aria", "keyboard", "screen reader")),
    ("form", ("form", "input", "submit", "validation", "field", "textarea", "select")),
    ("navigation", ("navigation", "route", "router", "redirect", "link", "tab", "breadcrumb")),
    ("web_ui", ("web ui", "frontend", "ui", "page", "screen", "view", "browser", ".tsx", ".jsx", "app/")),
    ("critical_flow", ("e2e", "user journey", "journey", "acceptance flow", "happy path", "checkout")),
    ("api_only", ("api", "endpoint", "route", "controller", "handler", "openapi", "contract")),
)

TEST_SURFACE_TO_USER_SURFACE = {
    "frontend_ui": "web_ui",
    "frontend_component": "web_ui",
    "frontend_visual": "web_ui",
    "user_journey": "critical_flow",
    "realtime": "realtime",
    "accessibility": "accessibility",
    "auth": "auth",
    "public_api": "api_only",
    "backend_api": "api_only",
}

CAPABILITY_EVIDENCE = {
    "browser_flow": ["e2e_run_report", "trace_or_video", "screenshot_on_failure"],
    "user_visible_assertion": ["assertion_summary"],
    "api_backed_state": ["assertion_summary"],
    "realtime_or_refresh": ["e2e_run_report", "trace_or_video", "assertion_summary"],
    "accessibility_smoke": ["accessibility_report"],
    "auth_state": ["e2e_run_report", "trace_or_video"],
    "negative_path": ["assertion_summary"],
    "full_user_journey": ["e2e_run_report", "trace_or_video", "assertion_summary"],
    "api_or_contract_evidence": ["api_contract_report"],
}

DEFAULT_ACCEPTED_ALTERNATIVES = {
    "browser_flow": [
        "component_integration_with_real_api_contract",
        "manual_acceptance_walkthrough_with_recorded_steps",
    ],
    "api_or_contract_evidence": ["api_contract_report", "contract_test_report"],
}

DEFAULT_RISK_CAPABILITY_DEFAULTS = {
    "low": ["browser_flow", "user_visible_assertion"],
    "medium": ["browser_flow", "user_visible_assertion", "api_backed_state"],
    "high": ["browser_flow", "user_visible_assertion", "api_backed_state", "negative_path"],
}

DEFAULT_SURFACE_CAPABILITY_DEFAULTS = {
    "web_ui": ["browser_flow", "user_visible_assertion"],
    "form": ["browser_flow", "user_visible_assertion", "api_backed_state"],
    "navigation": ["browser_flow", "user_visible_assertion"],
    "auth": ["browser_flow", "auth_state", "negative_path"],
    "permission": ["browser_flow", "auth_state", "negative_path"],
    "workspace_boundary": ["browser_flow", "auth_state", "negative_path"],
    "realtime": ["browser_flow", "realtime_or_refresh"],
    "query_invalidation": ["browser_flow", "realtime_or_refresh"],
    "critical_flow": ["full_user_journey", "api_backed_state"],
    "accessibility": ["accessibility_smoke"],
    "api_only": ["api_or_contract_evidence"],
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
    test_obligation = task.get("test_obligation")
    if isinstance(test_obligation, dict):
        for key in ("risk_level", "surfaces", "required_capabilities", "evidence_required"):
            value = test_obligation.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
            elif isinstance(value, str):
                parts.append(value)
    return "\n".join(parts).lower()


def infer_user_surfaces(task: dict[str, Any]) -> list[str]:
    text = task_text(task)
    surfaces = [surface for surface, patterns in USER_SURFACE_PATTERNS if any(pattern in text for pattern in patterns)]
    test_obligation = task.get("test_obligation")
    if isinstance(test_obligation, dict):
        for surface in test_obligation.get("surfaces") or []:
            mapped = TEST_SURFACE_TO_USER_SURFACE.get(str(surface))
            if mapped:
                surfaces.append(mapped)
    if surfaces:
        surfaces = list(dict.fromkeys(surfaces))
        if "api_only" in surfaces and len(surfaces) > 1:
            surfaces = [surface for surface in surfaces if surface != "api_only"]
        return surfaces
    paths = [str(path) for path in task.get("authorized_paths") or []]
    if any(path.endswith((".tsx", ".jsx")) or "/app/" in path or "/pages/" in path for path in paths):
        return ["web_ui"]
    if any(path.endswith((".md", ".mdx", ".txt")) for path in paths) and not any(path.endswith((".py", ".ts", ".tsx", ".js", ".jsx")) for path in paths):
        return ["documentation"]
    return ["api_only"]


def infer_risk_level(task: dict[str, Any], user_surfaces: list[str]) -> str:
    explicit_test = task.get("test_obligation") if isinstance(task.get("test_obligation"), dict) else {}
    test_risk = explicit_test.get("risk_level")
    if test_risk in {"low", "medium", "high"}:
        return str(test_risk)
    text = task_text(task)
    if any(surface in HIGH_RISK_SURFACES for surface in user_surfaces):
        return "high"
    if any(word in text for word in E2E_RISK_WORDS):
        return "high"
    if user_surfaces == ["documentation"] or any(word in text for word in ("copy", "style", "css", "readme", "docs")):
        return "low"
    return "medium"


def capabilities_for(policy: dict[str, Any], risk_level: str, user_surfaces: list[str]) -> list[str]:
    capabilities: list[str] = []
    risk_defaults = policy.get("capability_defaults") if isinstance(policy.get("capability_defaults"), dict) else {}
    surface_defaults = policy.get("surface_defaults") if isinstance(policy.get("surface_defaults"), dict) else {}
    risk_defaults = {**DEFAULT_RISK_CAPABILITY_DEFAULTS, **risk_defaults}
    surface_defaults = {**DEFAULT_SURFACE_CAPABILITY_DEFAULTS, **surface_defaults}
    if user_surfaces == ["api_only"]:
        return ["api_or_contract_evidence"]
    if user_surfaces == ["documentation"]:
        return ["api_or_contract_evidence"]
    for capability in risk_defaults.get(risk_level) or []:
        capabilities.append(str(capability))
    for surface in user_surfaces:
        for capability in surface_defaults.get(surface) or []:
            capabilities.append(str(capability))
    if not capabilities:
        capabilities.extend(["browser_flow", "user_visible_assertion"])
    return list(dict.fromkeys(capabilities))


def evidence_for(capabilities: list[str]) -> list[str]:
    evidence: list[str] = []
    for capability in capabilities:
        evidence.extend(CAPABILITY_EVIDENCE.get(capability, []))
    return list(dict.fromkeys(evidence))


def normalize_e2e_obligation(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    explicit = task.get("e2e_obligation") if isinstance(task.get("e2e_obligation"), dict) else {}
    inferred_surfaces = infer_user_surfaces(task)
    user_surfaces = explicit.get("user_surfaces") if isinstance(explicit.get("user_surfaces"), list) and explicit.get("user_surfaces") else inferred_surfaces
    user_surfaces = [str(surface) for surface in user_surfaces]
    risk_level = explicit.get("risk_level") if explicit.get("risk_level") in {"low", "medium", "high"} else infer_risk_level(task, user_surfaces)
    capabilities = explicit.get("required_capabilities") if isinstance(explicit.get("required_capabilities"), list) and explicit.get("required_capabilities") else capabilities_for(policy, risk_level, user_surfaces)
    capabilities = [str(capability) for capability in capabilities]
    evidence_required = explicit.get("evidence_required") if isinstance(explicit.get("evidence_required"), list) and explicit.get("evidence_required") else evidence_for(capabilities)
    evidence_required = [str(evidence) for evidence in evidence_required]
    accepted_alternatives = explicit.get("accepted_alternatives") if isinstance(explicit.get("accepted_alternatives"), dict) else DEFAULT_ACCEPTED_ALTERNATIVES
    inferred_fields = []
    if "risk_level" not in explicit:
        inferred_fields.append("risk_level")
    if "user_surfaces" not in explicit:
        inferred_fields.append("user_surfaces")
    if "required_capabilities" not in explicit:
        inferred_fields.append("required_capabilities")
    if "evidence_required" not in explicit:
        inferred_fields.append("evidence_required")
    return {
        "risk_level": risk_level,
        "user_surfaces": user_surfaces,
        "required_capabilities": list(dict.fromkeys(capabilities)),
        "evidence_required": list(dict.fromkeys(evidence_required)),
        "accepted_alternatives": accepted_alternatives,
        "_harness_e2e_required": user_surfaces not in (["api_only"], ["documentation"]),
        "_harness_source": "explicit" if not inferred_fields else "inferred" if not explicit else "explicit_plus_inferred",
        "_harness_inferred_fields": inferred_fields,
    }


def is_e2e_obligation_complete(obligation: dict[str, Any]) -> bool:
    return (
        obligation.get("risk_level") in {"low", "medium", "high"}
        and isinstance(obligation.get("user_surfaces"), list)
        and bool(obligation.get("user_surfaces"))
        and isinstance(obligation.get("required_capabilities"), list)
        and bool(obligation.get("required_capabilities"))
        and isinstance(obligation.get("evidence_required"), list)
        and bool(obligation.get("evidence_required"))
    )
