"""Handler-level regression for `interaction prototype-check` registry resolution.

Locks in fix #4: project-level SUC registry is read via the glob-based domain SSOT
(`parse_project_system_use_cases`) — prefix-agnostic, file-name-agnostic — instead of
the old hardcoded `theforce-system-use-cases.md` + `SUC-TF-[A-Z]+-[0-9]+` regex.
"""

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

from harness_cli_core.app.commands.interaction_handlers import (  # noqa: E402
    cmd_interaction_prototype_check,
)


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


_BEHAVIOR_GRAPH = """\
mission_id: M-1
surfaces:
  - surf: SURF-BOARD
    name: 看板
    type: page
    page_entry: board.html
    via_controls: []
page_states:
  - id: PS-SURF-BOARD-data
    surf: SURF-BOARD
    page_entry: board.html
    state: data
steps:
  - id: SUC-01-FLOW-01.data
    suc: SUC-01
    page_state: PS-SURF-BOARD-data
edges:
  - from: ENTRY
    to: SUC-01-FLOW-01.data
    kind: action
    desc: 打开
flows:
  - id: 主流
    suc: SUC-01
    path: [SUC-01-FLOW-01.data]
"""

_USE_CASE_MODEL = "# 用例模型\nSUC-01 看板加载，流步骤 SUC-01-FLOW-01。\n"
_SURFACE_MODEL = "# Surface\n| surface id | 名称 | 类型 | baseline | page_entry | via |\n|---|---|---|---|---|---|\n| SURF-BOARD | 看板 | page | create | board.html |  |\n"


def _setup(tmp_path: Path) -> None:
    art = tmp_path / "harness-runtime" / "harness" / "artifacts" / "M-1"
    _write(art / "interaction" / "interaction-spec" / "behavior-graph.yaml", _BEHAVIOR_GRAPH)
    _write(art / "interaction" / "interaction-spec" / "surface-model.md", _SURFACE_MODEL)
    _write(art / "product" / "use-case-model.md", _USE_CASE_MODEL)


def _run(tmp_path: Path) -> dict:
    args = argparse.Namespace(root=str(tmp_path), mission="M-1", prototype_root="", json=True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cmd_interaction_prototype_check(args)
    return json.loads(buf.getvalue())


def test_prototype_check_registry_sucs_from_glob_not_hardcoded_filename(tmp_path: Path) -> None:
    _setup(tmp_path)
    # 非 theforce 命名的注册表文件 — 旧硬编码会漏读，glob 会命中。
    _write(
        tmp_path / "project-knowledge" / "product" / "system-use-cases" / "foo-system-use-cases.md",
        "# 注册表\n| SUC | 名称 | BUC | surface | page_entry | anchor |\n|---|---|---|---|---|---|\n"
        "| SUC-TF-START-001 | 入驻 | BUC-1 | SURF-X | a.html | [data-x] |\n",
    )
    result = _run(tmp_path)
    codes = [f["code"] for f in result["findings"]]
    # 注册表 SUC 不在图里 → 被纳入分母并报缺口（旧硬编码下文件名不符会静默漏掉）。
    assert "UPSTREAM_REGISTRY_SUC_NOT_IN_GRAPH" in codes
    assert any(f.get("suc") == "SUC-TF-START-001" for f in result["findings"])


def test_prototype_check_registry_sucs_prefix_agnostic(tmp_path: Path) -> None:
    _setup(tmp_path)
    # 非 TF 前缀的 SUC — 旧 'SUC-TF-...' 正则会漏，新实现命中。
    _write(
        tmp_path / "project-knowledge" / "product" / "system-use-cases" / "core.md",
        "# 注册表\n| SUC | 名称 | BUC | surface | page_entry | anchor |\n|---|---|---|---|---|---|\n"
        "| SUC-CORE-001 | 核心 | BUC-1 | SURF-X | a.html | [data-x] |\n",
    )
    result = _run(tmp_path)
    assert any(f.get("suc") == "SUC-CORE-001" for f in result["findings"])
