#!/usr/bin/env python3
"""finishing-branch-improvement-plan M3.1 hook: require gate PASS before mission close.

PreToolUse hook for `harness mission close *`.
Verifies that `harness gate run --stage finishing-branch` has recorded PASS
in the finishing-branch contract's effectiveness_review.last_gate_run_status.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_MISSION_CLOSE_RE = re.compile(r"\bharness\s+mission\s+close\b")


def _check_gate_pass(cwd: Path) -> tuple[bool, str]:
    """Return (gate_passed, reason)."""
    import glob as _glob
    try:
        import yaml as _yaml
    except ImportError:
        return True, "yaml unavailable; gate check skipped"
    pattern = str(
        cwd / "harness-runtime" / "harness" / "stages" / "*"
        / "contracts" / "finishing-branch.contract.yaml"
    )
    matches = _glob.glob(pattern)
    if not matches:
        return True, "no finishing-branch contract found; gate check advisory"
    try:
        doc = _yaml.safe_load(Path(matches[0]).read_text(encoding="utf-8"))
    except Exception:
        return True, "contract unreadable; gate check advisory"
    if not isinstance(doc, dict):
        return True, "contract invalid shape; gate check advisory"
    eff = doc.get("effectiveness_review")
    if not isinstance(eff, dict):
        return False, "effectiveness_review missing in contract; run `harness gate run --stage finishing-branch` first"
    last_status = eff.get("last_gate_run_status")
    if last_status != "PASS":
        return False, f"last gate run status={last_status!r}; must be PASS before mission close"
    return True, "gate PASS confirmed"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not _MISSION_CLOSE_RE.search(command):
        return 0

    cwd = Path(payload.get("cwd") or ".")
    gate_passed, reason = _check_gate_pass(cwd)
    if gate_passed:
        return 0

    print(
        f"HarnessV2 finishing-branch hook BLOCKED (check_close_gate): {reason}.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
