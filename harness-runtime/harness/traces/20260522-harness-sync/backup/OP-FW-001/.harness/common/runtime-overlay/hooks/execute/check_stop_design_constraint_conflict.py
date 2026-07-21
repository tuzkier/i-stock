#!/usr/bin/env python3
"""execute M5 / protocol stop_if hook: `design_constraint_conflict`.

When the effective overlay's prohibited_paths list (sourced from
breakdown's `tasks[].prohibited_paths` which can carry design constraint
references like forbidden_paths from solution / tech-design contracts) is
hit, deny.

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


def _match_glob_list(file_path: str, patterns: list[str]) -> str | None:
    norm = file_path.lstrip("./")
    for pat in patterns:
        if fnmatch.fnmatch(norm, pat) or fnmatch.fnmatch(file_path, pat):
            return pat
    return None


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
        return 0
    if "design_constraint_conflict" not in (overlay.get("stop_if") or []):
        return 0
    prohibited = overlay.get("prohibited_paths") or []
    matched = _match_glob_list(file_path, prohibited)
    if matched is None:
        return 0
    print(
        "HarnessV2 execute stop_if BLOCKED (design_constraint_conflict): "
        f"{file_path!r} matches prohibited_paths pattern {matched!r}. "
        "This path is forbidden by upstream design constraints; record "
        "`harness execute stop-event record --kind design_constraint_conflict` "
        "and return to design via Decision Gate.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
