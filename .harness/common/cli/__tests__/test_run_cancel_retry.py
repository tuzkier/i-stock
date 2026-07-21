"""Tests for `harness run cancel` and `harness run retry` (PT-CLI-EXTEND-02).

Both subcommands are CLI Bridge shims that record typed action intents and
emit deterministic JSON envelopes. Cancel honors backend capability honesty
(SOL-RISK-002, SCN-RUN-CANCEL-DEGRADE): when the targeted Run's backend cannot cancel, the
shim degrades to a `cancellation_requested` state with exit=0 (not silent
success). Retry honors INV-09: a new run_id is always issued, never the old
one.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CLI_ENTRY = Path(__file__).resolve().parents[1] / "harness_cli.py"


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI_ENTRY), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / "harness-runtime" / "harness" / "control-events").mkdir(parents=True)
    return ws


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------

def test_cancel_arg_parse_missing_run_exits_2() -> None:
    result = _run("run", "cancel", "--workspace", "/tmp/ws")
    assert result.returncode == 2
    assert "run" in result.stderr.lower()


def test_cancel_happy_emits_status_cancelled(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    result = _run("run", "cancel", "--workspace", str(ws), "--run", "run-abc123")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["run_id"] == "run-abc123"
    assert payload["status"] == "cancelled"


def test_cancel_unsupported_backend_degrades(tmp_path: Path) -> None:
    """When THEFORCE_ADAPTER_CANCEL_SUPPORT=none, cancel degrades to cancellation_requested
    and emits a capability_downgrade marker. Exit code still 0 to allow CLI Bridge
    to propagate the honest status to the user (SOL-RISK-002 / SCN-RUN-CANCEL-DEGRADE)."""
    ws = _workspace(tmp_path)
    env = {"THEFORCE_ADAPTER_CANCEL_SUPPORT": "none", "PATH": "/usr/bin:/bin"}
    result = _run("run", "cancel", "--workspace", str(ws), "--run", "run-cursor1", env=env)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "cancellation_requested"
    assert payload.get("capability_downgrade") is True
    assert payload["run_id"] == "run-cursor1"


def test_cancel_appends_control_event(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    _run("run", "cancel", "--workspace", str(ws), "--run", "run-ledger1")
    ledger = ws / "harness-runtime" / "harness" / "control-events" / "cancel-intents.jsonl"
    assert ledger.exists()
    entry = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert entry["kind"] == "cancel_run"
    assert entry["run_id"] == "run-ledger1"


def test_cancel_workspace_runtime_missing_exits_5(tmp_path: Path) -> None:
    ws = tmp_path / "bare"
    ws.mkdir()
    result = _run("run", "cancel", "--workspace", str(ws), "--run", "run-xyz")
    assert result.returncode == 5


# ---------------------------------------------------------------------------
# retry
# ---------------------------------------------------------------------------

def test_retry_arg_parse_missing_run_exits_2() -> None:
    result = _run("run", "retry", "--workspace", "/tmp/ws")
    assert result.returncode == 2


def test_retry_emits_new_run_id_and_preserves_old(tmp_path: Path) -> None:
    """INV-09: retry must create a NEW run_id; old run_id is preserved as retry_of."""
    ws = _workspace(tmp_path)
    old = "run-original-001"
    result = _run("run", "retry", "--workspace", str(ws), "--run", old)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "new_run_id" in payload
    assert payload["new_run_id"] != old
    assert payload["retry_of"] == old
    assert payload["status"] == "queued"


def test_retry_appends_control_event_with_retry_of(tmp_path: Path) -> None:
    ws = _workspace(tmp_path)
    _run("run", "retry", "--workspace", str(ws), "--run", "run-old-789")
    ledger = ws / "harness-runtime" / "harness" / "control-events" / "retry-intents.jsonl"
    assert ledger.exists()
    entry = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert entry["kind"] == "retry_run"
    assert entry["retry_of"] == "run-old-789"
    assert entry["run_id"] != "run-old-789"  # INV-09


def test_retry_workspace_runtime_missing_exits_5(tmp_path: Path) -> None:
    ws = tmp_path / "bare"
    ws.mkdir()
    result = _run("run", "retry", "--workspace", str(ws), "--run", "run-x")
    assert result.returncode == 5


def test_help_documents_both_subcommands() -> None:
    result = _run("run", "--help")
    assert result.returncode == 0
    assert "cancel" in result.stdout
    assert "retry" in result.stdout
