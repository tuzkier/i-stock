#!/usr/bin/env python3
"""HarnessV2 discovery PostToolUse hook: append a structured trace event when
the AI calls a graphify MCP tool (graphify_query / graphify_context).

Triggered on PostToolUse with tool_name matching mcp__graphify__* (or the
canonical names graphify_query / graphify_context). The hook locates the
active mission's trace JSONL under
`harness-runtime/harness/traces/<mission>/discovery.jsonl` and appends one
event so retrospective + discovery-effectiveness-reviewer can audit that the
brownfield path actually exercised graphify.

Exit conventions: 0 = success (always). Hooks must never silently block on
trace write failure; trace-log records are best-effort observability.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

# Recognize graphify tools regardless of MCP server prefix convention:
# - mcp__graphify__query / mcp__graphify__context / mcp__graphify__repos
# - bare graphify_query (legacy)
# - any future variant that contains "graphify" in the tool name.
_GRAPHIFY_TOOL_TOKENS = ("graphify",)


def _is_graphify_tool(tool_name: str) -> bool:
    name = (tool_name or "").lower()
    return any(token in name for token in _GRAPHIFY_TOOL_TOKENS)


def _find_active_mission(cwd: Path) -> str | None:
    """Best-effort mission resolution: read mission-status.yaml and take the
    first entry whose status looks active. Returns None if nothing usable."""
    status_path = cwd / "harness-runtime" / "harness" / "mission-status.yaml"
    if not status_path.exists():
        return None
    try:
        import yaml
    except ImportError:
        return None
    try:
        data = yaml.safe_load(status_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    for mission_id, entry in data.items():
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "").lower()
        if status in {"", "active", "in_progress", "running"}:
            return mission_id
    # Fallback: return whichever single mission exists.
    if len(data) == 1:
        return next(iter(data))
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_name = payload.get("tool_name") or ""
    if not _is_graphify_tool(tool_name):
        return 0

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    mission = _find_active_mission(cwd)
    if not mission:
        return 0

    trace_dir = cwd / "harness-runtime" / "harness" / "traces" / mission
    try:
        trace_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return 0
    trace_path = trace_dir / "discovery.jsonl"

    event = {
        "event": "graphify_query",
        "tool_name": tool_name,
        "recorded_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "tool_input": payload.get("tool_input") or {},
    }
    try:
        with trace_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
