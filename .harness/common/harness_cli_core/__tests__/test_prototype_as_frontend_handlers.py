"""Handler-level tests for prototype-as-frontend changeset gate A (#3)."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.app.commands.prototype_as_frontend_handlers import (  # noqa: E402
    cmd_prototype_as_frontend_changeset_check,
    cmd_prototype_as_frontend_path_check,
)


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


_UCM = "# 用例模型\nSUC-01-FLOW-01 加载；SUC-01-FLOW-02 提交。\n"

_CONTRACT = (
    "control_contract:\n"
    "  interaction_spec:\n"
    "    ref: interaction-spec\n"
)

# 含 required_tokens 命中字段 + surfaces 机器表。
_HEADER = (
    "interaction_spec_ref: x\nspec_conformance: ok\nbaseline_ref: -\n"
    "domain_refs: Entity:X\ndata-testid: yes\n"
    "## surfaces\n"
    "| surface_id | kind | operation | file_path | baseline_ref | traces_to | domain_refs |\n"
    "|---|---|---|---|---|---|---|\n"
)


def _setup(tmp_path: Path, changeset_body: str) -> None:
    stage = tmp_path / "harness-runtime" / "harness" / "stages" / "M-1"
    _write(stage / "contracts" / "prototype-as-frontend.contract.yaml", _CONTRACT)
    _write(stage / "frontend-changeset.md", changeset_body)
    art = tmp_path / "harness-runtime" / "harness" / "artifacts" / "M-1" / "product"
    _write(art / "use-case-model.md", _UCM)


def _run(tmp_path: Path) -> dict:
    args = argparse.Namespace(root=str(tmp_path), mission="M-1", compat=False, json=True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_prototype_as_frontend_changeset_check(args)
    return json.loads(buf.getvalue())


def _codes(result: dict) -> list[str]:
    return [f["code"] for f in result["findings"]]


def test_changeset_check_fails_when_prd_flowstep_uncovered(tmp_path: Path) -> None:
    body = _HEADER + "| SURF-001 | route | create_surface | app/p.tsx | null | SUC-01-FLOW-01 | Entity:X |\n"
    _setup(tmp_path, body)
    result = _run(tmp_path)
    assert result["status"] == "FAIL"
    assert "FRONTEND_FLOWSTEP_NOT_IN_CHANGESET" in _codes(result)


def test_changeset_check_passes_when_all_flowsteps_traced_or_na(tmp_path: Path) -> None:
    body = (
        _HEADER
        + "| SURF-001 | route | create_surface | app/p.tsx | null | SUC-01-FLOW-01 | Entity:X |\n"
        + "\n## 界面承载豁免（N/A）\n"
        + "| prd_node_id | 豁免粒度 | 理由 | 责任归属 |\n"
        + "|---|---|---|---|\n"
        + "| SUC-01-FLOW-02 | flowstep | 纯后台步骤无界面 | po |\n"
    )
    _setup(tmp_path, body)
    result = _run(tmp_path)
    assert "FRONTEND_FLOWSTEP_NOT_IN_CHANGESET" not in _codes(result)


def test_changeset_check_warns_on_stale_na_exemption(tmp_path: Path) -> None:
    body = (
        _HEADER
        + "| SURF-001 | route | create_surface | app/p.tsx | null | SUC-01-FLOW-01, SUC-01-FLOW-02 | Entity:X |\n"
        + "\n## 界面承载豁免（N/A）\n"
        + "| prd_node_id | 豁免粒度 | 理由 | 责任归属 |\n"
        + "|---|---|---|---|\n"
        + "| SUC-01-FLOW-02 | flowstep | 其实已实现 | po |\n"
    )
    _setup(tmp_path, body)
    result = _run(tmp_path)
    assert "FRONTEND_NA_EXEMPTION_STALE" in _codes(result)


def test_changeset_check_unparseable_surfaces_fails(tmp_path: Path) -> None:
    body = (
        "interaction_spec_ref: x\nspec_conformance: ok\nbaseline_ref: -\n"
        "domain_refs: Entity:X\ndata-testid: yes\ntraces_to SUC-01-FLOW-01\n"
        "这是一份只有散文、没有 SURF 机器表的 changeset。\n"
    )
    _setup(tmp_path, body)
    result = _run(tmp_path)
    assert "FRONTEND_CHANGESET_SURFACES_UNPARSEABLE" in _codes(result)


# ---- 门B：path-check 把 PRD 流步骤 × e2e_obligation 的覆盖做成 FAIL 门 ----

def _setup_with_contract(tmp_path: Path, contract_body: str) -> None:
    stage = tmp_path / "harness-runtime" / "harness" / "stages" / "M-1"
    _write(stage / "contracts" / "prototype-as-frontend.contract.yaml", contract_body)
    _write(stage / "frontend-changeset.md", _HEADER)
    art = tmp_path / "harness-runtime" / "harness" / "artifacts" / "M-1" / "product"
    _write(art / "use-case-model.md", _UCM)


def _run_path_check(tmp_path: Path) -> dict:
    args = argparse.Namespace(root=str(tmp_path), mission="M-1", compat=False, json=True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_prototype_as_frontend_path_check(args)
    return json.loads(buf.getvalue())


def test_path_check_fails_when_flowstep_missing_e2e_obligation(tmp_path: Path) -> None:
    # SUC-01-FLOW-01 有 required 义务；SUC-01-FLOW-02 无 → 门B 应对后者 FAIL。
    contract = (
        "control_contract:\n"
        "  e2e_obligation:\n"
        "    - flow_step: SUC-01-FLOW-01\n"
        "      status: required\n"
    )
    _setup_with_contract(tmp_path, contract)
    result = _run_path_check(tmp_path)
    assert "FLOWSTEP_E2E_OBLIGATION_MISSING" in _codes(result)
    missing = [
        f for f in result["findings"] if f["code"] == "FLOWSTEP_E2E_OBLIGATION_MISSING"
    ]
    assert any("SUC-01-FLOW-02" in f["message"] for f in missing)
    assert all("SUC-01-FLOW-01" not in f["message"] for f in missing)


def test_path_check_passes_e2e_obligation_when_required_or_accepted(tmp_path: Path) -> None:
    contract = (
        "control_contract:\n"
        "  e2e_obligation:\n"
        "    - flow_step: SUC-01-FLOW-01\n"
        "      status: required\n"
        "    - flow_step: SUC-01-FLOW-02\n"
        "      status: accepted_alternative\n"
        "      accepted_reason: 纯后台流步骤，由集成测试覆盖\n"
    )
    _setup_with_contract(tmp_path, contract)
    result = _run_path_check(tmp_path)
    assert "FLOWSTEP_E2E_OBLIGATION_MISSING" not in _codes(result)
