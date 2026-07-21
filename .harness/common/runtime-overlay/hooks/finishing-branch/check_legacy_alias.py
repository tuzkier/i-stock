#!/usr/bin/env python3
"""finishing-branch M3.1 PreToolUse hook (H5): warn / soft-block when the
mission close command uses a legacy alias (manual / cancelled) outside the
2-mission compatibility window.

Plan §finishing-branch M2.1: `harness mission close --status <enum>`
accepts `manual` and `cancelled` as legacy aliases for the new enum but
emits a translation warning recorded at
`harness-runtime/harness/translation-warning.yaml`. After 2 mission cycles
the aliases FAIL.

This hook implements the soft-block contract: when the command uses a
legacy alias AND the project's `harness-runtime/config/harness.yaml`
declares `finishing_branch.legacy_alias_window=closed`, deny.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

_LEGACY_ALIASES = {"manual", "cancelled"}
_MISSION_CLOSE_RE = re.compile(r"\bharness\s+mission\s+close\b")
_STATUS_RE = re.compile(r"--status\s+([^\s'\"]+)")


def _legacy_window_open(cwd: Path) -> bool:
    """Default: window is OPEN (legacy aliases accepted with translation
    warning). The window closes when harness.yaml declares so explicitly.
    """
    config = cwd / "harness-runtime/config/harness.yaml"
    if not config.exists() or yaml is None:
        return True
    try:
        data = yaml.safe_load(config.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return True
    if not isinstance(data, dict):
        return True
    fb = data.get("finishing_branch") or {}
    if not isinstance(fb, dict):
        return True
    return fb.get("legacy_alias_window") != "closed"


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
    status_match = _STATUS_RE.search(command)
    if status_match is None or status_match.group(1) not in _LEGACY_ALIASES:
        return 0
    cwd = Path(payload.get("cwd") or ".")
    if _legacy_window_open(cwd):
        print(
            "HarnessV2 finishing-branch hook ADVISORY (legacy_alias_used): "
            f"--status={status_match.group(1)!r} is a legacy alias. "
            "Translation will be recorded in translation-warning.yaml. "
            "Plan to migrate to the typed enum (merged/pr/kept/discarded) "
            "within 2 mission cycles.",
            file=sys.stderr,
        )
        return 0
    print(
        "HarnessV2 finishing-branch hook BLOCKED (legacy_alias_window=closed): "
        f"--status={status_match.group(1)!r} is no longer accepted. "
        "Use the typed enum: merged | pr | kept | discarded.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
