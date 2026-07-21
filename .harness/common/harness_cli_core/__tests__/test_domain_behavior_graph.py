"""Unit tests for the behavior-graph SSOT model: parsing, reachability, the single
reconcile (bijections + coverage), view projection and feedback navigation."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain import behavior_graph as bg  # noqa: E402


def _codes(findings, category=None):
    return [f["code"] for f in findings if category is None or f.get("category") == category]


SURF_CATALOG = {"SURF-BOARD": {"via_controls": {"workspace-switcher"}}}


def _graph():
    return {
        "page_states": [
            {"id": "PS-SURF-BOARD-loading", "surf": "SURF-BOARD", "page_entry": "board.html", "state": "loading", "anchor_root": "[data-state=loading]"},
            {"id": "PS-SURF-BOARD-data", "surf": "SURF-BOARD", "page_entry": "board.html", "state": "data",
             "objects": [{"obj": "OBJ-01", "fields": ["id"], "state": "readable"}]},
            {"id": "PS-SURF-BOARD-empty", "surf": "SURF-BOARD", "page_entry": "board.html", "state": "empty"},
        ],
        "steps": [
            {"id": "SUC-01-FLOW-01.loading", "suc": "SUC-01", "page_state": "PS-SURF-BOARD-loading"},
            {"id": "SUC-01-FLOW-01.data", "suc": "SUC-01", "page_state": "PS-SURF-BOARD-data", "acceptance_refs": ["SCN-01"]},
            {"id": "SUC-01-FLOW-01.empty", "suc": "SUC-01", "page_state": "PS-SURF-BOARD-empty", "acceptance_refs": ["SCN-02"]},
        ],
        "edges": [
            {"from": "ENTRY", "to": "SUC-01-FLOW-01.loading", "kind": "action", "desc": "打开", "e2e_obligation": True, "testid": "board-open"},
            {"from": "SUC-01-FLOW-01.loading", "to": "SUC-01-FLOW-01.data", "kind": "system_event", "desc": "有节点", "via": "SURF-BOARD/workspace-switcher"},
            {"from": "SUC-01-FLOW-01.loading", "to": "SUC-01-FLOW-01.empty", "kind": "system_event", "desc": "无节点", "via": "SURF-BOARD/workspace-switcher"},
        ],
        "flows": [
            {"id": "主成功流", "suc": "SUC-01", "path": ["SUC-01-FLOW-01.loading", "SUC-01-FLOW-01.data"]},
            {"id": "备选流-空", "suc": "SUC-01", "path": ["SUC-01-FLOW-01.loading", "SUC-01-FLOW-01.empty"]},
        ],
    }


def _all_anchors(graph):
    t = bg.graph_tables(graph)
    return {
        "steps": {str(s["id"]) for s in t["steps"]},
        "page_states": {str(p["id"]) for p in t["page_states"]},
        "vias": {"SURF-BOARD/workspace-switcher"},
        "testids": {"board-open"},
    }


# ---- surface catalog parsing ----

def test_parse_surface_catalog_fixed_columns():
    cat = bg.parse_surface_catalog(
        "| surface id | 名称 | 类型 | baseline 关系 | page_entry | via 控件清单 |\n"
        "|---|---|---|---|---|---|\n"
        "| SURF-BOARD | 看板 | page | create | board.html | workspace-switcher, refresh-btn |\n"
    )
    assert cat["SURF-BOARD"]["via_controls"] == {"workspace-switcher", "refresh-btn"}
    assert cat["SURF-BOARD"]["page_entry"] == "board.html"


# ---- reachability ----

def test_reachable_from_entry():
    t = bg.graph_tables(_graph())
    assert bg.reachable_step_ids(t["steps"], t["edges"]) == {
        "SUC-01-FLOW-01.loading", "SUC-01-FLOW-01.data", "SUC-01-FLOW-01.empty",
    }


def _orphan_graph():
    graph = _graph()
    graph["page_states"].append({"id": "PS-SURF-BOARD-orphan", "surf": "SURF-BOARD", "page_entry": "board.html", "state": "orphan"})
    graph["steps"].append({"id": "SUC-01-FLOW-01.orphan", "suc": "SUC-01", "page_state": "PS-SURF-BOARD-orphan"})
    return graph


def test_orphan_pagestate_flagged_unreachable():
    # no edge targets the orphan step
    f = bg.reconcile_findings(tables=bg.graph_tables(_orphan_graph()), surfaces=SURF_CATALOG, proto_anchors=None)
    assert "PAGESTATE_UNREACHABLE" in _codes(f, "reachability")


# ---- reachability gate level (#1) ----

def _unreachable_finding(findings):
    return next((x for x in findings if x["code"] == "PAGESTATE_UNREACHABLE"), None)


def test_unreachable_defaults_to_fail():
    f = bg.reconcile_findings(tables=bg.graph_tables(_orphan_graph()), surfaces=SURF_CATALOG, proto_anchors=None)
    assert _unreachable_finding(f)["level"] == "FAIL"


def test_unreachable_warn_level_downgrades():
    f = bg.reconcile_findings(
        tables=bg.graph_tables(_orphan_graph()), surfaces=SURF_CATALOG, proto_anchors=None,
        reachability_level="warn",
    )
    assert _unreachable_finding(f)["level"] == "WARN"


def test_unreachable_unknown_level_falls_back_to_fail():
    f = bg.reconcile_findings(
        tables=bg.graph_tables(_orphan_graph()), surfaces=SURF_CATALOG, proto_anchors=None,
        reachability_level="bogus",
    )
    assert _unreachable_finding(f)["level"] == "FAIL"


def test_resolve_reachability_level():
    assert bg.resolve_reachability_level({}) == "fail"
    assert bg.resolve_reachability_level({"interaction": {"reachability_gate_level": "warn"}}) == "warn"
    assert bg.resolve_reachability_level({"interaction": {"reachability_gate_level": "FAIL"}}) == "fail"
    assert bg.resolve_reachability_level({"interaction": {"reachability_gate_level": "bogus"}}) == "fail"


# ---- the core: SUC-internal branch coverage (the bug this redesign fixes) ----

def test_clean_graph_with_full_anchors_passes():
    graph = _graph()
    f = bg.reconcile_findings(
        tables=bg.graph_tables(graph), surfaces=SURF_CATALOG,
        proto_anchors=_all_anchors(graph), manifest_viewports={"desktop", "mobile"},
    )
    assert [x for x in f if x["level"] == "FAIL"] == []


def test_missing_branch_anchor_is_caught_per_state():
    """The old bug: anchoring SUC-01 once counted all branches covered. Now each
    page-state/step must be individually anchored."""
    graph = _graph()
    anchors = _all_anchors(graph)
    # prototype only anchored the 'data' branch, dropped 'empty'
    anchors["steps"].discard("SUC-01-FLOW-01.empty")
    anchors["page_states"].discard("PS-SURF-BOARD-empty")
    f = bg.reconcile_findings(
        tables=bg.graph_tables(graph), surfaces=SURF_CATALOG,
        proto_anchors=anchors, manifest_viewports={"desktop", "mobile"},
    )
    codes = _codes(f)
    assert "TRACE_STEP_NOT_ANCHORED" in codes
    assert "TRACE_PAGESTATE_NOT_ANCHORED" in codes
    assert "VISUAL_STEP_COVERAGE_MISSING" in codes


# ---- graph self-consistency ----

def test_step_pagestate_unresolved():
    graph = _graph()
    graph["steps"][0]["page_state"] = "PS-DOES-NOT-EXIST"
    f = bg.reconcile_findings(tables=bg.graph_tables(graph), surfaces=SURF_CATALOG, proto_anchors=None)
    assert "GRAPH_STEP_PAGESTATE_UNRESOLVED" in _codes(f, "graph")


def test_system_event_without_via():
    graph = _graph()
    graph["edges"][1]["via"] = None
    f = bg.reconcile_findings(tables=bg.graph_tables(graph), surfaces=SURF_CATALOG, proto_anchors=None)
    assert "GRAPH_SYSTEM_EVENT_MISSING_VIA" in _codes(f, "graph")


def test_via_undeclared_in_surface_catalog():
    graph = _graph()
    graph["edges"][1]["via"] = "SURF-BOARD/ghost-control"
    f = bg.reconcile_findings(tables=bg.graph_tables(graph), surfaces=SURF_CATALOG, proto_anchors=None)
    assert "EDGE_VIA_UNDECLARED" in _codes(f, "graph")


def test_pagestate_surf_unknown():
    graph = _graph()
    graph["page_states"][0]["surf"] = "SURF-GHOST"
    f = bg.reconcile_findings(tables=bg.graph_tables(graph), surfaces=SURF_CATALOG, proto_anchors=None)
    assert "GRAPH_PAGESTATE_SURF_UNKNOWN" in _codes(f, "graph")


def test_flow_sequence_broken():
    graph = _graph()
    graph["flows"][0]["path"] = ["SUC-01-FLOW-01.loading", "SUC-01-FLOW-01.empty"]  # no edge loading->... wait empty has edge
    # break it: insert a pair with no edge
    graph["flows"][0]["path"] = ["SUC-01-FLOW-01.data", "SUC-01-FLOW-01.empty"]
    f = bg.reconcile_findings(tables=bg.graph_tables(graph), surfaces=SURF_CATALOG, proto_anchors=None)
    assert "FLOW_SEQUENCE_BROKEN" in _codes(f, "reachability")


# ---- anchor dangling ----

def test_dangling_prototype_anchor():
    graph = _graph()
    anchors = _all_anchors(graph)
    anchors["steps"].add("SUC-99-FLOW-09.ghost")
    f = bg.reconcile_findings(
        tables=bg.graph_tables(graph), surfaces=SURF_CATALOG,
        proto_anchors=anchors, manifest_viewports={"desktop", "mobile"},
    )
    assert "TRACE_ANCHOR_STEP_DANGLING" in _codes(f, "anchor")


# ---- prototype absent ----

def test_prototype_absent_skips_anchor_checks():
    f = bg.reconcile_findings(tables=bg.graph_tables(_graph()), surfaces=SURF_CATALOG, proto_anchors=None)
    assert "PROTOTYPE_ABSENT" in _codes(f)
    assert "TRACE_STEP_NOT_ANCHORED" not in _codes(f)


# ---- upstream ----

def test_prd_step_unbound_warns():
    f = bg.reconcile_findings(
        tables=bg.graph_tables(_graph()), surfaces=SURF_CATALOG, proto_anchors=None,
        prd_abstract_steps={"SUC-01-FLOW-09.ghost"},
    )
    assert "UPSTREAM_PRD_STEP_UNBOUND" in _codes(f, "upstream")


# ---- locator ----

def test_e2e_edge_testid_missing_in_prototype():
    graph = _graph()
    anchors = _all_anchors(graph)
    anchors["testids"].discard("board-open")
    f = bg.reconcile_findings(
        tables=bg.graph_tables(graph), surfaces=SURF_CATALOG,
        proto_anchors=anchors, manifest_viewports={"desktop", "mobile"},
    )
    assert "LOCATOR_MISSING_FOR_E2E_EDGE" in _codes(f, "locator")


# ---- views + walkthrough projection ----

def test_views_and_walkthrough_render():
    graph = _graph()
    assert "# 走查视图" in bg.render_by_suc_view(graph)
    assert "SUC-01-FLOW-01.empty" in bg.render_by_suc_view(graph)
    assert "# 建页视图" in bg.render_by_surface_view(graph)
    assert "OBJ-01" in bg.render_by_object_view(graph)
    js = bg.walkthrough_js(graph)
    assert js.startswith("window.__HARNESS_WALKTHROUGH__")
    wt = bg.walkthrough_index(graph)
    assert wt["by_suc"][0]["suc"] == "SUC-01"
    assert len(wt["by_suc"][0]["flows"]) == 2


def test_resolve_feedback_from_graph_forward_nav():
    nav = bg.resolve_feedback_from_graph(_graph(), step="SUC-01-FLOW-01.empty")
    assert nav["forward_nav"]
    assert nav["forward_nav"][0]["page_state"] == "PS-SURF-BOARD-empty"
    assert nav["forward_nav"][0]["page_entry"] == "board.html"


# ---- N/A 豁免（机器段）解析与校验 (#2a/#2b) ----

_NA_TABLE = (
    "## N/A 豁免（机器段）\n"
    "| PRD 节点 id | 豁免粒度 | 理由 | 责任归属 |\n"
    "|------------|----------|------|----------|\n"
    "| {{node}} | suc | {{reason}} | {{owner}} |\n"  # 模板占位行：首列不匹配 → 跳过
    "| SUC-07 | suc | 纯后台批处理用例，无任何用户可观察界面承载 | product-owner |\n"
    "这是一段散文，含 SUC-09 但不在表里，应被跳过。\n"
)


def test_parse_na_exemptions_fixed_columns():
    rows = bg.parse_na_exemptions(_NA_TABLE)
    assert len(rows) == 1
    assert rows[0] == {
        "node": "SUC-07", "granularity": "suc",
        "reason": "纯后台批处理用例，无任何用户可观察界面承载", "owner": "product-owner",
    }


def test_na_exemption_grants_suc_level_exempt():
    rows = bg.parse_na_exemptions(
        "| SUC-07 | suc | 后台批处理无界面 | product-owner |\n"
    )
    exempt, findings = bg.na_exemption_findings(
        exemptions=rows, graph=_graph(),
        prd_sucs={"SUC-07"}, prd_flowsteps=set(), prd_beats=set(),
    )
    assert exempt == {"SUC-07"}
    assert [x for x in findings if x["level"] == "FAIL"] == []


def test_na_exemption_stale_when_suc_in_graph():
    rows = bg.parse_na_exemptions("| SUC-01 | suc | 其实有界面 | po |\n")
    exempt, findings = bg.na_exemption_findings(
        exemptions=rows, graph=_graph(),
        prd_sucs={"SUC-01"}, prd_flowsteps=set(), prd_beats=set(),
    )
    assert "NA_EXEMPTION_STALE" in _codes(findings, "upstream")
    assert "SUC-01" not in exempt


def test_na_exemption_stale_flowstep_and_beat():
    rows = bg.parse_na_exemptions("| SUC-01-FLOW-01 | flowstep | 其实有界面 | po |\n")
    _e, f = bg.na_exemption_findings(
        exemptions=rows, graph=_graph(), prd_sucs=set(),
        prd_flowsteps={"SUC-01-FLOW-01"}, prd_beats=set(),
    )
    assert "NA_EXEMPTION_STALE" in _codes(f, "upstream")
    rows2 = bg.parse_na_exemptions("| SUC-01-FLOW-01.empty | beat | 其实有界面 | po |\n")
    _e2, f2 = bg.na_exemption_findings(
        exemptions=rows2, graph=_graph(), prd_sucs=set(),
        prd_flowsteps=set(), prd_beats={"SUC-01-FLOW-01.empty"},
    )
    assert "NA_EXEMPTION_STALE" in _codes(f2, "upstream")


def test_na_exemption_incomplete_reason_or_owner():
    rows = bg.parse_na_exemptions("| SUC-07 | suc | {{reason}} | po |\n")
    _e, f = bg.na_exemption_findings(
        exemptions=rows, graph=_graph(), prd_sucs={"SUC-07"}, prd_flowsteps=set(), prd_beats=set(),
    )
    assert "NA_EXEMPTION_INCOMPLETE" in _codes(f, "upstream")


def test_na_exemption_bad_granularity():
    rows = bg.parse_na_exemptions("| SUC-07 | page | 后台 | po |\n")
    _e, f = bg.na_exemption_findings(
        exemptions=rows, graph=_graph(), prd_sucs={"SUC-07"}, prd_flowsteps=set(), prd_beats=set(),
    )
    assert "NA_EXEMPTION_BAD_GRANULARITY" in _codes(f, "upstream")


def test_na_exemption_node_granularity_mismatch():
    rows = bg.parse_na_exemptions("| SUC-09 | beat | 后台 | po |\n")
    _e, f = bg.na_exemption_findings(
        exemptions=rows, graph=_graph(), prd_sucs={"SUC-09"}, prd_flowsteps=set(), prd_beats=set(),
    )
    assert "NA_EXEMPTION_NODE_GRANULARITY_MISMATCH" in _codes(f, "upstream")


def test_na_exemption_unknown_node_warns():
    rows = bg.parse_na_exemptions("| SUC-99 | suc | 后台 | po |\n")
    _e, f = bg.na_exemption_findings(
        exemptions=rows, graph=_graph(), prd_sucs={"SUC-07"}, prd_flowsteps=set(), prd_beats=set(),
    )
    assert "NA_EXEMPTION_UNKNOWN_NODE" in _codes(f, "upstream")
    assert all(x["level"] != "FAIL" for x in f if x["code"] == "NA_EXEMPTION_UNKNOWN_NODE")


# ---- PRD 扇出 token 完整性 (#2c) ----

def test_prd_fanout_beats_missing():
    f = bg.prd_fanout_token_findings(
        ucm_text="流步骤 SUC-01-FLOW-03 扇出 多个结局",
        prd_flowsteps={"SUC-01-FLOW-03"}, prd_beats=set(),
    )
    assert "PRD_FANOUT_BEATS_MISSING" in _codes(f, "upstream")


def test_prd_fanout_satisfied_when_beat_present():
    f = bg.prd_fanout_token_findings(
        ucm_text="流步骤 SUC-01-FLOW-03 扇出 多个结局 SUC-01-FLOW-03.empty",
        prd_flowsteps={"SUC-01-FLOW-03"}, prd_beats={"SUC-01-FLOW-03.empty"},
    )
    assert f == []


def test_prd_fanout_single_outcome_not_flagged():
    f = bg.prd_fanout_token_findings(
        ucm_text="流步骤 SUC-01-FLOW-03 单一结局，正常返回",
        prd_flowsteps={"SUC-01-FLOW-03"}, prd_beats=set(),
    )
    assert f == []


def test_prd_fanout_convention_note_not_flagged():
    # 约定 / 解释段（含「不在此列」「单结局」或引文 `>`）解释扇出规约本身，不是对某 fs 的扇出声明。
    ucm = (
        "> 凡一个流步骤会扇出多个结局，逐个拆成节拍。单结局流步骤（SUC-01-FLOW-02 扫描 node）不在此列。\n"
    )
    f = bg.prd_fanout_token_findings(
        ucm_text=ucm, prd_flowsteps={"SUC-01-FLOW-02"}, prd_beats=set(),
    )
    assert f == []


# ---------------------------------------------------------------------------
# 下游原型覆盖率门 downstream_prototype_coverage_findings
# ---------------------------------------------------------------------------

def test_downstream_coverage_surf_all_carried_passes():
    # solution/tech 卡 SURF 级：所有 SURF 都被下游承载 → 空 findings。
    findings = bg.downstream_prototype_coverage_findings(
        merged_graph=_graph(), surface_catalog=SURF_CATALOG,
        carried_refs={"SURF-BOARD"}, stage="solution",
    )
    assert findings == []


def test_downstream_coverage_surf_missing_fails():
    # surface_catalog 多出一个 SURF，下游没承载 → 1 条 SURFACE_NOT_CARRIED。
    catalog = dict(SURF_CATALOG)
    catalog["SURF-DETAIL"] = {"via_controls": set()}
    findings = bg.downstream_prototype_coverage_findings(
        merged_graph=_graph(), surface_catalog=catalog,
        carried_refs={"SURF-BOARD"}, stage="technical_analysis",
    )
    assert _codes(findings, "prototype_coverage") == ["SURFACE_NOT_CARRIED"]
    assert findings[0]["surf"] == "SURF-DETAIL"
    assert findings[0]["level"] == "FAIL"


def test_downstream_coverage_breakdown_missing_pagestate_fails():
    # breakdown 卡 PS 级：缺承载某个 page_state → PAGESTATE_NOT_COVERED。
    findings = bg.downstream_prototype_coverage_findings(
        merged_graph=_graph(), surface_catalog=SURF_CATALOG,
        carried_refs={"PS-SURF-BOARD-loading", "PS-SURF-BOARD-data"},
        stage="breakdown",
    )
    codes = _codes(findings, "prototype_coverage")
    assert codes == ["PAGESTATE_NOT_COVERED"]
    assert findings[0]["page_state"] == "PS-SURF-BOARD-empty"


def test_downstream_coverage_solution_does_not_check_pagestate():
    # solution 阶段只卡 SURF：即便一个 PS 都没承载，只要 SURF 承载就 PASS。
    findings = bg.downstream_prototype_coverage_findings(
        merged_graph=_graph(), surface_catalog=SURF_CATALOG,
        carried_refs={"SURF-BOARD"}, stage="solution",
    )
    assert findings == []


def test_downstream_coverage_legal_exemption_grants_pass():
    # breakdown 缺一个 PS，但带合法豁免（id+理由）→ 豁免放行，空 findings。
    findings = bg.downstream_prototype_coverage_findings(
        merged_graph=_graph(), surface_catalog=SURF_CATALOG,
        carried_refs={"PS-SURF-BOARD-loading", "PS-SURF-BOARD-data"},
        stage="breakdown",
        exemptions={"PS-SURF-BOARD-empty": "空态由后端兜底，决策门已登记"},
    )
    assert findings == []


def test_downstream_coverage_exemption_without_reason_fails():
    # 豁免无理由 → PROTOTYPE_EXEMPTION_NO_REASON，且该 PS 仍未被放行（因豁免无效）。
    findings = bg.downstream_prototype_coverage_findings(
        merged_graph=_graph(), surface_catalog=SURF_CATALOG,
        carried_refs={"PS-SURF-BOARD-loading", "PS-SURF-BOARD-data"},
        stage="breakdown",
        exemptions={"PS-SURF-BOARD-empty": "   "},
    )
    codes = set(_codes(findings, "prototype_coverage"))
    assert "PROTOTYPE_EXEMPTION_NO_REASON" in codes
    assert "PAGESTATE_NOT_COVERED" in codes


def test_downstream_coverage_empty_graph_never_fails():
    # 无图（非 UI 任务 / 未跑 interaction）→ 分母为空 → 空 findings，绝不 FAIL。
    for stage in ("solution", "technical_analysis", "breakdown"):
        findings = bg.downstream_prototype_coverage_findings(
            merged_graph={}, surface_catalog={}, carried_refs=set(), stage=stage,
        )
        assert findings == []


def test_downstream_coverage_unknown_stage_no_findings():
    # 不参与覆盖率门的 stage（如 verify）→ 空 findings。
    findings = bg.downstream_prototype_coverage_findings(
        merged_graph=_graph(), surface_catalog=SURF_CATALOG,
        carried_refs=set(), stage="verify",
    )
    assert findings == []


# ---------------------------------------------------------------------------
# prototype_e2e_alignment_coverage —— verify 阶段原型对齐 e2e 机器门
# ---------------------------------------------------------------------------

def _e2e_graph(*edges):
    """构造仅含 edges 表的最小图（本门只读 edges）。每个 edge dict 直接透传。"""
    return {"page_states": [], "steps": [], "edges": list(edges), "flows": []}


# 两条 e2e_obligation 边（testid: a / b），外加一条普通边（不计入必需集）。
_TWO_OBLIGATION_EDGES = (
    {"from": "S1", "to": "S2", "kind": "action", "e2e_obligation": True, "testid": "board-open"},
    {"from": "S2", "to": "S3", "kind": "action", "e2e_obligation": True, "testid": "board-add-card"},
    {"from": "S3", "to": "S4", "kind": "system_event", "via": "v"},  # 非义务边，忽略
)


def test_e2e_alignment_full_coverage_is_empty():
    # 必需 testid 全部被通过断言覆盖 → 空 findings。
    findings = bg.prototype_e2e_alignment_coverage(
        graph=_e2e_graph(*_TWO_OBLIGATION_EDGES),
        covered_testids={"board-open", "board-add-card"},
        exemptions={},
    )
    assert findings == []


def test_e2e_alignment_missing_one_fails():
    # 缺一个 testid 的断言绑定 → 该 testid 产 FAIL PROTOTYPE_E2E_EDGE_NOT_ASSERTED。
    findings = bg.prototype_e2e_alignment_coverage(
        graph=_e2e_graph(*_TWO_OBLIGATION_EDGES),
        covered_testids={"board-open"},
        exemptions={},
    )
    codes = _codes(findings, "prototype_alignment")
    assert codes == ["PROTOTYPE_E2E_EDGE_NOT_ASSERTED"]
    assert findings[0]["level"] == "FAIL"
    assert findings[0]["testid"] == "board-add-card"


def test_e2e_alignment_placeholder_testid_warns_not_fails():
    # 声明 e2e_obligation 但 testid 占位 / 缺失 → WARN E2E_OBLIGATION_EDGE_NO_TESTID，不 FAIL。
    findings = bg.prototype_e2e_alignment_coverage(
        graph=_e2e_graph(
            {"from": "S1", "to": "S2", "e2e_obligation": True, "testid": "{{TODO}}"},
            {"from": "S2", "to": "S3", "e2e_obligation": True},  # testid 缺失
        ),
        covered_testids=set(),
        exemptions={},
    )
    levels = {f["level"] for f in findings}
    codes = set(_codes(findings, "prototype_alignment"))
    assert levels == {"WARN"}
    assert codes == {"E2E_OBLIGATION_EDGE_NO_TESTID"}
    assert len(findings) == 2


def test_e2e_alignment_legal_exemption_grants_pass():
    # 缺一个 testid，但带合法豁免（testid+理由）→ 豁免放行，空 findings。
    findings = bg.prototype_e2e_alignment_coverage(
        graph=_e2e_graph(*_TWO_OBLIGATION_EDGES),
        covered_testids={"board-open"},
        exemptions={"board-add-card": "该转移本期改由后端事件触发，决策门已登记 N/A"},
    )
    assert findings == []


def test_e2e_alignment_exemption_without_reason_fails():
    # 豁免无理由 → PROTOTYPE_EXEMPTION_NO_REASON，且该 testid 仍未放行（豁免无效）。
    findings = bg.prototype_e2e_alignment_coverage(
        graph=_e2e_graph(*_TWO_OBLIGATION_EDGES),
        covered_testids={"board-open"},
        exemptions={"board-add-card": "   "},
    )
    codes = set(_codes(findings, "prototype_alignment"))
    assert "PROTOTYPE_EXEMPTION_NO_REASON" in codes
    assert "PROTOTYPE_E2E_EDGE_NOT_ASSERTED" in codes


def test_e2e_alignment_no_graph_never_fails():
    # 无图 / 无 edges / 无义务边 → 空 findings，绝不 FAIL。
    for graph in ({}, {"edges": []}, _e2e_graph({"from": "S1", "to": "S2", "kind": "action"})):
        findings = bg.prototype_e2e_alignment_coverage(
            graph=graph, covered_testids=set(), exemptions={},
        )
        assert findings == []


# ===========================================================================
# composition axis (region tree / layout skeleton)
# ===========================================================================

_REGION_CAT = {
    "R-BOARD-main": {"surf": "SURF-BOARD", "parent": "root", "layout": "grid",
                     "priority": "primary", "role": "content", "carries": "", "scan_order": 1},
}


def _comp_graph(*, region="R-BOARD-main", fields=("id",), surf="SURF-BOARD"):
    obj = {"obj": "OBJ-01", "fields": list(fields), "state": "readable"}
    if region is not None:
        obj["region"] = region
    return {
        "page_states": [
            {"id": "PS-SURF-BOARD-data", "surf": surf, "page_entry": "board.html",
             "state": "data", "objects": [obj]},
        ],
        "steps": [{"id": "SUC-01-FLOW-01.data", "suc": "SUC-01", "page_state": "PS-SURF-BOARD-data"}],
        "edges": [{"from": "ENTRY", "to": "SUC-01-FLOW-01.data", "kind": "action", "desc": "x"}],
        "flows": [{"id": "f", "suc": "SUC-01", "path": ["SUC-01-FLOW-01.data"]}],
    }


def _comp(graph, regions, *, surfaces=None, proto=None, level="fail"):
    return bg.composition_findings(
        tables=bg.graph_tables(graph), regions=regions,
        surfaces=surfaces or SURF_CATALOG, proto_anchors=proto, level=level,
    )


# ---- region catalog parsing ----

def test_parse_region_catalog_fixed_columns():
    cat = bg.parse_region_catalog(
        "| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| R-BOARD-main | SURF-BOARD | root | grid | primary | content | OBJ-01 | 2 |\n"
        "| {{placeholder}} | x | x | x | x | x | x | x |\n"
    )
    assert set(cat) == {"R-BOARD-main"}
    assert cat["R-BOARD-main"]["surf"] == "SURF-BOARD"
    assert cat["R-BOARD-main"]["layout"] == "grid"
    assert cat["R-BOARD-main"]["scan_order"] == 2


def test_surface_and_region_parsers_dont_cross_contaminate():
    text = (
        "| SURF-BOARD | 看板 | page | create | board.html | ws |\n"
        "| R-BOARD-main | SURF-BOARD | root | grid | primary | content | x | 1 |\n"
    )
    assert set(bg.parse_surface_catalog(text)) == {"SURF-BOARD"}
    assert set(bg.parse_region_catalog(text)) == {"R-BOARD-main"}


# ---- adoption boundary + happy path ----

def test_composition_off_returns_empty():
    assert _comp(_comp_graph(region=None), _REGION_CAT, level="off") == []


def test_composition_clean_passes_with_render():
    f = _comp(_comp_graph(), _REGION_CAT, proto={"regions": {"R-BOARD-main"}}, level="fail")
    assert _codes(f, "composition") == []


def test_reconcile_without_regions_skips_composition():
    # 向后兼容：regions 省略（None）→ 旧调用不触发组成门。
    f = bg.reconcile_findings(tables=bg.graph_tables(_comp_graph(region=None)),
                              surfaces=SURF_CATALOG, proto_anchors=None)
    assert _codes(f, "composition") == []


# ---- the "pile of controls" structural gate ----

def test_object_unplaced_fails():
    f = _comp(_comp_graph(region=None), _REGION_CAT, level="fail")
    codes = _codes(f, "composition")
    assert "OBJECT_UNPLACED" in codes
    assert all(x["level"] == "FAIL" for x in f if x["code"] == "OBJECT_UNPLACED")


def test_object_unplaced_warn_level_downgrades():
    f = _comp(_comp_graph(region=None), _REGION_CAT, level="warn")
    assert [x["level"] for x in f if x["code"] == "OBJECT_UNPLACED"] == ["WARN"]


def test_object_region_unknown():
    assert "OBJECT_REGION_UNKNOWN" in _codes(_comp(_comp_graph(region="R-NOPE"), _REGION_CAT))


def test_region_surf_mismatch():
    # SURF-BOARD 已采用区域树，但对象落到了 SURF-OTHER 的区域 → mismatch。
    cat = {
        "R-BOARD-main": {"surf": "SURF-BOARD", "parent": "root", "layout": "grid",
                         "priority": "primary", "role": "content", "carries": "", "scan_order": 1},
        "R-OTHER-x": {"surf": "SURF-OTHER", "parent": "root", "layout": "grid",
                      "priority": "primary", "role": "content", "carries": "", "scan_order": 1},
    }
    surfaces = {"SURF-BOARD": {"via_controls": set()}, "SURF-OTHER": {"via_controls": set()}}
    f = _comp(_comp_graph(region="R-OTHER-x"), cat, surfaces=surfaces)
    assert "REGION_SURF_MISMATCH" in _codes(f, "composition")


def test_layout_region_missing_no_cascade():
    # surface 完全无区域 → 只报 LAYOUT_REGION_MISSING，不级联 OBJECT_UNPLACED。
    f = _comp(_comp_graph(region=None), {}, level="fail")
    codes = _codes(f, "composition")
    assert "LAYOUT_REGION_MISSING" in codes
    assert "OBJECT_UNPLACED" not in codes


# ---- region catalog validity ----

def test_region_bad_enum_and_parent_and_surf():
    cat = {
        "R-BOARD-main": {"surf": "SURF-BOARD", "parent": "root", "layout": "grid",
                         "priority": "primary", "role": "content", "carries": "", "scan_order": 1},
        "R-BAD": {"surf": "SURF-GHOST", "parent": "R-MISSING", "layout": "blob",
                  "priority": "primary", "role": "content", "carries": "", "scan_order": 2},
    }
    codes = _codes(_comp(_comp_graph(), cat, proto={"regions": {"R-BOARD-main", "R-BAD"}}), "composition")
    assert "REGION_SURF_UNKNOWN" in codes
    assert "REGION_PARENT_UNRESOLVED" in codes
    assert "REGION_BAD_ENUM" in codes


# ---- prototype fidelity ----

def test_region_not_rendered():
    f = _comp(_comp_graph(), _REGION_CAT, proto={"regions": set()})
    assert "REGION_NOT_RENDERED" in _codes(f, "composition")


def test_region_anchor_dangling():
    f = _comp(_comp_graph(), _REGION_CAT, proto={"regions": {"R-BOARD-main", "R-GHOST"}})
    assert "REGION_ANCHOR_DANGLING" in _codes(f, "composition")


# ---- advisory WARNs ----

def test_scan_order_missing_warn():
    cat = {"R-BOARD-main": {"surf": "SURF-BOARD", "parent": "root", "layout": "grid",
                            "priority": "primary", "role": "content", "carries": "", "scan_order": None}}
    f = _comp(_comp_graph(), cat, proto={"regions": {"R-BOARD-main"}})
    assert [x["level"] for x in f if x["code"] == "SCAN_ORDER_MISSING"] == ["WARN"]


def test_region_dead_warn():
    cat = dict(_REGION_CAT)
    cat["R-BOARD-dead"] = {"surf": "SURF-BOARD", "parent": "root", "layout": "row",
                           "priority": "tertiary", "role": "status", "carries": "", "scan_order": 2}
    f = _comp(_comp_graph(), cat, proto={"regions": {"R-BOARD-main", "R-BOARD-dead"}})
    dead = [x for x in f if x["code"] == "REGION_DEAD"]
    assert dead and dead[0]["level"] == "WARN" and dead[0]["region"] == "R-BOARD-dead"


# ---- helpers: anchors / merge / graph regions / config ----

def test_extract_anchors_includes_regions():
    out = bg.extract_prototype_anchors('<div data-region="R-BOARD-main"></div>')
    assert out["regions"] == {"R-BOARD-main"}


def test_regions_from_graph():
    g = {"regions": [{"region": "R-X", "surf": "SURF-BOARD", "parent": "root",
                      "layout": "grid", "priority": "primary", "role": "content", "scan_order": 1}]}
    assert bg.regions_from_graph(g)["R-X"]["surf"] == "SURF-BOARD"


def test_merge_graphs_unions_regions():
    proj = {"regions": [{"region": "R-OLD", "surf": "SURF-BOARD"}]}
    mission = {"regions": [{"region": "R-NEW", "surf": "SURF-BOARD"}]}
    merged = bg.merge_graphs(proj, mission)
    ids = {r["region"] for r in merged["regions"]}
    assert ids == {"R-OLD", "R-NEW"}


def test_merge_graphs_retires_region():
    proj = {"regions": [{"region": "R-OLD", "surf": "SURF-BOARD"}]}
    mission = {"regions": [{"region": "R-NEW", "surf": "SURF-BOARD"}], "retired": ["R-OLD"]}
    ids = {r["region"] for r in bg.merge_graphs(proj, mission)["regions"]}
    assert ids == {"R-NEW"}


def _supersede_project():
    return {
        "mission_id": "m-old",
        "surfaces": [{"surf": "SURF-BOARD", "name": "工作图看板"}],
        "page_states": [
            {"id": "PS-SURF-BOARD-readable", "surf": "SURF-BOARD"},
            {"id": "PS-SURF-BOARD-empty", "surf": "SURF-BOARD"},
        ],
        "steps": [{"id": "SUC-TF-BOARD-001-FLOW-01.readable", "page_state": "PS-SURF-BOARD-readable"}],
        "edges": [{"from": "ENTRY", "to": "SUC-TF-BOARD-001-FLOW-01.readable", "kind": "action"}],
        "flows": [{"id": "FLOW-OLD", "path": ["SUC-TF-BOARD-001-FLOW-01.readable"]}],
        "regions": [{"region": "R-OLD", "surf": "SURF-BOARD"}],
    }


def _supersede_mission(successor="SURF-CP-BOARD", rationale="lane×node 进化为 mission×stage"):
    return {
        "mission_id": "m-new",
        "surfaces": [{"surf": "SURF-CP-BOARD", "name": "mission×stage 看板"}],
        "page_states": [{"id": "PS-CP-BOARD-ready", "surf": "SURF-CP-BOARD"}],
        "steps": [{"id": "SUC-11-FLOW-01.ready", "page_state": "PS-CP-BOARD-ready"}],
        "edges": [{"from": "ENTRY", "to": "SUC-11-FLOW-01.ready", "kind": "action"}],
        "flows": [{"id": "FLOW-NEW", "path": ["SUC-11-FLOW-01.ready"]}],
        "regions": [{"region": "R-NEW", "surf": "SURF-CP-BOARD"}],
        "superseded": [{"predecessor": "SURF-BOARD", "successor": successor,
                        "kind": "surface", "rationale": rationale}],
    }


def test_merge_graphs_supersede_drops_predecessor_surface():
    """supersede(kind=surface): the predecessor surface + all its page_states/steps/
    regions drop from the merged graph (one board, not two), the successor carries
    forward, and predecessor edges/flows are pruned."""
    merged = bg.merge_graphs(_supersede_project(), _supersede_mission())
    assert {p["id"] for p in merged["page_states"]} == {"PS-CP-BOARD-ready"}
    assert {s["surf"] for s in merged["surfaces"]} == {"SURF-CP-BOARD"}
    assert {r["region"] for r in merged["regions"]} == {"R-NEW"}
    assert {f["id"] for f in merged["flows"]} == {"FLOW-NEW"}
    assert all(e["to"] != "SUC-TF-BOARD-001-FLOW-01.readable" for e in merged["edges"])


def test_merge_graphs_supersede_records_provenance():
    merged = bg.merge_graphs(_supersede_project(), _supersede_mission())
    log = merged.get("superseded_log")
    assert log and log[0]["predecessor"] == "SURF-BOARD" and log[0]["successor"] == "SURF-CP-BOARD"
    assert log[0]["mission"] == "m-new"


def test_supersede_findings_pass_when_successor_present():
    mission = _supersede_mission()
    merged = bg.merge_graphs(_supersede_project(), mission)
    tables = {"page_states": merged["page_states"], "steps": merged["steps"]}
    surfaces = {s["surf"]: s for s in merged["surfaces"]}
    findings = bg.supersede_findings(tables=tables, surfaces=surfaces, entries=bg.parse_supersede(mission))
    assert not [f for f in findings if f["level"] == "FAIL"]


def test_supersede_findings_fail_on_ghost_successor():
    """A supersede pointing at a non-existent successor is a disguised deletion —
    the regression-degradation backdoor the guard must catch."""
    mission = _supersede_mission(successor="SURF-GHOST")
    merged = bg.merge_graphs(_supersede_project(), mission)
    tables = {"page_states": merged["page_states"], "steps": merged["steps"]}
    surfaces = {s["surf"]: s for s in merged["surfaces"]}
    findings = bg.supersede_findings(tables=tables, surfaces=surfaces, entries=bg.parse_supersede(mission))
    assert any(f["code"] == "SUPERSEDE_SUCCESSOR_MISSING" and f["level"] == "FAIL" for f in findings)


def test_supersede_findings_fail_when_no_successor():
    mission = _supersede_mission()
    mission["superseded"] = [{"predecessor": "SURF-BOARD", "kind": "surface"}]
    findings = bg.supersede_findings(tables={"page_states": [], "steps": []}, surfaces={},
                                     entries=bg.parse_supersede(mission))
    assert any(f["code"] == "SUPERSEDE_SUCCESSOR_MISSING" for f in findings)


def test_supersede_findings_warn_on_missing_rationale():
    mission = _supersede_mission(rationale="")
    merged = bg.merge_graphs(_supersede_project(), mission)
    surfaces = {s["surf"]: s for s in merged["surfaces"]}
    findings = bg.supersede_findings(
        tables={"page_states": merged["page_states"], "steps": merged["steps"]},
        surfaces=surfaces, entries=bg.parse_supersede(mission))
    assert any(f["code"] == "SUPERSEDE_RATIONALE_MISSING" and f["level"] == "WARN" for f in findings)


def test_resolve_composition_level():
    assert bg.resolve_composition_level({"interaction": {"composition_gate_level": "fail"}}) == "fail"
    assert bg.resolve_composition_level({"interaction": {"composition_gate_level": "OFF"}}) == "off"
    assert bg.resolve_composition_level({}) == "warn"
    assert bg.resolve_composition_level({"interaction": {"composition_gate_level": "bogus"}}) == "warn"


# ===========================================================================
# design system gate (R9: assemble from component library)
# ===========================================================================

_BASE_MD = (
    "| 组件 id | 名称 | 构成 | 变体 | 状态矩阵（全） | 用到 token | 实现路径 | source | status |\n"
    "|---|---|---|---|---|---|---|---|---|\n"
    "| {{BC-id}} | x | x | x | x | x | x | x | draft |\n"
    "| BC-card | 卡片 | x | x | default/hover | --radius-1 | components/base/Card | obs | stable |\n"
    "<!-- 注释示例不该被解析：\n| BC-ghost | 幽灵 | x | x | x | x | x | x | x |\n-->\n"
)
_BIZ_MD = (
    "| 组件 id | 名称 | 业务场景(SUC) | 承载对象(OBJ) | 组成(BC) | 状态矩阵（全） | 数据 | 实现路径 | source mission | status |\n"
    "|---|---|---|---|---|---|---|---|---|---|\n"
    "| {{UC-id}} | x | x | x | x | x | x | x | x | draft |\n"
    "| UC-card | 卡片 | SUC-01 | OBJ-01 | BC-card | default/loading/empty | id | components/business/Card | m:1 | draft |\n"
)
_SHELL_MD = (
    "| 壳区域 id | 角色 | 承载 | source | status |\n"
    "|---|---|---|---|---|\n"
    "| {{SHELL-id}} | x | x | x | draft |\n"
    "| SHELL-header | header | logo | obs | stable |\n"
)


def _ds(tables, catalogs, *, proto=None, sucs=None, objs=None, level="fail"):
    return bg.design_system_findings(
        tables=bg.graph_tables(tables) if "page_states" in tables else tables,
        catalogs=catalogs, proto_anchors=proto,
        prd_sucs=sucs, prd_objs=objs, level=level,
    )


def _cat(base="", biz="", shell=""):
    return {
        "base": bg.parse_base_components(base),
        "business": bg.parse_business_components(biz),
        "shell": bg.parse_shell_catalog(shell),
    }


# ---- parsers: placeholder + comment skipping ----

def test_parse_base_skips_placeholder_and_comment():
    cat = bg.parse_base_components(_BASE_MD)
    assert set(cat) == {"BC-card"}  # {{BC-id}} 占位 + 注释 BC-ghost 都跳过


def test_parse_business_composed_of_and_bindings():
    cat = bg.parse_business_components(_BIZ_MD)
    assert set(cat) == {"UC-card"}
    assert cat["UC-card"]["composed_of"] == {"BC-card"}
    assert cat["UC-card"]["suc"] == "SUC-01" and cat["UC-card"]["obj"] == "OBJ-01"


def test_parse_shell_skips_placeholder():
    assert set(bg.parse_shell_catalog(_SHELL_MD)) == {"SHELL-header"}


# ---- non-destructive boundary ----

def test_design_system_empty_catalogs_no_findings():
    assert _ds(_graph(), _cat(), proto=None, level="fail") == []


def test_design_system_off_returns_empty():
    assert _ds(_graph(), _cat(base=_BASE_MD, biz=_BIZ_MD), level="off") == []


# ---- catalog integrity ----

def test_bizcomp_base_unresolved():
    biz = _BIZ_MD.replace("BC-card", "BC-missing")
    f = _ds(_graph(), _cat(base=_BASE_MD, biz=biz), level="fail")
    assert "BIZCOMP_BASE_UNRESOLVED" in _codes(f, "design_system")


def test_bizcomp_binding_dangling_suc():
    # UC-card 绑 SUC-01，但上游只有 SUC-99 → dangling
    f = _ds(_graph(), _cat(base=_BASE_MD, biz=_BIZ_MD), sucs={"SUC-99"}, objs={"OBJ-01"}, level="fail")
    assert "BIZCOMP_BINDING_DANGLING" in _codes(f, "design_system")


def test_bizcomp_binding_ok_when_upstream_present():
    f = _ds(_graph(), _cat(base=_BASE_MD, biz=_BIZ_MD), sucs={"SUC-01"}, objs={"OBJ-01"}, level="fail")
    assert "BIZCOMP_BINDING_DANGLING" not in _codes(f, "design_system")


def test_bizcomp_state_missing_warn():
    biz = _BIZ_MD.replace("default/loading/empty", "")
    f = _ds(_graph(), _cat(base=_BASE_MD, biz=biz), level="fail")
    sm = [x for x in f if x["code"] == "BIZCOMP_STATE_MISSING"]
    assert sm and sm[0]["level"] == "WARN"


# ---- object.bizcomp binding ----

def _graph_with_bizcomp(bizcomp="UC-card"):
    g = _graph()
    g["page_states"][1]["objects"][0]["bizcomp"] = bizcomp
    return g


def test_object_bizcomp_unknown():
    f = _ds(_graph_with_bizcomp("UC-nope"), _cat(base=_BASE_MD, biz=_BIZ_MD), level="fail")
    assert "OBJECT_BIZCOMP_UNKNOWN" in _codes(f, "design_system")


def test_object_no_bizcomp_warn_when_adopted():
    # business 目录非空（采用），但对象无 bizcomp → WARN nudge
    f = _ds(_graph(), _cat(base=_BASE_MD, biz=_BIZ_MD), level="fail")
    assert [x["level"] for x in f if x["code"] == "OBJECT_NO_BIZCOMP"] == ["WARN"]


# ---- prototype anchor dangling ----

def test_bizcomp_anchor_dangling():
    proto = {"bizcomps": {"UC-ghost"}, "shells": set()}
    f = _ds(_graph(), _cat(base=_BASE_MD, biz=_BIZ_MD), proto=proto, level="fail")
    assert "BIZCOMP_ANCHOR_DANGLING" in _codes(f, "design_system")


def test_shell_anchor_dangling():
    proto = {"bizcomps": set(), "shells": {"SHELL-ghost"}}
    f = _ds(_graph(), _cat(base=_BASE_MD, shell=_SHELL_MD), proto=proto, level="fail")
    assert "SHELL_ANCHOR_DANGLING" in _codes(f, "design_system")


def test_warn_level_downgrades_design_system_fails():
    biz = _BIZ_MD.replace("BC-card", "BC-missing")
    f = _ds(_graph(), _cat(base=_BASE_MD, biz=biz), level="warn")
    assert [x["level"] for x in f if x["code"] == "BIZCOMP_BASE_UNRESOLVED"] == ["WARN"]


def test_resolve_design_system_level():
    assert bg.resolve_design_system_level({"interaction": {"design_system_gate_level": "fail"}}) == "fail"
    assert bg.resolve_design_system_level({}) == "warn"
    assert bg.resolve_design_system_level({"interaction": {"design_system_gate_level": "bogus"}}) == "warn"


def test_extract_anchors_includes_design_system_buckets():
    out = bg.extract_prototype_anchors(
        '<div data-shell="SHELL-header"><div data-bizcomp="UC-card" data-basecomp="BC-card"></div></div>'
    )
    assert out["shells"] == {"SHELL-header"} and out["bizcomps"] == {"UC-card"} and out["basecomps"] == {"BC-card"}
