"""Pure helpers for retrospective stage commands.

Reads trace events, mission approvals and stage effectiveness_review data.
The corresponding command handlers live in
:mod:`harness_cli_core.app.commands.retrospective_handlers`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness_cli_core.domain.approvals import load_approvals
from harness_cli_core.infra.io import load_yaml
from harness_cli_core.infra.runtime_paths import runtime_harness_root


def stage_dir(root: Path, mission: str) -> Path:
    return runtime_harness_root(root) / "stages" / mission


def read_trace_events(root: Path, mission: str) -> list[dict[str, Any]]:
    """Read all events from the mission trace JSONL log."""
    trace_path = runtime_harness_root(root) / "state" / "trace" / f"{mission}-trace.jsonl"
    if not trace_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:  # noqa: BLE001
            pass
    return events


def read_approvals_for_mission(root: Path, mission: str) -> list[dict[str, Any]]:
    """Read approval records for a mission from approvals.json."""
    try:
        _doc, records = load_approvals(root)
    except Exception:  # noqa: BLE001
        return []
    return [r for r in records if r.get("mission") == mission]


def read_stage_effectiveness(root: Path, mission: str) -> dict[str, dict[str, Any]]:
    """Read effectiveness_review fields from stage contracts."""
    stages_root = runtime_harness_root(root) / "stages" / mission / "contracts"
    result: dict[str, dict[str, Any]] = {}
    if not stages_root.exists():
        return result
    for contract_path in stages_root.glob("*.contract.yaml"):
        try:
            doc = load_yaml(contract_path)
            cc = doc.get("control_contract", {})
            er = cc.get("effectiveness_review", {})
            if er:
                result[contract_path.stem] = {
                    "rounds_used": er.get("rounds_used"),
                    "last_verdict": er.get("last_verdict"),
                    "checkpoints": er.get("checkpoints", []),
                }
        except Exception:  # noqa: BLE001
            pass
    return result
