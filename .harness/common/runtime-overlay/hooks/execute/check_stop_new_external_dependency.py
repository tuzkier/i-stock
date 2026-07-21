#!/usr/bin/env python3
"""execute M5 / protocol stop_if hook: `new_external_dependency`.

Triggered when an Edit/Write touches a file declared in
`harness-runtime/config/dependency-files.yaml`. Such mutations imply a
project-level dependency change that must go through Decision Gate, never
silent slipped in by execute.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_DEP_CONFIG = "harness-runtime/config/dependency-files.yaml"
_OVERLAY_GLOB = "harness-runtime/harness/stages/*/runtime/effective-overlay.json"


def _load_dep_patterns(cwd: Path) -> list[str]:
    path = cwd / _DEP_CONFIG
    if not path.exists() or yaml is None:
        return []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return []
    patterns: list[str] = []
    for entry in (doc or {}).get("dependency_files", []):
        if isinstance(entry, dict) and isinstance(entry.get("pattern"), str):
            patterns.append(entry["pattern"])
    return patterns


def _stop_if_active(cwd: Path) -> bool:
    for path in sorted(cwd.glob(_OVERLAY_GLOB), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if "new_external_dependency" in (data.get("stop_if") or []):
            return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    if not _stop_if_active(cwd):
        return 0
    patterns = _load_dep_patterns(cwd)
    basename = Path(file_path).name
    if not any(basename == pat or file_path.endswith("/" + pat) for pat in patterns):
        return 0
    print(
        "HarnessV2 execute stop_if BLOCKED (new_external_dependency): "
        f"{file_path!r} matches a project dependency file "
        f"({patterns!r}). Mutations require Decision Gate via "
        "`harness execute stop-event record --kind new_external_dependency`.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
