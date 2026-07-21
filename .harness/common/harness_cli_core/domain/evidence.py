"""Domain helpers for the evidence store (`evidence.json` per mission)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness_cli_core.domain.manifest import load_manifest
from harness_cli_core.infra.runtime_paths import resolve_path, runtime_harness_root


def evidence_store_path(root: Path, mission_id: str, explicit: str | None = None) -> Path:
    path = resolve_path(root, explicit)
    if path:
        return path
    return runtime_harness_root(root) / "traces" / mission_id / "evidence" / "evidence.json"


def load_evidence_store(path: Path, mission_id: str) -> dict[str, Any]:
    if path.exists():
        data = load_manifest(path)
        if isinstance(data.get("evidence"), list):
            return {
                "schema_version": data.get("schema_version") or 1,
                "mission_id": data.get("mission_id") or mission_id,
                "evidence": [item for item in data.get("evidence") or [] if isinstance(item, dict)],
                "links": [item for item in data.get("links") or [] if isinstance(item, dict)],
            }
    return {"schema_version": 1, "mission_id": mission_id, "evidence": [], "links": []}
