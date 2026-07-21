"""Stage hook checks: discovery.

Migrated from .harness/common/runtime-overlay/hooks/discovery/*.py — the six
legacy standalone scripts now run in-process under the unified dispatcher.
"""

from __future__ import annotations

import datetime as _dt
import os
import re

from context import HookContext
from entry import BASH, WRITE, HookEntry
from result import HookResult
from lib import commands, contracts, runtime

# --- path signals ----------------------------------------------------------
_DISCOVERY_ARTIFACT_PATH_RE = re.compile(
    r"harness-runtime/harness/stages/(?P<mission>[^/]+)/"
    r"(?:discovery-brief\.md|contracts/discovery-brief\.contract\.yaml)$"
)
_DISCOVERY_BRIEF_PATH_RE = re.compile(
    r"harness-runtime/harness/stages/(?P<mission>[^/]+)/discovery-brief\.md$"
)
_STAGE_WORKTREE_RE = re.compile(r"/\.?worktrees/stage-[^/]+-discovery/")
_DOWNGRADE_ENV = "HARNESS_GIT_STRATEGY_DOWNGRADED"

_CONTRACT_FILENAME = "discovery-brief.contract.yaml"
# 修复必重审：discovery-brief.md 改动后，置脏 contract 的嵌套 recheck 标志，
# 与 prd / solution 的 effectiveness_review 口径一致（嵌套，非 intake 顶层口径）。
_RECHECK_FIELD = "effectiveness_review.pending_reviewer_recheck"


# --- check-stage-worktree-discovery -----------------------------------------
def check_stage_worktree(ctx: HookContext) -> HookResult:
    """Block discovery-brief writes outside the discovery stage worktree."""
    target = ctx.file_path
    if target is None:
        return HookResult.ok()
    rel = ctx.rel_path(target)
    if not _DISCOVERY_ARTIFACT_PATH_RE.search(rel):
        return HookResult.ok()

    if os.environ.get(_DOWNGRADE_ENV) == "1":
        return HookResult.ok()

    cwd_norm = str(ctx.cwd.resolve()) + "/"
    if _STAGE_WORKTREE_RE.search(cwd_norm):
        return HookResult.ok()

    return HookResult.block(
        f"HarnessV2 discovery hook BLOCKED: cannot write {rel} from cwd {str(ctx.cwd)!r}. "
        "Run `git-workflow start-stage(discovery)` to create the stage worktree first, "
        f"or set {_DOWNGRADE_ENV}=1 for downgraded git strategy."
    )


# --- check-graphify-brownfield ----------------------------------------------
def _is_brownfield(ctx: HookContext) -> bool:
    """Brownfield ≡ a populated graphify-out/ index exists at the project root."""
    graphify = ctx.cwd / "graphify-out"
    if not graphify.exists() or not graphify.is_dir():
        return False
    try:
        return any(graphify.iterdir())
    except OSError:
        return False


def _graphify_evidence(contract_path) -> tuple[bool, str]:
    if not contract_path.exists():
        return False, (
            "contract.yaml not yet materialized; run `harness contract fill "
            "--template discovery-brief` first."
        )
    contract = contracts.load_contract(contract_path)
    if not contract:
        return False, "contract.yaml is missing `control_contract:` root."

    existing = contract.get("existing_solutions") or []
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict) and str(item.get("source", "")).startswith("graphify"):
                return True, "graphify_* source recorded in existing_solutions[]"

    degradations = contract.get("degradations") or []
    if isinstance(degradations, list):
        for item in degradations:
            if isinstance(item, dict) and item.get("kind") in {"graphify_unavailable", "graphify_stale"}:
                return True, f"{item.get('kind')} recorded in degradations[]"

    return False, (
        "brownfield mission but contract.yaml lacks graphify_* in existing_solutions[] "
        "AND no graphify_unavailable/graphify_stale in degradations[]; either run graphify "
        "queries first or record the degradation explicitly."
    )


def check_graphify_brownfield(ctx: HookContext) -> HookResult:
    """Block discovery-brief.md writes on brownfield missions without graphify
    evidence in the brief's contract."""
    target = ctx.file_path
    if target is None:
        return HookResult.ok()
    rel = ctx.rel_path(target)
    match = _DISCOVERY_BRIEF_PATH_RE.search(rel)
    if not match:
        return HookResult.ok()

    if not _is_brownfield(ctx):
        return HookResult.ok()

    mission = match.group("mission")
    contract_path = contracts.stage_contract_path(ctx.cwd, mission, _CONTRACT_FILENAME)
    ok, reason = _graphify_evidence(contract_path)
    if ok:
        return HookResult.ok()

    return HookResult.block(
        f"HarnessV2 discovery hook BLOCKED: brownfield mission {mission!r} cannot write "
        f"{rel} without graphify evidence. {reason}"
    )


