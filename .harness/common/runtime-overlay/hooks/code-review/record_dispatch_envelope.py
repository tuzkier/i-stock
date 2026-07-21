#!/usr/bin/env python3
"""code-review M3.1 PostToolUse hook: record dispatch envelope evidence
when a reviewer sub-agent completes.

This hook fires on PostToolUse agent dispatch events.  It appends a
`dispatches[]` entry to the code-review contract with the role, model,
execution_mode, fallback_used, started_at, and completed_at fields so
the Gate can verify that every reviewer ran in a real sub-agent context
(not main_agent_fallback, which cannot produce a PASS verdict).

The hook is best-effort (exit 0 always) — contract writes fail gracefully.

Exit conventions: 0 — always (non-blocking post hook).
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

_MISSION_RE = re.compile(r"--mission\s+([^\s'\"]+)")
_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    # This hook is designed for PostToolUse on `Task` / agent dispatch events.
    # Claude Code surfaces these as tool_name="Task" or "Dispatch".
    tool_name = payload.get("tool_name") or ""
    if tool_name not in ("Task", "Dispatch", "agent_dispatch"):
        return 0

    if yaml is None:
        return 0

    tool_input = payload.get("tool_input") or {}
    tool_output = payload.get("tool_response") or payload.get("tool_output") or {}

    role = (
        str(tool_input.get("subagent_type") or tool_input.get("role") or "")
    )
    if not role.endswith("-reviewer"):
        return 0

    model = str(
        tool_output.get("model")
        or tool_input.get("model")
        or payload.get("model")
        or "unknown"
    )
    execution_mode = str(
        tool_output.get("execution_mode")
        or tool_input.get("execution_mode")
        or "spawn_agent"
    )
    fallback_used = bool(execution_mode == "main_agent_fallback")
    started_at = str(tool_input.get("started_at") or payload.get("started_at") or _now_iso())
    completed_at = _now_iso()

    # Try to extract mission_id from the tool invocation command / description.
    description = str(tool_input.get("description") or tool_input.get("prompt") or "")
    mission_match = _MISSION_RE.search(description)
    if mission_match is None:
        return 0
    mission_id = mission_match.group(1)

    cwd = payload.get("cwd") or str(Path.cwd())
    contract_path = (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "code-review.contract.yaml"
    )
    if not contract_path.exists():
        return 0

    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return 0

    if not isinstance(data, dict):
        return 0

    contract = (
        data.get("control_contract")
        if isinstance(data.get("control_contract"), dict)
        else data
    )
    if not isinstance(contract, dict):
        return 0

    dispatches = contract.get("dispatches")
    if not isinstance(dispatches, list):
        dispatches = []
        contract["dispatches"] = dispatches

    envelope = {
        "role": role,
        "execution_mode": execution_mode,
        "model": model,
        "fallback_used": fallback_used,
        "started_at": started_at,
        "completed_at": completed_at,
    }
    dispatches.append(envelope)

    try:
        contract_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
            + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
