"""Unit tests for breakdown domain helpers."""

from __future__ import annotations

import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.breakdown import delta_spec_scenarios, uncovered_delta_scenarios  # noqa: E402


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _relpath(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def test_delta_spec_scenarios_scan_artifact_store_specs(tmp_path: Path) -> None:
    mission = "M-1"
    _write(
        tmp_path / "harness-runtime" / "harness" / "artifacts" / mission / "product" / "specs" / "cap-a" / "spec.md",
        "# Cap A — 差量规格\n\n"
        "## ADDED Requirements\n\n"
        "### Requirement: A\n\n"
        "#### Scenario: Create visible result\n",
    )

    deltas = delta_spec_scenarios(tmp_path, mission, {"cap-a/spec.md#Create visible result"}, _relpath)

    assert deltas == [
        {
            "capability": "cap-a",
            "spec_path": f"harness-runtime/harness/artifacts/{mission}/product/specs/cap-a/spec.md",
            "scenarios": [
                {
                    "name": "Create visible result",
                    "covered": True,
                    "trace_id": "cap-a/spec.md#Create visible result",
                }
            ],
        }
    ]


def test_uncovered_delta_scenarios_keep_legacy_stage_fallback(tmp_path: Path) -> None:
    mission = "M-legacy"
    _write(
        tmp_path / "harness-runtime" / "harness" / "stages" / mission / "specs" / "cap-legacy" / "spec.md",
        "# Legacy Cap — 差量规格\n\n"
        "## ADDED Requirements\n\n"
        "### Requirement: A\n\n"
        "#### Scenario: Legacy uncovered\n",
    )

    total, uncovered = uncovered_delta_scenarios(tmp_path, mission, set())

    assert total == 1
    assert uncovered == [
        {
            "capability": "cap-legacy",
            "scenario": "Legacy uncovered",
            "expected_trace": "cap-legacy/spec.md#Legacy uncovered",
        }
    ]
