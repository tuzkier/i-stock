#!/usr/bin/env python3
"""verify M3.1 PreToolUse hook: block a contract patch that sets
ac_trace[*].conclusion=pass unless the AC has both command evidence and
result evidence. UI ACs additionally require screenshot / video / dom kind.

Intercepts `harness contract patch` Bash calls that carry
`ac_trace` and `conclusion: pass` in the patch payload, and also
intercepts Write/Edit of verification-report.contract.yaml (in case the
agent tries to set conclusion directly).

For Write/Edit interception the hook reads the proposed new content and
checks every ac_trace entry with conclusion=pass.

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

_PATCH_CMD_RE = re.compile(
    r"\bharness\s+contract\s+patch\b.*\bac_trace\b.*\bconclusion\b.*\bpass\b",
    re.IGNORECASE | re.DOTALL,
)
_CONTRACT_MARKER = "verification-report.contract.yaml"
_UI_SURFACE_KINDS = {"screenshot", "video", "dom", "dom_snapshot"}


def _has_sufficient_evidence(
    ac_id: str,
    ac: dict,
    command_evidence: list[dict],
    result_evidence: list[dict],
) -> tuple[bool, str]:
    """Check AC has at least one command_evidence + one result_evidence entry.
    For UI ACs additionally require screenshot/video/dom kind.
    Returns (ok, reason)."""
    cmd_ids: set[str] = set(ac.get("command_evidence_ids") or [])
    res_ids: set[str] = set(ac.get("result_evidence_ids") or [])
    if not cmd_ids:
        return False, f"ac_trace[{ac_id}].conclusion=pass but no command_evidence_ids"
    if not res_ids:
        return False, f"ac_trace[{ac_id}].conclusion=pass but no result_evidence_ids"
    # For UI ACs, verify result_evidence kind includes screenshot/video/dom
    is_ui = (
        ac.get("surface_type") == "ui"
        or bool(ac.get("ui_surface"))
    )
    if is_ui:
        res_ev_map = {e.get("id"): e for e in result_evidence if isinstance(e, dict)}
        ui_kind_found = False
        for rid in res_ids:
            ev = res_ev_map.get(rid) or {}
            kind = str(ev.get("kind") or "").lower()
            if kind in _UI_SURFACE_KINDS:
                ui_kind_found = True
                break
        if not ui_kind_found:
            return (
                False,
                f"ac_trace[{ac_id}].surface_type=ui but no linked result_evidence "
                "with kind in [screenshot, video, dom]",
            )
    return True, ""


def _check_contract_doc(doc: dict) -> list[str]:
    """Return list of violations found in the contract document."""
    violations: list[str] = []
    if not isinstance(doc, dict):
        return violations
    inner = doc.get("control_contract") if isinstance(doc.get("control_contract"), dict) else doc
    ac_traces: list[dict] = inner.get("ac_trace") or []
    command_evidence: list[dict] = inner.get("command_evidence") or []
    result_evidence: list[dict] = inner.get("result_evidence") or []
    if not isinstance(ac_traces, list):
        return violations
    for entry in ac_traces:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("conclusion", "")).lower() != "pass":
            continue
        ac_id = entry.get("id") or entry.get("ac_id") or "<unknown>"
        ok, reason = _has_sufficient_evidence(
            ac_id, entry, command_evidence, result_evidence
        )
        if not ok:
            violations.append(reason)
    return violations


def _check_bash_patch(command: str) -> list[str]:
    """Extract inline JSON from a harness contract patch call and check ACs."""
    if yaml is None:
        return []
    # Try to extract JSON blob from the command
    json_match = re.search(r"--data\s+'?(\{.*?\})'?\s*$", command, re.DOTALL)
    if json_match:
        try:
            doc = json.loads(json_match.group(1))
            return _check_contract_doc(doc)
        except (json.JSONDecodeError, ValueError):
            pass
    return []


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    violations: list[str] = []

    if tool_name == "Bash":
        command = tool_input.get("command") or ""
        if not _PATCH_CMD_RE.search(command):
            return 0
        violations = _check_bash_patch(command)

    elif tool_name in {"Write", "Edit", "MultiEdit"}:
        file_path = tool_input.get("file_path") or ""
        if _CONTRACT_MARKER not in file_path:
            return 0
        if yaml is None:
            return 0
        # For Write we have new_string; for Edit we have new_string; for
        # MultiEdit we have edits[].new_string — try to parse proposed content.
        content: str | None = None
        if tool_name in {"Write", "Edit"}:
            content = tool_input.get("new_string") or tool_input.get("content") or ""
        elif tool_name == "MultiEdit":
            # Combine all new_string fragments — conservative: if any pass AC
            # would be introduced we need to check.
            parts = [
                e.get("new_string", "")
                for e in (tool_input.get("edits") or [])
                if isinstance(e, dict)
            ]
            content = "\n".join(parts)
        if not content or "conclusion" not in content or "pass" not in content:
            return 0
        try:
            doc = yaml.safe_load(content)
        except yaml.YAMLError:
            return 0
        if doc is None:
            return 0
        violations = _check_contract_doc(doc)

    else:
        return 0

    if not violations:
        return 0
    viol_str = "; ".join(violations)
    print(
        "HarnessV2 verify hook BLOCKED (AC_EVIDENCE_INSUFFICIENT): "
        "cannot set ac_trace[*].conclusion=pass without both command evidence "
        "and result evidence. UI ACs additionally require screenshot/video/dom kind. "
        f"Violations: [{viol_str}]. "
        "Collect required evidence via `harness evidence command collect` and "
        "`harness contract add-execution-result` before marking ACs as pass.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
