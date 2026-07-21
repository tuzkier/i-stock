#!/usr/bin/env python3
"""verify M3.1 PreToolUse hook: deny direct E2E test commands when
e2e.enabled=true in the verification contract.

When verify controls E2E via `harness verify e2e-status`, the agent must
not bypass the normalised three-step runner by calling Playwright / jest /
cypress / npm-e2e scripts directly.

Blocked command patterns:
  - npx playwright test*
  - npx playwright run*
  - npm run e2e*
  - yarn e2e*
  - pnpm e2e*
  - pytest -m e2e*
  - python -m pytest ... e2e*

State check: if verification-report.contract.yaml has e2e.enabled=true the
block is hard. If the contract is absent or the flag is false / missing,
the hook passes through (no unnecessary friction).

Exit convention: 0 = allow; 2 = block.
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

# Commands that indicate a direct E2E run (case-insensitive)
_E2E_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bnpx\s+playwright\s+(test|run)\b", re.IGNORECASE),
    re.compile(r"\bnpm\s+run\s+e2e\b", re.IGNORECASE),
    re.compile(r"\byarn\s+e2e\b", re.IGNORECASE),
    re.compile(r"\bpnpm\s+e2e\b", re.IGNORECASE),
    re.compile(r"\bpytest\s+.*\s+-m\s+e2e\b", re.IGNORECASE),
    re.compile(r"\bpython\s+.*pytest\b.*\be2e\b", re.IGNORECASE),
    re.compile(r"\bcypress\s+run\b", re.IGNORECASE),
]


def _is_e2e_command(command: str) -> bool:
    return any(pat.search(command) for pat in _E2E_PATTERNS)


def _e2e_enabled(cwd: Path) -> bool | None:
    """Return True if verification contract declares e2e.enabled=true.
    Returns None if contract not found (hook should pass through)."""
    if yaml is None:
        return None
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
        e2e = doc.get("e2e")
        if isinstance(e2e, dict):
            return bool(e2e.get("enabled", False))
        # flat field
        if isinstance(doc.get("e2e_enabled"), bool):
            return doc["e2e_enabled"]
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not _is_e2e_command(command):
        return 0
    cwd = Path(payload.get("cwd") or ".")
    enabled = _e2e_enabled(cwd)
    if enabled is not True:
        # e2e.enabled not set or false — allow direct run
        return 0
    print(
        "HarnessV2 verify hook BLOCKED (DIRECT_E2E_DENIED): "
        "e2e.enabled=true in the verification contract. "
        "Direct E2E commands are not permitted during verify; use "
        "`harness verify e2e-status --mission <id> --json` to run the "
        "normalised e2e_resolver / e2e_runner / normalise three-step suite. "
        f"Blocked command: {command[:200]!r}",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
