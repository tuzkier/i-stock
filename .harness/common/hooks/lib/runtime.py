"""Runtime-state helpers: mission-status, gate reports, traces, overlay,
approvals. All readers are fail-open (return None / [] on any failure)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import contracts

_ACTIVE_STATUSES = {"in_progress", "active", "running", "open", "pending"}


def runtime_root(cwd: Path) -> Path:
    return cwd / "harness-runtime" / "harness"


def state_dir(cwd: Path) -> Path:
    return runtime_root(cwd) / "state"


# --- mission resolution ----------------------------------------------------
def mission_status(cwd: Path) -> dict | None:
    return contracts.load_yaml(runtime_root(cwd) / "mission-status.yaml")


def _mission_slice_stage(cwd: Path, entry: dict[str, Any]) -> str | None:
    work_graph = entry.get("work_graph")
    if not isinstance(work_graph, dict):
        return None
    rel_path = work_graph.get("mission_slice")
    if not isinstance(rel_path, str) or not rel_path:
        return None
    path = cwd / rel_path
    data = contracts.load_yaml(path)
    if not isinstance(data, dict):
        return None
    control_plane = data.get("control_plane")
    if not isinstance(control_plane, dict):
        return None
    stage = control_plane.get("stage")
    return stage if isinstance(stage, str) and stage else None


def active_mission(cwd: Path) -> tuple[str | None, str | None]:
    """Resolve (mission_id, stage).

    Order of precedence:
      1. HARNESS_MISSION_ID env var (id only — stage still from slice/status)
      2. state/active-mission file (id only)
      3. active mission entry's Work Graph Mission Slice control_plane.stage
      4. mission-status.yaml current_stage fallback for legacy/test fixtures.

    """
    data = mission_status(cwd)
    env_id = os.environ.get("HARNESS_MISSION_ID") or None
    file_id = None
    active_file = state_dir(cwd) / "active-mission"
    if active_file.exists():
        try:
            file_id = active_file.read_text(encoding="utf-8").strip() or None
        except OSError:
            file_id = None

    if not isinstance(data, dict) or not data:
        return env_id or file_id, None

    entries = {k: v for k, v in data.items() if isinstance(v, dict) and "current_stage" in v}
    chosen_id = env_id or file_id
    if chosen_id and chosen_id in entries:
        entry = entries[chosen_id]
    else:
        entry = None
        for mid, value in entries.items():
            if str(value.get("status", "")).lower() in _ACTIVE_STATUSES:
                chosen_id, entry = mid, value
                break
        if entry is None and entries:
            # No explicitly-active mission: take the last declared entry.
            chosen_id, entry = list(entries.items())[-1]

    if entry is None:
        top_stage = data.get("current_stage")
        return chosen_id, top_stage if isinstance(top_stage, str) else None

    stage = _mission_slice_stage(cwd, entry) or entry.get("current_stage")
    return (
        chosen_id,
        stage if isinstance(stage, str) else None,
    )


# --- gate reports ----------------------------------------------------------
def latest_gate_report(cwd: Path, mission_id: str, glob_pattern: str) -> dict | None:
    """Newest (by mtime) gate-report JSON matching glob_pattern under
    state/gate-reports/<mission_id>/."""
    base = state_dir(cwd) / "gate-reports" / mission_id
    if not base.is_dir():
        return None
    candidates = sorted(base.glob(glob_pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in candidates:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return None


# --- approvals -------------------------------------------------------------
def load_approvals(cwd: Path) -> list[dict]:
    """Read state/approvals.json, normalized to a list of records."""
    path = state_dir(cwd) / "approvals.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        return []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        records = data.get("approvals", [])
    else:
        records = []
    return [r for r in records if isinstance(r, dict)]


# --- effective overlay (execute stop_if) -----------------------------------
def load_overlay(cwd: Path) -> dict | None:
    """First stages/*/runtime/effective-overlay.json found."""
    base = runtime_root(cwd) / "stages"
    if not base.is_dir():
        return None
    for path in sorted(base.glob("*/runtime/effective-overlay.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return None


# --- traces ----------------------------------------------------------------
def append_trace(cwd: Path, rel_path: str, record: dict) -> bool:
    """Append a JSON record as one line to a trace file under runtime_root."""
    path = runtime_root(cwd) / rel_path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False
