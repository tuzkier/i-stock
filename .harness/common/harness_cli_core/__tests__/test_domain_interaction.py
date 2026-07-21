"""Unit tests for `harness_cli_core.domain.interaction`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.interaction import (  # noqa: E402
    DOMAIN_REF_RE,
    INTERACTION_REQUIRED_FILES,
    INTERACTION_REQUIRED_STATES,
    interaction_required_decision,
    interaction_product_dir,
    OPERABLE_PROTOTYPE_FORBIDDEN_RE,
    OPERABLE_PROTOTYPE_INTERACTIVE_RE,
    TRACE_REF_RE,
    alignment_current_payload,
    artifact_rel_path,
    artifact_role,
    collect_known_upstream_refs,
    collect_refs_from_path,
    collect_refs_from_value,
    contains_any,
    contains_ascii_wireframe,
    contract_feedback_sync_findings,
    covered_manifest_values,
    html_without_comments,
    interaction_prd_feedback_required,
    interaction_spec_dir,
    is_operable_prototype_artifact,
    is_placeholder_or_convention_ref,
    known_domain_refs,
    load_visual_manifest,
    resolve_feedback_routing,
    row_has_locator_strategy,
    scenario_rows_with_locator_obligation,
    spec_text_blob,
    state_has_na_reason,
)


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Constant tables
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# interaction_required_decision —— 原型必要性 = 阶段内确定记录 prototype-necessity.json
# 默认进入 interaction、阶段内判定；不读 use-case-model 的 UIC、不扫关键词
# ---------------------------------------------------------------------------

def _write_necessity(tmp_path: Path, mission: str, record: dict) -> None:
    from harness_cli_core.domain.interaction import prototype_necessity_path

    path = prototype_necessity_path(tmp_path, mission)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding="utf-8")


def test_interaction_required_true_when_determination_needed(tmp_path: Path) -> None:
    _write_necessity(tmp_path, "m1", {"needed": True, "reason": "有用户可观察界面", "decided_by": "agent"})
    d = interaction_required_decision(tmp_path, "m1")
    assert d["decided"] is True
    assert d["source"] == "determination"
    assert d["decided_by"] == "agent"


def test_interaction_required_false_when_determination_not_needed(tmp_path: Path) -> None:
    _write_necessity(tmp_path, "m2", {"needed": False, "reason": "纯后台批处理", "decided_by": "agent"})
    d = interaction_required_decision(tmp_path, "m2")
    assert d["decided"] is False
    assert d["source"] == "determination"


def test_interaction_required_none_when_no_determination(tmp_path: Path) -> None:
    # 无确定记录 = 尚未在阶段内判定 → 默认进入 interaction（不猜、不关键词）
    d = interaction_required_decision(tmp_path, "m3")
    assert d["decided"] is None
    assert d["source"] == "determination:absent"


def test_interaction_required_no_keyword_fallback(tmp_path: Path) -> None:
    # 即使产品定义正文里全是"原型/前端/用户旅程"等词，无确定记录仍判 None——不靠关键词
    _write(interaction_product_dir(tmp_path, "m4") / "use-case-model.md",
           "本任务做原型、前端、用户旅程、可视化界面。\n")
    assert interaction_required_decision(tmp_path, "m4")["decided"] is None


def test_required_files_and_states_match_workflow() -> None:
    # 新模型：手写真相源 = surface-model.md + behavior-graph.yaml（旧 3 散文已废弃）。
    assert "surface-model.md" in INTERACTION_REQUIRED_FILES
    assert "behavior-graph.yaml" in INTERACTION_REQUIRED_FILES
    assert "use-case-realization.md" not in INTERACTION_REQUIRED_FILES
    # STATE-* canonical 仍由旧 visual-coverage-check 的 fallback 使用，保留常量。
    assert "STATE-LOADING" in INTERACTION_REQUIRED_STATES
    assert "STATE-ERROR" in INTERACTION_REQUIRED_STATES


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

def test_domain_ref_re_matches_known_prefixes() -> None:
    assert DOMAIN_REF_RE.findall("see BO-USER and CMD-LOGIN") == ["BO-USER", "CMD-LOGIN"]


def test_trace_ref_re_matches_uppercase_ids_only() -> None:
    # The regex enforces uppercase / digit characters after the prefix dash;
    # lowercase tails and non-whitelisted prefixes are intentionally rejected.
    refs = TRACE_REF_RE.findall("SCN-1 TASK-2 FLOW-ONBOARD CMD-LOGIN")
    assert set(refs) == {"SCN-1", "TASK-2", "FLOW-ONBOARD", "CMD-LOGIN"}
    # lowercase tail not matched
    assert TRACE_REF_RE.findall("FLOW-onboarding") == []
    # unknown prefix not matched
    assert TRACE_REF_RE.findall("PT-CLI-A") == []


def test_trace_ref_re_matches_real_page_state_id() -> None:
    # 真 page_state id（PS-<surf>-<state>）现在被纳入 trace 体系：下游契约可引用它。
    refs = TRACE_REF_RE.findall("依赖 PS-SURF-BOARD-empty 与 SURF-BOARD")
    assert "PS-SURF-BOARD-empty" in refs
    assert "SURF-BOARD" in refs


def test_real_page_state_id_not_treated_as_placeholder() -> None:
    # 真 PS id 不被占位过滤；占位形态（PS-NN / PS-XX）仍被过滤。
    assert is_placeholder_or_convention_ref("PS-SURF-BOARD-empty") is False
    assert is_placeholder_or_convention_ref("PS-NN") is True
    assert is_placeholder_or_convention_ref("PS-XX") is True


def test_operable_prototype_interactive_re_detects_button() -> None:
    assert OPERABLE_PROTOTYPE_INTERACTIVE_RE.search("<button>OK</button>")
    assert OPERABLE_PROTOTYPE_INTERACTIVE_RE.search('<a href="/x">go</a>')
    assert not OPERABLE_PROTOTYPE_INTERACTIVE_RE.search("<p>just text</p>")


def test_operable_prototype_forbidden_re_detects_trace_id() -> None:
    assert OPERABLE_PROTOTYPE_FORBIDDEN_RE.search("trace: SCN-LOGIN")
    assert not OPERABLE_PROTOTYPE_FORBIDDEN_RE.search("plain product copy")


# ---------------------------------------------------------------------------
# collect_refs_from_value
# ---------------------------------------------------------------------------

def test_collect_refs_walks_nested_structures() -> None:
    payload = {
        "outer": [{"id": "SCN-1"}, {"nested": "see TASK-9"}],
        "scalar": "hello FLOW-X",
    }
    refs = collect_refs_from_value(payload, TRACE_REF_RE)
    assert refs == {"SCN-1", "TASK-9", "FLOW-X"}


def test_collect_refs_skips_template_placeholder_strings() -> None:
    refs = collect_refs_from_value({"a": "see {{ SCN-X }} placeholder"}, TRACE_REF_RE)
    assert refs == set()


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def test_contains_any_case_insensitive() -> None:
    assert contains_any("User Goal documented", ("user goal", "missing"))
    assert not contains_any("nothing here", ("user goal",))


def test_contains_ascii_wireframe_detects_keyword_and_box_drawing() -> None:
    assert contains_ascii_wireframe("wireframe sketch")
    assert contains_ascii_wireframe("线框图 in spec")
    assert contains_ascii_wireframe("\n  +---+\n  | A |\n  +---+\n")
    assert not contains_ascii_wireframe("plain prose without art")


def test_state_has_na_reason_recognises_chinese_and_english() -> None:
    text = "STATE-EMPTY: 不适用 because no list view"
    assert state_has_na_reason(text, "STATE-EMPTY")
    assert not state_has_na_reason("STATE-EMPTY just listed without reason", "STATE-EMPTY")


def test_html_without_comments_strips_block_comments() -> None:
    src = "<div>a</div><!-- secret --><span>b</span><!-- multi\nline --><p>c</p>"
    assert html_without_comments(src) == "<div>a</div><span>b</span><p>c</p>"


# ---------------------------------------------------------------------------
# Artifact role / path helpers
# ---------------------------------------------------------------------------

def test_artifact_rel_path_normalises_separators() -> None:
    assert artifact_rel_path({"path": ".\\prototype\\index.html"}) == "prototype/index.html"
    assert artifact_rel_path({"path": "./visual/index.html"}) == "visual/index.html"
    assert artifact_rel_path({}) == ""


def test_artifact_role_prefers_explicit_role_then_kind() -> None:
    assert artifact_role({"artifact_role": "OPERABLE_PROTOTYPE"}) == "operable_prototype"
    assert artifact_role({"role": "Primary"}) == "primary"
    assert artifact_role({"kind": "HTML"}) == "html"
    assert artifact_role({}) == ""


def test_is_operable_prototype_artifact_requires_html_type() -> None:
    assert is_operable_prototype_artifact(
        {"type": "html", "role": "operable_prototype", "path": "x/y.html"}
    )
    # role matches but type is wrong → False
    assert not is_operable_prototype_artifact(
        {"type": "png", "role": "operable_prototype", "path": "x/y.png"}
    )
    # known path triggers True even without role
    assert is_operable_prototype_artifact(
        {"type": "html", "path": "prototype/index.html"}
    )
    # mission artifact prototype copies are no longer accepted as primary entry
    assert not is_operable_prototype_artifact(
        {"type": "html", "path": "visual-interaction/prototype/index.html"}
    )


# ---------------------------------------------------------------------------
# Visual manifest helpers
# ---------------------------------------------------------------------------

def test_load_visual_manifest_falls_back_when_missing(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    path, data = load_visual_manifest(tmp_path, "M-1")
    assert data is None
    assert path.name == "visual-interaction-manifest.json"


def test_load_visual_manifest_parses_valid_json(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    manifest_path = (
        runtime / "stages" / "M-1" / "visual-interaction" / "visual-interaction-manifest.json"
    )
    _write(manifest_path, json.dumps({"artifacts": []}))
    path, data = load_visual_manifest(tmp_path, "M-1")
    assert path == manifest_path
    assert data == {"artifacts": []}


def test_covered_manifest_values_skips_placeholders_and_non_dict_items() -> None:
    manifest = {
        "artifacts": [
            {"covers": {"flows": ["FLOW-A", "{{ todo }}", "FLOW-B"]}},
            "not-a-dict",
            {"covers": {"flows": ["FLOW-A"]}},  # de-dup
        ]
    }
    assert covered_manifest_values(manifest, "flows") == {"FLOW-A", "FLOW-B"}


# ---------------------------------------------------------------------------
# Locator helpers
# ---------------------------------------------------------------------------

def test_scenario_rows_only_returns_rows_with_id_or_priority() -> None:
    text = (
        "| SCN-1 | desc | row |\n"
        "| no id | nothing | row |\n"
        "| E2E-LOGIN | ok | yes |\n"
        "| P0 | yes too | |\n"
    )
    rows = scenario_rows_with_locator_obligation(text)
    captured_ids = [line for _, line in rows]
    assert any("SCN-1" in r for r in captured_ids)
    assert any("E2E-LOGIN" in r for r in captured_ids)
    assert any("P0" in r for r in captured_ids)
    assert all("no id" not in r for r in captured_ids)


def test_row_has_locator_strategy_detects_data_testid() -> None:
    assert row_has_locator_strategy("| SCN-1 | data-testid=login-button |")
    assert row_has_locator_strategy("| SCN-1 | use getByRole('button') |")
    assert not row_has_locator_strategy("| SCN-1 | TBD |")


# ---------------------------------------------------------------------------
# PRD feedback + known domain refs (filesystem)
# ---------------------------------------------------------------------------

def test_known_domain_refs_collects_from_product_dir(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "stages" / "M-1" / "product" / "product-domain-model.md",
        "Aggregate BO-ORDER references ENT-USER.",
    )
    refs = known_domain_refs(tmp_path, "M-1")
    assert "BO-ORDER" in refs
    assert "ENT-USER" in refs


def test_interaction_prd_feedback_required_picks_up_explicit_flag(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    contract_path = (
        runtime / "stages" / "M-1" / "contracts" / "interaction.contract.yaml"
    )
    _write(
        contract_path,
        "control_contract:\n  prd_feedback:\n    requires_prd_feedback: true\n",
    )
    assert interaction_prd_feedback_required(tmp_path, "M-1") is True


def test_interaction_prd_feedback_required_false_when_resolved(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    contract_path = (
        runtime / "stages" / "M-1" / "contracts" / "interaction.contract.yaml"
    )
    _write(
        contract_path,
        "control_contract:\n  prd_feedback:\n    status: resolved\n",
    )
    assert interaction_prd_feedback_required(tmp_path, "M-1") is False


# ---------------------------------------------------------------------------
# spec_text_blob + interaction_spec_dir
# ---------------------------------------------------------------------------

def test_interaction_spec_dir_layout(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    # New default: stage content resolves to the artifact store.
    assert (
        interaction_spec_dir(tmp_path, "M-1")
        == runtime / "artifacts" / "M-1" / "interaction" / "interaction-spec"
    )


def test_interaction_spec_dir_prefers_artifact_store(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    artifact_spec = runtime / "artifacts" / "M-1" / "interaction" / "interaction-spec"
    artifact_spec.mkdir(parents=True)
    assert interaction_spec_dir(tmp_path, "M-1") == artifact_spec


def test_interaction_spec_dir_falls_back_to_legacy_stage(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    legacy_spec = runtime / "stages" / "M-1" / "interaction-spec"
    legacy_spec.mkdir(parents=True)
    # Artifact store absent → legacy stage layout is honored for back-compat.
    assert interaction_spec_dir(tmp_path, "M-1") == legacy_spec


def test_spec_text_blob_concatenates_supported_files(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    spec_dir = runtime / "stages" / "M-1" / "interaction-spec"
    _write(spec_dir / "a.md", "alpha\n")
    _write(spec_dir / "b.yaml", "key: value\n")
    _write(spec_dir / "ignore.png", "binary")  # not in allowed suffix list
    blob = spec_text_blob(tmp_path, "M-1")
    assert "alpha" in blob
    assert "key: value" in blob
    assert "binary" not in blob


# ---------------------------------------------------------------------------
# alignment helpers
# ---------------------------------------------------------------------------

def test_alignment_current_payload_interaction_returns_spec_refs(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    spec_dir = runtime / "stages" / "M-1" / "interaction-spec"
    _write(spec_dir / "surface-model.md", "covers SCN-A and FLOW-ONBOARD")
    stage, payload, path = alignment_current_payload(tmp_path, "M-1", "interaction")
    assert stage == "interaction"
    assert isinstance(payload, dict)
    refs = set(payload["spec_refs"])
    assert "SCN-A" in refs or "FLOW-ONBOARD" in refs
    assert path == spec_dir


def test_collect_refs_from_path_directory_walks_supported_files(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    spec_dir = runtime / "stages" / "M-1" / "interaction-spec"
    _write(spec_dir / "a.md", "SCN-A here")
    _write(spec_dir / "nested" / "b.yaml", "ref: SCN-B\n")
    _write(spec_dir / "skip.png", "binary")
    refs = collect_refs_from_path(spec_dir)
    assert "SCN-A" in refs
    assert "SCN-B" in refs


def test_collect_known_upstream_refs_uses_stage_order(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    _write(
        runtime / "missions" / "M-1" / "mission-contract.md",
        "introduces SCN-A",
    )
    _write(
        runtime / "stages" / "M-1" / "product" / "product-definition.md",
        "covers SCN-B",
    )
    refs = collect_known_upstream_refs(tmp_path, "M-1", "interaction")
    assert "SCN-A" in refs
    assert "SCN-B" in refs


# ---------------------------------------------------------------------------
# Feedback-sync findings shared helper
# ---------------------------------------------------------------------------

def test_contract_feedback_sync_findings_empty_when_no_count(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "stages" / "M-1" / "contracts" / "interaction.contract.yaml",
        "control_contract:\n  feedback_sync:\n    unsynced_feedback_count: '{{ todo }}'\n",
    )
    assert contract_feedback_sync_findings(tmp_path, "M-1", "interaction.contract.yaml") == []


def test_contract_feedback_sync_findings_flags_positive_count(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "stages" / "M-1" / "contracts" / "interaction.contract.yaml",
        "control_contract:\n  feedback_sync:\n    unsynced_feedback_count: 3\n",
    )
    findings = contract_feedback_sync_findings(tmp_path, "M-1", "interaction.contract.yaml")
    assert len(findings) == 1
    assert findings[0]["code"] == "FEEDBACK_NOT_SYNCED"
    assert findings[0]["unsynced_feedback_count"] == 3


_BINDINGS_CONTRACT = """\
control_contract:
  prototype:
    surface_bindings:
    - surf: SURF-301
      suc: [SUC-01]
      obj: [OBJ-01, OBJ-02]
      scn: [SCN-01]
      page_entry: '#board'
      anchor_root: '[data-testid="board-body"]'
    - surf: SURF-101
      suc: [SUC-03]
      obj: [OBJ-05]
      scn: [SCN-04]
      page_entry: '#chat/:mission/:thread'
      anchor_root: '[data-testid="chat-timeline-root"]'
    - surf: SURF-102
      suc: [SUC-01, SUC-03]
      obj: [OBJ-06]
      scn: []
      page_entry: 左栏
      anchor_root: '[data-testid="left-sidebar-root"]'
