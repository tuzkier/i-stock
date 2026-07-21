"""Tests for `harness mission artifacts append` CLI (PT-CLI-EXTEND-03).

Records an `index_artifact` typed action intent into the workspace runtime
ledger. Validates the 6-kind closed set: text / code / config / log /
metric / external_link (matches tech-design DATA-05 RuntimeArtifact).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CLI_ENTRY = Path(__file__).resolve().parents[1] / "harness_cli.py"

ARTIFACT_KIND_CLOSED_SET = ("text", "code", "config", "log", "metric", "external_link")


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


@pytest.mark.parametrize("kind", ARTIFACT_KIND_CLOSED_SET)
def test_append_accepts_all_closed_set_kinds(tmp_path: Path, kind: str) -> None:
    ws = _workspace(tmp_path)
    result = _run(
        "mission", "artifacts-append",
        "--workspace", str(ws),
        "--mission", "M-1",
        "--kind", kind,
        "--path", "/tmp/sample.txt",
    )
    assert result.returncode == 0, f"kind={kind} stderr={result.stderr!r}"
    payload = json.loads(result.stdout)
    assert "artifact_id" in payload
    assert payload["kind"] == kind


def test_append_rejects_out_of_closed_set(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    result = _run(
        "mission", "artifacts-append",
        "--workspace", str(ws),
        "--mission", "M-1",
        "--kind", "binary",  # not in 6-set
        "--path", "/tmp/x.bin",
    )
    assert result.returncode == 2
    assert "binary" in result.stderr.lower() or "kind" in result.stderr.lower()


def test_append_missing_required_args_exits_2(tmp_path: Path) -> None:
    result = _run("mission", "artifacts-append", "--mission", "M-1")
    assert result.returncode == 2


def test_append_writes_ledger_entry(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    _run(
        "mission", "artifacts-append",
        "--workspace", str(ws),
        "--mission", "M-LEDGER",
        "--kind", "log",
        "--path", "/tmp/run.log",
    )
    ledger = ws / "harness-runtime" / "harness" / "control-events" / "artifact-index.jsonl"
    assert ledger.exists()
    entry = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert entry["kind"] == "index_artifact"
    assert entry["artifact_kind"] == "log"
    assert entry["artifact_path"] == "/tmp/run.log"
    assert entry["mission_id"] == "M-LEDGER"
    assert "artifact_id" in entry


def test_append_workspace_runtime_missing_exits_5(tmp_path: Path) -> None:
    ws = tmp_path / "bare"
    ws.mkdir()
    result = _run(
        "mission", "artifacts-append",
        "--workspace", str(ws),
        "--mission", "M-1",
        "--kind", "text",
        "--path", "/tmp/a.txt",
    )
    assert result.returncode == 5


def test_help_documents_kind_closed_set() -> None:
    result = _run("mission", "artifacts-append", "--help")
    assert result.returncode == 0
    out = result.stdout
    # Every kind in the closed set must appear in help
    for kind in ARTIFACT_KIND_CLOSED_SET:
        assert kind in out, f"help missing kind={kind}: {out}"
