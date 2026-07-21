from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from harness_cli_core.app.output import finding, status_from_findings
from harness_cli_core.domain.control_state import as_str_list
from harness_cli_core.domain.collections import unique
from harness_cli_core.domain.manifest import load_manifest, replace_template_values
from harness_cli_core.infra.runtime_paths import relpath


CONTRACT_PLACEHOLDER_RE = re.compile(r"(\{\{.*?\}\}|<[^>]+>)")


def contract_leaf_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        items: list[Any] = []
        for nested in value.values():
            items.extend(contract_leaf_values(nested))
        return items
    if isinstance(value, list):
        items = []
        for nested in value:
            items.extend(contract_leaf_values(nested))
        return items
    return [value]


def contract_contains_placeholder(value: Any) -> bool:
    return any(isinstance(item, str) and CONTRACT_PLACEHOLDER_RE.search(item) for item in contract_leaf_values(value))


def template_prefilled_role_verdict(verdict: dict[str, Any]) -> bool:
    return str(verdict.get("verdict") or "") == "PASS" and contract_contains_placeholder(verdict)


def scrub_template_role_verdicts(contract: dict[str, Any], *, template_mode: bool = False) -> bool:
    verdicts = contract.get("role_verdicts")
    if not isinstance(verdicts, list):
        return False
    cleaned = [
        item for item in verdicts
        if not (
            isinstance(item, dict)
            and (template_prefilled_role_verdict(item) or (template_mode and str(item.get("verdict") or "") == "PASS"))
        )
    ]
    if cleaned == verdicts:
        return False
    contract["role_verdicts"] = cleaned
    return True


def contract_governance_conflict(contract: dict[str, Any]) -> bool:
    policy = contract.get("stage_participation_policy") if isinstance(contract.get("stage_participation_policy"), dict) else {}
    obligations = contract.get("entered_stage_obligations") if isinstance(contract.get("entered_stage_obligations"), dict) else {}
    policy_reviews = set(as_str_list(policy.get("required_review_roles")))
    obligation_reviews = set(as_str_list(obligations.get("review_roles")))
    return bool(policy_reviews and obligation_reviews and policy_reviews != obligation_reviews)