"""


def _bindings_root(tmp_path: Path) -> Path:
    _write(
        tmp_path / "harness-runtime" / "harness" / "stages" / "M-1" / "contracts" / "interaction.contract.yaml",
        _BINDINGS_CONTRACT,
    )
    return tmp_path


def test_resolve_feedback_by_surface_returns_single_binding(tmp_path: Path) -> None:
    root = _bindings_root(tmp_path)
    out = resolve_feedback_routing(root, "M-1", surface="SURF-301")
    assert out["binding"]["surf"] == "SURF-301"
    assert [b["surf"] for b in out["bindings"]] == ["SURF-301"]
    assert out["forward_nav"][0]["page_entry"] == "#board"


def test_resolve_feedback_by_suc_reverse_resolves_all_carrying_surfaces(tmp_path: Path) -> None:
    root = _bindings_root(tmp_path)
    out = resolve_feedback_routing(root, "M-1", suc="SUC-01")
    # SUC-01 is carried by SURF-301 and SURF-102 -> forward navigation must list both
    assert {b["surf"] for b in out["bindings"]} == {"SURF-301", "SURF-102"}
    entries = {n["surf"]: n["page_entry"] for n in out["forward_nav"]}
    assert entries["SURF-301"] == "#board"
    assert "use-case-model.md" in " ".join(out["upstream_candidates"])


def test_resolve_feedback_by_suc_matches_op_flow_children_to_base(tmp_path: Path) -> None:
    root = _bindings_root(tmp_path)
    out = resolve_feedback_routing(root, "M-1", suc="SUC-03-OP-02")
    # child id must reverse to the surfaces bound to its base SUC-03
    assert {b["surf"] for b in out["bindings"]} == {"SURF-101", "SURF-102"}


def test_resolve_feedback_by_obj_reverse_resolves_carrying_surface(tmp_path: Path) -> None:
    root = _bindings_root(tmp_path)
    out = resolve_feedback_routing(root, "M-1", obj="OBJ-05")
    assert {b["surf"] for b in out["bindings"]} == {"SURF-101"}
    assert out["forward_nav"][0]["anchor_root"] == '[data-testid="chat-timeline-root"]'


def test_trace_nav_entries_groups_surfaces_by_suc(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import trace_nav_entries
    root = _bindings_root(tmp_path)
    entries = trace_nav_entries(root, "M-1")
    by_suc = {e["suc"]: e["surfaces"] for e in entries}
    # SUC-01 carried by SURF-301 and SURF-102
    assert {s["surf"] for s in by_suc["SUC-01"]} == {"SURF-301", "SURF-102"}
    # page_entry / anchor_root carried through for deep-linking the embedded prototype
    s301 = next(s for s in by_suc["SUC-01"] if s["surf"] == "SURF-301")
    assert s301["page_entry"] == "#board"
    assert s301["anchor_root"] == '[data-testid="board-body"]'
    # entries sorted by SUC id
    assert [e["suc"] for e in entries] == ["SUC-01", "SUC-03"]


_WORKFLOWS_MD = """\
# Workflows
## Workflow Set
| BUC | 名称 | 主路径 surface | 验证优先级 |
|---|---|---|---|
| BUC-X-PROPOSE-001 | 创建 Mission | SUR-CHAT-TIMELINE + SUR-COMPOSER | P0 |
| BUC-X-START-001 | 应用 Onboarding | SUR-ONBOARDING | P0 |
"""

_UCM_MD = """\
### SUC-01：展示 Work Graph Board
### SUC-03：进入或创建 Mission 绑定对话
"""

_SURFACES_MD = """\
# UI Surfaces
| Surface ID | 名称 | 类型 | 关键职责 |
|---|---|---|---|
| SUR-CHAT-TIMELINE | 主面 chat timeline | core surface | 承载消息序列 |
| SUR-ONBOARDING | 应用 Onboarding | application surface | 首次启动身份确认 |
"""

_PROJECT_SUC_MD = """\
# 系统用例注册表
| SUC | 名称 | 实现 BUC | 承载 surface | 入口页 page_entry | 锚点 anchor_root | 来源 |
|---|---|---|---|---|---|---|
| SUC-TF-START-001 | 应用入驻 | BUC-TF-START-001 | SUR-ONBOARDING | onboarding.html | [data-testid="onboarding-root"] | M-0 |
| SUC-TF-RECOVER-001 | 失败恢复 | BUC-TF-RECOVER-001 | SUR-CHAT-TIMELINE | index.html | [data-testid="chat-timeline-root"] | M-0 |
"""

_FRAME_CONTRACT = """\
control_contract:
  prototype:
    surface_bindings:
    - surf: SURF-101
      suc: [SUC-03]
      obj: [OBJ-05]
      page_entry: 'index.html'
      anchor_root: '[data-testid="chat-timeline-root"]'
    - surf: SURF-102
      suc: [SUC-03]
      obj: [OBJ-06]
      page_entry: 'index.html'
      anchor_root: '[data-testid="left-sidebar-root"]'
    - surf: SUR-ONBOARDING
      suc: [BUC-X-START-001]
      obj: [OBJ-07]
      page_entry: 'onboarding.html'
      anchor_root: '[data-testid="onboarding-root"]'
  surface_baseline:
    surfaces:
    - id: SURF-101
      baseline_ref: SUR-CHAT-TIMELINE
      decision: extend_surface
    - id: SURF-301
      baseline_ref: none
      decision: create_surface
