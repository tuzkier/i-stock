"""Handlers for `harness interaction ...` commands.

Covers ``check-ui-trigger``, ``spec-check``, ``ux-quality-check``,
``feedback-sync-check``, ``visual-coverage-check``, ``locator-check``, and
the aggregating ``gate-run`` that wraps the others plus
``alignment.check``.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
from pathlib import Path
from typing import Any

from harness_cli_core.app.output import emit_payload
from harness_cli_core.app.parser import root_arg
from harness_cli_core.domain.findings import finding, strict_status
from harness_cli_core.domain.approvals import approval_matches, load_approvals
from harness_cli_core.domain.config_snapshot import snapshot_prototype_config
from harness_cli_core.domain.interaction import (
    DOMAIN_REF_RE,
    INTERACTION_REQUIRED_FILES,
    INTERACTION_REQUIRED_STATES,
    interaction_required_decision,
    OPERABLE_PROTOTYPE_FORBIDDEN_RE,
    OPERABLE_PROTOTYPE_FORBIDDEN_TEXT,
    OPERABLE_PROTOTYPE_INTERACTIVE_RE,
    contains_any,
    contains_ascii_wireframe,
    contract_feedback_sync_findings,
    covered_manifest_values,
    artifact_rel_path,
    build_trace_index,
    extract_data_anchor_ids,
    extract_field_anchor_ids,
    field_coverage_findings,
    interaction_field_bindings,
    project_object_registry_ids,
    project_use_case_ids,
    html_without_comments,
    interaction_prd_feedback_required,
    interaction_product_dir,
    interaction_spec_dir,
    interaction_surface_binding_ids,
    is_operable_prototype_artifact,
    is_placeholder_or_convention_ref,
    known_domain_refs,
    load_visual_manifest,
    operable_visible_text,
    parse_project_system_use_cases,
    resolve_feedback_routing,
    resolve_visual_artifact_path,
    row_has_locator_strategy,
    scenario_rows_with_locator_obligation,
    spec_text_blob,
    state_concept_covered,
    state_has_na_reason,
    trace_coverage_findings,
    prototype_frame_nav,
    TRACE_OBJ_RE,
    TRACE_SUC_RE,
    TRACE_SURF_RE,
)
from harness_cli_core.domain import behavior_graph as bg
from harness_cli_core.infra.runtime_paths import (
    load_runtime_config,
    mission_stage_dir,
    read_text_if_exists,
    relpath,
)

# PRD abstract outcome-node ids (use-case-model 结局节点 / 节拍)，形如 SUC-01-FLOW-01.empty
PRD_ABSTRACT_STEP_RE = re.compile(r"\bSUC-[0-9]+-FLOW-[0-9]+\.[A-Za-z0-9_-]+\b")


def _interaction_prototype_root(root: Path, args: argparse.Namespace) -> str:
    explicit = str(getattr(args, "prototype_root", "") or "").strip()
    if explicit:
        return explicit
    prototype = snapshot_prototype_config(root, load_runtime_config(root))
    interactive = (
        prototype.get("interactive_prototype")
        if isinstance(prototype.get("interactive_prototype"), dict)
        else {}
    )
    if str(interactive.get("prototype_project_root_status") or "") != "resolved":
        return ""
    return str(interactive.get("prototype_project_root") or "").strip()


def cmd_interaction_check_ui_trigger(args: argparse.Namespace) -> int:
    """是否需要 interaction / 原型阶段——**读 PRD 用例模型的界面承载要求 `UIC-xx`**，
    不扫关键词、无兜底。

    判定真相源是产品分析阶段的 reasoned 结论（界面承载要求），不是 mission-contract /
    产品定义里的关键词。interaction 结构上依赖 PRD：没有 use-case-model（未做 PRD）就
    没有原型 → 返回 ``requires_interaction=null`` + ``needs_prd=true``，让上游补 PRD，
    既不默认进、也不退回关键词猜。
    """
    root = Path(root_arg(args))
    mission_id = args.mission
    decision = interaction_required_decision(root, mission_id)
    decided = decision["decided"]

    if decided is None:
        # 尚未产出原型必要性确定记录：每个 mission 默认进入 interaction 阶段，
        # 由 interaction-designer 在阶段内 Step 0 判定。不再"无 PRD 即无原型"。
        return emit_payload(
            args,
            {
                "status": "PASS",
                "control": "interaction.check-ui-trigger",
                "mission_id": mission_id,
                "requires_interaction": None,
                "default_enter": True,
                "pending_in_stage_decision": True,
                "decided_by": decision["source"],
                "reason": decision["reason"],
                "findings": [],
            },
        )

    return emit_payload(
        args,
        {
            "status": "PASS",
            "control": "interaction.check-ui-trigger",
            "mission_id": mission_id,
            "requires_interaction": bool(decided),
            "decided_by": decision.get("decided_by") or decision["source"],
            "reason": decision["reason"],
            "findings": [],
        },
    )


def cmd_interaction_spec_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    spec_dir = interaction_spec_dir(root, mission)
    findings: list[dict[str, object]] = []

    if not spec_dir.exists():
        findings.append(
            finding(
                "FAIL",
                "INTERACTION_SPEC_MISSING",
                f"interaction-spec directory not found: {relpath(root, spec_dir)}",
                path=relpath(root, spec_dir),
            )
        )
    for name in INTERACTION_REQUIRED_FILES:
        path = spec_dir / name
        if not path.exists():
            findings.append(
                finding(
                    "FAIL",
                    "INTERACTION_SPEC_FILE_MISSING",
                    f"interaction-spec required file missing: {name}",
                    path=relpath(root, path),
                )
            )

    # State coverage 已下沉到 behavior-graph 的 page_states，由 `prototype-check` 的
    # coverage / reachability category 在 page-state 颗粒强制（每个声明态须有锚点且图可达），
    # 取代旧的"interaction-contract.md 含 6 个 canonical STATE-* token"检查。

    blob = spec_text_blob(root, mission)
    focus_sources = blob.lower()
    if not any(token in focus_sources for token in ("focus", "焦点", "keyboard", "键盘")):
        findings.append(
            finding(
                "FAIL",
                "INTERACTION_FOCUS_STATE_MISSING",
                "interaction-spec must cover disabled/focus or keyboard focus behavior.",
                path=relpath(root, spec_dir),
            )
        )

    domain_mapping_path = spec_dir / "surface-model.md"
    domain_refs = DOMAIN_REF_RE.findall(read_text_if_exists(domain_mapping_path))
    known_refs = known_domain_refs(root, mission)
    if domain_refs and known_refs:
        for ref in sorted(set(domain_refs) - known_refs):
            findings.append(
                finding(
                    "FAIL",
                    "UNKNOWN_DOMAIN_REF",
                    f"interaction domain-ui-mapping references unknown domain id {ref}.",
                    ref=ref,
                    path=relpath(root, domain_mapping_path),
                )
            )
    elif not domain_refs:
        findings.append(
            finding(
                "FAIL",
                "MISSING_ALIGNMENT_EVIDENCE",
                "surface-model.md must include Entity/Command/State/Permission/Invariant or BO refs.",
                path=relpath(root, domain_mapping_path),
            )
        )

    if interaction_prd_feedback_required(root, mission):
        findings.append(
            finding(
                "FAIL",
                "PRD_FEEDBACK_REQUIRED",
                "Interaction contract records new scenario/domain/permission/scope feedback that must return to PRD or Decision Gate.",
            )
        )

    status, failed_checks = strict_status(findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "interaction.spec-check",
            "mission_id": mission,
            "interaction_spec_dir": relpath(root, spec_dir),
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def cmd_interaction_ux_quality_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    spec_dir = interaction_spec_dir(root, mission)
    blob = spec_text_blob(root, mission)
    findings: list[dict[str, object]] = []

    required_signals = [
        ("UX_USER_GOAL_MISSING", ("user goal", "用户目标", "用户来到", "完成目标")),
        ("UX_ENTRY_EXIT_MISSING", ("entry", "exit", "入口", "退出", "返回", "取消")),
        (
            "UX_SCREEN_PRIORITY_MISSING",
            ("screen priority", "priority", "信息层级", "主次", "primary", "secondary"),
        ),
        ("UX_ACTIONS_MISSING", ("actions", "action", "操作", "能做什么", "available when")),
        (
            "UX_INTERACTION_RULES_MISSING",
            (
                "interaction rules",
                "trigger",
                "system response",
                "ui feedback",
                "next state",
                "触发",
                "系统响应",
                "下一状态",
            ),
        ),
        ("UX_FEEDBACK_STRATEGY_MISSING", ("feedback", "反馈", "success", "error", "empty", "loading")),
        ("UX_RECOVERY_PATH_MISSING", ("recovery", "恢复", "retry", "重试", "返回", "取消")),
        ("UX_REVIEW_NOTES_MISSING", ("review notes", "reviewer", "审查", "检查")),
        (
            "UX_RESPONSIVE_RULE_MISSING",
            ("responsive", "viewport", "mobile", "desktop", "响应式", "移动端"),
        ),
        ("UX_COPY_LANGUAGE_MISSING", ("zh-CN", "中文", "copy", "文案")),
    ]
    for code, tokens in required_signals:
        if not contains_any(blob, tokens):
            findings.append(
                finding(
                    "FAIL",
                    code,
                    f"interaction-spec must document {code.lower().replace('_', ' ')}.",
                    path=relpath(root, spec_dir),
                )
            )

    if not contains_ascii_wireframe(blob):
        findings.append(
            finding(
                "FAIL",
                "UX_ASCII_WIREFRAME_MISSING",
                "interaction-spec must include a low-fidelity ASCII wireframe for key surfaces.",
                path=relpath(root, spec_dir),
            )
        )

    if not contains_any(blob, ("traces_to", "Trace", "追溯", "SCN-", "SUC-", "BO-", "CMD-")):
        findings.append(
            finding(
                "FAIL",
                "UX_TRACE_MISSING",
                "interaction-spec must include traceability to system use cases / scenarios / domain refs.",
                path=relpath(root, spec_dir),
            )
        )
    if not contains_any(blob, ("primary", "secondary", "主", "次", "hierarchy", "层级", "信息层级")):
        findings.append(
            finding(
                "FAIL",
                "UX_HIERARCHY_MISSING",
                "interaction-spec must explain screen priority / primary-secondary content.",
                path=relpath(root, spec_dir),
            )
        )

    status, failed_checks = strict_status(findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "interaction.ux-quality-check",
            "mission_id": mission,
            "interaction_spec_dir": relpath(root, spec_dir),
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def cmd_interaction_feedback_sync_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    stage_dir = mission_stage_dir(root, mission)
    findings: list[dict[str, object]] = []
    for contract_name in ("interaction.contract.yaml", "prototype-as-frontend.contract.yaml"):
        if (stage_dir / "contracts" / contract_name).exists():
            findings.extend(contract_feedback_sync_findings(root, mission, contract_name))

    consistency_path = interaction_spec_dir(root, mission) / "interaction-contract.md"
    consistency = read_text_if_exists(consistency_path).lower()
    if "feedback_not_synced" in consistency and not re.search(
        r"feedback_not_synced\s*[:|]\s*(none|0|无|not_applicable)", consistency
    ):
        findings.append(
            finding(
                "FAIL",
                "FEEDBACK_NOT_SYNCED",
                "interaction-spec consistency report contains feedback_not_synced findings.",
                path=relpath(root, consistency_path),
            )
        )

    status, failed_checks = strict_status(findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "interaction.feedback-sync-check",
            "mission_id": mission,
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def _operable_prototype_findings(
    root: Path,
    mission: str,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> list[dict[str, object]]:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        return [
            finding(
                "FAIL",
                "PRIMARY_PROTOTYPE_MISSING",
                "visual manifest must include artifacts[] with the long-lived primary operable prototype.",
                expected_path="configured prototype project root (prototype.interactive_prototype.prototype_project_root, default prototype/)",
            )
        ]

    primary = [
        artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and is_operable_prototype_artifact(artifact)
    ]
    if not primary:
        return [
            finding(
                "FAIL",
                "PRIMARY_PROTOTYPE_MISSING",
                "visual manifest must include the long-lived prototype project entry as an HTML artifact with artifact_role=operable_prototype.",
                expected_path="configured prototype project root (prototype.interactive_prototype.prototype_project_root, default prototype/)",
            )
        ]

    findings: list[dict[str, object]] = []
    for artifact in primary:
        path = resolve_visual_artifact_path(root, mission, manifest_path, artifact)
        rel = artifact_rel_path(artifact)
        if not path.exists():
            findings.append(
                finding(
                    "FAIL",
                    "PRIMARY_PROTOTYPE_FILE_MISSING",
                    f"primary operable prototype file missing: {rel}",
                    path=rel,
                )
            )
            continue
        html = read_text_if_exists(path)
        visibleish = html_without_comments(html)
        if not OPERABLE_PROTOTYPE_INTERACTIVE_RE.search(visibleish):
            findings.append(
                finding(
                    "FAIL",
                    "PRIMARY_PROTOTYPE_NOT_OPERABLE",
                    "primary prototype must expose real interaction affordances such as button/input/link/data-testid.",
                    path=rel,
                )
            )
        # Review/spec annotations are only forbidden in user-visible product TEXT.
        # JS fixture data / comments / CSS are not visible UI; element attributes
        # (data-testid, onclick, aria-label) are not visible copy; declared domain
        # field values (data-field, e.g. a Work Graph node id) are product data
        # under field-level trace — none of these may trip this check.
        product_copy = operable_visible_text(html)
        forbidden_hits = [
            token
            for token in OPERABLE_PROTOTYPE_FORBIDDEN_TEXT
            if token.lower() in product_copy.lower()
        ]
        if OPERABLE_PROTOTYPE_FORBIDDEN_RE.search(product_copy):
            forbidden_hits.append("trace id")
        if forbidden_hits:
            findings.append(
                finding(
                    "FAIL",
                    "PRIMARY_PROTOTYPE_CONTAINS_REVIEW_COPY",
                    "primary prototype must not mix review/spec/coverage instructions into the product UI.",
                    path=rel,
                    evidence=sorted(set(forbidden_hits)),
                )
            )
    return findings


def cmd_interaction_visual_coverage_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    manifest_path, manifest = load_visual_manifest(root, mission)
    findings: list[dict[str, object]] = []
    if manifest is None:
        findings.append(
            finding(
                "FAIL",
                "VISUAL_MANIFEST_MISSING",
                f"visual interaction manifest missing or invalid: {relpath(root, manifest_path)}",
                path=relpath(root, manifest_path),
            )
        )
        manifest = {}

    blob = spec_text_blob(root, mission)

    def _required_ids(prefix: str) -> set[str]:
        # Negative lookbehind avoids matching sub-tokens inside compound upstream
        # ids (e.g. FLOW-01 inside SUC-01-FLOW-01); placeholder/convention/range
        # tokens from explanatory prose are filtered out.
        raw = re.findall(rf"(?<![\w-]){prefix}-[A-Za-z0-9._-]+", blob)
        return {
            ref.rstrip(".,;:，。；：")
            for ref in raw
            if not is_placeholder_or_convention_ref(ref.rstrip(".,;:，。；："))
        }

    required_flows = _required_ids("FLOW")
    required_states = _required_ids("STATE")
    required_surfaces = _required_ids("SURF")
    if not required_states:
        required_states = set(INTERACTION_REQUIRED_STATES)
    covered_flows = covered_manifest_values(manifest, "flows")
    covered_states = covered_manifest_values(manifest, "states")
    covered_surfaces = covered_manifest_values(manifest, "surfaces")
    covered_viewports = {v.lower() for v in covered_manifest_values(manifest, "viewports")}
    findings.extend(_operable_prototype_findings(root, mission, manifest_path, manifest))

    for surface_id in sorted(required_surfaces - covered_surfaces):
        findings.append(
            finding(
                "FAIL",
                "VISUAL_SURFACE_COVERAGE_MISSING",
                f"visual manifest must cover interaction surface {surface_id}.",
                surface_id=surface_id,
            )
        )
    for flow_id in sorted(required_flows - covered_flows):
        findings.append(
            finding(
                "FAIL",
                "VISUAL_FLOW_COVERAGE_MISSING",
                f"visual manifest must cover interaction flow {flow_id}.",
                flow_id=flow_id,
            )
        )
    for state_id in sorted(required_states - covered_states):
        findings.append(
            finding(
                "FAIL",
                "VISUAL_STATE_COVERAGE_MISSING",
                f"visual manifest must cover interaction state {state_id}.",
                state_id=state_id,
            )
        )
    for viewport in ("desktop", "mobile"):
        if viewport not in covered_viewports:
            findings.append(
                finding(
                    "FAIL",
                    "VISUAL_VIEWPORT_COVERAGE_MISSING",
                    f"visual manifest must cover the {viewport} viewport.",
                    viewport=viewport,
                )
            )

    status, failed_checks = strict_status(findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "interaction.visual-coverage-check",
            "mission_id": mission,
            "manifest_path": relpath(root, manifest_path),
            "required_flows": sorted(required_flows),
            "required_states": sorted(required_states),
            "required_surfaces": sorted(required_surfaces),
            "covered_flows": sorted(covered_flows),
            "covered_states": sorted(covered_states),
            "covered_surfaces": sorted(covered_surfaces),
            "covered_viewports": sorted(covered_viewports),
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def cmd_interaction_trace_coverage_check(args: argparse.Namespace) -> int:
    """Reconcile PRD inventory ↔ interaction-spec binding ↔ prototype trace anchors.

    Object axis = OBJ-xx (business-object-analysis.md). Fails on dropped bindings,
    dangling anchors and unknown upstream refs; warns on unbound PRD ids.
    Emits trace-index.json into the prototype project root for low-noise 回溯.
    """
    root = Path(root_arg(args))
    mission = args.mission
    findings: list[dict[str, object]] = []

    manifest_path, manifest = load_visual_manifest(root, mission)
    if manifest is None:
        findings.append(
            finding(
                "FAIL",
                "VISUAL_MANIFEST_MISSING",
                f"visual interaction manifest missing or invalid: {relpath(root, manifest_path)}",
                path=relpath(root, manifest_path),
            )
        )
        manifest = {}

    # Declared trace binding — canonical machine source is contract.yaml#surface_bindings.
    # Once a mission has a visual-interaction manifest, the trace spine is mandatory:
    # missing bindings are a contract defect, not an opt-out path.
    binding = interaction_surface_binding_ids(root, mission)
    spec_surf, spec_suc, spec_obj = binding["surf"], binding["suc"], binding["obj"]
    adopted = bool(spec_surf or spec_suc or spec_obj)
    if not adopted:
        findings.append(
            finding(
                "FAIL",
                "TRACE_BINDING_MISSING",
                "interaction.contract.yaml 未声明 prototype.surface_bindings；有 visual-interaction manifest 时必须写入 SURF↔SUC↔OBJ 机器绑定，不允许跳过 trace 对账。",
                path=relpath(root, mission_stage_dir(root, mission) / "contracts" / "interaction.contract.yaml"),
            )
        )

    # Current mission PRD inventory (drives the "unbound" WARN — only this mission is
    # accountable for its own ids).
    product_dir = interaction_product_dir(root, mission)
    prd_suc = set(TRACE_SUC_RE.findall(read_text_if_exists(product_dir / "use-case-model.md")))
    prd_obj = set(TRACE_OBJ_RE.findall(read_text_if_exists(product_dir / "business-object-analysis.md")))
    # Project-level registries widen only the "valid to reference" universe (other
    # missions' objects / use cases) — they do NOT make this mission responsible for
    # binding them.
    extra_valid_obj = project_object_registry_ids(root)
    extra_valid_suc = project_use_case_ids(root)

    # Embodied in prototype: page-level manifest covers + element-level data-* anchors
    proto_surf = covered_manifest_values(manifest, "surfaces")
    proto_suc = covered_manifest_values(manifest, "use_cases")
    proto_obj = covered_manifest_values(manifest, "objects")
    proto_fields: dict[str, set[str]] = {}
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), list) else []
    for artifact in artifacts:
        if isinstance(artifact, dict) and is_operable_prototype_artifact(artifact):
            html = read_text_if_exists(resolve_visual_artifact_path(root, mission, manifest_path, artifact))
            if html:
                anchors = extract_data_anchor_ids(html)
                proto_surf |= anchors["surf"]
                proto_suc |= anchors["suc"]
                proto_obj |= anchors["obj"]
                for obj_id, flds in extract_field_anchor_ids(html).items():
                    proto_fields.setdefault(obj_id, set()).update(flds)

    if adopted:
        findings.extend(
            trace_coverage_findings(
                prd_suc=prd_suc,
                prd_obj=prd_obj,
                spec_surf=spec_surf,
                spec_suc=spec_suc,
                spec_obj=spec_obj,
                proto_surf=proto_surf,
                proto_suc=proto_suc,
                proto_obj=proto_obj,
                extra_valid_suc=extra_valid_suc,
                extra_valid_obj=extra_valid_obj,
            )
        )
        fb = interaction_field_bindings(root, mission)
        findings.extend(
            field_coverage_findings(
                bound_objs=fb["bound_objs"],
                declared=fb["declared"],
                waived=fb["waived"],
                objs_with_fields_key=fb["objs_with_fields_key"],
                proto_fields=proto_fields,
            )
        )

    status, failed_checks = strict_status(findings)
    trace_index = build_trace_index(
        mission=mission,
        prd_suc=prd_suc,
        prd_obj=prd_obj,
        spec_surf=spec_surf,
        spec_suc=spec_suc,
        spec_obj=spec_obj,
        proto_surf=proto_surf,
        proto_suc=proto_suc,
        proto_obj=proto_obj,
        status=status,
    )

    # Write trace-index.json (+ trace-nav.js) into the prototype project root when
    # known. trace-index.json is the 回溯 audit artifact; trace-nav.js is the
    # SUC-directory data source consumed by the framework prototype frame shell
    # (harness-prototype-frame.html) — emitted as a JS global so the shell loads it
    # via <script> even under file://.
    trace_index_path = None
    trace_nav_path = None
    proto_root = str(getattr(args, "prototype_root", "") or "").strip()
    if proto_root:
        proto_dir = root / proto_root
        out = proto_dir / "trace-index.json"
        if out.parent.exists():
            out.write_text(json.dumps(trace_index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            trace_index_path = relpath(root, out)
            nav_out = proto_dir / "trace-nav.js"
            nav_payload = prototype_frame_nav(root, mission)
            nav_out.write_text(
                "window.__HARNESS_TRACE_NAV__ = "
                + json.dumps(nav_payload, ensure_ascii=False, indent=2)
                + ";\n",
                encoding="utf-8",
            )
            trace_nav_path = relpath(root, nav_out)

    return emit_payload(
        args,
        {
            "status": status,
            "control": "interaction.trace-coverage-check",
            "mission_id": mission,
            "manifest_path": relpath(root, manifest_path),
            "prd_inventory": {"suc": sorted(prd_suc), "obj": sorted(prd_obj)},
            "spec_binding": {"surf": sorted(spec_surf), "suc": sorted(spec_suc), "obj": sorted(spec_obj)},
            "prototype_anchors": {"surf": sorted(proto_surf), "suc": sorted(proto_suc), "obj": sorted(proto_obj)},
            "trace_index_path": trace_index_path,
            "trace_nav_path": trace_nav_path,
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def _collect_prototype_anchors(
    root: Path, mission: str, args: argparse.Namespace
) -> dict[str, set[str]] | None:
    """Union prototype trace anchors (data-step / data-pagestate / data-via /
    data-testid) from the long-lived prototype project (``--prototype-root`` glob)
    and any manifest-registered operable artifacts. Returns ``None`` when no
    prototype HTML is found (→ prototype absent)."""
    anchors: dict[str, set[str]] = {
        "steps": set(), "page_states": set(), "vias": set(),
        "testids": set(), "regions": set(),
        "shells": set(), "bizcomps": set(), "basecomps": set(),
    }
    found = False

    proto_root = str(getattr(args, "prototype_root", "") or "").strip()
    if proto_root:
        proto_dir = root / proto_root
        if proto_dir.exists():
            for html_file in sorted(proto_dir.rglob("*.html")):
                # 跳过 dev shell（驾驶舱本身），只扫产品原型页
                if html_file.name in {"harness-prototype-frame.html"}:
                    continue
                text = read_text_if_exists(html_file)
                if text:
                    found = True
                    for key, vals in bg.extract_prototype_anchors(text).items():
                        anchors[key] |= vals

    manifest_path, manifest = load_visual_manifest(root, mission)
    if isinstance(manifest, dict):
        artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), list) else []
        for artifact in artifacts:
            if isinstance(artifact, dict) and is_operable_prototype_artifact(artifact):
                text = read_text_if_exists(resolve_visual_artifact_path(root, mission, manifest_path, artifact))
                if text:
                    found = True
                    for key, vals in bg.extract_prototype_anchors(text).items():
                        anchors[key] |= vals

    return anchors if found else None


def cmd_interaction_prototype_check(args: argparse.Namespace) -> int:
    """Single lint pass for the interaction stage: reconcile the behavior graph
    (SSOT) against the surface catalog and the operable prototype.

    Returns ``{status, findings[]}`` with each finding category-tagged
    (graph / reachability / anchor / coverage / locator / upstream / composition /
    design_system). Supersedes the old trace-coverage-check / visual-coverage-check /
    locator-check trio.
    """
    root = Path(root_arg(args))
    mission = args.mission

    graph_path, graph = bg.load_behavior_graph(root, mission)
    if graph is None:
        # §11 过渡：未采用新模型的历史 mission 不硬阻断，发 WARN 提示。
        payload = {
            "status": "WARN",
            "control": "interaction.prototype-check",
            "mission_id": mission,
            "behavior_graph_path": relpath(root, graph_path),
            "findings": [
                finding(
                    "WARN", "BEHAVIOR_GRAPH_ABSENT",
                    f"未找到 behavior-graph.yaml（{relpath(root, graph_path)}）；该 mission 尚未采用行为图模型，跳过 step/page-state 对账。",
                    category="graph",
                )
            ],
            "failed_checks": [],
        }
        return emit_payload(args, payload)

    # 两层并集：项目级累积图（沉淀 SUC）∪ 本 mission 增量图 → 对整原型做回归 + 增量校验。
    # 修掉单 mission 的 dangling 假阳性（沉淀锚点在项目级图里合法），并强制沉淀态不被退化。
    project_graph = bg.load_project_behavior_graph(root)
    merged = bg.merge_graphs(project_graph, graph)
    tables = bg.graph_tables(merged)
    surface_model_text = read_text_if_exists(bg.surface_model_path(root, mission))
    surfaces = bg.parse_surface_catalog(surface_model_text)
    surfaces.update(bg.surfaces_from_graph(project_graph))  # 沉淀 surface 目录（内联）
    surfaces.update(bg.surfaces_from_graph(graph))           # 本 mission 内联 surface（如有）
    # 组成轴：区域树合并目录 = 本 mission surface-model 区域树 ∪ 项目级累积图沉淀 regions
    # ∪ 本 mission 内联 regions（如有）。对账合并图 → 沉淀区域回归校验。
    regions = bg.parse_region_catalog(surface_model_text)
    regions.update(bg.regions_from_graph(project_graph))
    regions.update(bg.regions_from_graph(graph))
    proto_anchors = _collect_prototype_anchors(root, mission, args)

    manifest_path, manifest = load_visual_manifest(root, mission)
    manifest = manifest if isinstance(manifest, dict) else {}
    manifest_covers = {
        "steps": covered_manifest_values(manifest, "steps"),
        "page_states": covered_manifest_values(manifest, "page_states"),
    }
    manifest_viewports = covered_manifest_values(manifest, "viewports")

    product_dir = interaction_product_dir(root, mission)
    ucm_text = read_text_if_exists(product_dir / "use-case-model.md")

    cfg = load_runtime_config(root)
    reachability_level = bg.resolve_reachability_level(cfg)
    composition_level = bg.resolve_composition_level(cfg)
    findings = bg.reconcile_findings(
        tables=tables,
        surfaces=surfaces,
        proto_anchors=proto_anchors,
        manifest_covers=manifest_covers,
        manifest_viewports=manifest_viewports,
        prd_abstract_steps=None,  # upstream 完整性改由下方 FAIL 级门处理（取代旧 WARN）
        reachability_level=reachability_level,
        regions=regions,
        composition_level=composition_level,
    )

    # ---- supersede 门：迭代取代既有 surface/锚点时，前驱已在 merge 阶段从合并图丢弃
    #      （回归门不再要求它物理在册），此处校验后继真实存在 + 被覆盖，杜绝"假取代真删除"。
    findings.extend(bg.supersede_findings(
        tables=tables, surfaces=surfaces, entries=bg.parse_supersede(graph),
    ))

    # ---- 上游→图 完整性门（FAIL）：保证 lint 分母（图）本身完整，PASS 才真代表
    #      "项目所有 SUC/flow/节拍都进了图、被原型体现"。----
    prd_sucs = set(re.findall(r"\bSUC-[0-9]+\b", ucm_text))
    prd_flowsteps = set(re.findall(r"\bSUC-[0-9]+-FLOW-[0-9]+\b", ucm_text))
    # 结局节拍（beat）对账分母必须排除"编号约定 / 举例"行——约定行里的 `SUC-xx-FLOW-xx.<结局>`
    # 示例（如「（如 `SUC-01-FLOW-01.empty`）」）不是真实 PRD 结局节拍，否则会被误当成"原型漏画"。
    # 口径与 bg.prd_fanout_token_findings 的 _NEG_MARKERS 一致（解释 / 引文 / 举例行不参与扇出对账）。
    _BEAT_NEG_MARKERS = ("不在此列", "单结局", "凡一个", "凡是", "如 `SUC", "例如", "形如", "示例")
    _beat_lines = [
        ln for ln in ucm_text.splitlines()
        if not any(m in ln for m in _BEAT_NEG_MARKERS)
    ]
    prd_beats = set(PRD_ABSTRACT_STEP_RE.findall("\n".join(_beat_lines)))
    # 项目级注册表 SUC（沉淀能力）：走 domain SSOT 的 glob 解析器（前缀无关、跨多文件去重），
    # 取代写死的单文件名 'theforce-system-use-cases.md' + 'SUC-TF-...' 正则。
    registry_sucs = {str(s["id"]) for s in parse_project_system_use_cases(root) if s.get("id")}
    # N/A 豁免：surface-model 的「N/A 豁免（机器段）」结构化固定列表（取代散文关键词 grep）。
    surface_text = read_text_if_exists(bg.surface_model_path(root, mission))
    exemptions = bg.parse_na_exemptions(surface_text)
    na_sucs, na_findings = bg.na_exemption_findings(
        exemptions=exemptions, graph=merged,
        prd_sucs=prd_sucs, prd_flowsteps=prd_flowsteps, prd_beats=prd_beats,
    )
    findings.extend(na_findings)
    findings.extend(bg.upstream_completeness_findings(
        graph=merged,
        prd_sucs=prd_sucs, prd_flowsteps=prd_flowsteps, prd_beats=prd_beats,
        registry_sucs=registry_sucs, na_sucs=na_sucs,
    ))
    # PRD 边界 token 完整性：声明扇出多结局的流步骤必须有 ≥1 个 .state 节拍 token。
    findings.extend(bg.prd_fanout_token_findings(
        ucm_text=ucm_text, prd_flowsteps=prd_flowsteps, prd_beats=prd_beats,
    ))

    # ---- 设计系统门（design_system, R9）：从组件库装配 + 业务组件可追溯。
    #      catalogs 从 project-knowledge/product/design-system 加载；空目录 = 未采用 = 跳过。
    ds_catalogs = bg.load_design_system_catalogs(root)
    design_system_level = bg.resolve_design_system_level(cfg)
    prd_objs = set(re.findall(r"\bOBJ-[0-9]+\b", ucm_text))  # best-effort 业务对象集（绑定 dangling 校验用）
    findings.extend(bg.design_system_findings(
        tables=tables, catalogs=ds_catalogs, proto_anchors=proto_anchors,
        prd_sucs=prd_sucs, prd_objs=prd_objs, level=design_system_level,
    ))

    has_fail = any(f.get("level") == "FAIL" for f in findings)
    has_warn = any(f.get("level") == "WARN" for f in findings)
    status = "FAIL" if has_fail else ("WARN" if has_warn else "PASS")
    failed_checks = [f for f in findings if f.get("level") == "FAIL"]

    step_ids = sorted(str(s.get("id")) for s in tables["steps"] if s.get("id"))
    ps_ids = sorted(str(p.get("id")) for p in tables["page_states"] if p.get("id"))
    covered_steps = sorted((proto_anchors or {}).get("steps", set()) | manifest_covers["steps"])
    covered_ps = sorted((proto_anchors or {}).get("page_states", set()) | manifest_covers["page_states"])

    return emit_payload(
        args,
        {
            "status": status,
            "control": "interaction.prototype-check",
            "mission_id": mission,
            "behavior_graph_path": relpath(root, graph_path),
            "project_graph_present": bool(project_graph),
            "scope": "merged(project ∪ mission)",
            "prototype_present": proto_anchors is not None,
            "required": {"steps": step_ids, "page_states": ps_ids},
            "covered": {"steps": covered_steps, "page_states": covered_ps},
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def cmd_interaction_project(args: argparse.Namespace) -> int:
    """Generate the three derived views from behavior-graph.yaml, plus the
    cockpit data file walkthrough.js. All outputs are GENERATED — never hand-edited.
    """
    root = Path(root_arg(args))
    mission = args.mission
    graph_path, graph = bg.load_behavior_graph(root, mission)
    if graph is None:
        return emit_payload(args, {
            "status": "BLOCKED",
            "control": "interaction.project",
            "mission_id": mission,
            "behavior_graph_path": relpath(root, graph_path),
            "findings": [finding(
                "FAIL", "BEHAVIOR_GRAPH_ABSENT",
                f"无 behavior-graph.yaml（{relpath(root, graph_path)}），无法派生视图。",
            )],
            "failed_checks": [{"check": "project", "status": "BLOCKED"}],
        })

    # 视图与演示数据从 (项目级 ∪ 本 mission) 合并图派生，呈现累积全景；本任务 SUC 打 focus。
    project_graph = bg.load_project_behavior_graph(root)
    merged = bg.merge_graphs(project_graph, graph)
    focus_sucs = bg.flow_suc_ids(graph)
    # SUC 描述：本 mission 取 use-case-model 标题，项目级取 SUC 注册表名称。
    from harness_cli_core.domain.interaction import suc_titles as _mission_suc_titles
    suc_title_map: dict[str, str] = dict(_mission_suc_titles(root, mission))
    for su in parse_project_system_use_cases(root):
        if su.get("id") and su.get("title"):
            suc_title_map.setdefault(str(su["id"]), str(su["title"]))

    views_dir = bg.behavior_graph_path(root, mission).parent / "views"
    views_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for name, text in (
        ("by-suc.md", bg.render_by_suc_view(merged)),
        ("by-surface.md", bg.render_by_surface_view(merged)),
        ("by-object.md", bg.render_by_object_view(merged)),
    ):
        out = views_dir / name
        out.write_text(text, encoding="utf-8")
        written.append(relpath(root, out))

    walkthrough_path = None
    player_shell_path = None
    proto_root = str(getattr(args, "prototype_root", "") or "").strip()
    if proto_root:
        proto_dir = root / proto_root
        if proto_dir.exists():
            out = proto_dir / "walkthrough.js"
            out.write_text(bg.walkthrough_js(merged, focus_sucs=focus_sucs, suc_titles=suc_title_map), encoding="utf-8")
            walkthrough_path = relpath(root, out)
            # 同时刷新演示导览播放器壳（dev-only，模板渲染、勿手改），避免 prototype 内的
            # harness-prototype-frame.html 与升级后的播放器漂移（它只读 walkthrough.js）。
            shell_tpl = root / "harness-runtime" / "templates" / "prototype" / "harness-prototype-frame.html"
            if shell_tpl.exists():
                shell_out = proto_dir / "harness-prototype-frame.html"
                shell_out.write_text(shell_tpl.read_text(encoding="utf-8"), encoding="utf-8")
                player_shell_path = relpath(root, shell_out)

    return emit_payload(args, {
        "status": "PASS",
        "control": "interaction.project",
        "mission_id": mission,
        "behavior_graph_path": relpath(root, graph_path),
        "views": written,
        "walkthrough_path": walkthrough_path,
        "player_shell_path": player_shell_path,
    })


def cmd_interaction_resolve_feedback(args: argparse.Namespace) -> int:
    """Route prototype feedback (by SURF / SUC / OBJ / step anchor) back to the docs
    that own it. Forward-navigation prefers behavior-graph when present; falls back
    to the legacy surface_bindings resolver otherwise."""
    root = Path(root_arg(args))
    surface = str(getattr(args, "surface", "") or "").strip()
    suc = str(getattr(args, "suc", "") or "").strip()
    obj = str(getattr(args, "obj", "") or "").strip()
    step = str(getattr(args, "step", "") or "").strip()
    routing = resolve_feedback_routing(root, args.mission, surface=surface, suc=suc, obj=obj)

    # Prefer behavior-graph forward-nav (page_state + page_entry + anchor_root).
    _gpath, graph = bg.load_behavior_graph(root, args.mission)
    if isinstance(graph, dict) and graph:
        graph_nav = bg.resolve_feedback_from_graph(
            graph, surface=surface, suc=suc, obj=obj, step=step
        )
        routing["forward_nav"] = graph_nav["forward_nav"]
        routing["query"]["step"] = step

    status = "PASS" if (surface or suc or obj or step) else "BLOCKED"
    return emit_payload(
        args,
        {
            "status": status,
            "control": "interaction.resolve-feedback",
            **routing,
        },
    )


def cmd_interaction_locator_check(args: argparse.Namespace) -> int:
    root = Path(root_arg(args))
    mission = args.mission
    spec_dir = interaction_spec_dir(root, mission)
    findings: list[dict[str, object]] = []
    rows: list[tuple[Path, int, str]] = []
    if spec_dir.exists():
        for path in sorted(spec_dir.rglob("*.md")):
            if not path.is_file():
                continue
            for line_no, row in scenario_rows_with_locator_obligation(read_text_if_exists(path)):
                rows.append((path, line_no, row))
    if not rows:
        findings.append(
            finding(
                "FAIL",
                "LOCATOR_OBLIGATION_MISSING",
                "P0/P1 scenario E2E obligations with locator strategy are missing.",
                path=relpath(root, spec_dir),
            )
        )
    for path, line_no, row in rows:
        if not row_has_locator_strategy(row):
            findings.append(
                finding(
                    "FAIL",
                    "E2E_LOCATOR_MISSING",
                    "P0/P1 scenario obligation must declare data-testid or accessibility locator strategy.",
                    path=relpath(root, path),
                    line=line_no,
                )
            )

    status, failed_checks = strict_status(findings)
    return emit_payload(
        args,
        {
            "status": status,
            "control": "interaction.locator-check",
            "mission_id": mission,
            "scenario_rows_checked": len(rows),
            "findings": findings,
            "failed_checks": failed_checks,
        },
    )


def _interaction_user_confirmation_check(root: Path, mission: str) -> dict[str, Any]:
    confirmation_path = (
        root
        / "harness-runtime"
        / "harness"
        / "traces"
        / mission
        / "user-prototype-confirmation.md"
    )
    findings: list[dict[str, object]] = []
    if not confirmation_path.exists():
        findings.append(
            finding(
                "FAIL",
                "USER_PROTOTYPE_CONFIRMATION_MISSING",
                "interaction stage requires user confirmation of the long-lived operable prototype.",
                path=relpath(root, confirmation_path),
            )
        )

    _document, approvals = load_approvals(root)
    matches = [
        record
        for record in approvals
        if approval_matches(
            record,
            mission=mission,
            approval_type="checkpoint",
            stage="interaction",
            status="approved",
        )
    ]
    if not matches:
        findings.append(
            finding(
                "FAIL",
                "USER_PROTOTYPE_APPROVAL_MISSING",
                "interaction stage requires `harness approval append --type checkpoint --stage interaction --status approved` after user prototype confirmation.",
            )
        )

    status, failed_checks = strict_status(findings)
    return {
        "status": status,
        "control": "interaction.user-prototype-confirmation-check",
        "mission_id": mission,
        "confirmation_path": relpath(root, confirmation_path),
        "approval": matches[-1] if matches else None,
        "findings": findings,
        "failed_checks": failed_checks,
    }


def cmd_interaction_gate_run(args: argparse.Namespace) -> int:
    """Aggregating gate for the interaction stage.

    Wraps spec / ux-quality / visual-coverage / locator / alignment /
    feedback-sync, then writes per-check flag files when PASS.
    """
    from harness_cli_core.app.commands.alignment_handlers import cmd_alignment_check

    root = Path(root_arg(args))
    mission = args.mission
    proto_root = _interaction_prototype_root(root, args)
    if proto_root and not str(getattr(args, "prototype_root", "") or "").strip():
        setattr(args, "prototype_root", proto_root)
    checks: dict[str, dict[str, Any]] = {}
    failed_checks: list[dict[str, Any]] = []
    for name, handler, extra in (
        ("spec_check", cmd_interaction_spec_check, {}),
        ("ux_quality_check", cmd_interaction_ux_quality_check, {}),
        ("prototype_check", cmd_interaction_prototype_check, {}),
        ("alignment_check", cmd_alignment_check, {"stage": "interaction"}),
        ("feedback_sync_check", cmd_interaction_feedback_sync_check, {}),
    ):
        check_args = argparse.Namespace(**vars(args))
        for key, value in extra.items():
            setattr(check_args, key, value)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            handler(check_args)
        try:
            result = json.loads(buf.getvalue())
        except json.JSONDecodeError:
            result = {"status": "BLOCKED", "failed_checks": [{"check": name, "status": "BLOCKED"}]}
        checks[name] = result
        if result.get("status") not in {"PASS", "WARN"}:
            for item in result.get("failed_checks") or result.get("findings") or []:
                if isinstance(item, dict):
                    failed_checks.append({"check": name, **item})
            if not (result.get("failed_checks") or result.get("findings")):
                failed_checks.append({"check": name, "status": result.get("status")})

    confirmation_result = _interaction_user_confirmation_check(root, mission)
    checks["user_prototype_confirmation_check"] = confirmation_result
    if confirmation_result.get("status") not in {"PASS", "WARN"}:
        for item in confirmation_result.get("failed_checks") or confirmation_result.get("findings") or []:
            if isinstance(item, dict):
                failed_checks.append({"check": "user_prototype_confirmation_check", **item})

    status = (
        "FAIL"
        if failed_checks
        else (
            "WARN"
            if any(r.get("status") == "WARN" for r in checks.values())
            else "PASS"
        )
    )
    payload = {
        "status": status,
        "control": "interaction.gate-run",
        "mission_id": mission,
        "checks": checks,
        "failed_checks": failed_checks,
    }
    reports_dir = mission_stage_dir(root, mission) / "gate-reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "interaction__hard_gate.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if status == "PASS":
        traces_dir = mission_stage_dir(root, mission) / "traces"
        traces_dir.mkdir(parents=True, exist_ok=True)
        (traces_dir / "interaction_gate_pass.flag").write_text("PASS", encoding="utf-8")
        (traces_dir / "alignment_pass.flag").write_text("PASS", encoding="utf-8")
    return emit_payload(args, payload)


__all__ = [
    "cmd_interaction_check_ui_trigger",
    "cmd_interaction_spec_check",
    "cmd_interaction_ux_quality_check",
    "cmd_interaction_feedback_sync_check",
    "cmd_interaction_visual_coverage_check",
    "cmd_interaction_trace_coverage_check",
    "cmd_interaction_prototype_check",
    "cmd_interaction_project",
    "cmd_interaction_resolve_feedback",
    "cmd_interaction_locator_check",
    "cmd_interaction_gate_run",
]
