#!/usr/bin/env python3
"""Resolve Harness professional role policy for a stage.

The resolver is deterministic and only consumes local runtime config plus an
optional mission contract override. It is safe to run inside an installed target
project because all paths are relative to the target root.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - runtime guard
    raise SystemExit("PyYAML is required to resolve role policy") from exc

WORK_GRAPH_SCRIPTS = Path(__file__).resolve().parents[2] / "work-graph" / "scripts"
if str(WORK_GRAPH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(WORK_GRAPH_SCRIPTS))

from work_graph_lib import lane_action_registry_from_config, lane_action_snapshot, lane_stage_for_node  # noqa: E402


DEFAULT_STAGE_POLICIES: dict[str, dict[str, Any]] = {
    "intake": {
        "required_execution_roles": ["mission-framing-expert"],
        "required_review_roles": ["mission-contract-effectiveness-reviewer"],
    },
    "discovery": {
        "required_execution_roles": ["discovery-analyst"],
        "required_review_roles": ["discovery-effectiveness-reviewer"],
    },
    "prd": {
        "required_execution_roles": [
            "business-domain-modeler",
            "acceptance-scenario-designer",
            "product-scope-strategist",
            "senior-product-expert",
        ],
        "required_review_roles": ["product-definition-reviewer"],
    },
    "design": {
        "required_execution_roles": ["solution-architect", "tech-designer"],
        "required_review_roles": ["solution-effectiveness-reviewer", "technical-design-effectiveness-reviewer"],
        "conditional_roles": [
            {"role": "agent-capability-designer", "kind": "execution", "when": ["agent_engineering", "agent_capability"]},
            {"role": "agent-capability-reviewer", "kind": "review", "when": ["agent_engineering", "agent_capability"]},
            {"role": "interaction-designer", "kind": "execution", "when": ["frontend_ui", "user_journey"]},
            {"role": "interaction-reviewer", "kind": "review", "when": ["frontend_ui", "user_journey"]},
        ],
    },
    "dependency-impact": {
        "required_execution_roles": ["integration-impact-expert"],
        "required_review_roles": ["dependency-validity-reviewer"],
    },
    "breakdown": {
        "required_execution_roles": ["delivery-slicer", "test-planning-expert"],
        "required_review_roles": ["execution-plan-effectiveness-reviewer"],
    },
    "execute": {
        "required_execution_roles": ["execute-control-plane-executor"],
        "required_review_roles": ["spec-reviewer"],
        "role_carriers": {"execute-control-plane-executor": "skill"},
    },
    "code-review": {
        "required_execution_roles": ["review-control-plane-executor"],
        "required_review_roles": ["correctness-reviewer", "tdd-reviewer"],
        "role_carriers": {"review-control-plane-executor": "skill"},
    },
    "verify": {
        "required_execution_roles": ["verification-engineer"],
        "required_review_roles": ["verification-effectiveness-reviewer"],
    },
    "delivery": {
        "required_execution_roles": ["release-readiness-expert"],
        "required_review_roles": ["acceptance-package-reviewer"],
    },
}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def load_runtime_config(root: Path) -> dict[str, Any]:
    for path in (
        root / "harness-runtime" / "config" / "harness.yaml",
        root / "package" / "harness-runtime" / "config" / "harness.yaml",
    ):
        config = load_yaml(path)
        if config:
            return config
    return {}


def find_control_contract(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
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


def listify(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def merge_unique(base: list[str], override: list[str]) -> list[str]:
    result: list[str] = []
    for item in [*base, *override]:
        if item and item not in result:
            result.append(item)
    return result


def configured_policy(config: dict[str, Any], stage: str) -> dict[str, Any]:
    roles = config.get("professional_roles")
    if not isinstance(roles, dict):
        return {}
    policies = roles.get("stage_policies")
    if not isinstance(policies, dict):
        return {}
    policy = policies.get(stage)
    return policy if isinstance(policy, dict) else {}


def lane_action_policy(config: dict[str, Any], stage: str) -> dict[str, Any]:
    work_graph = config.get("work_graph") if isinstance(config.get("work_graph"), dict) else {}
    lanes = work_graph.get("lanes") if isinstance(work_graph.get("lanes"), dict) else {}
    for lane, lane_spec in lanes.items():
        for entry in lane_spec.get("stages", []) if isinstance(lane_spec, dict) else []:
            if isinstance(entry, dict) and entry.get("stage") == stage:
                _lane, _stage, action = lane_stage_for_node(config, {"id": "<role-policy>", "lane": str(lane), "stage": stage})
                snapshot = lane_action_snapshot(str(lane), action, "{mission_id}")
                return {
                    "work_graph_lane": str(lane),
                    "graph_operation": snapshot.get("graph_operation"),
                    "allowed_graph_operations": listify(snapshot.get("allowed_graph_operations")),
                    "output_artifact": snapshot.get("output_artifact"),
                    "carrier": snapshot.get("carrier"),
                    "skill": snapshot.get("skill"),
                    "required_execution_roles": listify(snapshot.get("required_execution_roles")),
                    "required_review_roles": listify(snapshot.get("required_review_roles")),
                    "conditional_roles": listify(action.get("conditional_roles")),
                    "role_carriers": snapshot.get("role_carriers") if isinstance(snapshot.get("role_carriers"), dict) else {},
                }

    lane_actions = lane_action_registry_from_config(config)
    for lane, action in lane_actions.items():
        if isinstance(action, dict) and action.get("stage") == stage:
            return {
                "work_graph_lane": str(lane),
                "graph_operation": action.get("graph_operation"),
                "allowed_graph_operations": listify(action.get("allowed_graph_operations")),
                "output_artifact": action.get("output_artifact"),
                "carrier": action.get("carrier"),
                "skill": action.get("skill"),
                "required_execution_roles": listify(action.get("required_execution_roles")),
                "required_review_roles": listify(action.get("required_review_roles")),
                "conditional_roles": listify(action.get("conditional_roles")),
                "role_carriers": action.get("role_carriers") if isinstance(action.get("role_carriers"), dict) else {},
            }
    return {}


def mission_override(contract: dict[str, Any], stage: str) -> dict[str, Any]:
    overrides = contract.get("role_policy_overrides") or contract.get("role_policy")
    if not isinstance(overrides, dict):
        return {}
    if overrides.get("stage") == stage:
        return overrides
    by_stage = overrides.get(stage)
    return by_stage if isinstance(by_stage, dict) else {}


def resolve_policy(
    stage: str,
    config: dict[str, Any] | None = None,
    mission_contract: dict[str, Any] | None = None,
    surfaces: list[str] | None = None,
) -> dict[str, Any]:
    surfaces = surfaces or []
    base = DEFAULT_STAGE_POLICIES.get(stage, {})
    configured = configured_policy(config or {}, stage)
    override = mission_override(mission_contract or {}, stage)
    registry_action = lane_action_policy(config or {}, stage)
    override_action = override if registry_action and override else {}
    action_sources = [registry_action, override_action]
    action_scoped = any(action_sources)
    policy_sources = action_sources if action_scoped else [base, configured, override]

    required_execution_roles: list[str] = []
    required_review_roles: list[str] = []
    for source in policy_sources:
        required_execution_roles = merge_unique(required_execution_roles, listify(source.get("required_execution_roles")))
        required_review_roles = merge_unique(required_review_roles, listify(source.get("required_review_roles")))

    conditional_candidates: list[Any] = []
    for source in policy_sources:
        conditional_candidates.extend(listify(source.get("conditional_roles")))
    conditional_roles: list[dict[str, Any]] = []
    for item in conditional_candidates:
        if not isinstance(item, dict) or not item.get("role"):
            continue
        triggers = [str(value) for value in listify(item.get("when"))]
        matched = sorted(set(triggers) & set(surfaces))
        if matched:
            conditional_roles.append(
                {
                    "role": item["role"],
                    "kind": item.get("kind", "execution"),
                    "reason": ",".join(matched),
                    "carrier": item.get("carrier", "agent"),
                }
            )
        elif item.get("skip_reason"):
            conditional_roles.append(
                {
                    "role": item["role"],
                    "kind": item.get("kind", "execution"),
                    "skip_reason": item["skip_reason"],
                    "carrier": item.get("carrier", "agent"),
                }
            )

    carrier_sources = [base, configured, *action_sources, override]
    role_carriers = {}
    for source in carrier_sources:
        if isinstance(source.get("role_carriers"), dict):
            role_carriers.update(source["role_carriers"])
    identity_source = registry_action if registry_action else override_action
    work_graph_lane = identity_source.get("work_graph_lane")
    graph_operation = identity_source.get("graph_operation")
    allowed_graph_operations = identity_source.get("allowed_graph_operations") or []
    output_artifact = identity_source.get("output_artifact")
    carrier = identity_source.get("carrier")
    skill = identity_source.get("skill")

    return {
        "stage": stage,
        "policy_scope": "work_graph_stage" if action_scoped else "stage",
        "work_graph_lane": work_graph_lane,
        "graph_operation": graph_operation,
        "allowed_graph_operations": allowed_graph_operations,
        "output_artifact": output_artifact,
        "carrier": carrier,
        "skill": skill,
        "required_execution_roles": required_execution_roles,
        "required_review_roles": required_review_roles,
        "conditional_roles": conditional_roles,
        "role_carriers": role_carriers,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--mission-contract", help="Mission contract YAML path, or markdown path with Contract reference")
    parser.add_argument("--surface", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    config = load_runtime_config(root)
    mission_contract = find_control_contract(root / args.mission_contract) if args.mission_contract else {}
    result = resolve_policy(args.stage, config=config, mission_contract=mission_contract, surfaces=args.surface)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text if args.json else yaml.safe_dump(result, sort_keys=False, allow_unicode=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
