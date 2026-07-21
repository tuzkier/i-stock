"""Stage hook checks: code-review.

Migrated from .harness/common/runtime-overlay/hooks/code-review/*.py — the seven
legacy standalone scripts now run in-process under the unified dispatcher.

code-review is a pure-review stage: contract-via-CLI guard, review-ready gate,
reviewer write guard, dangerous-git guard, pending-recheck lifecycle, and
reviewer dispatch-envelope recording.
"""

from __future__ import annotations

import datetime as _dt
import re

from context import HookContext
from entry import BASH, HookEntry, TASK, WRITE, WRITE_NB
from result import HookResult
from lib import commands, contracts, roles

_CONTRACT_FILENAME = "code-review.contract.yaml"
_RECHECK_FIELD = "effectiveness_review.pending_reviewer_recheck"

# control-plane artifacts that mark_pending_recheck must NOT treat as code edits
_CONTROL_PLANE_RE = (
    re.compile(r"code-review\.contract\.yaml$"),
    re.compile(r"code-review\.md$"),
)
# mission id embedded in a stage artifact path (mark_pending_recheck)
_STAGE_PATH_MISSION_RE = re.compile(r"harness(?:-runtime)?/harness/stages/([^/]+)/")
# code-review output artifacts that might carry a PASS verdict
_REVIEW_ARTIFACT_RE = re.compile(
    r"harness(?:-runtime)?/harness/stages/[^/]+/"
    r"(?:code-review\.md|contracts/code-review\.contract\.yaml)$"
)
_PASS_CONTENT_RE = re.compile(r"\bPASS\b|\bApproved\b|\bpassed\b", re.IGNORECASE)
# mission id embedded in a Task dispatch description / prompt
_MISSION_IN_TEXT_RE = re.compile(r"--mission\s+([^\s'\"]+)")
# dangerous-git kinds blocked during code-review (legacy deny_dangerous_git set)
_GIT_DANGER_KINDS = (
    "force-push",
    "hard-reset",
    "branch-delete",
    "clean-force",
    "checkout-discard",
    "restore-discard",
)


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_control_plane(file_path: str) -> bool:
    return any(p.search(file_path) for p in _CONTROL_PLANE_RE)


# --- checks ----------------------------------------------------------------
def check_contract_via_cli(ctx: HookContext) -> HookResult:
    """PreToolUse Write/Edit: forbid direct edits of code-review.contract.yaml."""
    try:
        file_path = ctx.file_path or ""
        if _CONTRACT_FILENAME not in file_path:
            return HookResult.ok()
        return HookResult.block(
            f"HarnessV2 code-review hook BLOCKED: direct Write/Edit of "
            f"{_CONTRACT_FILENAME} is forbidden. Use `harness contract fill/patch/"
            "add-verdict --json` so multi-reviewer verdicts stay typed."
        )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()


