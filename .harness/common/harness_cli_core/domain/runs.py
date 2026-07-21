"""Domain helpers for AgentRun lifecycle ledger writes.

These helpers are the persistence boundary for the typed action intents that
back `harness agent dispatch`, `harness run cancel`, and `harness run retry`.
They live here so the CLI command modules stay thin and so other callers
(tests, future server-side flows) can reuse the same write semantics without
shelling out to the CLI.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


def new_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:16]}"


def workspace_runtime_dir(workspace: Path) -> Path:
    return workspace / "harness-runtime" / "harness"


def workspace_initialized(workspace: Path) -> bool:
    return workspace_runtime_dir(workspace).is_dir()


def control_events_dir(workspace: Path) -> Path:
    return workspace_runtime_dir(workspace) / "control-events"


def append_control_event(
    workspace: Path,
    *,
    kind: str,
    filename: str,
    extra: Mapping[str, Any] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Append a typed action intent to the workspace control-events ledger.

    Returns the dict that was written so callers can echo / extend it for the
    stdout envelope.
    """
    target_dir = control_events_dir(workspace)
    target_dir.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = dict(extra) if extra else {}
    # canonical fields are authoritative — never let caller-supplied `extra`
    # shadow them
    entry["kind"] = kind
    entry["created_at"] = created_at or datetime.now(timezone.utc).isoformat()
    with (target_dir / filename).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
