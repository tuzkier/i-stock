"""Stage hook checks: finishing_branch."""

from __future__ import annotations

import re
from pathlib import Path

from context import HookContext
from entry import BASH, HookEntry
from result import HookResult
from lib import commands, contracts, runtime

# deny_direct_runtime_mutation manifest matcher is ["Edit", "Write"].
WRITE_NO_MULTI = frozenset({"Edit", "Write"})

_MERGE_RE = re.compile(r"\bgit\s+merge\b", re.IGNORECASE)
_PUSH_U_RE = re.compile(r"\bgit\s+push\b.*?-u\s+origin\b", re.IGNORECASE)
_GH_PR_CREATE_RE = re.compile(r"\bgh\s+pr\s+create\b", re.IGNORECASE)
_FB_EXECUTE_RE = re.compile(r"\bharness\s+finishing-branch\s+execute\b")
_STATUS_RE = re.compile(r"--status\s+([^\s'\"]+)")
_LEGACY_ALIASES = {"manual", "cancelled"}
_MISSION_STATUS_PATTERNS = (
    "harness-runtime/harness/mission-status.yaml",
    "harness-runtime/harness/mission_status.yaml",
)


def _fb_contract(cwd: Path) -> dict | None:
    """First finishing-branch.contract.yaml under stages/*/contracts/.

    NOTE: this contract is read as the raw YAML doc (not unwrapped), matching
    the legacy hooks which indexed top-level keys (branch_status / pr_body /
    effectiveness_review / git_ops / close_choice)."""
    base = cwd / "harness-runtime" / "harness" / "stages"
    if not base.is_dir():
        return None
    for path in sorted(base.glob("*/contracts/finishing-branch.contract.yaml")):
        if path.exists():
            return contracts.load_yaml(path)
    return None


def _fb_contract_path(cwd: Path) -> Path | None:
    base = cwd / "harness-runtime" / "harness" / "stages"
    if not base.is_dir():
        return None
    for path in sorted(base.glob("*/contracts/finishing-branch.contract.yaml")):
        if path.exists():
            return path
    return None


def _has_boundary_approval(cwd: Path, *keywords: str) -> bool:
    """True when an approved boundary approval comment mentions any keyword.

    Reads the correct runtime path via runtime.load_approvals (fixes the
    legacy bug where hooks read harness-runtime/state/approvals.json)."""
    for rec in runtime.load_approvals(cwd):
        if rec.get("type") == "boundary" and rec.get("status") == "approved":
            comment = str(rec.get("comment") or "").lower()
            if any(kw in comment for kw in keywords):
                return True
    return False


# --- PreToolUse: bash guards -----------------------------------------------
def check_legacy_alias(ctx: HookContext) -> HookResult:
    """Advisory / hard-block for legacy mission-close status aliases."""
    try:
        command = ctx.command or ""
        if not commands.is_mission_close(command):
            return HookResult.ok()
        m = _STATUS_RE.search(command)
        if m is None or m.group(1) not in _LEGACY_ALIASES:
            return HookResult.ok()
        alias = m.group(1)

        # Legacy window is OPEN by default; closes when harness.yaml says so.
        window_open = True
        config = ctx.cwd / "harness-runtime" / "config" / "harness.yaml"
        data = contracts.load_yaml(config)
        if isinstance(data, dict):
            fb = data.get("finishing_branch")
            if isinstance(fb, dict):
                window_open = fb.get("legacy_alias_window") != "closed"

        if window_open:
            return HookResult.advise(
                "HarnessV2 finishing-branch hook ADVISORY (legacy_alias_used): "
                f"--status={alias!r} is a legacy alias. "
                "Translation will be recorded in translation-warning.yaml. "
                "Plan to migrate to the typed enum (merged/pr/kept/discarded) "
                "within 2 mission cycles."
            )
        return HookResult.block(
            "HarnessV2 finishing-branch hook BLOCKED (legacy_alias_window=closed): "
            f"--status={alias!r} is no longer accepted. "
            "Use the typed enum: merged | pr | kept | discarded."
        )
    except Exception:
        return HookResult.ok()


def deny_force_push(ctx: HookContext) -> HookResult:
    """Deny `git push --force` without a force-push boundary approval."""
    command = ctx.command or ""
    if commands.git_danger(command, kinds=["force-push"]) is None:
        return HookResult.ok()
    if _has_boundary_approval(ctx.cwd, "force-push", "force_push"):
        return HookResult.advise(
            "HarnessV2 finishing-branch hook ADVISORY (force_push_approved): "
            "force push authorized via boundary approval."
        )
    return HookResult.block(
        "HarnessV2 finishing-branch hook BLOCKED (deny_force_push): "
        "git push --force is not permitted without a boundary approval. "
        "Use `harness approval append --type boundary --status approved "
        "--comment force-push` to authorize, then retry."
    )


