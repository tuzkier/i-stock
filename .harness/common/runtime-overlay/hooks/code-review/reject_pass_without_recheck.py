#!/usr/bin/env python3
"""code-review M3.1 PreToolUse hook: reject writing PASS to code-review.md
or code-review.contract.yaml when pending_reviewer_recheck=true.

This provides a second layer of defence (after check_review_ready) against
the "fix code → skip re-review → write PASS" anti-pattern.  It fires on
PreToolUse Write where the target file looks like a code-review output
artifact that might carry a PASS verdict.

Exit conventions:
  0 — pass (not writing a PASS token to a code-review artifact)
  2 — block (writing PASS while pending_reviewer_recheck=true)
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

_REVIEW_ARTIFACT_RE = re.compile(
    r"harness(?:-runtime)?/harness/stages/[^/]+/"
    r"(?:code-review\.md|contracts/code-review\.contract\.yaml)$"
)
_MISSION_RE = re.compile(
    r"harness(?:-runtime)?/harness/stages/([^/]+)/"
)
_PASS_CONTENT_RE = re.compile(r"\bPASS\b|\bApproved\b|\bpassed\b", re.IGNORECASE)


def _load_pending_recheck(cwd: str, mission_id: str) -> bool:
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
        return False
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return False
    if not isinstance(data, dict):
        return False
    contract = (
        data.get("control_contract")
        if isinstance(data.get("control_contract"), dict)
        else data
    )
    if not isinstance(contract, dict):
        return False
    eff = contract.get("effectiveness_review")
    return bool(isinstance(eff, dict) and eff.get("pending_reviewer_recheck"))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Write":
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = str(tool_input.get("file_path") or "")
    content = str(tool_input.get("content") or "")

    if not _REVIEW_ARTIFACT_RE.search(file_path):
        return 0
    if not _PASS_CONTENT_RE.search(content):
        # Not writing a PASS — allow.
        return 0

    mission_match = _MISSION_RE.search(file_path)
    if mission_match is None:
        return 0
    mission_id = mission_match.group(1)

    cwd = payload.get("cwd") or str(Path.cwd())
    if not _load_pending_recheck(cwd, mission_id):
        return 0

    print(
        "HarnessV2 code-review hook BLOCKED: pending_reviewer_recheck=true. "
        "Writing PASS to a code-review artifact is not allowed until all "
        "reviewers have re-examined the fixed code. "
        "Run another reviewer dispatch round and clear the recheck flag first.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