# --- check-dependency-validity ----------------------------------------------
def check_dependency_validity(ctx: HookContext) -> HookResult:
    """Block `harness contract/gate advance` when dependency-impact was required
    but dependency-validity-reviewer has not PASSed."""
    command = ctx.command
    if not commands.is_advance(command):
        return HookResult.ok()

    mission = commands.mission_id(command)
    if not mission:
        return HookResult.ok()

    contract_path = contracts.stage_contract_path(ctx.cwd, mission, _CONTRACT_FILENAME)
    if not contract_path.exists():
        return HookResult.ok()

    raw = contracts.load_yaml(contract_path)
    contract = raw.get("control_contract") if isinstance(raw, dict) else None
    if not isinstance(contract, dict):
        return HookResult.ok()

    dependency_trigger = contract.get("dependency_trigger") or {}
    required = bool(dependency_trigger.get("required")) if isinstance(dependency_trigger, dict) else False
    if not required:
        return HookResult.ok()

    role_verdicts = contract.get("role_verdicts") or []
    for entry in role_verdicts:
        if not isinstance(entry, dict):
            continue
        dispatch = entry.get("dispatch")
        role = dispatch.get("subagent_id") if isinstance(dispatch, dict) else entry.get("role")
        if role == "dependency-validity-reviewer" and str(
            entry.get("verdict") or entry.get("status") or ""
        ).upper() == "PASS":
            return HookResult.ok()

    degradations = contract.get("degradations") or []
    for entry in degradations:
        if isinstance(entry, dict) and "dependency" in str(entry.get("kind", "")).lower():
            return HookResult.ok()

    return HookResult.block(
        f"HarnessV2 discovery hook BLOCKED: mission {mission!r} contract has "
        f"dependency_trigger.required=true but no dependency-validity-reviewer PASS "
        f"in role_verdicts[]. Run dependency-impact skill and record reviewer verdict "
        f"before advancing the gate."
    )


# --- check-gate-pass --------------------------------------------------------
def check_gate_pass(ctx: HookContext) -> HookResult:
    """Block `harness mission stage complete discovery` unless the latest
    discovery__*.json gate report has status=PASS."""
    command = ctx.command
    if not commands.is_stage_complete(command):
        return HookResult.ok()

    explicit_stage = commands.stage(command)
    if explicit_stage and explicit_stage != "discovery":
        return HookResult.ok()

    mission = commands.mission_id(command)
    if not mission:
        return HookResult.ok()

    reports_dir = runtime.state_dir(ctx.cwd) / "gate-reports" / mission
    if not reports_dir.exists():
        return HookResult.block(
            f"HarnessV2 discovery hook BLOCKED: no gate-reports dir for mission {mission!r}; "
            f"run `harness gate run --stage discovery --mission {mission}` first."
        )

    report = runtime.latest_gate_report(ctx.cwd, mission, "discovery__*.json")
    if report is None:
        return HookResult.block(
            f"HarnessV2 discovery hook BLOCKED: no discovery__*.json gate report for "
            f"mission {mission!r}; run `harness gate run --stage discovery "
            f"--mission {mission}` first."
        )

    status = str(report.get("status") or "").upper()
    if status == "PASS":
        return HookResult.ok()

    return HookResult.block(
        f"HarnessV2 discovery hook BLOCKED: latest discovery gate report has "
        f"status={status!r} (expected PASS); re-run `harness gate run "
        f"--stage discovery --mission {mission}` after fixing FAIL findings."
    )


