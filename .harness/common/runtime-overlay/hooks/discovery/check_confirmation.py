#!/usr/bin/env python3
"""HarnessV2 discovery PreToolUse hook: block `harness mission stage start <next>`
unless approvals.json contains a typed discovery_confirmation record for the mission.

Triggered on PreToolUse(Bash) matching `harness mission stage start`. Enforces
discovery workflow Step 10 HARD-GATE physically: the user must have actually
confirmed discovery findings (approval type=checkpoint, checkpoint=discovery_confirmation,
status=approved) before the mission can advance to PRD / next stage.

Skip cases:
- The target stage IS discovery → no-op (this hook only fires on outbound advance).
- approvals.json has a `discovery_skip` record (CLI-recorded explicit skip) → allow.

Exit conventions: 0 = allow; 2 = block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HARNESS_STAGE_START_RE = re.compile(r"harness\s+mission\s+stage\s+start")
_MISSION_FLAG_RE = re.compile(r"--mission[=\s]+(\S+)")
_STAGE_FLAG_RE = re.compile(r"--stage[=\s]+(\S+)")


def _resolve_command(payload: dict) -> str | None:
    tool_input = payload.get("tool_input") or {}
    for key in ("command", "cmd"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    command = _resolve_command(payload) or ""
    if not _HARNESS_STAGE_START_RE.search(command):
        return 0

    # If the next stage is discovery itself this hook is not the right gate.
    stage_match = _STAGE_FLAG_RE.search(command)
    if stage_match and stage_match.group(1) == "discovery":
        return 0

    mission_match = _MISSION_FLAG_RE.search(command)
    if not mission_match:
        return 0
    mission = mission_match.group(1)

    cwd = Path(payload.get("cwd") or Path.cwd()).resolve()
    approvals_path = cwd / "harness-runtime" / "harness" / "state" / "approvals.json"
    if not approvals_path.exists():
        print(
            f"HarnessV2 discovery hook BLOCKED: approvals.json not found; mission {mission!r} "
            f"has no discovery_confirmation record. Run discovery Step 10 first.",
            file=sys.stderr,
        )
        return 2

    try:
        document = json.loads(approvals_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0  # malformed; let other validators catch this

    records = document.get("approvals") if isinstance(document, dict) else document
    if not isinstance(records, list):
        return 0

    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("mission_id") != mission:
            continue
        # Accept either an explicit discovery_skip OR a discovery_confirmation
        # checkpoint approval as evidence that discovery has been transitioned out.
        rtype = record.get("type") or ""
        checkpoint = record.get("checkpoint") or ""
        status = (record.get("status") or "").lower()
        if rtype == "discovery_skip":
            return 0
        if (
            rtype == "checkpoint"
            and checkpoint == "discovery_confirmation"
            and status == "approved"
        ):
            return 0

    print(
        f"HarnessV2 discovery hook BLOCKED: mission {mission!r} cannot advance past discovery — "
        f"no approvals.json record of type=discovery_skip or "
        f"(type=checkpoint, checkpoint=discovery_confirmation, status=approved). "
        f"Run discovery Step 10 user confirmation first.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
{
  "_comment": "code-review-improvement-plan M3.1 hook manifest. Pure-review stage: contract-via-CLI + review-ready gate + reviewer write guard + dangerous-git guard + pending-recheck lifecycle + dispatch envelope recording.",
  "stage": "code-review",
  "hooks": [
    {
      "id": "code-review-check-contract-via-cli",
      "event": "PreToolUse",
      "matcher": "Write|Edit|MultiEdit",
      "script": "check_contract_via_cli.py",
      "purpose": "Block direct Write/Edit of code-review.contract.yaml."
    },
    {
      "id": "code-review-check-review-ready",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "check_review_ready.py",
      "purpose": "Block `harness mission stage complete code-review` until pending_reviewer_recheck=false and no unresolved High findings."
    },
    {
      "id": "code-review-deny-reviewer-write",
      "event": "PreToolUse",
      "matcher": "Write|Edit|MultiEdit|NotebookEdit",
      "script": "deny_reviewer_write.py",
      "purpose": "Block reviewer sub-agents from directly editing source files; reviewers may only write findings to the contract via harness CLI."
    },
    {
      "id": "code-review-deny-dangerous-git",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "deny_dangerous_git.py",
      "purpose": "Block destructive git commands (force push, reset --hard, branch -D, clean -f, checkout --, restore .) during code-review stage."
    },
    {
      "id": "code-review-mark-pending-recheck",
      "event": "PostToolUse",
      "matcher": "Write|Edit|MultiEdit|NotebookEdit",
      "script": "mark_pending_recheck.py",
      "purpose": "Set pending_reviewer_recheck=true in the contract after any code edit (excluding edits to the contract and code-review.md themselves)."
    },
    {
      "id": "code-review-reject-pass-without-recheck",
      "event": "PreToolUse",
      "matcher": "Write",
      "script": "reject_pass_without_recheck.py",
      "purpose": "Block writing PASS conclusion to code-review artifacts when pending_reviewer_recheck=true."
    },
    {
      "id": "code-review-record-dispatch-envelope",
      "event": "PostToolUse",
      "matcher": "Task",
      "script": "record_dispatch_envelope.py",
      "purpose": "Append reviewer sub-agent dispatch envelopes to the contract for audit trail when a reviewer Task is dispatched."
    }
  ]
}
