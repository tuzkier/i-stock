"""Unit tests for `harness_cli_core.domain.retrospective`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.retrospective import (  # noqa: E402
    read_approvals_for_mission,
    read_stage_effectiveness,
    read_trace_events,
    stage_dir,
)


def _write(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_stage_dir_layout(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    assert stage_dir(tmp_path, "M-1") == runtime / "stages" / "M-1"


def test_read_trace_events_returns_empty_when_missing(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    assert read_trace_events(tmp_path, "M-1") == []


def test_read_trace_events_parses_jsonl_and_skips_bad_lines(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "state" / "trace" / "M-1-trace.jsonl",
        "\n".join(
            [
                json.dumps({"type": "stage_enter", "stage": "prd"}),
                "  ",  # blank-ish line ignored
                "not-json-line",  # malformed ignored
                json.dumps({"type": "gate_fail", "stage": "verify"}),
                "",
            ]
        )
        + "\n",
    )
    events = read_trace_events(tmp_path, "M-1")
    assert events == [
        {"type": "stage_enter", "stage": "prd"},
        {"type": "gate_fail", "stage": "verify"},
    ]


def test_read_approvals_for_mission_returns_empty_when_store_missing(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    assert read_approvals_for_mission(tmp_path, "M-1") == []


def test_read_stage_effectiveness_returns_empty_when_dir_missing(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    assert read_stage_effectiveness(tmp_path, "M-1") == {}


def test_read_stage_effectiveness_extracts_review_block(tmp_path: Path) -> None:
    runtime = tmp_path / "harness-runtime" / "harness"
    runtime.mkdir(parents=True)
    _write(
        runtime / "stages" / "M-1" / "contracts" / "prd.contract.yaml",
        (
            "control_contract:\n"
            "  effectiveness_review:\n"
            "    rounds_used: 2\n"
            "    last_verdict: pass\n"
            "    checkpoints:\n"
            "      - prd-gate\n"
        ),
    )
    # contract without effectiveness_review is silently dropped
    _write(
        runtime / "stages" / "M-1" / "contracts" / "solution.contract.yaml",
        "control_contract: {}\n",
    )
    eff = read_stage_effectiveness(tmp_path, "M-1")
    assert "prd.contract" in eff
    assert eff["prd.contract"] == {
        "rounds_used": 2,
        "last_verdict": "pass",
        "checkpoints": ["prd-gate"],
    }
    assert "solution.contract" not in eff
