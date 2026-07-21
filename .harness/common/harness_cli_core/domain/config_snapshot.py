from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from harness_cli_core.domain.autonomy import autonomy_alias_map, normalize_autonomy_level
from harness_cli_core.domain.knowledge import project_knowledge_root
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_paths import relpath


def as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def load_project_stage_rules(root: Path) -> tuple[dict[str, Any], Path | None]:
    for path in (
        project_knowledge_root(root) / "engineering" / "policies" / "stage-rules.yaml",
        root / "package" / "project-knowledge" / "engineering" / "policies" / "stage-rules.yaml",
    ):
        data = load_yaml(path)
        if data:
            return data, path
    return {}, None


def snapshot_prototype_config(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    prototype = dict(config.get("prototype") if isinstance(config.get("prototype"), dict) else {})
    frontend = dict(
        prototype.get("frontend_engineering")
        if isinstance(prototype.get("frontend_engineering"), dict)
        else {}
    )

    stage_rules, stage_rules_path = load_project_stage_rules(root)
    interaction_rules = stage_rules.get("interaction") if isinstance(stage_rules.get("interaction"), dict) else {}
    stage_rules_root = str(interaction_rules.get("frontend_project_root") or "").strip()
    config_root = str(frontend.get("frontend_project_root") or "").strip()

    if stage_rules_root:
        frontend["frontend_project_root"] = stage_rules_root
        frontend["frontend_project_root_source"] = (
            f"{relpath(root, stage_rules_path) if stage_rules_path else 'project-knowledge/engineering/policies/stage-rules.yaml'}"
            ":interaction.frontend_project_root"
        )
        frontend["frontend_project_root_status"] = "resolved"
    elif config_root:
        frontend["frontend_project_root"] = config_root
        frontend["frontend_project_root_source"] = "harness-runtime/config/harness.yaml:prototype.frontend_engineering.frontend_project_root"
        frontend["frontend_project_root_status"] = "resolved"
    else:
        frontend["frontend_project_root"] = ""
        frontend["frontend_project_root_source"] = None
        frontend["frontend_project_root_status"] = "unresolved"

    prototype["frontend_engineering"] = frontend

    interactive = dict(
        prototype.get("interactive_prototype")
        if isinstance(prototype.get("interactive_prototype"), dict)
        else {}
    )
    stage_rules_proto_root = str(interaction_rules.get("prototype_project_root") or "").strip()
    config_proto_root = str(interactive.get("prototype_project_root") or "").strip()

    if stage_rules_proto_root:
        interactive["prototype_project_root"] = stage_rules_proto_root
        interactive["prototype_project_root_source"] = (
            f"{relpath(root, stage_rules_path) if stage_rules_path else 'project-knowledge/engineering/policies/stage-rules.yaml'}"
            ":interaction.prototype_project_root"
        )
        interactive["prototype_project_root_status"] = "resolved"
    elif config_proto_root:
        interactive["prototype_project_root"] = config_proto_root
        interactive["prototype_project_root_source"] = "harness-runtime/config/harness.yaml:prototype.interactive_prototype.prototype_project_root"
        interactive["prototype_project_root_status"] = "resolved"
    else:
        interactive["prototype_project_root"] = ""
        interactive["prototype_project_root_source"] = None
        interactive["prototype_project_root_status"] = "unresolved"

    prototype["interactive_prototype"] = interactive
    return prototype


def detect_model_adapter(requested: str, adapters: dict[str, Any]) -> tuple[str, str]:
    if requested and requested != "auto":
        return requested, "configured"
    env_override = os.environ.get("HARNESS_MODEL_ADAPTER") or os.environ.get("HARNESS_ADAPTER")
    if env_override and env_override in adapters:
        return env_override, "environment_override"
    if any(os.environ.get(name) for name in ("CODEX_SHELL", "CODEX_THREAD_ID", "CODEX_CI")) and "codex" in adapters:
        return "codex", "environment"
    if any(name.startswith("CURSOR_") for name in os.environ) and "cursor" in adapters:
        return "cursor", "environment"
    if any(name.startswith("CLAUDE") for name in os.environ) and "claude" in adapters:
        return "claude", "environment"
    return requested or "auto", "unresolved"


def model_policy_defaults(model_routing: dict[str, Any], adapter_config: dict[str, Any], kind: str) -> dict[str, Any]:
    global_defaults = ((model_routing.get("defaults") or {}).get(kind) or {}) if isinstance(model_routing.get("defaults"), dict) else {}
    adapter_defaults = ((adapter_config.get("defaults") or {}).get(kind) or {}) if isinstance(adapter_config.get("defaults"), dict) else {}
    return {
        "candidates": as_str_list(adapter_defaults.get("candidates")) or as_str_list(global_defaults.get("candidates")),
        "fallback": adapter_defaults.get("fallback") or global_defaults.get("fallback") or None,
        "prefer_high_capability": bool(adapter_defaults.get("prefer_high_capability", global_defaults.get("prefer_high_capability", False))),
    }


def resolve_role_model_policy(
    role: str,
    kind: str,
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    roles = adapter_config.get("roles") if isinstance(adapter_config.get("roles"), dict) else {}
    role_config = roles.get(role) if isinstance(roles.get(role), dict) else {}
    inherited_kind = str(role_config.get("inherit") or kind)
    default_kind = inherited_kind if inherited_kind in model_defaults else kind
    default_policy = model_defaults.get(default_kind, model_defaults.get(kind, {}))
    candidates = as_str_list(role_config.get("candidates")) or list(default_policy.get("candidates") or [])
    return {
        "kind": kind,
        "source": "role" if as_str_list(role_config.get("candidates")) else f"default.{default_kind}",
        "inherit": inherited_kind if role_config.get("inherit") else "",
        "candidates": candidates,
        "fallback": role_config.get("fallback") or default_policy.get("fallback") or None,
    }


def add_role_model_policy(
    policies: dict[str, dict[str, Any]],
    role: str,
    kind: str,
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> None:
    if role and role not in policies:
        policies[role] = resolve_role_model_policy(role, kind, adapter_config, model_defaults)


def professional_role_model_policies(
    professional_roles: dict[str, Any],
    work_graph: dict[str, Any],
    adapter_config: dict[str, Any],
    model_defaults: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    policies: dict[str, dict[str, Any]] = {}
    adapter_roles = adapter_config.get("roles") if isinstance(adapter_config.get("roles"), dict) else {}
    for role, role_config in adapter_roles.items():
        if not isinstance(role_config, dict):
            continue
        inherited = str(role_config.get("inherit") or "")
        inferred_kind = "review" if inherited == "review" or str(role).endswith("reviewer") else "execution"
        add_role_model_policy(policies, str(role), inferred_kind, adapter_config, model_defaults)

    sources = []
    stage_policies = professional_roles.get("stage_policies") if isinstance(professional_roles.get("stage_policies"), dict) else {}
    sources.extend(stage_policies.values())
    lane_actions = work_graph.get("lane_actions") if isinstance(work_graph.get("lane_actions"), dict) else {}
    sources.extend(lane_actions.values())
    for source in sources:
        if not isinstance(source, dict):
            continue
        for role in as_str_list(source.get("required_execution_roles")):
            add_role_model_policy(policies, role, "execution", adapter_config, model_defaults)
        for role in as_str_list(source.get("required_review_roles")):
            add_role_model_policy(policies, role, "review", adapter_config, model_defaults)
        conditional_roles = source.get("conditional_roles") if isinstance(source.get("conditional_roles"), list) else []
        for item in conditional_roles:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or ("review" if str(item.get("role", "")).endswith("reviewer") else "execution"))
            add_role_model_policy(policies, str(item.get("role") or ""), kind, adapter_config, model_defaults)
    return dict(sorted(policies.items()))


def snapshot_execution_governance(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("execution_governance")
    if not isinstance(raw, dict):
        return {}
    aliases = autonomy_alias_map(config)
    snapshot = dict(raw)
    received = raw.get("default_level")
    canonical = normalize_autonomy_level(received, aliases)
    if canonical is not None:
        snapshot["default_level"] = canonical
        if isinstance(received, str) and received.strip() != canonical:
            snapshot["default_level_resolution"] = {
                "received": received.strip(),
                "canonical": canonical,
                "source": "legacy_alias",
            }
    return snapshot


def build_config_snapshot_payload(root: Path, config: dict[str, Any], model_routing: dict[str, Any]) -> dict[str, Any]:
    professional_roles = config.get("professional_roles") if isinstance(config.get("professional_roles"), dict) else {}
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    spec_config = config.get("spec") if isinstance(config.get("spec"), dict) else {}
    adapters = model_routing.get("adapters") if isinstance(model_routing, dict) else {}
    adapters = adapters if isinstance(adapters, dict) else {}
    requested_adapter = str(model_routing.get("current_adapter") or "auto") if isinstance(model_routing, dict) else "auto"
    adapter, adapter_resolution = detect_model_adapter(requested_adapter, adapters)
    adapter_config = adapters.get(adapter) if isinstance(adapters.get(adapter), dict) else {}
    model_defaults = {
        "execution": model_policy_defaults(model_routing, adapter_config, "execution"),
        "review": model_policy_defaults(model_routing, adapter_config, "review"),
    }
    role_model_policies = professional_role_model_policies(professional_roles, work_graph, adapter_config, model_defaults)
    execution_model_policy = {
        "adapter": adapter,
        "requested_adapter": requested_adapter,
        "adapter_resolution": adapter_resolution,
        "executor_tier": "standard",
        "candidates": model_defaults["execution"]["candidates"],
        "fallback": model_defaults["execution"]["fallback"],
    }
    # interaction 门级（行为图可达性）：内联归一化避免对 behavior_graph 反向依赖。
    # 与 behavior_graph.resolve_reachability_level 口径一致：fail|warn，非白名单回退 fail。
    interaction_cfg = config.get("interaction") if isinstance(config.get("interaction"), dict) else {}
    _reach = str(interaction_cfg.get("reachability_gate_level") or "").strip().lower()
    _reach = _reach if _reach in ("fail", "warn") else "fail"
    review_model_policy = {
        "adapter": adapter,
        "requested_adapter": requested_adapter,
        "adapter_resolution": adapter_resolution,
        "candidates": model_defaults["review"]["candidates"],
        "fallback": model_defaults["review"]["fallback"],
        "prefer_high_capability": model_defaults["review"]["prefer_high_capability"],
    }
    return {
        "status": "PASS",
        "control": "config.snapshot",
        "execute_mode": config.get("execute_mode", "sdd"),
        "project_name": config.get("project_name", ""),
        "default_mode": config.get("default_mode"),
        "brownfield": config.get("brownfield"),
        "pre_checkpoint_doc_review": config.get("pre_checkpoint_doc_review", True),
        "spec": {"enabled": bool(spec_config.get("enabled", False))},
        "interaction": {"reachability_gate_level": _reach},
        "escalation": config.get("escalation") if isinstance(config.get("escalation"), dict) else {},
        "dependency_impact": config.get("dependency_impact") if isinstance(config.get("dependency_impact"), dict) else {},
        "e2e": config.get("e2e") if isinstance(config.get("e2e"), dict) else {},
        "prototype": snapshot_prototype_config(root, config),
        "visual_interaction": config.get("visual_interaction") if isinstance(config.get("visual_interaction"), dict) else {},
        "agent_engineering": config.get("agent_engineering") if isinstance(config.get("agent_engineering"), dict) else {},
        "project_lint": config.get("project_lint") if isinstance(config.get("project_lint"), dict) else {},
        "project_knowledge": {
            "root": relpath(root, project_knowledge_root(root)),
            "exists": project_knowledge_root(root).exists(),
        },
        "execution_governance": snapshot_execution_governance(config),
        "professional_roles": {
            "enabled": professional_roles.get("enabled", True),
            "stage_policies": professional_roles.get("stage_policies") or {},
        },
        "work_graph": {
            "node_kinds": work_graph.get("node_kinds") or {},
            "lane_actions": work_graph.get("lane_actions") or {},
            "selection_strategy": work_graph.get("selection_strategy") or {},
            "stage_completion": work_graph.get("stage_completion") or {},
        },
        "execution_model_policy": execution_model_policy,
        "review_model_policy": review_model_policy,
        "model_routing": {
            "requested_adapter": requested_adapter,
            "adapter": adapter,
            "adapter_resolution": adapter_resolution,
            "defaults": model_defaults,
            "roles": role_model_policies,
            "fallback": model_routing.get("fallback") if isinstance(model_routing.get("fallback"), dict) else {},
        },
        "findings": [],
    }
