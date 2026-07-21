#!/usr/bin/env python3
"""execute M5 / protocol stop_if hook: `changes_outside_authorized_paths`.

Reads the effective overlay state written by `harness execute apply-overlay`
to learn the current Atomic Task's authorized_paths, and denies any
Edit/Write/MultiEdit whose file_path is not covered.

State source: `harness-runtime/harness/stages/<mission>/runtime/effective-overlay.json`
written by the apply-overlay CLI. Schema:
  {
    "task_id": "AT-001",
    "authorized_paths": ["src/auth/**", "tests/auth/**"],
    "prohibited_paths": ["src/legacy/**"],
    "stop_if": ["changes_outside_authorized_paths", ...]
  }

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

_OVERLAY_GLOB = "harness-runtime/harness/stages/*/runtime/effective-overlay.json"


def _find_overlay_state(cwd: Path) -> dict | None:
    for path in sorted(cwd.glob(_OVERLAY_GLOB), reverse=True):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _path_in_glob_list(file_path: str, patterns: list[str]) -> bool:
    if not patterns:
        return False
    norm = file_path.lstrip("./")
    return any(
        fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(file_path, pat)
        for pat in patterns
    )


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
    overlay = _find_overlay_state(cwd)
    if overlay is None:
        # No active overlay → no per-task path constraint; defer to stage
        # overlay which already runs at the permissions layer.
        return 0
    if "changes_outside_authorized_paths" not in (overlay.get("stop_if") or []):
        return 0
    authorized = overlay.get("authorized_paths") or []
    if _path_in_glob_list(file_path, authorized):
        return 0
    print(
        "HarnessV2 execute stop_if BLOCKED (changes_outside_authorized_paths): "
        f"{file_path!r} is not in the current task's authorized_paths "
        f"{authorized!r}. Record a stop event via "
        "`harness execute stop-event record --kind changes_outside_authorized_paths` "
        "before expanding the boundary.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
