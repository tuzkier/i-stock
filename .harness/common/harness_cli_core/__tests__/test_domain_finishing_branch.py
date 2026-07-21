"""Unit tests for `harness_cli_core.domain.finishing_branch`."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.finishing_branch import (  # noqa: E402
    load_contract,
    mission_info,
    stage_dir,
)


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_stage_dir_resolves_under_runtime(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    assert stage_dir(tmp_path, "M-1") == runtime / "stages" / "M-1"


def test_mission_info_defaults_base_to_main(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    info = mission_info(tmp_path, "M-missing")
    assert info == {"mission_branch": None, "base_branch": "main"}


def test_mission_info_reads_git_block(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "mission-status.yaml",
        "M-1:\n  git:\n    mission_branch: feature/m1\n    base_branch: develop\n",
    )
    info = mission_info(tmp_path, "M-1")
    assert info == {"mission_branch": "feature/m1", "base_branch": "develop"}


def test_mission_info_falls_back_to_top_level_mission_branch(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "mission-status.yaml",
        "M-1:\n  mission_branch: feature/legacy\n",
    )
    info = mission_info(tmp_path, "M-1")
    assert info == {"mission_branch": "feature/legacy", "base_branch": "main"}


def test_mission_info_falls_back_to_current_matching_branch(tmp_path: Path, monkeypatch) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(runtime / "mission-status.yaml", "M-1:\n  status: active\n")
    import harness_cli_core.domain.finishing_branch as finishing_branch

    class Result:
        returncode = 0
        stdout = "dev/M-1-feature\n"

    monkeypatch.setattr(finishing_branch.subprocess, "run", lambda *args, **kwargs: Result())
    info = mission_info(tmp_path, "M-1")
    assert info == {"mission_branch": "dev/M-1-feature", "base_branch": "main"}


def test_load_contract_empty_when_missing(tmp_path: Path) -> None:
    assert load_contract(tmp_path, "M-1") == {}


def test_load_contract_reads_yaml(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "stages" / "M-1" / "contracts" / "finishing-branch.contract.yaml",
        "kind: finishing-branch\nfoo: bar\n",
    )
    assert load_contract(tmp_path, "M-1") == {"kind": "finishing-branch", "foo": "bar"}


def test_load_contract_empty_when_yaml_malformed(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "stages" / "M-1" / "contracts" / "finishing-branch.contract.yaml",
        "foo: [unterminated",
    )
    assert load_contract(tmp_path, "M-1") == {}
