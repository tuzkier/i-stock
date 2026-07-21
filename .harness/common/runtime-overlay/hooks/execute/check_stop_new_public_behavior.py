#!/usr/bin/env python3
"""execute M5 / protocol stop_if hook: `new_public_behavior_without_delta_spec`.

The full semantic (public API surface change vs spec coverage) requires
language-specific static analysis. M5 ships a typed escape valve: when the
flag is active AND no delta spec exists under
`harness-runtime/harness/artifacts/<mission>/product/specs/` for the touched task,
writes to project source code (anything matching authorized_paths
without a same-named spec file) trip an alert.

The hook intentionally errs toward soft-block: it writes a warning to
stderr with rc=0 unless `strict_public_behavior=true` is set in the
overlay state. M5+ language-aware deep analysis is plan §future-research.

Exit convention: 0 = allow (or soft warn); 2 = block (only when strict).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_OVERLAY_GLOB = "harness-runtime/harness/stages/*/runtime/effective-overlay.json"


def _find_overlay_state(cwd: Path) -> tuple[dict, Path] | None:
    for path in sorted(cwd.glob(_OVERLAY_GLOB), reverse=True):
        try:
            return json.loads(path.read_text(encoding="utf-8")), path
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _delta_specs_present(state_path: Path) -> bool:
    # state_path = .../stages/<mission>/runtime/effective-overlay.json
    stage_dir = state_path.parent.parent
    specs_dir = stage_dir / "specs"
    if not specs_dir.exists():
        return False
    return any(specs_dir.rglob("spec.md"))


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
    found = _find_overlay_state(cwd)
    if found is None:
        return 0
    overlay, state_path = found
    if "new_public_behavior_without_delta_spec" not in (overlay.get("stop_if") or []):
        return 0
    # If delta specs exist for this mission, we trust breakdown's
    # check-coverage gate to have done its job.
    if _delta_specs_present(state_path):
        return 0
    strict = bool(overlay.get("strict_public_behavior"))
    # Only deny in strict mode; otherwise write an advisory message.
    if strict:
        print(
            "HarnessV2 execute stop_if BLOCKED "
            "(new_public_behavior_without_delta_spec, strict): "
            f"no delta spec found under stages/*/specs/ for this mission, "
            "but the task allows new public behavior. Confirm spec coverage "
            "and record `harness execute stop-event record "
            "--kind new_public_behavior_without_delta_spec` if intentional.",
            file=sys.stderr,
        )
        return 2
    print(
        "HarnessV2 execute stop_if ADVISORY "
        "(new_public_behavior_without_delta_spec): the current task allows "
        "new public behavior but no delta spec is present. Confirm spec "
        "coverage before continuing.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
