"""Stage hook checks: intake.

Migrated from .harness/common/runtime-overlay/hooks/intake/*.py — the five
legacy standalone scripts now run in-process under the unified dispatcher.
"""

from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess

from context import HookContext
from entry import BASH, READ, WRITE, WRITE_NB, HookEntry
from result import HookResult
from lib import commands, contracts

# --- shared path signals ---------------------------------------------------
_PROTECTED_BRANCH_PATTERNS = (
    re.compile(r"harness-runtime/harness/mission-status\.yaml$"),
    re.compile(r"harness-runtime/harness/work-graph/"),
)
_MISSION_BRANCH_RE = re.compile(r"^mission/.+")

_MISSION_CONTRACT_PATH_RE = re.compile(
    r"harness-runtime/harness/missions/(?P<mission>[^/]+)/"
    r"(?:mission-contract\.md|contracts/mission-contract\.contract\.yaml)$"
)
_STAGE_WORKTREE_RE = re.compile(r"/\.?worktrees/stage-[^/]+-intake/")
_DOWNGRADE_ENV = "HARNESS_GIT_STRATEGY_DOWNGRADED"

_CONTEXT_PATH_RE = re.compile(r"(?:^|/)project-context\.md$")

_CONTRACT_FILENAME = "mission-contract.contract.yaml"


def _current_git_branch(cwd: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


# --- check-mission-branch ---------------------------------------------------
def check_mission_branch(ctx: HookContext) -> HookResult:
    """Block runtime YAML edits when not on a mission/<id> branch."""
    target = ctx.file_path
    if target is None:
        return HookResult.ok()
    rel = ctx.rel_path(target)
    if not any(pat.search(rel) for pat in _PROTECTED_BRANCH_PATTERNS):
        return HookResult.ok()

    branch = _current_git_branch(str(ctx.cwd))
    if branch is None:
        return HookResult.ok()
    if _MISSION_BRANCH_RE.match(branch):
        return HookResult.ok()

    return HookResult.block(
        f"HarnessV2 intake hook BLOCKED: cannot write {rel} on branch {branch!r}. "
        "Run `git-workflow prepare` to create a mission/<mission-id> branch first."
    )


# --- check-stage-worktree ---------------------------------------------------
def check_stage_worktree(ctx: HookContext) -> HookResult:
    """Block mission-contract writes outside the intake stage worktree."""
    target = ctx.file_path
    if target is None:
        return HookResult.ok()
    rel = ctx.rel_path(target)
    if not _MISSION_CONTRACT_PATH_RE.search(rel):
        return HookResult.ok()

    if os.environ.get(_DOWNGRADE_ENV) == "1":
        return HookResult.ok()

    cwd_norm = str(ctx.cwd.resolve()) + "/"
    if _STAGE_WORKTREE_RE.search(cwd_norm):
        return HookResult.ok()

    return HookResult.block(
        f"HarnessV2 intake hook BLOCKED: cannot write {rel} from cwd {str(ctx.cwd)!r}. "
        "Run `git-workflow start-stage(intake)` to create the stage worktree first, "
        f"or set {_DOWNGRADE_ENV}=1 for downgraded git strategy."
    )


# --- check-pending-recheck --------------------------------------------------
def check_pending_recheck(ctx: HookContext) -> HookResult:
    """Block `harness gate/contract advance` while the mission-contract carries
    an unresolved pending_reviewer_recheck flag."""
    command = ctx.command
    if not commands.is_advance(command):
        return HookResult.ok()

    mission_id = commands.mission_id(command)
    if mission_id is None:
        return HookResult.ok()

    contract_path = contracts.stage_contract_path(
        ctx.cwd, mission_id, _CONTRACT_FILENAME, base="missions"
    )
    if contracts.pending_recheck(contract_path):
        return HookResult.block(
            f"HarnessV2 intake hook BLOCKED: {contract_path.name} has "
            "pending_reviewer_recheck=true. Re-run mission-contract-effectiveness-reviewer "
            "before advancing."
        )
    return HookResult.ok()


# --- mark-pending-recheck ---------------------------------------------------
def mark_pending_recheck(ctx: HookContext) -> HookResult:
    """After a mission-contract edit, flip pending_reviewer_recheck=true so the
    pre-advance check fires."""
    target = ctx.file_path
    if target is None:
        return HookResult.ok()
    rel = ctx.rel_path(target)
    match = _MISSION_CONTRACT_PATH_RE.search(rel)
    if not match:
        return HookResult.ok()

    mission_id = match.group("mission")
    contract_path = contracts.stage_contract_path(
        ctx.cwd, mission_id, _CONTRACT_FILENAME, base="missions"
    )
    if not contract_path.exists():
        return HookResult.ok()

    contracts.set_pending_recheck(contract_path, True)
    return HookResult.ok()


# --- record-context-read ----------------------------------------------------
def record_context_read(ctx: HookContext) -> HookResult:
    """Append a structured trace event when project-context.md is read."""
    target = ctx.file_path
    if target is None or not _CONTEXT_PATH_RE.search(target):
        return HookResult.ok()

    state_file = ctx.runtime_root / "state" / "active-mission"
    mission_id: str | None = None
    if state_file.exists():
        try:
            mission_id = state_file.read_text(encoding="utf-8").strip() or None
        except OSError:
            mission_id = None

    rel = f"traces/{mission_id}/steps.jsonl" if mission_id else "traces/_context-reads.jsonl"
    from lib import runtime

    runtime.append_trace(
        ctx.cwd,
        rel,
        {
            "event": "context-read",
            "path": target,
            "mission_id": mission_id,
            "timestamp": _dt.datetime.now().astimezone().isoformat(),
        },
    )
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="check-mission-branch", event="PreToolUse",
              check=check_mission_branch, tools=WRITE_NB),
    HookEntry(id="check-stage-worktree", event="PreToolUse",
              check=check_stage_worktree, tools=WRITE),
    HookEntry(id="check-pending-recheck", event="PreToolUse",
              check=check_pending_recheck, tools=BASH),
    HookEntry(id="mark-pending-recheck", event="PostToolUse",
              check=mark_pending_recheck, tools=WRITE),
    HookEntry(id="record-context-read", event="PostToolUse",
              check=record_context_read, tools=READ),
]
