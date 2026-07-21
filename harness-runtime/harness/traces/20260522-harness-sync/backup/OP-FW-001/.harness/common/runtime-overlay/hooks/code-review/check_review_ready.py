#!/usr/bin/env python3
"""code-review M3.1 PreToolUse hook: block `harness mission stage complete
code-review` until the upstream `pending_reviewer_recheck` flag has cleared
for every reviewer (multi-reviewer parallel completion).
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

_STAGE_COMPLETE_RE = re.compile(
    r"\bharness\s+mission\s+stage\s+complete\s+code-review\b"
)
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _load_contract(cwd: str, mission_id: str) -> dict | None:
    path = (
        Path(cwd)
        / "harness-runtime"
        / "harness"
        / "stages"
        / mission_id
        / "contracts"
        / "code-review.contract.yaml"
    )
    if not path.exists() or yaml is None:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if not _STAGE_COMPLETE_RE.search(command):
        return 0
    mission_match = _MISSION_FLAG_RE.search(command)
    if mission_match is None:
        return 0
    cwd = payload.get("cwd") or str(Path.cwd())
    contract = _load_contract(cwd, mission_match.group(1))
    if contract is None:
        print(
            "HarnessV2 code-review hook BLOCKED: cannot verify review "
            "readiness (code-review.contract.yaml unloadable). Run "
            "`harness review check-ready --json` and capture a PASS "
            "before stage complete.",
            file=sys.stderr,
        )
        return 2
    eff = contract.get("effectiveness_review") if isinstance(contract.get("effectiveness_review"), dict) else {}
    if eff.get("pending_reviewer_recheck"):
        print(
            "HarnessV2 code-review hook BLOCKED: pending_reviewer_recheck=true. "
            "Resolve all High findings or re-run reviewers before stage complete.",
            file=sys.stderr,
        )
        return 2
    # High findings must be resolved (severity = High AND status != resolved).
    findings = contract.get("findings") if isinstance(contract.get("findings"), list) else []
    open_high = [
        f
        for f in findings
        if isinstance(f, dict)
        and (f.get("severity") or "").lower() == "high"
        and (f.get("status") or "open").lower() != "resolved"
    ]
    if open_high:
        ids = ", ".join(str(f.get("id") or "<unknown>") for f in open_high)
        print(
            "HarnessV2 code-review hook BLOCKED: unresolved High findings: "
            f"{ids}. Resolve or mark each via "
            "`harness contract patch --add-finding-resolution`.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