def check_review_ready(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: block `harness mission stage complete code-review` until
    pending_reviewer_recheck=false and no unresolved High findings."""
    try:
        if not commands.is_stage_complete(ctx.command, "code-review"):
            return HookResult.ok()
        mission_id = commands.mission_id(ctx.command) or ctx.mission_id
        if not mission_id:
            return HookResult.ok()
        contract_path = contracts.stage_contract_path(
            ctx.cwd, mission_id, _CONTRACT_FILENAME
        )
        if not contract_path.exists():
            return HookResult.block(
                "HarnessV2 code-review hook BLOCKED: cannot verify review "
                "readiness (code-review.contract.yaml unloadable). Run "
                "`harness review check-ready --json` and capture a PASS "
                "before stage complete."
            )
        contract = contracts.load_contract(contract_path)
        if not contract:
            return HookResult.block(
                "HarnessV2 code-review hook BLOCKED: cannot verify review "
                "readiness (code-review.contract.yaml unloadable). Run "
                "`harness review check-ready --json` and capture a PASS "
                "before stage complete."
            )
        eff = contract.get("effectiveness_review")
        if isinstance(eff, dict) and eff.get("pending_reviewer_recheck"):
            return HookResult.block(
                "HarnessV2 code-review hook BLOCKED: pending_reviewer_recheck=true. "
                "Resolve all High findings or re-run reviewers before stage complete."
            )
        findings = contract.get("findings")
        findings = findings if isinstance(findings, list) else []
        open_high = [
            f
            for f in findings
            if isinstance(f, dict)
            and (f.get("severity") or "").lower() == "high"
            and (f.get("status") or "open").lower() != "resolved"
        ]
        if open_high:
            ids = ", ".join(str(f.get("id") or "<unknown>") for f in open_high)
            return HookResult.block(
                "HarnessV2 code-review hook BLOCKED: unresolved High findings: "
                f"{ids}. Resolve or mark each via "
                "`harness contract patch --add-finding-resolution`."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def deny_reviewer_write(ctx: HookContext) -> HookResult:
    """PreToolUse Write/Edit/MultiEdit/NotebookEdit: block reviewer sub-agents
    from directly editing files."""
    try:
        role = ctx.agent_role
        if not role or not roles.is_reviewer(role):
            return HookResult.ok()
        return HookResult.block(
            f"HarnessV2 code-review hook BLOCKED: reviewer role {role!r} "
            "attempted a write tool. Reviewer agents are readonly. "
            "Use harness contract patch/add-verdict to record findings."
        )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()


def deny_dangerous_git(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: block destructive git commands during code-review."""
    try:
        kind = commands.git_danger(ctx.command, kinds=_GIT_DANGER_KINDS)
        if kind is None:
            return HookResult.ok()
        return HookResult.block(
            f"HarnessV2 code-review hook BLOCKED: dangerous git command "
            f"({kind}) is not allowed during code-review stage. "
            "Use safe git operations (diff, status, log) instead."
        )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()


def mark_pending_recheck(ctx: HookContext) -> HookResult:
    """PostToolUse: set pending_reviewer_recheck=true after any code edit
    (excluding edits to the contract / code-review.md themselves)."""
    try:
        file_path = ctx.file_path or ""
        if not file_path:
            return HookResult.ok()
        if _is_control_plane(file_path):
            return HookResult.ok()
        match = _STAGE_PATH_MISSION_RE.search(file_path.replace("\\", "/"))
        if match is None:
            return HookResult.ok()
        mission_id = match.group(1)
        contract_path = contracts.stage_contract_path(
            ctx.cwd, mission_id, _CONTRACT_FILENAME
        )
        if not contract_path.exists():
            return HookResult.ok()
        contracts.set_pending_recheck(contract_path, True, field_path=_RECHECK_FIELD)
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def reject_pass_without_recheck(ctx: HookContext) -> HookResult:
    """PreToolUse Write: block writing a PASS verdict to a code-review artifact
    while pending_reviewer_recheck=true."""
    try:
        if ctx.tool_name != "Write":
            return HookResult.ok()
        file_path = ctx.file_path or ""
        if not _REVIEW_ARTIFACT_RE.search(file_path.replace("\\", "/")):
            return HookResult.ok()
        content = ctx.tool_input.get("content")
        content = content if isinstance(content, str) else ""
        if not _PASS_CONTENT_RE.search(content):
            return HookResult.ok()
        match = _STAGE_PATH_MISSION_RE.search(file_path.replace("\\", "/"))
        if match is None:
            return HookResult.ok()
        contract_path = contracts.stage_contract_path(
            ctx.cwd, match.group(1), _CONTRACT_FILENAME
        )
        if contracts.pending_recheck(contract_path, field_path=_RECHECK_FIELD):
            return HookResult.block(
                "HarnessV2 code-review hook BLOCKED: pending_reviewer_recheck=true. "
                "Writing PASS to a code-review artifact is not allowed until all "
                "reviewers have re-examined the fixed code. "
                "Run another reviewer dispatch round and clear the recheck flag first."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def record_dispatch_envelope(ctx: HookContext) -> HookResult:
    """PostToolUse Task: append a reviewer sub-agent dispatch envelope to the
    code-review contract for the Gate audit trail."""
    try:
        tool_input = ctx.tool_input
        tool_output = ctx.tool_response or {}
        role = str(tool_input.get("subagent_type") or tool_input.get("role") or "")
        if not role.endswith("-reviewer"):
            return HookResult.ok()

        model = str(
            tool_output.get("model")
            or tool_input.get("model")
            or ctx.raw.get("model")
            or "unknown"
        )
        execution_mode = str(
            tool_output.get("execution_mode")
            or tool_input.get("execution_mode")
            or "spawn_agent"
        )
        fallback_used = execution_mode == "main_agent_fallback"
        started_at = str(
            tool_input.get("started_at") or ctx.raw.get("started_at") or _now_iso()
        )
        completed_at = _now_iso()

        description = str(tool_input.get("description") or tool_input.get("prompt") or "")
        match = _MISSION_IN_TEXT_RE.search(description)
        if match is None:
            return HookResult.ok()
        mission_id = match.group(1)

        contract_path = contracts.stage_contract_path(
            ctx.cwd, mission_id, _CONTRACT_FILENAME
        )
        if not contract_path.exists():
            return HookResult.ok()
        raw = contracts.load_yaml(contract_path)
        if raw is None:
            return HookResult.ok()
        body = (
            raw.get("control_contract")
            if isinstance(raw.get("control_contract"), dict)
            else raw
        )
        if not isinstance(body, dict):
            return HookResult.ok()
        dispatches = body.get("dispatches")
        if not isinstance(dispatches, list):
            dispatches = []
            body["dispatches"] = dispatches
        dispatches.append(
            {
                "role": role,
                "execution_mode": execution_mode,
                "model": model,
                "fallback_used": fallback_used,
                "started_at": started_at,
                "completed_at": completed_at,
            }
        )
        contracts.save_yaml(contract_path, raw)
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="code-review-check-contract-via-cli", event="PreToolUse",
              check=check_contract_via_cli, tools=WRITE),
    HookEntry(id="code-review-check-review-ready", event="PreToolUse",
              check=check_review_ready, tools=BASH),
    HookEntry(id="code-review-deny-reviewer-write", event="PreToolUse",
              check=deny_reviewer_write, tools=WRITE_NB),
    HookEntry(id="code-review-deny-dangerous-git", event="PreToolUse",
              check=deny_dangerous_git, tools=BASH),
    HookEntry(id="code-review-mark-pending-recheck", event="PostToolUse",
              check=mark_pending_recheck, tools=WRITE_NB),
    HookEntry(id="code-review-reject-pass-without-recheck", event="PreToolUse",
              check=reject_pass_without_recheck, tools=WRITE),
    HookEntry(id="code-review-record-dispatch-envelope", event="PostToolUse",
              check=record_dispatch_envelope, tools=TASK),
]
