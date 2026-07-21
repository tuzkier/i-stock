#!/usr/bin/env python3
"""Resolve Harness E2E obligations into concrete browser test actions."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from toolchain_probe import find_latest_mission, load_json, read_text  # noqa: E402

try:  # e2e_obligation_policy.py may be introduced by another worker.
    import e2e_obligation_policy as external_e2e_policy  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover - compatibility fallback
    external_e2e_policy = None


E2E_CAPABILITY_TOOL_PREFERENCES = {
    "browser_flow": ["playwright", "cypress"],
    "full_user_journey": ["playwright", "cypress"],
    "user_visible_assertion": ["playwright", "cypress"],
    "api_backed_state": ["playwright"],
    "auth_state": ["playwright"],
    "negative_path": ["playwright", "cypress"],
    "realtime_or_refresh": ["playwright"],
    "accessibility_smoke": ["@axe-core/playwright", "axe-core"],
    "trace_or_video": ["playwright"],
    "screenshot_on_failure": ["playwright", "cypress"],
}

TOOL_INSTALL = {
    "playwright": {"ecosystem": "typescript", "packages": ["@playwright/test"]},
    "cypress": {"ecosystem": "typescript", "packages": ["cypress"]},
    "@axe-core/playwright": {"ecosystem": "typescript", "packages": ["@axe-core/playwright", "axe-core"]},
    "axe-core": {"ecosystem": "typescript", "packages": ["axe-core"]},
}

DEFAULT_EVIDENCE_REQUIRED = [
    "e2e_run_report",
    "trace_or_video",
    "screenshot_on_failure",
    "assertion_summary",
]

DEFAULT_ACCEPTED_ALTERNATIVES = {
    "browser_flow": [
        "component_integration_with_real_api_contract",
        "manual_acceptance_walkthrough_with_recorded_steps",
    ]
}

UI_SURFACE_KEYWORDS = {
    "web_ui": ("ui", "frontend", "page", "screen", "view", "tsx", "jsx", "component", "browser"),
    "auth": ("auth", "login", "permission", "rbac", "role", "session", "token"),
    "realtime": ("realtime", "websocket", "refresh", "invalidation", "subscription", "live"),
    "accessibility": ("accessibility", "a11y", "aria", "keyboard"),
}


def load_yaml(path: Path) -> dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def extract_contract(path: Path) -> dict[str, Any]:
    if yaml is None:
        return {}
    if path.exists():
        parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        contract = parsed.get("control_contract")
        return contract if isinstance(contract, dict) else {}
    return {}


def package_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "package-lock.json").exists():
        return "npm"
    return "npm"


def install_command(root: Path, packages: list[str]) -> str:
    manager = package_manager(root)
    if manager == "pnpm":
        return "pnpm add -D " + " ".join(packages)
    if manager == "yarn":
        return "yarn add -D " + " ".join(packages)
    return "npm install -D " + " ".join(packages)


def approved_packages(config: dict[str, Any]) -> set[str]:
    approved: set[str] = set()
    e2e = config.get("e2e") if isinstance(config.get("e2e"), dict) else {}
    toolchain = e2e.get("toolchain") if isinstance(e2e.get("toolchain"), dict) else {}
    for source in (toolchain.get("approved_tools"), (config.get("test_toolchain") or {}).get("approved_tools")):
        if not isinstance(source, dict):
            continue
        for values in source.values():
            if isinstance(values, list):
                approved.update(str(item) for item in values)
    return approved


def package_scripts(root: Path, rel: str) -> dict[str, str]:
    scripts = load_json(root / rel).get("scripts")
    return {str(k): str(v) for k, v in scripts.items()} if isinstance(scripts, dict) else {}


def dependency_names(root: Path, rel: str) -> set[str]:
    data = load_json(root / rel)
    names: set[str] = set()
    for field in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps = data.get(field)
        if isinstance(deps, dict):
            names.update(str(name) for name in deps)
    return names


def file_exists_any(root: Path, patterns: list[str]) -> bool:
    return any(any(root.glob(pattern)) for pattern in patterns)


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def package_command(root: Path, script: str) -> str | None:
    scripts = package_scripts(root, "package.json")
    frontend_scripts = package_scripts(root, "apps/frontend/package.json")
    manager = package_manager(root)
    if script in scripts:
        return f"{manager} run {script}"
    if script in frontend_scripts:
        if manager == "pnpm":
            return f"pnpm --dir apps/frontend run {script}"
        if manager == "yarn":
            return "yarn --cwd apps/frontend " + script
        return f"npm --prefix apps/frontend run {script}"
    return None


def existing_artifacts(root: Path) -> dict[str, Any]:
    html_candidates = [
        "playwright-report/index.html",
        "apps/frontend/playwright-report/index.html",
        "cypress/reports/index.html",
        "apps/frontend/cypress/reports/index.html",
    ]
    traces: list[str] = []
    videos: list[str] = []
    screenshots: list[str] = []
    for base in ["test-results", "apps/frontend/test-results", "cypress", "apps/frontend/cypress"]:
        base_path = root / base
        if not base_path.exists():
            continue
        for path in base_path.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(root))
            suffix = path.suffix.lower()
            if suffix == ".zip" or "trace" in path.name.lower():
                traces.append(rel)
            elif suffix in {".webm", ".mp4"}:
                videos.append(rel)
            elif suffix in {".png", ".jpg", ".jpeg"}:
                screenshots.append(rel)
    return {
        "html_report": next((rel for rel in html_candidates if (root / rel).exists()), "",
        ),
        "trace": sorted(set(traces)),
        "video": sorted(set(videos)),
        "screenshots": sorted(set(screenshots)),
    }


def detect_e2e_toolchain(root: Path, config: dict[str, Any], mission_id: str | None) -> list[dict[str, Any]]:
    root_deps = dependency_names(root, "package.json")
    frontend_deps = dependency_names(root, "apps/frontend/package.json")
    deps = root_deps | frontend_deps
    scripts = {**package_scripts(root, "package.json"), **package_scripts(root, "apps/frontend/package.json")}
    e2e_config = config.get("e2e") if isinstance(config.get("e2e"), dict) else {}
    framework = str(e2e_config.get("framework") or "playwright").lower()
    test_dir = str(e2e_config.get("test_dir") or "tests/e2e")
    trace_dir = f"harness-runtime/harness/traces/{mission_id or 'unknown'}/e2e"

    playwright_command = (
        package_command(root, "e2e")
        or package_command(root, "test:e2e")
        or "npx playwright test"
    )
    cypress_command = (
        package_command(root, "e2e")
        or package_command(root, "test:e2e")
        or "npx cypress run"
    )
    playwright_configured = (
        "@playwright/test" in deps
        or any("playwright" in script for script in scripts.values())
        or file_exists_any(root, ["playwright.config.*", "apps/frontend/playwright.config.*"])
    )
    cypress_configured = (
        "cypress" in deps
        or any("cypress" in script for script in scripts.values())
        or file_exists_any(root, ["cypress.config.*", "apps/frontend/cypress.config.*"])
    )
    axe_configured = "@axe-core/playwright" in deps or "axe-core" in deps or "cypress-axe" in deps

    return [
        {
            "tool": "playwright",
            "category": "browser_flow",
            "configured": playwright_configured,
            "available": command_available("npx") or command_available("pnpm") or command_available("playwright"),
            "commands": [playwright_command],
            "report_paths": [
                "playwright-report/index.html",
                "test-results",
                f"{trace_dir}/playwright-output.txt",
            ],
            "artifact_types": ["html_report", "trace", "video", "screenshots", "assertion_summary"],
            "purpose": "Run browser E2E flows with trace/video/screenshot diagnostics.",
            "notes": [] if playwright_configured else ["No Playwright dependency/config/script detected."],
        },
        {
            "tool": "cypress",
            "category": "browser_flow",
            "configured": cypress_configured,
            "available": command_available("npx") or command_available("pnpm") or command_available("cypress"),
            "commands": [cypress_command],
            "report_paths": [
                "cypress/screenshots",
                "cypress/videos",
                f"{trace_dir}/cypress-output.txt",
            ],
            "artifact_types": ["video", "screenshots", "assertion_summary"],
            "purpose": "Run Cypress browser E2E flows.",
            "notes": [] if cypress_configured else ["No Cypress dependency/config/script detected."],
        },
        {
            "tool": "@axe-core/playwright",
            "category": "accessibility_smoke",
            "configured": axe_configured,
            "available": command_available("npx") or command_available("pnpm"),
            "commands": [playwright_command],
            "report_paths": [test_dir, f"{trace_dir}/accessibility-output.txt"],
            "artifact_types": ["assertion_summary"],
            "purpose": "Provide accessibility smoke evidence through browser tests.",
            "notes": [] if axe_configured else ["No axe accessibility dependency detected."],
        },
    ]


def task_text(task: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("id", "objective", "title", "summary", "description"):
        if isinstance(task.get(key), str):
            parts.append(task[key])
    for key in ("authorized_paths", "traces_to"):
        value = task.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
    return "\n".join(parts).lower()


def fallback_normalize_obligation(task: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    explicit = task.get("e2e_obligation") if isinstance(task.get("e2e_obligation"), dict) else {}
    text = task_text(task)
    inferred_surfaces = [
        surface for surface, keywords in UI_SURFACE_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]
    if not inferred_surfaces and any(path.endswith((".tsx", ".jsx", ".css")) for path in task.get("authorized_paths") or []):
        inferred_surfaces = ["web_ui"]
    surfaces = explicit.get("user_surfaces") or explicit.get("surfaces") or inferred_surfaces
    surfaces = [str(surface) for surface in surfaces] if isinstance(surfaces, list) else []
    risk_level = explicit.get("risk_level") if explicit.get("risk_level") in {"low", "medium", "high"} else (
        "high" if any(surface in {"auth", "realtime"} for surface in surfaces) else "medium" if surfaces else "low"
    )

    required = explicit.get("required_capabilities")
    if not isinstance(required, list) or not required:
        required = []
        if surfaces:
            required.extend(["browser_flow", "user_visible_assertion"])
        if "auth" in surfaces:
            required.extend(["auth_state", "negative_path"])
        if "realtime" in surfaces:
            required.append("realtime_or_refresh")
        if "accessibility" in surfaces:
            required.append("accessibility_smoke")
        if risk_level == "high" and surfaces:
            required.append("full_user_journey")
    required = list(dict.fromkeys(str(item) for item in required))

    evidence = explicit.get("evidence_required") if isinstance(explicit.get("evidence_required"), list) else []
    evidence = list(dict.fromkeys([*DEFAULT_EVIDENCE_REQUIRED, *(str(item) for item in evidence)])) if required else []
    accepted = explicit.get("accepted_alternatives") if isinstance(explicit.get("accepted_alternatives"), dict) else DEFAULT_ACCEPTED_ALTERNATIVES
    inferred_fields = []
    if "risk_level" not in explicit:
        inferred_fields.append("risk_level")
    if "user_surfaces" not in explicit and "surfaces" not in explicit:
        inferred_fields.append("user_surfaces")
    if "required_capabilities" not in explicit:
        inferred_fields.append("required_capabilities")
    if "evidence_required" not in explicit:
        inferred_fields.append("evidence_required")
    return {
        "risk_level": risk_level,
        "user_surfaces": surfaces,
        "required_capabilities": required,
        "evidence_required": evidence,
        "accepted_alternatives": accepted,
        "_harness_source": "explicit" if explicit and not inferred_fields else "explicit_plus_inferred" if explicit else "inferred",
        "_harness_inferred_fields": inferred_fields,
    }


def normalizer() -> Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]:
    for name in ("normalize_obligation", "normalize_e2e_obligation"):
        candidate = getattr(external_e2e_policy, name, None)
        if callable(candidate):
            return candidate
    return fallback_normalize_obligation


def resolve(root: Path, mission_id: str | None) -> dict[str, Any]:
    mission_id = find_latest_mission(root, mission_id)
    config = load_yaml(root / "harness-runtime/config/harness.yaml")
    e2e_config = config.get("e2e") if isinstance(config.get("e2e"), dict) else {}
    e2e_enabled = bool(e2e_config.get("enabled", True))
    e2e_policy = e2e_config.get("obligation_policy") if isinstance(e2e_config.get("obligation_policy"), dict) else {}
    install_policy = (
        ((e2e_config.get("toolchain") or {}).get("install_policy") if isinstance(e2e_config.get("toolchain"), dict) else None)
        or ((config.get("test_toolchain") or {}).get("install_policy") if isinstance(config.get("test_toolchain"), dict) else None)
        or "auto_for_required_whitelist"
    )
    stage_root = root / "harness-runtime/harness/stages" / str(mission_id)
    contract = extract_contract(stage_root / "contracts" / "execution-brief.contract.yaml")
    tasks = contract.get("tasks") if isinstance(contract.get("tasks"), list) else []
    toolchain = detect_e2e_toolchain(root, config, mission_id)
    tool_by_name = {tool["tool"]: tool for tool in toolchain}
    approved = approved_packages(config)
    has_package_json = (root / "package.json").exists() or (root / "apps/frontend/package.json").exists()

    obligations: list[dict[str, Any]] = []
    install_actions_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    decision_gate_reasons: list[dict[str, Any]] = []
    normalize = normalizer()

    for task in tasks:
        if not isinstance(task, dict):
            continue
        obligation = normalize(task, e2e_policy)
        source = obligation.pop("_harness_source", "external")
        inferred = obligation.pop("_harness_inferred_fields", [])
        required = list(dict.fromkeys(str(item) for item in obligation.get("required_capabilities") or []))
        capability_map: dict[str, Any] = {}
        for capability in required:
            candidates = E2E_CAPABILITY_TOOL_PREFERENCES.get(capability, ["playwright"])
            selected = next((tool for tool in candidates if (tool_by_name.get(tool) or {}).get("configured")), None)
            selected = selected or candidates[0]
            selected_tool = tool_by_name.get(selected, {})
            missing = not bool(selected_tool.get("configured"))
            capability_map[capability] = {
                "candidate_tools": candidates,
                "selected_tool": selected,
                "configured": bool(selected_tool.get("configured")),
                "available": bool(selected_tool.get("available")),
                "missing": missing,
            }
            if missing:
                install_info = TOOL_INSTALL.get(selected, {})
                packages = [str(pkg) for pkg in install_info.get("packages") or []]
                unapproved = [pkg for pkg in packages if pkg not in approved and selected not in approved]
                if not has_package_json:
                    decision_gate_reasons.append({
                        "task_id": task.get("id"),
                        "capability": capability,
                        "reason": "missing_package_json_for_e2e_install",
                        "tool": selected,
                        "packages": packages,
                    })
                elif unapproved:
                    decision_gate_reasons.append({
                        "task_id": task.get("id"),
                        "capability": capability,
                        "reason": "non_whitelisted_tool",
                        "tool": selected,
                        "packages": packages,
                    })
                elif install_policy == "auto_for_required_whitelist":
                    command = install_command(root, packages)
                    key = (selected, command)
                    action = install_actions_by_key.setdefault(key, {
                        "task_ids": [],
                        "capabilities": [],
                        "tool": selected,
                        "packages": packages,
                        "command": command,
                    })
                    if task.get("id") not in action["task_ids"]:
                        action["task_ids"].append(task.get("id"))
                    if capability not in action["capabilities"]:
                        action["capabilities"].append(capability)
        obligations.append({
            "task_id": task.get("id"),
            "obligation_source": source,
            "inferred_fields": inferred,
            "risk_level": obligation.get("risk_level"),
            "user_surfaces": obligation.get("user_surfaces") or obligation.get("surfaces") or [],
            "required_capabilities": required,
            "evidence_required": obligation.get("evidence_required") or [],
            "accepted_alternatives": obligation.get("accepted_alternatives") or {},
            "capabilities": capability_map,
        })

    install_actions = list(install_actions_by_key.values())
    if not e2e_enabled:
        status = "WARN"
        decision_gate_reasons.append({"reason": "e2e_disabled_requires_user_acceptance"})
    elif decision_gate_reasons:
        status = "BLOCKED"
    elif install_actions:
        status = "WARN"
    elif not tasks:
        status = "WARN"
    else:
        missing = [
            detail for obligation in obligations
            for detail in (obligation.get("capabilities") or {}).values()
            if detail.get("missing")
        ]
        status = "FAIL" if missing else "PASS"

    artifact_root = f"harness-runtime/harness/traces/{mission_id or 'unknown'}/e2e"
    return {
        "schema_version": 1,
        "type": "e2e_plan",
        "mission_id": mission_id,
        "status": status,
        "e2e_enabled": e2e_enabled,
        "install_policy": install_policy,
        "framework": e2e_config.get("framework", "playwright"),
        "base_url": e2e_config.get("base_url", ""),
        "test_dir": e2e_config.get("test_dir", "tests/e2e"),
        "tasks": obligations,
        "obligations": obligations,
        "toolchain": toolchain,
        "install_actions": install_actions,
        "decision_gate_reasons": decision_gate_reasons,
        "artifact_policy": {
            "artifact_root": artifact_root,
            "status_artifact": f"{artifact_root}/e2e-status.json",
            "run_artifact": f"{artifact_root}/e2e-run.json",
            "required_artifacts": DEFAULT_EVIDENCE_REQUIRED,
            "collect": existing_artifacts(root),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--mission-id")
    parser.add_argument("--output")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = resolve(root, args.mission_id)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
