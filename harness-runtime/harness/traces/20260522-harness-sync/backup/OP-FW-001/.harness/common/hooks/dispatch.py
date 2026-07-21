#!/usr/bin/env python3
"""HarnessV2 hook dispatcher — the single entry registered in settings.json.

Reads one Claude Code hook payload from stdin, resolves the active mission
stage from mission-status.yaml, and runs that stage's checks (plus baseline
checks) in-process. Replaces the legacy model of 78 standalone scripts each
registered globally.

Exit conventions:
  0 — allow
  2 — block (PreToolUse: deny the tool call;
             PostToolUse: surface the message back to the model)

Dispatch never raises: any unexpected error degrades to exit 0 (fail-open),
matching the legacy per-script behavior.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

from context import HookContext  # noqa: E402
from lib import runtime  # noqa: E402
from registry import BASELINE, REGISTRY  # noqa: E402


def _resolve_event(payload: dict) -> str:
    for index, arg in enumerate(sys.argv):
        if arg == "--event" and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
        if arg.startswith("--event="):
            return arg.split("=", 1)[1]
    event = payload.get("hook_event_name")
    return event if isinstance(event, str) and event else "PreToolUse"


def run(payload: dict) -> int:
    event = _resolve_event(payload)
    ctx = HookContext.from_payload(payload, event=event)

    mission_id, stage = runtime.active_mission(ctx.cwd)
    ctx.mission_id = mission_id
    ctx.stage = stage

    entries = list(BASELINE)
    if stage and stage in REGISTRY:
        entries.extend(REGISTRY[stage])

    for entry in entries:
        if not entry.matches(ctx):
            continue
        try:
            result = entry.check(ctx)
        except Exception:  # one bad check must not break the rest — fail-open
            continue
        if result is None:
            continue
        if result.is_block:
            sys.stderr.write(result.message.rstrip() + "\n")
            return 2
        if result.message:
            sys.stderr.write(result.message.rstrip() + "\n")
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        return run(payload)
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
