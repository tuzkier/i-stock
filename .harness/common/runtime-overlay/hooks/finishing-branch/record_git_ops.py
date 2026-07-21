#!/usr/bin/env python3
"""finishing-branch-improvement-plan M3.1 hook: record git_ops evidence after execute.

PostToolUse hook for `harness finishing-branch execute *`.
Appends git_ops evidence to the finishing-branch contract.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_FB_EXECUTE_RE = re.compile(r"\bharness\s+finishing-branch\s+execute\b")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not _FB_EXECUTE_RE.search(command):
        return 0

    # Try to parse the output JSON from the execute command.
    output = str(payload.get("tool_response") or payload.get("output") or "")
    git_ops = []
    strategy = ""
    try:
        out_data = json.loads(output)
        git_ops = out_data.get("git_ops") or []
        strategy = str(out_data.get("strategy") or "")
    except (json.JSONDecodeError, ValueError):
        pass

    if not git_ops and not strategy:
        return 0

    # Find and update finishing-branch contract.
    cwd = Path(payload.get("cwd") or ".")
    import glob as _glob
    try:
        import yaml as _yaml
    except ImportError:
        return 0
    pattern = str(
        cwd / "harness-runtime" / "harness" / "stages" / "*"
        / "contracts" / "finishing-branch.contract.yaml"
    )
    matches = _glob.glob(pattern)
    if not matches:
        return 0

    try:
        contract_path = Path(matches[0])
        doc = _yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        if not isinstance(doc, dict):
            return 0
        existing_ops = doc.get("git_ops") or []
        for op in git_ops:
            existing_ops.append(op)
        doc["git_ops"] = existing_ops
        if strategy:
            close_choice = doc.get("close_choice") if isinstance(doc.get("close_choice"), dict) else {}
            close_choice["strategy"] = strategy
            doc["close_choice"] = close_choice
        contract_path.write_text(
            _yaml.dump(doc, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