"""


def _frame_root(tmp_path: Path) -> Path:
    _write(tmp_path / "project-knowledge" / "product" / "workflows" / "wf.md", _WORKFLOWS_MD)
    _write(tmp_path / "project-knowledge" / "product" / "ui-surfaces" / "sur.md", _SURFACES_MD)
    _write(tmp_path / "project-knowledge" / "product" / "system-use-cases" / "suc.md", _PROJECT_SUC_MD)
    _write(
        tmp_path / "harness-runtime" / "harness" / "artifacts" / "M-1" / "product" / "use-case-model.md",
        _UCM_MD,
    )
    _write(
        tmp_path / "harness-runtime" / "harness" / "stages" / "M-1" / "contracts" / "interaction.contract.yaml",
        _FRAME_CONTRACT,
    )
    return tmp_path


def test_parse_project_use_cases_skips_header_and_extracts_surfaces(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import parse_project_use_cases
    _write(tmp_path / "project-knowledge" / "product" / "workflows" / "wf.md", _WORKFLOWS_MD)
    ucs = parse_project_use_cases(tmp_path)
    ids = [u["id"] for u in ucs]
    assert ids == ["BUC-X-PROPOSE-001", "BUC-X-START-001"]  # header row "BUC" skipped
    propose = ucs[0]
    assert propose["title"] == "创建 Mission"
    assert propose["surfaces"] == ["SUR-CHAT-TIMELINE", "SUR-COMPOSER"]
    assert propose["priority"] == "P0"


def test_parse_project_system_use_cases_extracts_registry(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import parse_project_system_use_cases
    _write(tmp_path / "project-knowledge" / "product" / "system-use-cases" / "suc.md", _PROJECT_SUC_MD)
    sucs = parse_project_system_use_cases(tmp_path)
    ids = [s["id"] for s in sucs]
    assert ids == ["SUC-TF-START-001", "SUC-TF-RECOVER-001"]  # 表头 "SUC" 行被跳过
    start = sucs[0]
    assert start["title"] == "应用入驻"
    assert start["surfaces"] == ["SUR-ONBOARDING"]
    assert start["page_entry"] == "onboarding.html"
    assert start["anchor_root"] == '[data-testid="onboarding-root"]'


def test_suc_titles_reads_use_case_model_headings(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import suc_titles
    root = _frame_root(tmp_path)
    titles = suc_titles(root, "M-1")
    assert titles["SUC-01"] == "展示 Work Graph Board"
    assert titles["SUC-03"] == "进入或创建 Mission 绑定对话"


def test_parse_project_surfaces_extracts_registry(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import parse_project_surfaces
    _write(tmp_path / "project-knowledge" / "product" / "ui-surfaces" / "sur.md", _SURFACES_MD)
    surfaces = parse_project_surfaces(tmp_path)
    ids = [s["id"] for s in surfaces]
    assert ids == ["SUR-CHAT-TIMELINE", "SUR-ONBOARDING"]  # header "Surface ID" skipped
    chat = surfaces[0]
    assert chat["name"] == "主面 chat timeline"
    assert chat["type"] == "core surface"
    assert chat["desc"] == "承载消息序列"


def test_prototype_frame_nav_lists_system_use_cases_one_per_suc(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import prototype_frame_nav
    root = _frame_root(tmp_path)
    nav = prototype_frame_nav(root, "M-1")
    # 左侧 item 遍历 SUC 生成：一个 SUC 一条（SUC-03 有 SURF-101/102 两条 binding，仍只一条）
    by_id = {f["id"]: f for f in nav["focus"]}
    assert list(by_id.keys()) == ["SUC-03"]
    chat = by_id["SUC-03"]
    assert chat["title"] == "进入或创建 Mission 绑定对话"
    assert chat["page_entry"] == "index.html"  # 入口页 = 第一个可路由 surface
    assert chat["focus"] is True
    assert set(chat["surfaces"]) == {"SURF-101", "SURF-102"}  # 该 SUC 涉及的界面边界（信息）
    # 项目已有 SUC = 项目级系统用例注册表沉淀（之前 Mission 已实现的能力），均为 SUC-*
    proj = {p["id"]: p for p in nav["project"]}
    assert set(proj.keys()) == {"SUC-TF-START-001", "SUC-TF-RECOVER-001"}
    assert proj["SUC-TF-START-001"]["page_entry"] == "onboarding.html"
    assert proj["SUC-TF-START-001"]["focus"] is False
    assert proj["SUC-TF-RECOVER-001"]["page_entry"] == "index.html"
    # 业务用例(BUC)与组件级 surface 不作为左侧导航项；左侧全是 SUC
    all_ids = [c["id"] for c in nav["focus"] + nav["project"]]
    assert all(i.startswith("SUC-") for i in all_ids)
    assert all(not i.startswith("BUC-") for i in all_ids)
    assert "SUR-CHAT-TIMELINE" not in all_ids and "SUR-ONBOARDING" not in all_ids


def test_extract_field_anchor_ids_parses_dotted_tokens() -> None:
    from harness_cli_core.domain.interaction import extract_field_anchor_ids
    html = '<span data-field="OBJ-02.id OBJ-02.title">x</span><b data-field="OBJ-04.lane">y</b><i data-field="bad">z</i>'
    out = extract_field_anchor_ids(html)
    assert out["OBJ-02"] == {"id", "title"}
    assert out["OBJ-04"] == {"lane"}
    assert "bad" not in out  # malformed token ignored


_FIELDS_CONTRACT = """\
control_contract:
  prototype:
    surface_bindings:
    - surf: SURF-301
      obj: [OBJ-02, OBJ-06]
      fields:
        OBJ-02: [id, title, status]
        OBJ-06: []