# --- check-confirmation -----------------------------------------------------
def check_confirmation(ctx: HookContext) -> HookResult:
    """Block `harness mission stage start <next>` unless approvals.json carries
    a discovery_skip record or an approved discovery_confirmation checkpoint."""
    command = ctx.command
    if not commands.is_stage_start(command):
        return HookResult.ok()

    if commands.stage(command) == "discovery":
        return HookResult.ok()

    mission = commands.mission_id(command)
    if not mission:
        return HookResult.ok()

    approvals_path = runtime.state_dir(ctx.cwd) / "approvals.json"
    if not approvals_path.exists():
        return HookResult.block(
            f"HarnessV2 discovery hook BLOCKED: approvals.json not found; mission {mission!r} "
            f"has no discovery_confirmation record. Run discovery Step 10 first."
        )

    for record in runtime.load_approvals(ctx.cwd):
        if record.get("mission_id") != mission:
            continue
        rtype = record.get("type") or ""
        checkpoint = record.get("checkpoint") or ""
        status = (record.get("status") or "").lower()
        if rtype == "discovery_skip":
            return HookResult.ok()
        if rtype == "checkpoint" and checkpoint == "discovery_confirmation" and status == "approved":
            return HookResult.ok()

    return HookResult.block(
        f"HarnessV2 discovery hook BLOCKED: mission {mission!r} cannot advance past discovery — "
        f"no approvals.json record of type=discovery_skip or "
        f"(type=checkpoint, checkpoint=discovery_confirmation, status=approved). "
        f"Run discovery Step 10 user confirmation first."
    )


# --- mark-pending-recheck ---------------------------------------------------
def mark_pending_recheck(ctx: HookContext) -> HookResult:
    """PostToolUse: 改 discovery-brief.md 后，置脏 discovery-brief.contract.yaml
    的 effectiveness_review.pending_reviewer_recheck=true。

    让 discovery-effectiveness-reviewer 的"修复后强制重审"从 prose 升级为物理门：
    改了 brief 就必须重跑 reviewer 才能 advance。字段不存在时由
    contracts.set_pending_recheck 用嵌套 setdefault 注入（schema 继承
    common.yaml 的 additionalProperties:true，注入不破坏 contract check）。"""
    try:
        target = ctx.file_path
        if target is None:
            return HookResult.ok()
        rel = ctx.rel_path(target)
        match = _DISCOVERY_BRIEF_PATH_RE.search(rel)
        if not match:
            return HookResult.ok()
        mission = match.group("mission")
        contract_path = contracts.stage_contract_path(ctx.cwd, mission, _CONTRACT_FILENAME)
        if not contract_path.exists():
            return HookResult.ok()
        contracts.set_pending_recheck(contract_path, True, field_path=_RECHECK_FIELD)
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


# --- check-pending-recheck --------------------------------------------------
def check_pending_recheck(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: 当 discovery-brief.contract.yaml 仍带
    pending_reviewer_recheck=true 时，拦截 `harness gate/contract advance`。"""
    try:
        if not commands.is_advance(ctx.command):
            return HookResult.ok()
        mission = commands.mission_id(ctx.command) or ctx.mission_id
        if not mission:
            return HookResult.ok()
        contract_path = contracts.stage_contract_path(ctx.cwd, mission, _CONTRACT_FILENAME)
        if contracts.pending_recheck(contract_path, field_path=_RECHECK_FIELD):
            return HookResult.block(
                f"HarnessV2 discovery hook BLOCKED: {_CONTRACT_FILENAME} has "
                "pending_reviewer_recheck=true. Re-run discovery-effectiveness-reviewer "
                "before advancing."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


# --- record-graphify-query --------------------------------------------------
def record_graphify_query(ctx: HookContext) -> HookResult:
    """Append a structured trace event whenever a graphify MCP tool is called."""
    if "graphify" not in (ctx.tool_name or "").lower():
        return HookResult.ok()

    mission, _stage = runtime.active_mission(ctx.cwd)
    if not mission:
        return HookResult.ok()

    runtime.append_trace(
        ctx.cwd,
        f"traces/{mission}/discovery.jsonl",
        {
            "event": "graphify_query",
            "tool_name": ctx.tool_name,
            "recorded_at": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
            "tool_input": ctx.tool_input or {},
        },
    )
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="check-stage-worktree-discovery", event="PreToolUse",
              check=check_stage_worktree, tools=WRITE),
    HookEntry(id="check-graphify-brownfield", event="PreToolUse",
              check=check_graphify_brownfield, tools=WRITE),
    HookEntry(id="check-dependency-validity", event="PreToolUse",
              check=check_dependency_validity, tools=BASH),
    HookEntry(id="check-gate-pass", event="PreToolUse",
              check=check_gate_pass, tools=BASH),
    HookEntry(id="check-confirmation", event="PreToolUse",
              check=check_confirmation, tools=BASH),
    HookEntry(id="discovery-mark-pending-recheck", event="PostToolUse",
              check=mark_pending_recheck, tools=WRITE),
    HookEntry(id="discovery-check-pending-recheck", event="PreToolUse",
              check=check_pending_recheck, tools=BASH),
    HookEntry(id="record-graphify-query", event="PostToolUse",
              check=record_graphify_query, tools=frozenset()),
]
