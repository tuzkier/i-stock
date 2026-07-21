"""Stage hook checks: breakdown.

Migrated from .harness/common/runtime-overlay/hooks/breakdown/*.py — the seven
legacy standalone scripts now run in-process under the unified dispatcher.

The breakdown stage drives the execution-brief artifact: it is the only stage
that dispatches two execution workers (delivery-slicer + test-planning-expert)
under a shared parallel-worker barrier.
"""

from __future__ import annotations

import re

from context import HookContext
from entry import BASH, HookEntry, WRITE
from result import HookResult
from lib import commands, contracts

_CONTRACT_FILENAME = "execution-brief.contract.yaml"
_RECHECK_FIELD = "effectiveness_review.pending_reviewer_recheck"

# parallel-worker barrier (check_barrier_complete)
_REQUIRED_ROLES = ("delivery-slicer", "test-planning-expert")
_BARRIER = "breakdown-workers-parallel"

# execution-brief.md path signal (mark_pending_recheck)
_EXEC_BRIEF_MD_RE = re.compile(
    r"harness-runtime/harness/stages/[^/]+/execution-brief\.md$"
)

# first-write completeness heuristics (check_first_write_completeness)
_ATOMIC_QUEUE_MARKER_RE = re.compile(r"\batomic_task_queue\s*:", re.IGNORECASE)
_FORBIDDEN_STATUS_RE = re.compile(
    r"atomic_task_queue\s*:[\s\S]{0,200}?status\s*:\s*(missing|incomplete|draft)\b",
    re.IGNORECASE,
)
_PARENT_TASK_HEADER_RE = re.compile(
    r"^(?:#{2,4})\s+(?:Parent\s+Task|Task\s+T-?\d+|T-?\d+\s)",
    re.MULTILINE,
)

# writing-plans gating (check_writing_plans_boundary)
_WRITING_PLANS_CMD_RE = re.compile(r"\bharness\s+writing-plans\s+run\b")
_MODE_FLAG_RE = re.compile(r"--mode\s+([^\s'\"]+)")
_MANUAL_REPLAN_RE = re.compile(r"--manual-replan\b")
# advance command spanning gate advance / contract advance / stage complete
_ADVANCE_BARRIER_RE = re.compile(
    r"\bharness\s+(?:gate\s+advance|contract\s+advance|mission\s+stage\s+complete)\b"
)
_STAGE_COMPLETE_TOKEN_RE = re.compile(r"mission\s+stage\s+complete\s+([a-z_-]+)")


def _mission_id(ctx: HookContext) -> str | None:
    return commands.mission_id(ctx.command) or ctx.mission_id


def _contract(ctx: HookContext, mission_id: str) -> dict:
    return contracts.load_contract(
        contracts.stage_contract_path(ctx.cwd, mission_id, _CONTRACT_FILENAME)
    )


# --- checks ----------------------------------------------------------------
def check_contract_via_cli(ctx: HookContext) -> HookResult:
    """PreToolUse Write/Edit: forbid direct edits of execution-brief.contract.yaml.

    The contract YAML must only be reached through `harness contract fill /
    patch / add-execution-result`, which run schema validation + reviewer
    bookkeeping that direct edits would skip."""
    try:
        file_path = ctx.file_path or ""
        if _CONTRACT_FILENAME not in file_path:
            return HookResult.ok()
        return HookResult.block(
            f"HarnessV2 breakdown hook BLOCKED: direct Write/Edit of "
            f"{_CONTRACT_FILENAME} is forbidden. Use `harness contract fill/patch/"
            "add-execution-result --json` so schema validation and reviewer "
            "bookkeeping stay intact."
        )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()