"""


def test_interaction_field_bindings_parses_declared_and_waived(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import interaction_field_bindings
    _write(tmp_path / "harness-runtime" / "harness" / "stages" / "M-1" / "contracts" / "interaction.contract.yaml", _FIELDS_CONTRACT)
    fb = interaction_field_bindings(tmp_path, "M-1")
    assert fb["bound_objs"] == {"OBJ-02", "OBJ-06"}
    assert fb["declared"]["OBJ-02"] == {"id", "title", "status"}
    assert fb["waived"] == {"OBJ-06"}
    assert fb["objs_with_fields_key"] == {"OBJ-02", "OBJ-06"}


def test_field_coverage_findings_full_enforcement() -> None:
    from harness_cli_core.domain.interaction import field_coverage_findings
    # OBJ-02 declared [id,title,status]; OBJ-06 waived []; OBJ-03 bound but never declared
    fb_codes = lambda f: f["code"]
    findings = field_coverage_findings(
        bound_objs={"OBJ-02", "OBJ-06", "OBJ-03"},
        declared={"OBJ-02": {"id", "title", "status"}},
        waived={"OBJ-06"},
        objs_with_fields_key={"OBJ-02", "OBJ-06"},
        proto_fields={"OBJ-02": {"id", "title"}, "OBJ-06": {"scope"}},
    )
    codes = {f["code"] for f in findings}
    # OBJ-03 bound but no fields key -> undeclared
    assert "TRACE_OBJ_FIELDS_UNDECLARED" in codes
    # OBJ-02.status declared but not anchored -> not anchored
    assert any(f["code"] == "TRACE_OBJ_FIELD_NOT_ANCHORED" and f.get("field") == "status" for f in findings)
    # OBJ-06 waived but prototype anchored a field -> contradiction
    assert "TRACE_FIELD_ANCHOR_ON_WAIVED_OBJ" in codes


def test_field_coverage_findings_clean_when_fully_covered() -> None:
    from harness_cli_core.domain.interaction import field_coverage_findings
    findings = field_coverage_findings(
        bound_objs={"OBJ-02", "OBJ-06"},
        declared={"OBJ-02": {"id", "title"}},
        waived={"OBJ-06"},
        objs_with_fields_key={"OBJ-02", "OBJ-06"},
        proto_fields={"OBJ-02": {"id", "title"}},
    )
    assert findings == []


def test_project_object_registry_ids_parses_obj_ids(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import project_object_registry_ids
    _write(tmp_path / "project-knowledge" / "product" / "business-objects.md",
           "| OBJ id | 对象 |\n|---|---|\n| OBJ-06 | Workspace |\n| OBJ-07 | User |\n")
    assert project_object_registry_ids(tmp_path) == {"OBJ-06", "OBJ-07"}


def test_project_use_case_ids_from_workflows(tmp_path: Path) -> None:
    from harness_cli_core.domain.interaction import project_use_case_ids
    _write(tmp_path / "project-knowledge" / "product" / "workflows" / "wf.md", _WORKFLOWS_MD)
    assert project_use_case_ids(tmp_path) == {"BUC-X-PROPOSE-001", "BUC-X-START-001"}


def test_extract_anchors_recognizes_setattribute_form() -> None:
    from harness_cli_core.domain.interaction import extract_data_anchor_ids, extract_field_anchor_ids
    # JS-created elements set anchors via setAttribute instead of literal HTML attrs
    js = "wrap.setAttribute('data-obj', 'OBJ-08 OBJ-09'); el.setAttribute('data-field', 'OBJ-08.kind OBJ-09.id');"
    anchors = extract_data_anchor_ids(js)
    assert anchors["obj"] == {"OBJ-08", "OBJ-09"}
    fields = extract_field_anchor_ids(js)
    assert fields["OBJ-08"] == {"kind"}
    assert fields["OBJ-09"] == {"id"}
