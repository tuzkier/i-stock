#!/usr/bin/env python3
"""verify M1.4 (CROSS-STAGE-OVERLAY-PROTOCOL anchor side) PreToolUse hook:
block `harness mission stage complete verify` until every command_evidence /
result_evidence entry references a `required_evidence_id` that exists in
breakdown's execution-brief.contract.yaml (H3 primary key).

Verify must not invent IDs. The required_evidence_id field on each
command_evidence / result_evidence anchors back to a breakdown task's
typed required_evidence[].id.
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
    r"\bharness\s+mission\s+stage\s+complete\s+verify\b"
)
_MISSION_FLAG_RE = re.compile(r"--mission\s+([^\s'\"]+)")


def _load_yaml(path: Path) -> dict | None:
    if not path.exists() or yaml is None:
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _unwrap_contract(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    return doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc


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
    mission_id = mission_match.group(1)
    cwd = Path(payload.get("cwd") or ".")
    brief_path = cwd / f"harness-runtime/harness/stages/{mission_id}/contracts/execution-brief.contract.yaml"
    report_path = cwd / f"harness-runtime/harness/stages/{mission_id}/contracts/verification-report.contract.yaml"
    brief = _unwrap_contract(_load_yaml(brief_path))
    report = _unwrap_contract(_load_yaml(report_path))
    if brief is None or report is None:
        # Cannot enforce without both contracts — let other hooks decide.
        return 0
    valid_ids: set[str] = set()
    for task in brief.get("tasks") or []:
        if not isinstance(task, dict):
            continue
        for ev in task.get("required_evidence") or []:
            if isinstance(ev, dict) and isinstance(ev.get("id"), str):
                valid_ids.add(ev["id"])
    missing_refs: list[str] = []
    for key in ("command_evidence", "result_evidence"):
        entries = report.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            ref = entry.get("required_evidence_id")
            if not ref:
                missing_refs.append(
                    f"{key}.{entry.get('id', '<unknown>')}=<missing>"
                )
            elif ref not in valid_ids:
                missing_refs.append(
                    f"{key}.{entry.get('id', '<unknown>')}={ref!r} not in execution-brief"
                )
    if missing_refs:
        print(
            "HarnessV2 verify hook BLOCKED (VERIFY_EVIDENCE_ID_NOT_IN_UPSTREAM): "
            "verification-report.contract.yaml carries evidence entries that "
            "do not reference a valid breakdown required_evidence[].id. "
            f"Offending entries: {missing_refs}. "
            "Anchor each command/result_evidence to a typed upstream id; "
            "verify does not invent IDs.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
