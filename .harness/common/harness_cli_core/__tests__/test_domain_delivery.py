"""Unit tests for `harness_cli_core.domain.delivery`."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.delivery import (  # noqa: E402
    delivery_contract_path,
    tech_design_contract_path,
)


def test_delivery_contract_path_layout(tmp_path: Path) -> None:
    expected = (
        tmp_path
        / "harness-runtime"
        / "harness"
        / "stages"
        / "M-1"
        / "contracts"
        / "delivery.contract.yaml"
    )
    assert delivery_contract_path(tmp_path, "M-1") == expected


def test_tech_design_contract_path_layout(tmp_path: Path) -> None:
    expected = (
        tmp_path
        / "harness-runtime"
        / "harness"
        / "stages"
        / "M-1"
        / "contracts"
        / "tech-design.contract.yaml"
    )
    assert tech_design_contract_path(tmp_path, "M-1") == expected


def test_delivery_and_tech_design_paths_are_siblings(tmp_path: Path) -> None:
    delivery = delivery_contract_path(tmp_path, "M-1")
    tech = tech_design_contract_path(tmp_path, "M-1")
    assert delivery.parent == tech.parent
    assert delivery.name != tech.name
