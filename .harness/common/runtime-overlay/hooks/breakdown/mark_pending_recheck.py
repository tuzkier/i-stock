#!/usr/bin/env python3
"""breakdown-improvement-plan M3.1 PostToolUse hook: set
pending_reviewer_recheck=true after execution-brief.md edit.

Follows the same shape as the prd hook (plan §M3.1 reuses prd template):
whenever the AI edits execution-brief.md, this hook flips
`effectiveness_review.pending_reviewer_recheck=true` in the matching
execution-brief.contract.yaml. The pre-advance hook (check_pending_recheck)
then refuses to advance the gate until a reviewer round resets the flag.

Exit conventions: 0 = always (non-blocking post hook).
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

_EXEC_BRIEF_MD_PATTERN = re.compile(
    r"harness-runtime/harness/stages/[^/]+/execution-brief\.md$"
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if payload.get("tool_name", "") not in ("Edit", "Write", "MultiEdit"):
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not _EXEC_BRIEF_MD_PATTERN.search(file_path):
        return 0
    if yaml is None:
        return 0
    contract_path = (
        Path(file_path).resolve().parent
        / "contracts"
        / "execution-brief.contract.yaml"
    )
    if not contract_path.exists():
        return 0
    try:
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return 0
    if not isinstance(data, dict):
        return 0
    contract = data.get("control_contract") if isinstance(data.get("control_contract"), dict) else data
    if not isinstance(contract, dict):
        return 0
    eff = contract.get("effectiveness_review")
    if isinstance(eff, dict):
        eff["pending_reviewer_recheck"] = True
    else:
        contract["effectiveness_review"] = {"pending_reviewer_recheck": True}
    contract_path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
{
  "_comment": "verify-improvement-plan M3.1 hook manifest. Includes the M1.4 cross-stage anchor side: check_evidence_id_referenced enforces that every command/result_evidence entry references a valid breakdown required_evidence[].id (H3 primary key). M3.1 adds 10 additional hooks for worker/reviewer boundary, E2E control, gate prerequisites, acceptance evidence sufficiency, failure-path enforcement, and PostToolUse sensors.",
  "stage": "verify",
  "hooks": [
    {
      "id": "verify-check-contract-via-cli",
      "event": "PreToolUse",
      "matcher": "Write|Edit|MultiEdit",
      "script": "check_contract_via_cli.py",
      "purpose": "Block direct Write/Edit of verification-report.contract.yaml."
    },
    {
      "id": "verify-check-evidence-id-referenced",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "check_evidence_id_referenced.py",
      "purpose": "Block stage complete unless every command/result_evidence references a valid breakdown required_evidence id."
    },
    {
      "id": "verify-deny-reviewer-write",
      "event": "PreToolUse",
      "matcher": "Write|Edit|MultiEdit",
      "script": "deny_reviewer_write.py",
      "purpose": "Block verification-effectiveness-reviewer from writing files; reviewer is readonly."
    },
    {
      "id": "verify-check-worker-write-scope",
      "event": "PreToolUse",
      "matcher": "Write|Edit|MultiEdit",
      "script": "check_worker_write_scope.py",
      "purpose": "Block verification-engineer from writing files outside the allowed write_scope (verification-report, traces, approvals)."
    },
    {
      "id": "verify-deny-direct-e2e",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "deny_direct_e2e.py",
      "purpose": "Block direct Playwright/npm-e2e commands when e2e.enabled=true; must use `harness verify e2e-status`."
    },
    {
      "id": "verify-check-prereqs",
      "event": "PreToolUse",
      "matcher": "Bash",
      "script": "check_verify_prereqs.py",
      "purpose": "Block `harness gate advance` / `harness contract advance` until command_evidence_collected, gate PASS, and contradictions PASS."
    },
    {
      "id": "verify-check-ac-evidence",
      "event": "PreToolUse",
      "matcher": "Bash|Write|Edit|MultiEdit",
      "script": "check_ac_evidence.py",
      "purpose": "Block acceptance_trace[*].conclusion=pass patches that lack command + result evidence; UI acceptance scenarios require screenshot/video/dom."
    },
    {
      "id": "verify-require-failure-path",
      "event": "PreToolUse",
      "matcher": "Write|Edit|MultiEdit",
      "script": "require_failure_path.py",
      "purpose": "Block Edit/Write to src/** or tests/** during verify unless a typed failure_path record exists."
    },
    {
      "id": "verify-record-context-reads",
      "event": "PostToolUse",
      "matcher": "Read",
      "script": "record_context_reads.py",
      "purpose": "Sensor: append context_reads trace event when mission-contract/execution-brief/code-review/project-context are read."
    },
    {
      "id": "verify-record-dispatch",
      "event": "PostToolUse",
      "matcher": "Task",
      "script": "record_dispatch.py",
      "purpose": "Sensor: write dispatch envelope to trace and set reviewer_turn/worker_turn flag files."
    },
    {
      "id": "verify-record-command-flag",
      "event": "PostToolUse",
      "matcher": "Bash",
      "script": "record_command_flag.py",
      "purpose": "Sensor: write command_evidence_collected.flag after successful evidence command collect or verify run-tests."
    },
    {
      "id": "verify-mirror-evidence-graph",
      "event": "PostToolUse",
      "matcher": "Bash",
      "script": "mirror_evidence_graph.py",
      "purpose": "Sensor: rebuild evidence_graph.json from acceptance_trace after contract patch/add-execution-result calls."
    }
  ]
}
