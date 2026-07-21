"""In-process unit tests for `harness_cli_core.domain.runs`.

The CLI shim tests (.harness/common/cli/__tests__) drive the same code through
subprocess; these tests pin the domain seam directly so future refactors of
the CLI surface don't accidentally drift from the persistence contract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

COMMON_ROOT = Path(__file__).resolve().parents[2]
if str(COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(COMMON_ROOT))

from harness_cli_core.domain.runs import (  # noqa: E402
    append_control_event,
    control_events_dir,
    new_run_id,
    workspace_initialized,
    workspace_runtime_dir,
)


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    runtime = ws / "harness-runtime" / "harness"
    (runtime / "missions").mkdir(parents=True)
    return ws


def test_new_run_id_has_run_prefix_and_is_unique() -> None:
    ids = {new_run_id() for _ in range(50)}
    assert len(ids) == 50
    assert all(value.startswith("run-") for value in ids)
    # 16 hex chars after the prefix
    assert all(len(value) == len("run-") + 16 for value in ids)


def test_workspace_initialized_true_for_runtime_dir(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    assert workspace_initialized(ws) is True
    assert workspace_runtime_dir(ws) == ws / "harness-runtime" / "harness"


def test_workspace_initialized_false_for_bare_dir(tmp_path: Path) -> None:
    bare = tmp_path / "bare"
    bare.mkdir()
    assert workspace_initialized(bare) is False


def test_append_control_event_creates_dir_and_appends_jsonl(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    assert not control_events_dir(ws).exists()

    entry = append_control_event(
        ws,
        kind="dispatch_agent_run",
        filename="dispatch-intents.jsonl",
        extra={"run_id": "run-abc", "mission_id": "M-1"},
    )

    ledger = control_events_dir(ws) / "dispatch-intents.jsonl"
    assert ledger.exists()
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    written = json.loads(lines[0])
    assert written == entry
    assert written["kind"] == "dispatch_agent_run"
    assert written["run_id"] == "run-abc"
    assert written["mission_id"] == "M-1"
    assert "created_at" in written  # default timestamp populated


def test_append_control_event_uses_explicit_created_at(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    entry = append_control_event(
        ws,
        kind="cancel_run",
        filename="cancel-intents.jsonl",
        extra={"run_id": "run-xyz"},
        created_at="2026-05-26T00:00:00+00:00",
    )
    assert entry["created_at"] == "2026-05-26T00:00:00+00:00"


def test_append_control_event_appends_multiple_lines(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    for i in range(3):
        append_control_event(
            ws,
            kind="index_artifact",
            filename="artifact-index.jsonl",
            extra={"artifact_id": f"art-{i}"},
        )

    ledger = control_events_dir(ws) / "artifact-index.jsonl"
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    ids = [json.loads(line)["artifact_id"] for line in lines]
    assert ids == ["art-0", "art-1", "art-2"]


def test_append_control_event_extra_cannot_override_canonical_fields(
    tmp_path: Path,
) -> None:
    """Caller-supplied `extra` must not silently overwrite the canonical
    `kind` and `created_at` fields written by the helper."""
    ws = _make_workspace(tmp_path)
    entry = append_control_event(
        ws,
        kind="retry_run",
        filename="retry-intents.jsonl",
        extra={
            "run_id": "run-new",
            "retry_of": "run-old",
            "kind": "TAMPERED",
            "created_at": "1970-01-01T00:00:00+00:00",
        },
        created_at="2026-05-26T01:23:45+00:00",
    )
    assert entry["kind"] == "retry_run"
    assert entry["created_at"] == "2026-05-26T01:23:45+00:00"
    assert entry["run_id"] == "run-new"
    assert entry["retry_of"] == "run-old"
