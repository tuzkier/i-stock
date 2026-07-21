"""Tests for `harness agent dispatch` CLI (PT-CLI-EXTEND-01).

The CLI is invoked by the TheForce server's CLI Bridge as a subprocess shim;
it accepts the `dispatch_agent_run` typed action parameters, records the
intent into the workspace's runtime ledger, and emits a `{run_id, status}`
JSON envelope on stdout. Adapter execution itself happens server-side; this
CLI is only the typed-action persistence boundary (D-04, SCN-AGENT-DISPATCH, SCN-AGENT-LEDGER).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

CLI_ENTRY = Path(__file__).resolve().parents[1] / "harness_cli.py"
REPO_ROOT = Path(__file__).resolve().parents[4]

PERMISSION_MODES = ("read-only", "edit", "full")


def _run(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(CLI_ENTRY), *args]
    return subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )


def _make_workspace(tmp_path: Path) -> Path:
    """Materialize a minimal workspace with a harness-runtime/ directory."""
    ws = tmp_path / "demo-ws"
    runtime = ws / "harness-runtime" / "harness"
    (runtime / "missions").mkdir(parents=True)
    (runtime / "control-events").mkdir(parents=True)
    return ws


# AT-01-01 — argparse contract
# --------------------------------------------------------------------------

@pytest.mark.parametrize("backend", ["claude", "cursor"])
@pytest.mark.parametrize("permission", PERMISSION_MODES)
def test_arg_parse_valid(tmp_path: Path, backend: str, permission: str) -> None:
    """All four required arguments produce a successful run when present."""
    ws = _make_workspace(tmp_path)
    result = _run(
        "agent", "dispatch",
        "--workspace", str(ws),
        "--mission", "M-001",
        "--backend", backend,
        "--permission", permission,
        "--json",
    )
    assert result.returncode == 0, f"stderr={result.stderr!r} stdout={result.stdout!r}"


def test_arg_parse_missing_workspace_exits_2() -> None:
    """Missing required --workspace flag yields exit code 2 (argparse standard)."""
    result = _run("agent", "dispatch", "--mission", "M-001", "--backend", "claude", "--permission", "edit")
    assert result.returncode == 2
    assert "workspace" in result.stderr.lower()


def test_arg_parse_invalid_backend_exits_2() -> None:
    """Backend must be in the closed set {claude, cursor}."""
    result = _run(
        "agent", "dispatch",
        "--workspace", "/tmp/ws-does-not-matter",
        "--mission", "M-001",
        "--backend", "openai",   # not allowed
        "--permission", "edit",
    )
    assert result.returncode == 2
    assert "backend" in result.stderr.lower() or "openai" in result.stderr.lower()


def test_arg_parse_invalid_permission_exits_2() -> None:
    """Permission must be in {read-only, edit, full}."""
    result = _run(
        "agent", "dispatch",
        "--workspace", "/tmp/ws",
        "--mission", "M-001",
        "--backend", "claude",
        "--permission", "god-mode",   # not allowed
    )
    assert result.returncode == 2


# AT-01-02 — JSON output + ledger write
# --------------------------------------------------------------------------

def test_happy_path_emits_run_id_and_status_json(tmp_path: Path) -> None:
    """Happy path writes a JSON envelope `{run_id, status}` to stdout with exit 0."""
    ws = _make_workspace(tmp_path)
    result = _run(
        "agent", "dispatch",
        "--workspace", str(ws),
        "--mission", "M-HAPPY",
        "--backend", "claude",
        "--permission", "edit",
        "--json",
    )
    assert result.returncode == 0, f"stderr={result.stderr!r}"
    payload = json.loads(result.stdout)
    assert "run_id" in payload, payload
    assert payload.get("status") in {"dispatched", "queued"}
    assert payload.get("mission_id") == "M-HAPPY"
    assert payload.get("backend") == "claude"


def test_happy_path_appends_control_event_jsonl(tmp_path: Path) -> None:
    """A dispatch_agent_run intent must land in <workspace>/harness-runtime/harness/control-events/dispatch-intents.jsonl."""
    ws = _make_workspace(tmp_path)
    result = _run(
        "agent", "dispatch",
        "--workspace", str(ws),
        "--mission", "M-LEDGER",
        "--backend", "cursor",
        "--permission", "read-only",
        "--json",
    )
    assert result.returncode == 0
    ledger = ws / "harness-runtime" / "harness" / "control-events" / "dispatch-intents.jsonl"
    assert ledger.exists(), f"ledger not created: {ledger}"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["kind"] == "dispatch_agent_run"
    assert entry["mission_id"] == "M-LEDGER"
    assert entry["backend"] == "cursor"
    assert entry["permission_mode"] == "read-only"
    assert "run_id" in entry
    assert "created_at" in entry


def test_workspace_runtime_missing_exits_5(tmp_path: Path) -> None:
    """Workspace lacking a harness-runtime/ directory yields exit code 5 (workspace lock / not initialized)."""
    ws = tmp_path / "bare-ws"
    ws.mkdir()
    # No harness-runtime/ underneath.
    result = _run(
        "agent", "dispatch",
        "--workspace", str(ws),
        "--mission", "M-LOCK",
        "--backend", "claude",
        "--permission", "edit",
        "--json",
    )
    assert result.returncode == 5, f"stderr={result.stderr!r} stdout={result.stdout!r}"


# AT-01-03 — exit code matrix
# --------------------------------------------------------------------------

def test_adapter_unavailable_exits_9(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When THEFORCE_ADAPTER_AVAILABILITY=none is injected, command exits 9 (adapter unavailable)."""
    ws = _make_workspace(tmp_path)
    env = {"THEFORCE_ADAPTER_AVAILABILITY": "none", "PATH": "/usr/bin:/bin"}
    result = _run(
        "agent", "dispatch",
        "--workspace", str(ws),
        "--mission", "M-UNAVAIL",
        "--backend", "claude",
        "--permission", "edit",
        "--json",
        env=env,
    )
    assert result.returncode == 9, f"stderr={result.stderr!r} stdout={result.stdout!r}"


def test_exit_code_matrix_documented_in_help() -> None:
    """`harness agent dispatch --help` must enumerate the exit codes for downstream CLI Bridge."""
    result = _run("agent", "dispatch", "--help")
    assert result.returncode == 0
    out = result.stdout
    # exit code matrix referenced (0 / 2 / 5 / 9)
    assert "0" in out and "2" in out and "5" in out and "9" in out