def contract_hygiene_payload(contract: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if contract_contains_placeholder(contract):
        findings.append(finding("FAIL", "placeholder_in_runtime_artifact", "Contract still contains unresolved template placeholders", source="contract_hygiene"))
        findings.append(finding("WARN", "manual_patch_required", "Materialized contract requires explicit patch/fill before it can pass hygiene", source="contract_hygiene"))
    if any(isinstance(item, dict) and template_prefilled_role_verdict(item) for item in contract.get("role_verdicts") or []):
        findings.append(finding("FAIL", "prefilled_role_verdict", "Template-time role_verdicts must not prefill reviewer PASS", source="contract_hygiene"))
    if contract_governance_conflict(contract):
        findings.append(finding("FAIL", "governance_conflict", "stage_participation_policy conflicts with entered_stage_obligations", source="contract_hygiene"))
    return {"status": status_from_findings(findings), "findings": findings}


def contract_template_path(root: Path, template: str, *, package_root: Path) -> Path:
    name = template if template.endswith((".yaml", ".yml")) else f"{template}.contract.yaml"
    for base in (
        root / "harness-runtime" / "templates" / "contracts",
        package_root / "harness-runtime" / "templates" / "contracts",
    ):
        path = base / name
        if path.exists():
            return path
    return package_root / "harness-runtime" / "templates" / "contracts" / name


def control_contract_document(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    document = load_manifest(path)
    contract = document.get("control_contract")
    if not isinstance(contract, dict):
        contract = {}
        document["control_contract"] = contract
    return document, contract


def load_control_contract_or_empty(path: Path) -> dict[str, Any]:
    """Like :func:`load_control_contract` but returns ``{}`` instead of ``None``
    when the file is missing / invalid. Convenient for callers that always
    iterate over the result and want a falsy-but-iterable default.
    """
    if not path.exists():
        return {}
    try:
        import yaml
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(doc, dict):
        return {}
    cc = doc.get("control_contract")
    return cc if isinstance(cc, dict) else doc


def load_control_contract(path: Path) -> dict[str, Any] | None:
    """Load a control_contract block, returning ``None`` when the file is
    missing, invalid YAML, or otherwise unusable.

    Differs from :func:`control_contract_document` in that it never creates a
    fresh empty contract — callers want to know whether a real contract
    exists. Used by delivery and finishing-branch handlers.
    """
    if not path.exists():
        return None
    try:
        import yaml  # local import to keep the dependency surface small
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — surface any load failure as "not loadable"
        return None
    if not isinstance(doc, dict):
        return None
    block = doc.get("control_contract")
    return block if isinstance(block, dict) else doc


def build_contract_init_document(
    document: dict[str, Any],
    *,
    mission_id: str,
    stage: str,
    node_id: str | None = None,
    artifact_version: str = "v1",
    review_strategy: str | None = None,
    capability: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    replacements = {
        "mission_id": mission_id,
        "work_graph_node_id": node_id or "",
        "primary_work_graph_node": node_id or "",
        "artifact_version": artifact_version,
        "review_strategy": review_strategy or "",
        "capability_id": capability or "",
        "capability_name": capability or "",
    }
    materialized = replace_template_values(document, replacements)
    contract = materialized.get("control_contract") if isinstance(materialized.get("control_contract"), dict) else {}
    contract["mission_id"] = mission_id
    contract["stage"] = stage
    applied_fields = ["mission_id", "stage"]
    if node_id and isinstance(contract.get("work_graph_artifact"), dict):
        contract["work_graph_artifact"]["node_id"] = node_id
        contract["work_graph_artifact"]["artifact_version"] = artifact_version
        applied_fields.extend(["work_graph_artifact.node_id", "work_graph_artifact.artifact_version"])
    if scrub_template_role_verdicts(contract, template_mode=True):
        applied_fields.append("role_verdicts")
    return materialized, contract, unique(applied_fields)


def normalize_id(value: Any, prefix: str, index: int, existing: set[str]) -> str:
    raw = str(value or "").strip()
    if raw:
        existing.add(raw)
        return raw
    seq = index
    while True:
        candidate = f"{prefix}-{seq:02d}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
        seq += 1


def normalise_story_context(story: dict[str, Any]) -> dict[str, Any]:
    context = story.get("story_context")
    if isinstance(context, dict):
        result = dict(context)
    else:
        result = {}

    for key in ("user", "problem", "scenario", "value"):
        value = result.get(key)
        if value in (None, "") and story.get(key) not in (None, ""):
            result[key] = story.get(key)

    if result.get("user") in (None, "") and story.get("role") not in (None, ""):
        result["user"] = story.get("role")
    if result.get("value") in (None, "") and story.get("value") not in (None, ""):
        result["value"] = story.get("value")

    metrics = result.get("success_metrics")
    if not metrics:
        metrics = story.get("success_metrics")
    if not metrics and story.get("success_metric"):
        metrics = [{"id": "SM-01", "signal": story.get("success_metric"), "target": "observable"}]
    if metrics:
        result["success_metrics"] = metrics

    return result


def intent_framing_to_contract(framing: dict[str, Any]) -> dict[str, Any]:
    contract_fields: dict[str, Any] = {}

    objective = framing.get("objective")
    if isinstance(objective, dict):
        statement = objective.get("statement")
        if statement:
            contract_fields["objective"] = {
                "id": str(objective.get("id") or "OBJ-001"),
                "statement": str(statement),
            }
    elif isinstance(objective, str) and objective.strip():
        contract_fields["objective"] = {"id": "OBJ-001", "statement": objective.strip()}

    user_stories = framing.get("user_stories")
    if isinstance(user_stories, list):
        seen: set[str] = set()
        normalised: list[dict[str, Any]] = []
        for index, story in enumerate(user_stories, start=1):
            if not isinstance(story, dict):
                continue
            entry: dict[str, Any] = {
                "id": normalize_id(story.get("id"), "US", index, seen),
                "role": str(story.get("role") or ""),
                "goal": str(story.get("goal") or ""),
                "value": str(story.get("value") or ""),
            }
            story_context = normalise_story_context(story)
            if story_context:
                entry["story_context"] = story_context
            acceptance_refs = story.get("acceptance_refs") or story.get("traces_to", {}).get("ac") if isinstance(story.get("traces_to"), dict) else story.get("acceptance_refs")
            if isinstance(acceptance_refs, list) and acceptance_refs:
                entry["traces_to"] = {"ac": [str(ref) for ref in acceptance_refs if str(ref).strip()]}
            normalised.append(entry)
        if normalised:
            contract_fields["user_stories"] = normalised

    scope = framing.get("scope")
    if isinstance(scope, dict):
        scope_block: dict[str, Any] = {}
        seen_in: set[str] = set()
        in_items: list[dict[str, Any]] = []
        for index, item in enumerate(scope.get("in") or [], start=1):
            if isinstance(item, str):
                item = {"statement": item}
            if not isinstance(item, dict):
                continue
            statement = item.get("statement")
            if not statement:
                continue
            in_items.append({
                "id": normalize_id(item.get("id"), "SCOPE-IN", index, seen_in),
                "statement": str(statement),
            })
        if in_items:
            scope_block["in"] = in_items
        seen_out: set[str] = set()
        out_items: list[dict[str, Any]] = []
        for index, item in enumerate(scope.get("out") or [], start=1):
            if not isinstance(item, dict):
                continue
            statement = item.get("statement")
            reason = item.get("reason")
            if not statement or not reason:
                continue
            out_items.append({
                "id": normalize_id(item.get("id"), "SCOPE-OUT", index, seen_out),
                "statement": str(statement),
                "reason": str(reason),
            })
        if out_items:
            scope_block["out"] = out_items
        if scope_block:
            contract_fields["scope"] = scope_block

    acs = framing.get("acceptance_scenarios")
    if isinstance(acs, list):
        seen_acceptance: set[str] = set()
        normalised_acs: list[dict[str, Any]] = []
        for index, ac in enumerate(acs, start=1):
            if not isinstance(ac, dict):
                continue
            entry = {
                "id": normalize_id(ac.get("id"), "SCN", index, seen_acceptance),
                "statement": str(ac.get("statement") or ""),
            }
            if ac.get("given") or ac.get("when") or ac.get("then"):
                entry["given"] = str(ac.get("given") or "")
                entry["when"] = str(ac.get("when") or "")
                entry["then"] = str(ac.get("then") or "")
            if ac.get("verification_method"):
                entry["verification_method"] = str(ac.get("verification_method"))
            entry["verification_required"] = bool(ac.get("verification_required", True))
            normalised_acs.append(entry)
        if normalised_acs:
            contract_fields["acceptance_scenarios"] = normalised_acs

    autonomy_level = framing.get("autonomy_level")
    autonomy_block: dict[str, Any] = {}
    if isinstance(autonomy_level, str) and autonomy_level.strip():
        autonomy_block["level"] = autonomy_level.strip()
    governance_risk = framing.get("governance_risk")
    if isinstance(governance_risk, str) and governance_risk.strip():
        autonomy_block["governance_risk"] = governance_risk.strip()
    governance_assessment = framing.get("governance_assessment")
    if isinstance(governance_assessment, dict):
        autonomy_block["governance_assessment"] = governance_assessment
    for key in ("skippable_stages", "reviewer_pass_sufficient", "human_checkpoints", "escalation_triggers"):
        if key in framing and isinstance(framing[key], list):
            autonomy_block[key] = list(framing[key])
    if "required_checkpoints" in framing and isinstance(framing["required_checkpoints"], list):
        autonomy_block["human_checkpoints"] = list(framing["required_checkpoints"])
    if autonomy_block:
        autonomy_block.setdefault("governance_risk", "")
        autonomy_block.setdefault("governance_assessment", {
            "hard_triggers": [],
            "dimensions": {},
            "scale_signals": {},
            "decision_rule": "",
            "user_confirmation_required": True,
            "downgrade_or_checkpoint_removal_requires_approval": True,
        })
        contract_fields["autonomy"] = autonomy_block

    work_graph = framing.get("work_graph")
    if isinstance(work_graph, dict):
        wg_block: dict[str, Any] = {}
        for key in ("primary_nodes", "related_nodes"):
            if key in work_graph and isinstance(work_graph[key], list):
                wg_block[key] = list(work_graph[key])
        for key in ("operation", "from_lane", "to_lane", "board"):
            if work_graph.get(key):
                wg_block[key] = str(work_graph[key])
        if wg_block:
            contract_fields["work_graph"] = wg_block

    role_policy = framing.get("role_policy")
    if isinstance(role_policy, dict):
        contract_fields["role_policy"] = role_policy

    reserved = {
        "objective", "user_stories", "scope", "acceptance_scenarios",
        "autonomy_level", "skippable_stages", "reviewer_pass_sufficient",
        "human_checkpoints", "escalation_triggers", "required_checkpoints",
        "governance_risk", "governance_assessment", "work_graph", "role_policy",
    }
    for key, value in framing.items():
        if key not in reserved and key not in contract_fields:
            contract_fields[key] = value

    return contract_fields


def apply_intent_framing(contract: dict[str, Any], framing: dict[str, Any]) -> list[str]:
    fields = intent_framing_to_contract(framing)
    applied: list[str] = []
    for key, value in fields.items():
        if isinstance(value, dict) and isinstance(contract.get(key), dict):
            contract[key].update(value)
        else:
            contract[key] = value
        applied.append(key)
    if scrub_template_role_verdicts(contract):
        applied.append("role_verdicts")
    return unique(applied)


def set_path_value(document: dict[str, Any], target: str, value: Any, op: str) -> None:
    parts = [part for part in target.split(".") if part]
    if not parts:
        raise ValueError("patch target is required")
    current: Any = document
    for part in parts[:-1]:
        if not isinstance(current, dict):
            raise ValueError(f"patch target parent is not an object: {target}")
        current = current.setdefault(part, {})
    if not isinstance(current, dict):
        raise ValueError(f"patch target parent is not an object: {target}")
    leaf = parts[-1]
    if op == "set":
        current[leaf] = value
    elif op == "merge":
        existing = current.get(leaf)
        if not isinstance(existing, dict) or not isinstance(value, dict):
            raise ValueError("merge requires existing value and patch value to be objects")
        existing.update(value)
    elif op == "append":
        existing = current.setdefault(leaf, [])
        if not isinstance(existing, list):
            raise ValueError("append target must be a list")
        existing.append(value)
    else:
        raise ValueError(f"unsupported patch op: {op}")


def upsert_by_id(items: list[dict[str, Any]], item: dict[str, Any]) -> str:
    item_id = str(item.get("id") or "")
    if item_id:
        for index, existing in enumerate(items):
            if str(existing.get("id") or "") == item_id:
                items[index] = item
                return "replaced"
    items.append(item)
    return "appended"


def apply_contract_patch(
    document: dict[str, Any],
    *,
    add_round: bool = False,
    last_verdict: str | None = None,
    patch_doc: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    applied: list[dict[str, str]] = []
    if add_round:
        contract = document.setdefault("control_contract", {})
        if not isinstance(contract, dict):
            raise ValueError("control_contract is not an object")
        review_block = contract.setdefault("effectiveness_review", {})
        if not isinstance(review_block, dict):
            raise ValueError("control_contract.effectiveness_review is not an object")
        current = review_block.get("rounds_used")
        current_int = int(current) if isinstance(current, (int, float)) else 0
        review_block["rounds_used"] = current_int + 1
        applied.append({"target": "control_contract.effectiveness_review.rounds_used", "op": "increment"})
        if isinstance(last_verdict, str) and last_verdict.strip():
            review_block["last_verdict"] = last_verdict.strip()
            applied.append({"target": "control_contract.effectiveness_review.last_verdict", "op": "set"})

    if patch_doc is not None:
        has_control_contract = isinstance(document.get("control_contract"), dict)
        patches = patch_doc.get("patches") if isinstance(patch_doc.get("patches"), list) else [patch_doc]
        for patch in patches:
            if not isinstance(patch, dict):
                raise ValueError("patch entries must be objects")
            target = str(patch.get("target") or "")
            if not target:
                raise ValueError("patch target is required")
            if has_control_contract and not target.startswith("control_contract."):
                raise ValueError(f"patch target must be under control_contract: {target}")
            op = str(patch.get("op") or "set")
            set_path_value(document, target, patch.get("value"), op)
            applied.append({"target": target, "op": op})
    return applied


REVIEWER_ROLE_SUFFIXES = ("-reviewer", "-effectiveness-reviewer")
DISPATCH_REQUIRED_FIELDS = (
    "subagent_id",
    "model",
    "execution_mode",
    "started_at",
    "completed_at",
)
DISPATCH_EXECUTION_MODES = {"spawn_agent", "main_agent_fallback", "sequential"}


def is_reviewer_role(role: str) -> bool:
    if not isinstance(role, str):
        return False
    return any(role.endswith(suffix) for suffix in REVIEWER_ROLE_SUFFIXES)


# 横切 gap category SSOT（加性、开放枚举）：
# 这三类是跨阶段通用、机器可识别的 blocking_gap 类别，供后续 gate / 路由消费。
# 注意：这是“开放枚举”——阶段特有 category（如 lost_business_object /
# coverage_gap / insufficient_input / missing_invariant 等几十种自由字符串）
# 不在此集合内，且不应被任何校验拒绝。新增横切类别时只在此处扩展。
CROSSCUTTING_GAP_CATEGORIES = {
    "reasoning_chain_open",
    "internal_contradiction",
    "needs_user_clarification",
}

# 语义分组：可由产出者自行修复 → 回产出者重做。
PRODUCER_FIXABLE_GAP_CATEGORIES = {
    "reasoning_chain_open",
    "internal_contradiction",
}

# 语义分组：需要用户澄清 / 决策门，不能由产出者闭环。
USER_CLARIFICATION_GAP_CATEGORIES = {
    "needs_user_clarification",
}


def classify_gap_category(category: str) -> str:
    """将 blocking_gap 的 category 归类为消费侧可路由的语义桶。

    返回值：
    - "producer_fixable"：横切且可由产出者重做修复。
    - "needs_user_clarification"：横切且需要走澄清 / 决策门。
    - "stage_specific"：阶段特有或未知 category（兜底，永不报错）。

    这是开放枚举语义：任何不在横切 SSOT 内的字符串都归为 stage_specific，
    既不报错也不误分类，保证既有阶段特有 category 继续自由使用。
    """
    if category in PRODUCER_FIXABLE_GAP_CATEGORIES:
        return "producer_fixable"
    if category in USER_CLARIFICATION_GAP_CATEGORIES:
        return "needs_user_clarification"
    return "stage_specific"


# verify gate 纳入 reviewer role_verdict 的开放 verdict 集合。
REVIEWER_OPEN_VERDICTS = {"HOLD", "BLOCKED"}


def evaluate_reviewer_verdicts_for_gate(
    contract: dict[str, Any] | None,
    *,
    has_tradeoff_approval: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """纯函数：从 verify contract 的 role_verdicts 计算 gate 信号。

    规则：
    - 只看 reviewer-class 角色（is_reviewer_role）。
    - 同一角色取列表中最后出现的 verdict 作为最新结论。
    - 最新 verdict ∈ {HOLD, BLOCKED} 时：
        * 若 mission 已有 tradeoff/risk approval（has_tradeoff_approval=True），
          降级为 warning（不阻断 gate）。
        * 否则产出 failed_check，使 gate status != PASS。
    - PASS / PASS_WITH_RISK 等不产出任何信号。

    非破坏：contract 为 None、缺 role_verdicts、role_verdicts 非 list、
    或没有任何 reviewer verdict 时，返回空结果，调用方原有 PASS 不受影响。

    返回 {"failed_checks": [...], "warnings": [...]}，
    failed_check 结构对齐 verify gate 标准：
    {"check", "code", "role", "verdict", "message"}。
    """
    failed_checks: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not isinstance(contract, dict):
        return {"failed_checks": failed_checks, "warnings": warnings}
    raw = contract.get("role_verdicts")
    if not isinstance(raw, list):
        return {"failed_checks": failed_checks, "warnings": warnings}

    # 取每个 reviewer 角色的最新 verdict（按列表顺序后者覆盖前者）。
    latest_by_role: dict[str, dict[str, Any]] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        if not is_reviewer_role(role):
            continue
        latest_by_role[role] = entry

    for role, entry in latest_by_role.items():
        verdict = entry.get("verdict")
        if verdict not in REVIEWER_OPEN_VERDICTS:
            continue
        if has_tradeoff_approval:
            warnings.append(
                {
                    "check": "reviewer_verdict_open",
                    "code": "REVIEWER_VERDICT_HOLD",
                    "role": role,
                    "verdict": verdict,
                    "message": (
                        f"reviewer 角色 {role!r} 最新 verdict={verdict}，"
                        "但 mission 已有 tradeoff/risk approval，降级为 warning"
                    ),
                }
            )
            continue
        failed_checks.append(
            {
                "check": "reviewer_verdict_open",
                "code": "REVIEWER_VERDICT_HOLD",
                "role": role,
                "verdict": verdict,
                "message": (
                    f"reviewer 角色 {role!r} 最新 verdict={verdict}，"
                    "gate 不能 PASS；需修复后重审，或登记 tradeoff approval 豁免"
                ),
            }
        )
    return {"failed_checks": failed_checks, "warnings": warnings}


# 标准阶段顺序 SSOT：用于比较两个 upstream_stage 谁“更靠前”。
# 越靠前 index 越小；自动回退选择最靠上游（index 最小）的阶段，
# 这样一次回退就能覆盖所有下游缺口的根因。未知阶段名排在已知阶段之后
# （给一个大 index），即不会误判为“最靠前”。
STANDARD_STAGE_ORDER = (
    "intake",
    "prd",
    "solution",
    "technical_analysis",
    "interaction",
    "breakdown",
    "execute",
    "verify",
    "delivery",
)


def _stage_order_index(stage: str) -> int:
    """返回阶段在标准序中的下标；未知阶段排在已知阶段之后（稳定兜底）。"""
    try:
        return STANDARD_STAGE_ORDER.index(stage)
    except ValueError:
        return len(STANDARD_STAGE_ORDER)


def reviewer_upstream_rollback_signal(
    contract: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """纯函数：从 reviewer 最新 verdict 的 blocking_gaps 中提取“上游归因回退信号”。

    设计意图：当某阶段 reviewer 判定完备性缺口的根因在【前序某阶段】时，
    会在 blocking_gap object 上标 ``gap_root=upstream`` + ``upstream_stage=<阶段名>``。
    控制面消费此信号即可自动回退到该前序阶段重推。

    扫描规则（与 evaluate_reviewer_verdicts_for_gate 一致的最新口径）：
    - 只看 reviewer-class 角色（is_reviewer_role），按列表顺序取每角色最新 verdict。
    - 只看最新 verdict ∈ {HOLD, BLOCKED} 的 blocking_gaps（PASS / PASS_WITH_RISK 不触发回退）。
    - blocking_gap item 为 object 且 ``gap_root == "upstream"`` 且 ``upstream_stage`` 非空时计入。
      string item、缺 gap_root（缺省视为 self）、gap_root=self 一律不计入——非破坏。

    返回值：
    - 存在至少一个有效 upstream 信号时返回
      ``{"target_stage": <最靠上游的 upstream_stage>,
         "source_role": <提供该最靠前阶段信号的 reviewer 角色>,
         "gap_ids": [<所有命中 upstream 信号的 gap 标识/描述>]}``。
      多个 upstream_stage 时取标准阶段序中最靠前（index 最小）的那个作为 target_stage。
    - 无任何有效 upstream 信号时返回 None（调用方据此保持原有行为，绝不回退）。
    """
    if not isinstance(contract, dict):
        return None
    raw = contract.get("role_verdicts")
    if not isinstance(raw, list):
        return None

    # 取每个 reviewer 角色的最新 verdict（后者覆盖前者）。
    latest_by_role: dict[str, dict[str, Any]] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        if not is_reviewer_role(role):
            continue
        latest_by_role[role] = entry

    # 收集所有命中的 upstream 信号：(stage_index, stage, role, gap_id)。
    hits: list[tuple[int, str, str, str]] = []
    for role, entry in latest_by_role.items():
        if entry.get("verdict") not in REVIEWER_OPEN_VERDICTS:
            continue
        gaps = entry.get("blocking_gaps")
        if not isinstance(gaps, list):
            continue
        for gap in gaps:
            if not isinstance(gap, dict):
                # 旧扁平 string 写法不携带 gap_root，视为 self，不触发回退。
                continue
            if str(gap.get("gap_root") or "self") != "upstream":
                continue
            upstream_stage = str(gap.get("upstream_stage") or "")
            if not upstream_stage:
                continue
            gap_id = str(
                gap.get("id")
                or gap.get("gap_id")
                or gap.get("description")
                or gap.get("summary")
                or gap.get("category")
                or upstream_stage
            )
            hits.append((_stage_order_index(upstream_stage), upstream_stage, str(role), gap_id))

    if not hits:
        return None

    # target_stage = 最靠上游（index 最小）的 upstream_stage。
    target_index, target_stage, _, _ = min(hits, key=lambda item: item[0])
    # source_role 取贡献了该 target_stage 信号的角色（稳定：取第一个命中的）。
    source_role = next(role for index, _, role, _ in hits if index == target_index)
    gap_ids = [gap_id for _, _, _, gap_id in hits]
    return {
        "target_stage": target_stage,
        "source_role": source_role,
        "gap_ids": gap_ids,
    }


def _gap_clarification_text(gap: dict[str, Any]) -> str:
    """从 gap object 提取最适合呈现给用户的澄清问题文本（稳定兜底）。"""
    return str(
        gap.get("question")
        or gap.get("detail")
        or gap.get("description")
        or gap.get("summary")
        or gap.get("id")
        or gap.get("gap_id")
        or gap.get("category")
        or "需用户澄清的信息缺口"
    )


def reviewer_clarification_signal(
    contract: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """纯函数：从 reviewer 最新 verdict 的 blocking_gaps 中汇总"需用户澄清"批次。

    设计意图：当缺口根因是"输入类材料从未提供该事实"（``gap_root=clarification``，
    或旧写法 ``category=needs_user_clarification``），任何 agent 重导都补不出，
    必须由人澄清。控制面消费此信号，把分散在多个 reviewer / 多条 gap 的澄清需求
    "汇总打包"成一个批次一次性问人（避免零散打扰），人答复后沉淀回文档集
    （``materials/clarifications/``）成为完备性基线的一类输入。

    与 ``reviewer_upstream_rollback_signal`` 正交：
    - upstream  → 根因在前序 agent 阶段，控制面自动回退重导（reset_mission_stage）。
    - clarification → 根因是人从未提供的事实，控制面暂停到澄清 Decision Gate 问人。
    二者同时存在时，调用方应**先问人**（信息缺口是回退的前提）。

    扫描规则（与 ``reviewer_upstream_rollback_signal`` 一致的最新口径）：
    - 只看 reviewer-class 角色（is_reviewer_role），按列表顺序取每角色最新 verdict。
    - 只看最新 verdict ∈ {HOLD, BLOCKED} 的 blocking_gaps。
    - blocking_gap item 为 object 且满足任一即计入：
        * ``gap_root == "clarification"``（现代写法，权威）
        * ``category == "needs_user_clarification"``（旧写法，向后兼容）
      string item、其它 gap_root 一律不计入——非破坏。

    返回值：
    - 存在至少一个澄清需求时返回
      ``{"clarification_items": [{"role", "gap_id", "question"}, ...],
         "roles": [<去重的贡献角色，稳定有序>]}``。
    - 无澄清需求时返回 None（调用方据此保持原有行为，绝不暂停）。
    """
    if not isinstance(contract, dict):
        return None
    raw = contract.get("role_verdicts")
    if not isinstance(raw, list):
        return None

    # 取每个 reviewer 角色的最新 verdict（后者覆盖前者）。
    latest_by_role: dict[str, dict[str, Any]] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        if not is_reviewer_role(role):
            continue
        latest_by_role[role] = entry

    items: list[dict[str, str]] = []
    roles: list[str] = []
    for role, entry in latest_by_role.items():
        if entry.get("verdict") not in REVIEWER_OPEN_VERDICTS:
            continue
        gaps = entry.get("blocking_gaps")
        if not isinstance(gaps, list):
            continue
        role_hit = False
        for gap in gaps:
            if not isinstance(gap, dict):
                # 旧扁平 string 写法不携带归因，视为 self，不触发澄清。
                continue
            gap_root = str(gap.get("gap_root") or "self")
            category = str(gap.get("category") or "")
            if gap_root != "clarification" and category != "needs_user_clarification":
                continue
            gap_id = str(
                gap.get("id")
                or gap.get("gap_id")
                or gap.get("category")
                or "clarification"
            )
            items.append(
                {
                    "role": str(role),
                    "gap_id": gap_id,
                    "question": _gap_clarification_text(gap),
                }
            )
            role_hit = True
        if role_hit:
            roles.append(str(role))

    if not items:
        return None
    return {"clarification_items": items, "roles": roles}


# ── 改造④：有界反驳-仲裁协议 ───────────────────────────────────────────────────
# 默认反驳轮次上限（对齐 Capio 5.7"三轮是上限非必经"，这里取 2 轮 dispute 后升级）。
DEFAULT_DISPUTE_MAX_ROUNDS = 2


def dispute_has_evidence(dispute: dict[str, Any]) -> bool:
    """反驳是否带文档集内证据引用。

    空 evidence_refs = 无效反驳：worker 不能空口拒改，必须引用测试 / 代码 / ID /
    命令输出等文档集内证据。无效反驳不享受"暂不修复"，应转回修复循环。
    """
    refs = dispute.get("evidence_refs")
    if not isinstance(refs, list):
        return False
    return any(str(r).strip() for r in refs)


def _contract_disputes(contract: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(contract, dict):
        return []
    er = contract.get("effectiveness_review")
    if not isinstance(er, dict):
        return []
    disputes = er.get("disputes")
    return [d for d in disputes if isinstance(d, dict)] if isinstance(disputes, list) else []


def dispute_escalation_signal(
    contract: dict[str, Any] | None,
    *,
    max_rounds: int = DEFAULT_DISPUTE_MAX_ROUNDS,
) -> dict[str, Any] | None:
    """纯函数：汇总需升级 Decision Gate 仲裁的反驳。

    设计意图（改造④）：reviewer HOLD 后，worker 可二选一——接受走修复循环，或**带证据反驳**
    （记 dispute）。reviewer 收到反驳后撤 gap（status=withdrawn_by_reviewer）或补论证（round+1）。
    有界 ``max_rounds`` 轮仍不一致（status=open 且 round >= max_rounds）→ 升级用户仲裁。
    这避免 worker 盲目服从一个可能判错的 reviewer 而反复修没坏的东西。

    计入升级的条件（全部满足）：
    - dispute 为 object 且 status 为 ``open``（withdrawn / conceded / 已 escalated 不再计）；
    - ``dispute_has_evidence`` 为真（无证据的空口反驳不享受升级，应转回修复循环）；
    - ``round >= max_rounds``。

    返回 ``{"disputes": [{gap_id, role, round, worker_rebuttal}...]}``，无则 None（非破坏）。
    """
    hits: list[dict[str, Any]] = []
    for d in _contract_disputes(contract):
        if str(d.get("status") or "open") != "open":
            continue
        if not dispute_has_evidence(d):
            continue
        try:
            rnd = int(d.get("round") or 0)
        except (TypeError, ValueError):
            rnd = 0
        if rnd < max_rounds:
            continue
        hits.append(
            {
                "gap_id": str(d.get("gap_id") or ""),
                "role": str(d.get("role") or ""),
                "round": rnd,
                "worker_rebuttal": str(d.get("worker_rebuttal") or ""),
            }
        )
    if not hits:
        return None
    return {"disputes": hits}


def mission_has_tradeoff_approval(root: Path, mission: str | None) -> bool:
    """读取 approvals.json，判断 mission 是否已有 approved 的 tradeoff/risk 豁免。

    与 effectiveness rounds overflow 的豁免思路一致。
    缺文件 / 解析失败 / 缺 mission 时一律返回 False（不阻断、不报错）。
    """
    if not isinstance(mission, str) or not mission:
        return False
    approvals_path = root / "harness-runtime" / "harness" / "state" / "approvals.json"
    if not approvals_path.exists():
        return False
    try:
        data = json.loads(approvals_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    entries = data.get("approvals") if isinstance(data, dict) else data
    if not isinstance(entries, list):
        return False
    for entry in entries:
        if (
            isinstance(entry, dict)
            and entry.get("mission_id") == mission
            and entry.get("type") in {"tradeoff", "risk"}
            and entry.get("status") == "approved"
        ):
            return True
    return False


def validate_role_verdict_dispatch(verdict: dict[str, Any]) -> dict[str, Any] | None:
    role = verdict.get("role") if isinstance(verdict, dict) else None
    dispatch = verdict.get("dispatch") if isinstance(verdict, dict) else None
    is_reviewer = is_reviewer_role(role)

    if dispatch is None and not is_reviewer:
        return None

    if dispatch is None and is_reviewer:
        return {
            "code": "MISSING_DISPATCH",
            "message": (
                f"reviewer-class role {role!r} verdict must declare a `dispatch` block "
                f"with {list(DISPATCH_REQUIRED_FIELDS)}"
            ),
        }

    if not isinstance(dispatch, dict):
        return {
            "code": "INVALID_DISPATCH",
            "message": f"verdict.dispatch must be an object; received {type(dispatch).__name__}",
        }

    missing = [field for field in DISPATCH_REQUIRED_FIELDS if not dispatch.get(field)]
    if missing:
        return {
            "code": "MISSING_DISPATCH_FIELD",
            "message": f"verdict.dispatch missing required fields for role {role!r}: {missing}",
            "missing_fields": missing,
        }

    mode = dispatch.get("execution_mode")
    if mode not in DISPATCH_EXECUTION_MODES:
        return {
            "code": "INVALID_EXECUTION_MODE",
            "message": (
                f"verdict.dispatch.execution_mode must be one of {sorted(DISPATCH_EXECUTION_MODES)}; "
                f"received {mode!r}"
            ),
        }

    if is_reviewer and mode == "main_agent_fallback":
        return {
            "code": "REVIEWER_MAIN_AGENT_FALLBACK",
            "message": (
                f"reviewer-class role {role!r} cannot record a PASS verdict via main_agent_fallback; "
                "reviewers must run in a real subagent or surface as BLOCKED."
            ),
            "role": role,
        }

    return None


def add_role_verdict(contract: dict[str, Any], verdict: dict[str, Any]) -> str:
    role_verdicts = contract.setdefault("role_verdicts", [])
    if not isinstance(role_verdicts, list):
        raise ValueError("control_contract.role_verdicts must be a list")
    return upsert_by_id(role_verdicts, verdict)


def add_execution_result(contract: dict[str, Any], result: dict[str, Any]) -> tuple[bool, int | None]:
    has_list = isinstance(contract.get("execution_results"), list)
    has_barrier = bool(result.get("barrier_group"))
    if has_list or has_barrier:
        existing = contract.get("execution_results") if has_list else []
        if not isinstance(existing, list):
            existing = []
        key = (result.get("id"), result.get("role"))
        existing = [
            entry
            for entry in existing
            if not (
                isinstance(entry, dict)
                and (entry.get("id"), entry.get("role")) == key
            )
        ]
        existing.append(result)
        contract["execution_results"] = existing
        return True, len(existing)
    contract["execution_result"] = result
    return False, None


def code_review_contract_path(root: Path, mission: str) -> Path:
    return root / "harness-runtime" / "harness" / "stages" / mission / "contracts" / "code-review.contract.yaml"


def load_code_review_contract(root: Path, mission: str) -> tuple[Path, dict[str, Any] | None, str | None]:
    artifact = code_review_contract_path(root, mission)
    if not artifact.exists():
        return artifact, None, "code_review_contract_missing"
    try:
        document = load_manifest(artifact)
    except Exception:
        return artifact, None, "code_review_contract_invalid_yaml"
    if not isinstance(document, dict):
        return artifact, None, "code_review_contract_invalid_root"
    contract = (
        document.get("control_contract")
        if isinstance(document.get("control_contract"), dict)
        else document
    )
    if not isinstance(contract, dict):
        return artifact, None, "code_review_contract_invalid_shape"
    return artifact, contract, None


def archive_review_round(contract: dict[str, Any], *, timestamp: str, verdicts: list[Any] | None = None) -> int:
    eff = contract.get("effectiveness_review")
    if not isinstance(eff, dict):
        eff = {}
        contract["effectiveness_review"] = eff
    rounds_used = int(eff.get("rounds_used") or 0) + 1
    eff["rounds_used"] = rounds_used

    rounds_list = eff.get("rounds")
    if not isinstance(rounds_list, list):
        rounds_list = []
        eff["rounds"] = rounds_list

    round_entry: dict[str, Any] = {
        "round": rounds_used,
        "timestamp": timestamp,
    }
    if verdicts:
        round_entry["verdicts"] = verdicts
    rounds_list.append(round_entry)
    return rounds_used


FINDING_OWNERSHIP_POLICY: dict[str, list[str]] = {
    "correctness-reviewer": ["correctness", "logic", "algorithm"],
    "tdd-reviewer": ["coverage", "testing", "tdd"],
    "security-reviewer": ["security", "auth", "crypto"],
    "architecture-reviewer": ["architecture", "design", "coupling"],
    "interaction-reviewer": ["ui", "ux", "interaction"],
    "e2e-reviewer": ["e2e", "integration", "system"],
    "data-engineer": ["database", "migration", "data"],
    "integration-impact-expert": ["integration", "compatibility", "api"],
}


def finding_ownership_violations(contract: dict[str, Any]) -> list[dict[str, Any]]:
    findings_map: dict[str, dict[str, Any]] = {
        f["id"]: f
        for f in (contract.get("findings") or [])
        if isinstance(f, dict) and "id" in f
    }
    role_verdicts = contract.get("role_verdicts") or []
    violations: list[dict[str, Any]] = []
    for rv in role_verdicts:
        if not isinstance(rv, dict):
            continue
        role = rv.get("role", "")
        authorized = FINDING_OWNERSHIP_POLICY.get(role, [])
        for fid in (rv.get("findings") or []):
            finding_item = findings_map.get(fid)
            if not finding_item:
                continue
            category = (finding_item.get("category") or "").lower()
            if authorized and category and not any(auth in category for auth in authorized):
                violations.append(
                    {
                        "level": "WARN",
                        "code": "boundary_mismatch",
                        "role": role,
                        "finding_id": fid,
                        "category": category,
                        "authorized": authorized,
                        "message": (
                            f"{role} referenced finding {fid!r} (category={category!r}) "
                            f"outside its authorized boundary: {authorized}"
                        ),
                    }
                )
    return violations


def detect_finding_conflicts(contract: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    role_verdicts = contract.get("role_verdicts") or []
    fid_map: dict[str, list[tuple[str, str]]] = {}
    for rv in role_verdicts:
        if not isinstance(rv, dict):
            continue
        role = rv.get("role", "unknown")
        verdict = (rv.get("verdict") or "").upper()
        for fid in (rv.get("findings") or []):
            fid_map.setdefault(fid, []).append((role, verdict))

    conflicts: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for fid, entries in fid_map.items():
        verdicts = {v for _, v in entries}
        roles_list = [r for r, _ in entries]
        has_pass = any(v == "PASS" for v in verdicts)
        has_hold = any(v == "HOLD" for v in verdicts)
        if has_pass and has_hold:
            conflicts.append(
                {
                    "level": "FAIL",
                    "code": "pass_vs_hold",
                    "finding_id": fid,
                    "roles": roles_list,
                    "message": f"Finding {fid!r} has conflicting verdicts: {sorted(verdicts)}",
                }
            )
        elif len(entries) > 1 and len(verdicts) == 1:
            warnings.append(
                {
                    "level": "WARN",
                    "code": "boundary_overlap",
                    "finding_id": fid,
                    "roles": roles_list,
                    "message": f"Finding {fid!r} referenced by multiple reviewers: {roles_list}",
                }
            )
    return conflicts, warnings


BROWSER_PRIMARY_EVIDENCE_KINDS = {
    "dom",
    "dom_snapshot",
    "screenshot",
    "video",
    "trace",
    "accessibility_snapshot",
}


def verification_report_path(root: Path, mission: str) -> Path:
    return root / "harness-runtime" / "harness" / "stages" / mission / "contracts" / "verification-report.contract.yaml"


def resolve_verify_contract(root: Path, mission: str, artifact_arg: str | None = None) -> tuple[Path, dict[str, Any] | None, str | None]:
    path = Path(artifact_arg) if artifact_arg else verification_report_path(root, mission)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return path, None, "verification_report_contract_missing"
    try:
        doc = load_manifest(path)
    except Exception:
        return path, None, "verification_report_contract_invalid_yaml"
    if not isinstance(doc, dict):
        return path, None, "verification_report_contract_invalid_root"
    contract = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    if not isinstance(contract, dict):
        return path, None, "verification_report_contract_invalid_shape"
    return path, contract, None


def resolve_execution_brief_for_verify(root: Path, mission: str, upstream_arg: str | None = None) -> tuple[Path, dict[str, Any] | None, str | None]:
    if upstream_arg:
        path = Path(upstream_arg)
        if not path.is_absolute():
            path = root / path
    else:
        path = root / "harness-runtime" / "harness" / "stages" / mission / "contracts" / "execution-brief.contract.yaml"
    if not path.exists():
        return path, None, "execution_brief_contract_missing"
    try:
        doc = load_manifest(path)
    except Exception:
        return path, None, "execution_brief_contract_invalid_yaml"
    if not isinstance(doc, dict):
        return path, None, "execution_brief_contract_invalid_root"
    contract = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    if not isinstance(contract, dict):
        return path, None, "execution_brief_contract_invalid_shape"
    return path, contract, None


def required_evidence_ids(brief: dict[str, Any] | None) -> set[str]:
    valid_re_ids: set[str] = set()
    if brief is None:
        return valid_re_ids
    for task in brief.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        for required in task.get("required_evidence") or []:
            if isinstance(required, dict) and isinstance(required.get("id"), str):
                valid_re_ids.add(required["id"])
    return valid_re_ids


def check_acceptance_trace_payload(
    mission: str,
    contract: dict[str, Any],
    *,
    valid_re_ids: set[str] | None = None,
) -> dict[str, Any]:
    valid_re_ids = valid_re_ids or set()
    failed_checks: list[dict[str, Any]] = []
    command_evidence: dict[str, dict[str, Any]] = {}
    result_evidence: dict[str, dict[str, Any]] = {}
    for evidence in contract.get("command_evidence") or []:
        if isinstance(evidence, dict) and evidence.get("id"):
            command_evidence[evidence["id"]] = evidence
    for evidence in contract.get("result_evidence") or []:
        if isinstance(evidence, dict) and evidence.get("id"):
            result_evidence[evidence["id"]] = evidence

    if valid_re_ids:
        for key, entries in [("command_evidence", command_evidence), ("result_evidence", result_evidence)]:
            for evidence_id, evidence in entries.items():
                ref = evidence.get("required_evidence_id")
                if ref and ref not in valid_re_ids:
                    failed_checks.append({
                        "check": "required_evidence_id_not_in_upstream",
                        "code": "VERIFY_EVIDENCE_ID_NOT_IN_UPSTREAM",
                        "evidence_id": evidence_id,
                        "evidence_kind": key,
                        "required_evidence_id": ref,
                        "message": f"{key}[{evidence_id}].required_evidence_id={ref!r} not found in execution-brief required_evidence ids",
                    })

    for acceptance in contract.get("acceptance_trace") or []:
        if not isinstance(acceptance, dict):
            continue
        conclusion = str(acceptance.get("conclusion", "")).lower()
        if conclusion != "pass":
            continue
        acceptance_id = acceptance.get("id") or acceptance.get("acceptance_id") or "<unknown>"
        command_ids = set(acceptance.get("command_evidence_ids") or [])
        result_ids = set(acceptance.get("result_evidence_ids") or [])
        if not command_ids:
            failed_checks.append({
                "check": "missing_command_evidence",
                "acceptance_id": acceptance_id,
                "message": f"acceptance_trace[{acceptance_id}].conclusion=pass but no command_evidence_ids",
            })
        if not result_ids:
            failed_checks.append({
                "check": "missing_result_evidence",
                "acceptance_id": acceptance_id,
                "message": f"acceptance_trace[{acceptance_id}].conclusion=pass but no result_evidence_ids",
            })
        is_ui = acceptance.get("surface_type") == "ui" or bool(acceptance.get("ui_surface"))
        if is_ui:
            ui_kind_found = any(
                str((result_evidence.get(result_id) or {}).get("kind", "")).lower() in BROWSER_PRIMARY_EVIDENCE_KINDS
                for result_id in result_ids
            )
            if not ui_kind_found:
                failed_checks.append({
                    "check": "missing_ui_evidence_kind",
                    "acceptance_id": acceptance_id,
                    "message": f"acceptance_trace[{acceptance_id}].surface_type=ui but no result_evidence with kind in {sorted(BROWSER_PRIMARY_EVIDENCE_KINDS)}",
                })

    return {
        "status": "FAIL" if failed_checks else "PASS",
        "control": "contract.check-acceptance-trace",
        "mission_id": mission,
        "failed_checks": failed_checks,
        "upstream_re_ids_count": len(valid_re_ids),
    }


def build_contract_summary_payload(
    root: Path,
    mission_id: str,
    artifact: Path,
    contract: dict[str, Any],
    *,
    fmt: str = "json",
) -> dict[str, Any]:
    objective = contract.get("objective") if isinstance(contract.get("objective"), dict) else {}
    scope = contract.get("scope") if isinstance(contract.get("scope"), dict) else {}
    acs = contract.get("acceptance_scenarios") if isinstance(contract.get("acceptance_scenarios"), list) else []
    user_stories = contract.get("user_stories") if isinstance(contract.get("user_stories"), list) else []
    autonomy = contract.get("autonomy") if isinstance(contract.get("autonomy"), dict) else {}
    governance = autonomy.get("governance_assessment") if isinstance(autonomy.get("governance_assessment"), dict) else {}
    hard_triggers = governance.get("hard_triggers") if isinstance(governance.get("hard_triggers"), list) else []
    dimensions = governance.get("dimensions") if isinstance(governance.get("dimensions"), dict) else {}
    high_dimensions: list[str] = []
    medium_dimensions: list[str] = []
    for name, value in dimensions.items():
        if not isinstance(value, dict):
            continue
        level = str(value.get("level") or "").strip().lower()
        if level == "high":
            high_dimensions.append(str(name))
        elif level == "medium":
            medium_dimensions.append(str(name))

    summary = {
        "mission_id": mission_id,
        "contract_path": relpath(root, artifact),
        "objective": objective.get("statement") or objective.get("id") or "",
        "scope_in_count": len(scope.get("in") or []) if isinstance(scope.get("in"), list) else 0,
        "scope_out_count": len(scope.get("out") or []) if isinstance(scope.get("out"), list) else 0,
        "user_story_count": len(user_stories),
        "acceptance_scenarios_count": len(acs),
        "autonomy_level": autonomy.get("level") or "",
        "governance_risk": autonomy.get("governance_risk") or "",
        "governance_hard_trigger_count": len(hard_triggers),
        "governance_high_dimensions": high_dimensions,
        "governance_medium_dimensions": medium_dimensions,
        "governance_decision_rule": governance.get("decision_rule") or "",
        "governance_confirmation_required": bool(governance.get("user_confirmation_required", True)) if governance else False,
        "required_checkpoints": list(autonomy.get("human_checkpoints") or []),
        "skippable_stages": list(autonomy.get("skippable_stages") or []),
    }

    payload: dict[str, Any] = {
        "status": "PASS",
        "control": "contract.summary",
        "summary": summary,
        "findings": [],
    }
    if fmt == "user":
        lines = [
            f"Mission: {mission_id}",
            f"Objective: {summary['objective']}",
            f"Scope: {summary['scope_in_count']} in / {summary['scope_out_count']} out",
            f"User stories: {summary['user_story_count']}",
            f"Acceptance scenarios: {summary['acceptance_scenarios_count']}",
            f"Autonomy level: {summary['autonomy_level']}",
        ]
        if summary["governance_risk"]:
            lines.append(f"Governance risk: {summary['governance_risk']}")
        if summary["governance_hard_trigger_count"]:
            lines.append(f"Governance hard triggers: {summary['governance_hard_trigger_count']}")
        if summary["governance_high_dimensions"] or summary["governance_medium_dimensions"]:
            lines.append(
                "Governance dimensions: "
                f"high={', '.join(summary['governance_high_dimensions']) or 'none'}; "
                f"medium={', '.join(summary['governance_medium_dimensions']) or 'none'}"
            )
        if summary["governance_decision_rule"]:
            lines.append(f"Governance decision rule: {summary['governance_decision_rule']}")
        if summary["required_checkpoints"]:
            lines.append("Required checkpoints: " + ", ".join(summary["required_checkpoints"]))
        if summary["skippable_stages"]:
            lines.append("Skippable stages: " + ", ".join(summary["skippable_stages"]))
        payload["user_text"] = "\n".join(lines)
    return payload


def build_recheck_pending_payload(root: Path, artifact: Path, contract: dict[str, Any]) -> dict[str, Any]:
    pending = bool(contract.get("pending_reviewer_recheck"))
    status = "FAIL" if pending else "PASS"
    findings: list[dict[str, Any]] = []
    if pending:
        findings.append(
            {
                "level": "FAIL",
                "code": "PENDING_REVIEWER_RECHECK",
                "message": "contract was edited after the last review; reviewer re-run required before advance",
            }
        )
    return {
        "status": status,
        "control": "contract.check-recheck-pending",
        "contract": relpath(root, artifact),
        "pending_reviewer_recheck": pending,
        "findings": findings,
    }
