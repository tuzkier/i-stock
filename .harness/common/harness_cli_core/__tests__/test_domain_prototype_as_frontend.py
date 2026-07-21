"""Unit tests for `harness_cli_core.domain.prototype_as_frontend`."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.prototype_as_frontend import (  # noqa: E402
    changeset_traces_union,
    frontend_changeset_path,
    frontend_flowstep_obligation_coverage,
    frontend_na_stale_findings,
    frontend_project_root_from_contract,
    frontend_upstream_completeness_findings,
    parse_frontend_changeset_surfaces,
    parse_frontend_na_flowsteps,
    prototype_as_frontend_contract,
    prototype_as_frontend_contract_path,
)


def _codes(findings):
    return [f["code"] for f in findings]


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_paths_match_expected_layout(tmp_path: Path) -> None:
    expected_contract = (
        tmp_path
        / "harness-runtime"
        / "harness"
        / "stages"
        / "M-1"
        / "contracts"
        / "prototype-as-frontend.contract.yaml"
    )
    expected_changeset = (
        tmp_path
        / "harness-runtime"
        / "harness"
        / "stages"
        / "M-1"
        / "frontend-changeset.md"
    )
    assert prototype_as_frontend_contract_path(tmp_path, "M-1") == expected_contract
    assert frontend_changeset_path(tmp_path, "M-1") == expected_changeset


def test_prototype_as_frontend_contract_empty_when_missing(tmp_path: Path) -> None:
    assert prototype_as_frontend_contract(tmp_path, "M-1") == {}


def test_prototype_as_frontend_contract_reads_control_contract_block(tmp_path: Path) -> None:
    _write(
        prototype_as_frontend_contract_path(tmp_path, "M-1"),
        "control_contract:\n  frontend_project:\n    root: TheForce/web\n",
    )
    contract = prototype_as_frontend_contract(tmp_path, "M-1")
    assert contract["frontend_project"]["root"] == "TheForce/web"


def test_frontend_project_root_none_when_unresolved(tmp_path: Path) -> None:
    assert frontend_project_root_from_contract(tmp_path, "M-1") is None


def test_frontend_project_root_resolves_relative_to_repo_root(tmp_path: Path) -> None:
    _write(
        prototype_as_frontend_contract_path(tmp_path, "M-1"),
        "control_contract:\n  frontend_project:\n    root: TheForce/web\n",
    )
    resolved = frontend_project_root_from_contract(tmp_path, "M-1")
    assert resolved == tmp_path / "TheForce" / "web"


def test_frontend_project_root_keeps_absolute_path(tmp_path: Path) -> None:
    absolute = tmp_path / "elsewhere" / "web"
    _write(
        prototype_as_frontend_contract_path(tmp_path, "M-1"),
        f"control_contract:\n  frontend_project:\n    root: {absolute}\n",
    )
    assert frontend_project_root_from_contract(tmp_path, "M-1") == absolute


def test_frontend_project_root_none_when_placeholder(tmp_path: Path) -> None:
    _write(
        prototype_as_frontend_contract_path(tmp_path, "M-1"),
        "control_contract:\n  frontend_project:\n    root: '{{ todo }}'\n",
    )
    assert frontend_project_root_from_contract(tmp_path, "M-1") is None


# ---- 门A：结构化 changeset 解析 + 上游覆盖 (#3) ----

_CHANGESET = (
    "## surfaces\n"
    "| surface_id | kind | operation | file_path | baseline_ref | traces_to | domain_refs |\n"
    "|---|---|---|---|---|---|---|\n"
    "| SURF-001 | route | create_surface | app/board/page.tsx | null | SCN-01, SUC-01-FLOW-01 | Entity:Workspace, State:active |\n"
    "| SURF-002 | component | modify_surface | app/card.tsx | app/card.tsx | SUC-01-FLOW-02.empty | Action:create |\n"
    "这是散文行，不该被解析。\n"
)


def test_parse_frontend_changeset_surfaces_parses_fixed_columns():
    surfaces = parse_frontend_changeset_surfaces(_CHANGESET)
    assert len(surfaces) == 2
    assert surfaces[0]["surface_id"] == "SURF-001"
    assert surfaces[0]["baseline_ref"] is None
    assert surfaces[0]["traces_to"] == {"SCN-01", "SUC-01-FLOW-01"}
    assert surfaces[0]["domain_refs"] == {"Entity:Workspace", "State:active"}
    assert surfaces[1]["baseline_ref"] == "app/card.tsx"


def test_changeset_traces_union_normalizes_flowstep_prefix():
    surfaces = parse_frontend_changeset_surfaces(_CHANGESET)
    union = changeset_traces_union(surfaces)
    assert "SUC-01-FLOW-02.empty" in union
    assert "SUC-01-FLOW-02" in union  # 前缀归一
    assert "SUC-01-FLOW-01" in union


def test_frontend_upstream_completeness_flags_missing_flowstep():
    surfaces = parse_frontend_changeset_surfaces(
        "| SURF-001 | route | create_surface | app/p.tsx | null | SUC-01-FLOW-01 | Entity:X |\n"
    )
    f = frontend_upstream_completeness_findings(
        changeset_surfaces=surfaces,
        prd_flowsteps={"SUC-01-FLOW-01", "SUC-01-FLOW-02"},
    )
    assert _codes(f) == ["FRONTEND_FLOWSTEP_NOT_IN_CHANGESET"]
    assert f[0]["flow_step"] == "SUC-01-FLOW-02"


def test_frontend_upstream_na_exempts_flowstep():
    surfaces = parse_frontend_changeset_surfaces(
        "| SURF-001 | route | create_surface | app/p.tsx | null | SUC-01-FLOW-01 | Entity:X |\n"
    )
    f = frontend_upstream_completeness_findings(
        changeset_surfaces=surfaces,
        prd_flowsteps={"SUC-01-FLOW-01", "SUC-01-FLOW-02"},
        na_flowsteps={"SUC-01-FLOW-02"},
    )
    assert f == []


def test_na_flowsteps_suc_granularity_expands():
    na, exemptions = parse_frontend_na_flowsteps(
        "## 界面承载豁免（N/A）\n"
        "| prd_node_id | 豁免粒度 | 理由 | 责任归属 |\n"
        "|---|---|---|---|\n"
        "| SUC-07 | suc | 后台无界面 | po |\n",
        prd_flowsteps={"SUC-07-FLOW-01", "SUC-07-FLOW-02", "SUC-01-FLOW-01"},
    )
    assert na == {"SUC-07-FLOW-01", "SUC-07-FLOW-02"}
    assert exemptions[0]["granularity"] == "suc"


def test_frontend_na_stale_flags_already_traced():
    surfaces = parse_frontend_changeset_surfaces(
        "| SURF-001 | route | create_surface | app/p.tsx | null | SUC-01-FLOW-01 | Entity:X |\n"
    )
    f = frontend_na_stale_findings(na_flowsteps={"SUC-01-FLOW-01"}, changeset_surfaces=surfaces)
    assert "FRONTEND_NA_EXEMPTION_STALE" in _codes(f)
    assert f[0]["level"] == "WARN"


def test_frontend_flowstep_obligation_coverage_required_and_accepted():
    obligations = [
        {"flow_step": "SUC-01-FLOW-01", "status": "required"},
        {"flow_step": "SUC-01-FLOW-02", "status": "accepted_alternative", "accepted_reason": "纯后台"},
        {"flow_step": "SUC-01-FLOW-03", "status": "accepted_alternative", "accepted_reason": ""},
    ]
    cov = frontend_flowstep_obligation_coverage(
        {"SUC-01-FLOW-01", "SUC-01-FLOW-02", "SUC-01-FLOW-03", "SUC-01-FLOW-04"},
        obligations,
    )
    assert "SUC-01-FLOW-01" in cov["covered_flowsteps"]
    assert "SUC-01-FLOW-02" in cov["covered_flowsteps"]
    # FLOW-03 accepted 无 reason → 不计覆盖；FLOW-04 缺失 → uncovered
    assert "SUC-01-FLOW-03" in cov["uncovered_flowsteps"]
    assert "SUC-01-FLOW-04" in cov["uncovered_flowsteps"]
