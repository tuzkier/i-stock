"""check_contracts.py 下游原型覆盖率门接线的端到端单测。

聚焦验证三件事：
1. 无 behavior-graph（非 UI / 未跑 interaction）→ 整门跳过，零 finding（非破坏铁律）。
2. mission 有行为图、solution 漏承载某 SURF → SURFACE_NOT_CARRIED FAIL。
3. solution 承载全部 SURF → 无覆盖率 finding。
并验证 carried_refs 收集口径（decisions[].traces_to 里的 SURF-）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))
_CHECK_SCRIPTS = COMMON_ROOT / "skills" / "stage-gate" / "scripts"
if str(_CHECK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CHECK_SCRIPTS))

import check_contracts as cc  # noqa: E402


def _write_behavior_graph(root: Path, mission: str, surfs: list[str]) -> None:
    spec_dir = (
        root / "harness-runtime" / "harness" / "artifacts" / mission
        / "interaction" / "interaction-spec"
    )
    spec_dir.mkdir(parents=True, exist_ok=True)
    graph = {
        "mission_id": mission,
        "surfaces": [{"surf": s, "name": s} for s in surfs],
        "page_states": [{"id": f"PS-{s}-empty", "surf": s, "state": "empty"} for s in surfs],
        "steps": [],
        "edges": [],
        "flows": [],
    }
    (spec_dir / "behavior-graph.yaml").write_text(
        yaml.safe_dump(graph, allow_unicode=True), encoding="utf-8"
    )


def _solution_contract(mission: str, carried_surfs: list[str]) -> dict:
    return {
        "mission_id": mission,
        "decisions": [
            {
                "id": "DEC-01", "chosen": "x", "rationale": "y",
                "traces_to": ["SCN-01", *carried_surfs],
            }
        ],
    }


def test_no_behavior_graph_skips_gate(tmp_path: Path) -> None:
    # 非 UI 任务：mission 没有 behavior-graph → 覆盖率门零 finding。
    findings: list = []
    cc.check_solution_guide(
        _solution_contract("M-NOUI", []), findings, upstream_ids=set(), root=tmp_path,
    )
    assert not any(f.code in {"SURFACE_NOT_CARRIED", "PAGESTATE_NOT_COVERED"} for f in findings)


def test_solution_missing_surface_fails(tmp_path: Path) -> None:
    mission = "M-UI"
    _write_behavior_graph(tmp_path, mission, ["SURF-BOARD", "SURF-DETAIL"])
    findings: list = []
    # 只承载 SURF-BOARD，漏 SURF-DETAIL。
    cc.check_solution_guide(
        _solution_contract(mission, ["SURF-BOARD"]), findings, upstream_ids=set(), root=tmp_path,
    )
    surface_fails = [f for f in findings if f.code == "SURFACE_NOT_CARRIED"]
    assert len(surface_fails) == 1
    assert "SURF-DETAIL" in surface_fails[0].message
    assert surface_fails[0].level == "FAIL"


def test_solution_all_surfaces_carried_passes(tmp_path: Path) -> None:
    mission = "M-UI2"
    _write_behavior_graph(tmp_path, mission, ["SURF-BOARD"])
    findings: list = []
    cc.check_solution_guide(
        _solution_contract(mission, ["SURF-BOARD"]), findings, upstream_ids=set(), root=tmp_path,
    )
    assert not any(f.code == "SURFACE_NOT_CARRIED" for f in findings)


def test_exemption_carries_missing_surface(tmp_path: Path) -> None:
    mission = "M-UI3"
    _write_behavior_graph(tmp_path, mission, ["SURF-BOARD", "SURF-DETAIL"])
    contract = _solution_contract(mission, ["SURF-BOARD"])
    contract["prototype_coverage_exemptions"] = [
        {"id": "SURF-DETAIL", "reason": "详情页本期决策门确认延后，登记 N/A"},
    ]
    findings: list = []
    cc.check_solution_guide(contract, findings, upstream_ids=set(), root=tmp_path)
    assert not any(
        f.code in {"SURFACE_NOT_CARRIED", "PROTOTYPE_EXEMPTION_NO_REASON"} for f in findings
    )


def _write_behavior_graph_with_project_history(
    root: Path, mission: str, mission_surfs: list[str], history_surfs: list[str],
) -> None:
    """写 mission-local 图（只含 mission_surfs）+ 项目累积图（含额外历史 history_surfs）。
    用于验证下游覆盖率门分母只取 mission-local，不为历史 surface 误报。"""
    _write_behavior_graph(root, mission, mission_surfs)
    proj_dir = root / "project-knowledge" / "product" / "system-use-cases"
    proj_dir.mkdir(parents=True, exist_ok=True)
    proj_graph = {
        "surfaces": [{"surf": s, "name": s} for s in history_surfs],
        "page_states": [{"id": f"PS-{s}-empty", "surf": s, "state": "empty"} for s in history_surfs],
        "steps": [], "edges": [], "flows": [],
    }
    (proj_dir / "behavior-graph.yaml").write_text(
        yaml.safe_dump(proj_graph, allow_unicode=True), encoding="utf-8"
    )


def test_denominator_is_mission_local_not_project_history(tmp_path: Path) -> None:
    # mission 图只有 SURF-A；项目累积图额外有历史 SURF-HIST。下游只承载 SURF-A，
    # 不该因项目历史的 SURF-HIST 报 SURFACE_NOT_CARRIED（分母 = mission-local）。
    mission = "M-HIST"
    _write_behavior_graph_with_project_history(
        tmp_path, mission, mission_surfs=["SURF-A"], history_surfs=["SURF-HIST"],
    )
    findings: list = []
    cc.check_solution_guide(
        _solution_contract(mission, ["SURF-A"]), findings, upstream_ids=set(), root=tmp_path,
    )
    surface_fails = [f for f in findings if f.code == "SURFACE_NOT_CARRIED"]
    assert surface_fails == [], (
        "下游覆盖率门不应为项目历史 surface 误报：" + ", ".join(f.message for f in surface_fails)
    )


def _breakdown_contract(mission: str, carried_ps: list[str]) -> dict:
    """最小 breakdown action_contract：一个 task，traces_to 携带给定 PS- ref。
    仅用于覆盖率门接线测试（其余字段缺失只产生无关 finding，不影响 PS 门断言）。"""
    return {
        "type": "action_contract",
        "stage": "breakdown",
        "mission_id": mission,
        "tasks": [
            {"id": "T-1", "traces_to": ["SCN-01", *carried_ps], "required_evidence": ["x"]},
        ],
    }


def test_breakdown_missing_pagestate_fails(tmp_path: Path) -> None:
    # mission 图有 PS-SURF-A-empty / PS-SURF-B-empty；execution-brief 只承载前者。
    mission = "M-BD"
    _write_behavior_graph(tmp_path, mission, ["SURF-A", "SURF-B"])
    findings: list = []
    cc.check_action(
        _breakdown_contract(mission, ["PS-SURF-A-empty"]),
        findings, upstream_ids=set(), root=tmp_path,
    )
    ps_fails = [f for f in findings if f.code == "PAGESTATE_NOT_COVERED"]
    assert len(ps_fails) == 1
    assert "PS-SURF-B-empty" in ps_fails[0].message
    assert ps_fails[0].level == "FAIL"


def test_breakdown_all_pagestates_covered_passes(tmp_path: Path) -> None:
    mission = "M-BD2"
    _write_behavior_graph(tmp_path, mission, ["SURF-A"])
    findings: list = []
    cc.check_action(
        _breakdown_contract(mission, ["PS-SURF-A-empty"]),
        findings, upstream_ids=set(), root=tmp_path,
    )
    assert not any(f.code == "PAGESTATE_NOT_COVERED" for f in findings)


def test_breakdown_no_graph_skips_gate(tmp_path: Path) -> None:
    # 非 UI breakdown：无 mission 行为图 → PS 门零 finding（非破坏铁律）。
    findings: list = []
    cc.check_action(
        _breakdown_contract("M-BD-NOUI", []), findings, upstream_ids=set(), root=tmp_path,
    )
    assert not any(f.code == "PAGESTATE_NOT_COVERED" for f in findings)


def test_tech_guide_collects_from_modules_and_interface_changes(tmp_path: Path) -> None:
    mission = "M-TECH"
    _write_behavior_graph(tmp_path, mission, ["SURF-BOARD", "SURF-DETAIL"])
    contract = {
        "mission_id": mission,
        "modules": [{"id": "MOD-01", "responsibility": "r", "traces_to": ["SURF-BOARD"]}],
        "interface_changes": [{"id": "INT-01", "traces_to": ["SURF-DETAIL"]}],
    }
    findings: list = []
    cc.check_technical_guide(contract, findings, upstream_ids=set(), root=tmp_path)
    # 两个 SURF 都被 modules / interface_changes 承载 → 无覆盖率 FAIL。
    assert not any(f.code == "SURFACE_NOT_CARRIED" for f in findings)
