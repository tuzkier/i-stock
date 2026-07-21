"""Tests for `harness acceptance record` CLI (PT-CLI-EXTEND-04).

Records an `acceptance_decision` typed action intent (accept /
request_changes) into the workspace runtime ledger. Honors INV-10: an
`accept` decision without at least one --evidence-ref blocks with exit=7
(evidence gap) — the user must explicitly accept_with_risk via a separate
Decision Gate path (not implemented as a CLI shortcut here).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CLI_ENTRY = Path(__file__).resolve().parents[1] / "harness_cli.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_ENTRY), *args],
        capture_output=True,
        text=True,
    )


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / "harness-runtime" / "harness" / "control-events").mkdir(parents=True)
    return ws


def test_record_accept_with_evidence_emits_ids(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    result = _run(
        "acceptance", "record",
        "--workspace", str(ws),
        "--mission", "M-001",
        "--decision", "accept",
        "--evidence-ref", "ev-A",
        "--evidence-ref", "ev-B",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "acceptance_id" in payload
    assert "control_event_id" in payload
    assert payload["decision"] == "accept"
    assert payload["evidence_refs"] == ["ev-A", "ev-B"]


def test_record_accept_without_evidence_exits_7(tmp_path: Path) -> None:
    """INV-10: accept without evidence is an evidence gap blocker."""
    ws = _workspace(tmp_path)
    result = _run(
        "acceptance", "record",
        "--workspace", str(ws),
        "--mission", "M-001",
        "--decision", "accept",
    )
    assert result.returncode == 7
    assert "evidence" in result.stderr.lower()


def test_record_request_changes_without_evidence_ok(tmp_path: Path) -> None:
    """request_changes does not require evidence (it's flagging a gap)."""
    ws = _workspace(tmp_path)
    result = _run(
        "acceptance", "record",
        "--workspace", str(ws),
        "--mission", "M-001",
        "--decision", "request_changes",
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["decision"] == "request_changes"


def test_record_invalid_decision_exits_2(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    result = _run(
        "acceptance", "record",
        "--workspace", str(ws),
        "--mission", "M-001",
        "--decision", "accept_with_risk",  # not allowed via CLI; must go through Decision Gate
    )
    assert result.returncode == 2


def test_record_writes_ledger(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    _run(
        "acceptance", "record",
        "--workspace", str(ws),
        "--mission", "M-LEDGER",
        "--decision", "accept",
        "--evidence-ref", "ev-1",
    )
    ledger = ws / "harness-runtime" / "harness" / "control-events" / "acceptance-decisions.jsonl"
    assert ledger.exists()
    entry = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert entry["kind"] == "acceptance_decision"
    assert entry["decision"] == "accept"
    assert entry["mission_id"] == "M-LEDGER"
    assert entry["evidence_refs"] == ["ev-1"]


def test_record_workspace_runtime_missing_exits_5(tmp_path: Path) -> None:
    ws = tmp_path / "bare"
    ws.mkdir()
    result = _run(
        "acceptance", "record",
        "--workspace", str(ws),
        "--mission", "M-1",
        "--decision", "accept",
        "--evidence-ref", "ev-1",
    )
    assert result.returncode == 5


def test_record_multiple_decisions_preserve_history(tmp_path: Path) -> None:
    """append-only history — re-record accept/request_changes/accept yields 3 ledger lines."""
    ws = _workspace(tmp_path)
    for decision, ev in [("accept", "ev-1"), ("request_changes", None), ("accept", "ev-2")]:
        args = ["acceptance", "record", "--workspace", str(ws), "--mission", "M-H", "--decision", decision]
        if ev:
            args += ["--evidence-ref", ev]
        result = _run(*args)
        assert result.returncode == 0, f"{decision} failed: {result.stderr}"
    ledger = ws / "harness-runtime" / "harness" / "control-events" / "acceptance-decisions.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    decisions = [json.loads(l)["decision"] for l in lines]
    assert decisions == ["accept", "request_changes", "accept"]
