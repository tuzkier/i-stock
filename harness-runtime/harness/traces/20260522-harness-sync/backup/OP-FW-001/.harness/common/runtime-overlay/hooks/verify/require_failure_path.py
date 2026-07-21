#!/usr/bin/env python3
"""verify M3.1 PreToolUse hook: block Edit/Write to src/** or tests/**
during verify unless a typed failure_path record exists.

verify must not make implementation fixes inline. If a defect is found,
the agent must first record a failure_path via:
  harness verify failure-path --mission <id> --kind bug_fix --json
  OR
  harness verify failure-path --mission <id> --kind execute --json

The hook checks for a failure_path trace file written by the CLI
command or stored in the verification contract.

State signal:
  harness-runtime/harness/stages/<mission>/traces/failure_path.json
    {"kind": "bug_fix|execute|...", "recorded_at": "..."}
  OR verification-report.contract.yaml failure_path field is set.

Exit convention: 0 = allow; 2 = block.
"""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# Patterns that trigger the check (implementation / test files)
_PROTECTED_PATTERNS: list[str] = [
    "src/**",
    "tests/**",
    "test/**",
    "lib/**",
    "app/**",
]

_ALLOWED_FAILURE_KINDS = {"bug_fix", "execute", "decision_gate", "receiving_review"}


def _is_protected_path(file_path: str) -> bool:
    norm = file_path.lstrip("./")
    return any(fnmatch.fnmatch(norm, pat) for pat in _PROTECTED_PATTERNS)


def _failure_path_recorded(cwd: Path) -> bool:
    """Return True if any active mission has a failure_path record."""
    # Check trace files
    for trace_path in cwd.glob(
        "harness-runtime/harness/stages/*/traces/failure_path.json"
    ):
        try:
            data = json.loads(trace_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and data.get("kind") in _ALLOWED_FAILURE_KINDS:
            return True

    if yaml is None:
        return False

    # Check verification contract failure_path field
    for contract_path in cwd.glob(
        "harness-runtime/harness/stages/*/contracts/verification-report.contract.yaml"
    ):
        try:
            data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue
        if not isinstance(data, dict):
            continue
        doc = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
        fp = doc.get("failure_path")
        if isinstance(fp, dict) and fp.get("kind") in _ALLOWED_FAILURE_KINDS:
            return True
        if isinstance(fp, str) and fp in _ALLOWED_FAILURE_KINDS:
            return True

    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return 0
    if not _is_protected_path(file_path):
        return 0
    cwd = Path(payload.get("cwd") or ".")
    if _failure_path_recorded(cwd):
        return 0
    print(
        "HarnessV2 verify hook BLOCKED (FAILURE_PATH_REQUIRED): "
        f"verify stage must not edit implementation files ({file_path!r}) directly. "
        "Record a typed failure path first: "
        "`harness verify failure-path --mission <id> "
        "--kind bug_fix|execute|decision_gate|receiving_review --json`. "
        "Then the defect fix must happen in the designated bug-fix / execute stage.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