def deny_hard_reset(ctx: HookContext) -> HookResult:
    """Deny `git reset --hard` without a hard-reset boundary approval."""
    command = ctx.command or ""
    if commands.git_danger(command, kinds=["hard-reset"]) is None:
        return HookResult.ok()
    if _has_boundary_approval(ctx.cwd, "hard-reset", "hard_reset"):
        return HookResult.advise(
            "HarnessV2 finishing-branch hook ADVISORY (hard_reset_approved): "
            "git reset --hard authorized via boundary approval."
        )
    return HookResult.block(
        "HarnessV2 finishing-branch hook BLOCKED (deny_hard_reset): "
        "git reset --hard is not permitted at any stage without a Decision Gate. "
        "Use `harness approval append --type boundary --status approved "
        "--comment hard-reset` to authorize, then retry."
    )


def check_cleanup_authorization(ctx: HookContext) -> HookResult:
    """Authorize `git branch -D` / `git worktree remove` only with a discard
    confirmation boundary approval."""
    command = ctx.command or ""
    kind = commands.git_danger(command, kinds=["branch-delete", "worktree-remove"])
    if kind is None:
        return HookResult.ok()
    if _has_boundary_approval(ctx.cwd, "discard"):
        return HookResult.ok()
    if kind == "branch-delete":
        return HookResult.block(
            "HarnessV2 finishing-branch hook BLOCKED (check_cleanup_authorization): "
            "git branch -D requires a discard confirmation approval. "
            "Use `harness approval append --type boundary --status approved "
            "--comment discard` to authorize."
        )
    return HookResult.block(
        "HarnessV2 finishing-branch hook BLOCKED (check_cleanup_authorization): "
        "git worktree remove must be invoked via `harness finishing-branch cleanup` "
        "or with a discard confirmation approval."
    )


def check_branch_cleanliness(ctx: HookContext) -> HookResult:
    """Advisory / block before git merge or push -u based on branch_status."""
    try:
        command = ctx.command or ""
        is_merge = bool(_MERGE_RE.search(command))
        is_push = bool(_PUSH_U_RE.search(command))
        if not (is_merge or is_push):
            return HookResult.ok()

        doc = _fb_contract(ctx.cwd)
        branch_status = doc.get("branch_status") if isinstance(doc, dict) else None
        if branch_status is None:
            return HookResult.advise(
                "HarnessV2 finishing-branch hook ADVISORY (check_branch_cleanliness): "
                "no branch_status evidence found; run `harness finishing-branch status` "
                "before merge/push."
            )

        active = branch_status.get("active_stage_worktrees") or []
        blocked = branch_status.get("blocked_stage_worktrees") or []
        dirty = branch_status.get("dirty") or False
        if active or blocked or dirty:
            issues = []
            if active:
                issues.append(f"active stage worktrees: {active}")
            if blocked:
                issues.append(f"blocked/dirty stage worktrees: {blocked}")
            if dirty:
                issues.append("root worktree has uncommitted changes")
            return HookResult.block(
                "HarnessV2 finishing-branch hook BLOCKED (check_branch_cleanliness): "
                f"merge/push blocked: {'; '.join(issues)}. "
                "Resolve all stage worktree and dirty state issues before proceeding."
            )
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


def check_pr_body(ctx: HookContext) -> HookResult:
    """Advisory / block before `gh pr create` if pr_body.source_artifacts empty."""
    try:
        command = ctx.command or ""
        if not _GH_PR_CREATE_RE.search(command):
            return HookResult.ok()

        doc = _fb_contract(ctx.cwd)
        pr_body = doc.get("pr_body") if isinstance(doc, dict) else None
        if pr_body is None:
            return HookResult.advise(
                "HarnessV2 finishing-branch hook ADVISORY (check_pr_body): "
                "no pr_body evidence found in finishing-branch contract; "
                "run `harness finishing-branch pr-body` before `gh pr create`."
            )
        if not (pr_body.get("source_artifacts") or []):
            return HookResult.block(
                "HarnessV2 finishing-branch hook BLOCKED (check_pr_body): "
                "pr_body.source_artifacts is empty; PR body must reference "
                "delivery-package.md and verification evidence."
            )
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


