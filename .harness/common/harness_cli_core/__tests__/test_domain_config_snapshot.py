"""Unit tests for config snapshot payload — focuses on the additive
``interaction.reachability_gate_level`` key (#1)."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.config_snapshot import build_config_snapshot_payload  # noqa: E402


def _payload(tmp_path: Path, config: dict) -> dict:
    return build_config_snapshot_payload(tmp_path, config, {})


def test_reachability_gate_level_defaults_to_fail(tmp_path: Path) -> None:
    payload = _payload(tmp_path, {})
    assert payload["interaction"]["reachability_gate_level"] == "fail"


def test_reachability_gate_level_honours_warn(tmp_path: Path) -> None:
    payload = _payload(tmp_path, {"interaction": {"reachability_gate_level": "WARN"}})
    assert payload["interaction"]["reachability_gate_level"] == "warn"


def test_reachability_gate_level_dirty_value_falls_back_to_fail(tmp_path: Path) -> None:
    payload = _payload(tmp_path, {"interaction": {"reachability_gate_level": "bogus"}})
    assert payload["interaction"]["reachability_gate_level"] == "fail"
