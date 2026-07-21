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


# --- check-gitnexus-brownfield ----------------------------------------------
def _is_brownfield(ctx: HookContext) -> bool:
    """Brownfield ≡ a populated .gitnexus/ index exists at the project root."""
    gitnexus = ctx.cwd / ".gitnexus"
    if not gitnexus.exists() or not gitnexus.is_dir():
        return False
    try:
        return any(gitnexus.iterdir())
    except OSError:
        return False


def _gitnexus_evidence(contract_path) -> tuple[bool, str]:
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
            if isinstance(item, dict) and str(item.get("source", "")).startswith("gitnexus"):
                return True, "gitnexus_* source recorded in existing_solutions[]"

    degradations = contract.get("degradations") or []
    if isinstance(degradations, list):
        for item in degradations:
            if isinstance(item, dict) and item.get("kind") in {"gitnexus_unavailable", "gitnexus_stale"}:
                return True, f"{item.get('kind')} recorded in degradations[]"

    return False, (
        "brownfield mission but contract.yaml lacks gitnexus_* in existing_solutions[] "
        "AND no gitnexus_unavailable/gitnexus_stale in degradations[]; either run gitnexus "
        "queries first or record the degradation explicitly."
    )


def check_gitnexus_brownfield(ctx: HookContext) -> HookResult:
    """Block discovery-brief.md writes on brownfield missions without gitnexus
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
    ok, reason = _gitnexus_evidence(contract_path)
    if ok:
        return HookResult.ok()

    return HookResult.block(
        f"HarnessV2 discovery hook BLOCKED: brownfield mission {mission!r} cannot write "
        f"{rel} without gitnexus evidence. {reason}"
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


# --- record-gitnexus-query --------------------------------------------------
def record_gitnexus_query(ctx: HookContext) -> HookResult:
    """Append a structured trace event whenever a gitnexus MCP tool is called."""
    if "gitnexus" not in (ctx.tool_name or "").lower():
        return HookResult.ok()

    mission, _stage = runtime.active_mission(ctx.cwd)
    if not mission:
        return HookResult.ok()

    runtime.append_trace(
        ctx.cwd,
        f"traces/{mission}/discovery.jsonl",
        {
            "event": "gitnexus_query",
            "tool_name": ctx.tool_name,
            "recorded_at": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
            "tool_input": ctx.tool_input or {},
        },
    )
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="check-stage-worktree-discovery", event="PreToolUse",
              check=check_stage_worktree, tools=WRITE),
    HookEntry(id="check-gitnexus-brownfield", event="PreToolUse",
              check=check_gitnexus_brownfield, tools=WRITE),
    HookEntry(id="check-dependency-validity", event="PreToolUse",
              check=check_dependency_validity, tools=BASH),
    HookEntry(id="check-gate-pass", event="PreToolUse",
              check=check_gate_pass, tools=BASH),
    HookEntry(id="check-confirmation", event="PreToolUse",
              check=check_confirmation, tools=BASH),
    HookEntry(id="record-gitnexus-query", event="PostToolUse",
              check=record_gitnexus_query, tools=frozenset()),
]