def check_close_gate(ctx: HookContext) -> HookResult:
    """Block `harness mission close` unless effectiveness_review.last_gate_run_status
    is PASS in the finishing-branch contract."""
    try:
        command = ctx.command or ""
        if not commands.is_mission_close(command):
            return HookResult.ok()

        path = _fb_contract_path(ctx.cwd)
        if path is None:
            return HookResult.ok()  # no contract: advisory only
        doc = contracts.load_yaml(path)
        if not isinstance(doc, dict):
            return HookResult.ok()
        eff = doc.get("effectiveness_review")
        if not isinstance(eff, dict):
            return HookResult.block(
                "HarnessV2 finishing-branch hook BLOCKED (check_close_gate): "
                "effectiveness_review missing in contract; run "
                "`harness gate run --stage finishing-branch` first."
            )
        last_status = eff.get("last_gate_run_status")
        if last_status != "PASS":
            return HookResult.block(
                "HarnessV2 finishing-branch hook BLOCKED (check_close_gate): "
                f"last gate run status={last_status!r}; must be PASS before mission close."
            )
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


def deny_direct_runtime_mutation(ctx: HookContext) -> HookResult:
    """Block direct Edit/Write of mission-status.yaml under harness-runtime."""
    file_path = (ctx.file_path or "").replace("\\", "/")
    for pattern in _MISSION_STATUS_PATTERNS:
        if pattern in file_path:
            return HookResult.block(
                "HarnessV2 finishing-branch hook BLOCKED (deny_direct_runtime_mutation): "
                f"direct {ctx.tool_name} of {pattern!r} is not permitted. "
                "Use `harness mission close --mission <id> --strategy <enum>` "
                "to update mission close state."
            )
    return HookResult.ok()


# --- PostToolUse: record sensors -------------------------------------------
def record_git_ops(ctx: HookContext) -> HookResult:
    """Record git_ops evidence to finishing-branch contract after execute."""
    try:
        command = ctx.command or ""
        if not _FB_EXECUTE_RE.search(command):
            return HookResult.ok()

        import json

        output = ""
        for source in (ctx.tool_response, ctx.raw):
            for key in ("output", "content", "stdout"):
                value = source.get(key) if isinstance(source, dict) else None
                if isinstance(value, str) and value:
                    output = value
                    break
            if output:
                break

        git_ops: list = []
        strategy = ""
        try:
            out_data = json.loads(output)
            if isinstance(out_data, dict):
                git_ops = out_data.get("git_ops") or []
                strategy = str(out_data.get("strategy") or "")
        except (json.JSONDecodeError, ValueError):
            pass
        if not git_ops and not strategy:
            return HookResult.ok()

        path = _fb_contract_path(ctx.cwd)
        if path is None:
            return HookResult.ok()
        doc = contracts.load_yaml(path)
        if not isinstance(doc, dict):
            return HookResult.ok()
        existing_ops = doc.get("git_ops")
        if not isinstance(existing_ops, list):
            existing_ops = []
        existing_ops.extend(git_ops)
        doc["git_ops"] = existing_ops
        if strategy:
            close_choice = doc.get("close_choice")
            if not isinstance(close_choice, dict):
                close_choice = {}
            close_choice["strategy"] = strategy
            doc["close_choice"] = close_choice
        contracts.save_yaml(path, doc)
    except Exception:
        return HookResult.ok()
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="finishing-branch-check-legacy-alias", event="PreToolUse", check=check_legacy_alias, tools=BASH),
    HookEntry(id="finishing-branch-deny-force-push", event="PreToolUse", check=deny_force_push, tools=BASH),
    HookEntry(id="finishing-branch-deny-hard-reset", event="PreToolUse", check=deny_hard_reset, tools=BASH),
    HookEntry(id="finishing-branch-check-cleanup-authorization", event="PreToolUse", check=check_cleanup_authorization, tools=BASH),
    HookEntry(id="finishing-branch-check-branch-cleanliness", event="PreToolUse", check=check_branch_cleanliness, tools=BASH),
    HookEntry(id="finishing-branch-check-pr-body", event="PreToolUse", check=check_pr_body, tools=BASH),
    HookEntry(id="finishing-branch-check-close-gate", event="PreToolUse", check=check_close_gate, tools=BASH),
    HookEntry(id="finishing-branch-deny-direct-runtime-mutation", event="PreToolUse", check=deny_direct_runtime_mutation, tools=WRITE_NO_MULTI),
    HookEntry(id="finishing-branch-record-git-ops", event="PostToolUse", check=record_git_ops, tools=BASH),
]