def check_first_write_completeness(ctx: HookContext) -> HookResult:
    """PreToolUse Write: forbid writing execution-brief.md without a complete
    atomic_task_queue for every Parent task (first-write completeness HARD-GATE).
    """
    try:
        file_path = ctx.file_path or ""
        if not file_path.endswith("execution-brief.md"):
            return HookResult.ok()
        # First-write completeness only inspects the Write tool's full content.
        if ctx.tool_name != "Write":
            return HookResult.ok()
        content = ctx.tool_input.get("content")
        if not isinstance(content, str):
            return HookResult.ok()
        if not _ATOMIC_QUEUE_MARKER_RE.search(content):
            # Contract-prep stubs without Parent task headers are allowed.
            if not _PARENT_TASK_HEADER_RE.search(content):
                return HookResult.ok()
            return HookResult.block(
                "HarnessV2 breakdown hook BLOCKED: execution-brief.md contains "
                "Parent task headers but no `atomic_task_queue:` block. First "
                "write must include every Parent task's parent-local Atomic Task "
                "Queue (plan §2.7 first-write completeness HARD-GATE)."
            )
        bad_state = _FORBIDDEN_STATUS_RE.search(content)
        if bad_state is not None:
            return HookResult.block(
                "HarnessV2 breakdown hook BLOCKED: execution-brief.md "
                f"atomic_task_queue.status='{bad_state.group(1)}' is forbidden. "
                "First write must already declare status: ready (or accepted)."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def check_writing_plans_boundary(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: gate `harness writing-plans run` to the breakdown stage,
    require --mode internal-carrier."""
    try:
        command = ctx.command or ""
        if not _WRITING_PLANS_CMD_RE.search(command):
            return HookResult.ok()
        mode_match = _MODE_FLAG_RE.search(command)
        if mode_match is None or mode_match.group(1) != "internal-carrier":
            return HookResult.block(
                "HarnessV2 breakdown hook BLOCKED: `harness writing-plans run` "
                "requires --mode internal-carrier. writing-plans is the "
                "breakdown stage's internal carrier; no other entry is supported."
            )
        # Manual-replan escape hatch — honored only with explicit opt-in.
        if _MANUAL_REPLAN_RE.search(command):
            return HookResult.ok()
        # Dispatcher already confirmed mission stage == breakdown; ctx.stage is
        # the resolved current stage. Block only when it is a known non-breakdown.
        stage = (ctx.stage or "").strip()
        if stage and stage != "breakdown":
            return HookResult.block(
                f"HarnessV2 breakdown hook BLOCKED: writing-plans called from "
                f"stage={stage!r} (current); only allowed from `breakdown` or "
                "with --manual-replan + trace-log ack."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def check_barrier_complete(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: block stage advance until both delivery-slicer and
    test-planning-expert have DONE entries in execution_results[]."""
    try:
        command = ctx.command or ""
        if not _ADVANCE_BARRIER_RE.search(command):
            return HookResult.ok()
        # The command must target the breakdown stage.
        stage_match = commands.stage(command)
        complete_match = _STAGE_COMPLETE_TOKEN_RE.search(command)
        targets_breakdown = (stage_match == "breakdown") or (
            complete_match is not None and complete_match.group(1) == "breakdown"
        )
        if not targets_breakdown:
            return HookResult.ok()
        mission_id = _mission_id(ctx)
        if not mission_id:
            return HookResult.ok()
        contract = _contract(ctx, mission_id)
        if not contract:
            return HookResult.ok()
        done: set[str] = set()
        for entry in contract.get("execution_results") or []:
            if not isinstance(entry, dict) or entry.get("status") != "DONE":
                continue
            if entry.get("barrier_group") and entry["barrier_group"] != _BARRIER:
                continue
            role = entry.get("role")
            if isinstance(role, str):
                done.add(role)
        missing = [r for r in _REQUIRED_ROLES if r not in done]
        if missing:
            return HookResult.block(
                f"HarnessV2 breakdown hook BLOCKED: parallel-worker barrier "
                f"'{_BARRIER}' incomplete. Missing DONE entries for: "
                f"{', '.join(missing)}. Re-dispatch the missing roles before "
                "advancing."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def check_gate_pass(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: block `harness mission stage complete breakdown` until
    effectiveness_review.last_gate_run_status == PASS."""
    try:
        if not commands.is_stage_complete(ctx.command, "breakdown"):
            return HookResult.ok()
        mission_id = _mission_id(ctx)
        if not mission_id:
            return HookResult.ok()
        contract_path = contracts.stage_contract_path(
            ctx.cwd, mission_id, _CONTRACT_FILENAME
        )
        if not contract_path.exists():
            return HookResult.block(
                "HarnessV2 breakdown hook BLOCKED: cannot verify gate run "
                "result (execution-brief.contract.yaml unloadable). Run "
                "`harness execution-brief gate run --json` and capture the "
                "PASS verdict before stage complete."
            )
        contract = contracts.load_contract(contract_path)
        if not contract:
            return HookResult.block(
                "HarnessV2 breakdown hook BLOCKED: cannot verify gate run "
                "result (execution-brief.contract.yaml unloadable). Run "
                "`harness execution-brief gate run --json` and capture the "
                "PASS verdict before stage complete."
            )
        eff = contract.get("effectiveness_review")
        status = eff.get("last_gate_run_status") if isinstance(eff, dict) else None
        if status != "PASS":
            return HookResult.block(
                "HarnessV2 breakdown hook BLOCKED: effectiveness_review."
                f"last_gate_run_status={status!r}; must be 'PASS' before "
                "`harness mission stage complete breakdown`. Run "
                "`harness execution-brief gate run --json` and record the "
                "PASS result."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def check_pending_recheck(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: block `harness gate/contract advance` while the
    breakdown contract carries pending_reviewer_recheck=true."""
    try:
        if not commands.is_advance(ctx.command):
            return HookResult.ok()
        stage_match = commands.stage(ctx.command)
        if stage_match and stage_match != "breakdown":
            return HookResult.ok()
        mission_id = _mission_id(ctx)
        if not mission_id:
            return HookResult.ok()
        contract_path = contracts.stage_contract_path(
            ctx.cwd, mission_id, _CONTRACT_FILENAME
        )
        if contracts.pending_recheck(contract_path, field_path=_RECHECK_FIELD):
            return HookResult.block(
                "HarnessV2 breakdown hook BLOCKED: execution-brief.contract.yaml "
                "has pending_reviewer_recheck=true. Run execution-plan-"
                "effectiveness-reviewer again (with `harness contract patch "
                "--add-round`) before advancing."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def mark_pending_recheck(ctx: HookContext) -> HookResult:
    """PostToolUse: flip pending_reviewer_recheck=true on the breakdown contract
    after execution-brief.md is edited."""
    try:
        rel = ctx.rel_path()
        if not _EXEC_BRIEF_MD_RE.search(rel):
            return HookResult.ok()
        mission_id = rel.split("harness-runtime/harness/stages/", 1)[1].split("/", 1)[0]
        if not mission_id:
            return HookResult.ok()
        contract_path = contracts.stage_contract_path(
            ctx.cwd, mission_id, _CONTRACT_FILENAME
        )
        if not contract_path.exists():
            return HookResult.ok()
        contracts.set_pending_recheck(contract_path, True, field_path=_RECHECK_FIELD)
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="breakdown-check-contract-via-cli", event="PreToolUse",
              check=check_contract_via_cli, tools=WRITE),
    HookEntry(id="breakdown-check-first-write-completeness", event="PreToolUse",
              check=check_first_write_completeness, tools=WRITE),
    HookEntry(id="breakdown-check-writing-plans-boundary", event="PreToolUse",
              check=check_writing_plans_boundary, tools=BASH),
    HookEntry(id="breakdown-check-barrier-complete", event="PreToolUse",
              check=check_barrier_complete, tools=BASH),
    HookEntry(id="breakdown-check-gate-pass", event="PreToolUse",
              check=check_gate_pass, tools=BASH),
    HookEntry(id="breakdown-mark-pending-recheck", event="PostToolUse",
              check=mark_pending_recheck, tools=WRITE),
    HookEntry(id="breakdown-check-pending-recheck", event="PreToolUse",
              check=check_pending_recheck, tools=BASH),
]
