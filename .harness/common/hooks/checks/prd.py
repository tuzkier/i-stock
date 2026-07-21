"""Stage hook checks: prd.

Migrated from .harness/common/runtime-overlay/hooks/prd/*.py — the five legacy
standalone scripts now run in-process under the unified dispatcher.
"""

from __future__ import annotations

import json
import re

from context import HookContext
from entry import BASH, WRITE, HookEntry
from result import HookResult
from lib import commands, contracts, runtime

# --- path signals ----------------------------------------------------------
_CONTRACT_PATH_RE = re.compile(r"contracts/prd\.contract\.yaml$")
_PRD_WRITE_RE = re.compile(
    r"harness-runtime/harness/stages/[^/]+/(product/(product-definition|product-evidence|product-domain-model)\.md|specs/.+/spec\.md)$"
)
_PRODUCT_DEFINITION_RE = re.compile(r"harness-runtime/harness/stages/[^/]+/product/product-definition\.md$")

_CONTRACT_FILENAME = "prd.contract.yaml"
_RECHECK_FIELD = "effectiveness_review.pending_reviewer_recheck"


# --- prd-check-contract-via-cli ---------------------------------------------
def check_contract_via_cli(ctx: HookContext) -> HookResult:
    """Block direct Write/Edit of prd.contract.yaml — must use harness CLI."""
    file_path = ctx.file_path or ""
    if _CONTRACT_PATH_RE.search(file_path):
        return HookResult.block(
            "HarnessV2 prd hook BLOCKED: direct Write/Edit of prd.contract.yaml is "
            "not allowed. Use `harness contract fill` or `harness contract patch` instead."
        )
    return HookResult.ok()


# --- prd-check-stage-worktree -----------------------------------------------
def check_stage_worktree(ctx: HookContext) -> HookResult:
    """Block product definition / spec writes outside harness-runtime/harness/stages/<id>/."""
    file_path = ctx.file_path or ""
    if _PRD_WRITE_RE.search(file_path):
        return HookResult.ok()
    if "product-definition.md" in file_path or "product-evidence.md" in file_path or "product-domain-model.md" in file_path or "spec.md" in file_path:
        return HookResult.block(
            f"HarnessV2 prd hook BLOCKED: prd artifact write outside stage directory: "
            f"{file_path}. product artifacts and spec.md must be under "
            "harness-runtime/harness/stages/<id>/."
        )
    return HookResult.ok()


# --- prd-mark-pending-recheck -----------------------------------------------
def mark_pending_recheck(ctx: HookContext) -> HookResult:
    """After a product-definition.md edit, set effectiveness_review.pending_reviewer_recheck=true
    on the sibling prd.contract.yaml."""
    file_path = ctx.file_path or ""
    if not _PRODUCT_DEFINITION_RE.search(file_path):
        return HookResult.ok()

    # Contract sits in stages/<id>/contracts/prd.contract.yaml, alongside product/.
    from pathlib import Path

    contract_path = Path(file_path).resolve().parents[1] / "contracts" / _CONTRACT_FILENAME
    if not contract_path.exists():
        return HookResult.ok()

    contracts.set_pending_recheck(contract_path, True, field_path=_RECHECK_FIELD)
    return HookResult.ok()


# --- prd-check-pending-recheck ----------------------------------------------
def check_pending_recheck(ctx: HookContext) -> HookResult:
    """Block `harness gate/contract advance` while prd.contract.yaml carries an
    unresolved effectiveness_review.pending_reviewer_recheck flag."""
    command = ctx.command
    if not commands.is_advance(command):
        return HookResult.ok()

    mission_id = commands.mission_id(command)
    if mission_id is None:
        return HookResult.ok()

    contract_path = contracts.stage_contract_path(ctx.cwd, mission_id, _CONTRACT_FILENAME)
    if contracts.pending_recheck(contract_path, field_path=_RECHECK_FIELD):
        return HookResult.block(
            f"HarnessV2 prd hook BLOCKED: {contract_path.name} has "
            "pending_reviewer_recheck=true. Re-run product-definition-reviewer "
            "before advancing."
        )
    return HookResult.ok()


# --- prd-check-gate-pass ----------------------------------------------------
def _latest_prd_gate_pass(ctx: HookContext, mission_id: str) -> bool:
    """True when the most recent prd gate report passed.

    The prd gate report carries `gate_effect` / `decision` rather than a
    `status` field, and stage matching is by substring, so the generic
    runtime.latest_gate_report glob helper cannot be used directly here.
    """
    gate_dir = runtime.state_dir(ctx.cwd) / "gate-reports" / mission_id
    if not gate_dir.exists():
        return False

    latest_report: dict | None = None
    latest_mtime = 0.0
    for report_path in gate_dir.glob("*.json"):
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        stage = str(data.get("stage") or data.get("from_stage") or "").lower()
        if "prd" not in stage:
            continue
        try:
            mtime = report_path.stat().st_mtime
        except OSError:
            continue
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_report = data

    if latest_report is None:
        return False
    return (
        latest_report.get("gate_effect") == "pass"
        or latest_report.get("decision") == "can_continue"
    )


def check_gate_pass(ctx: HookContext) -> HookResult:
    """Block `harness mission stage complete prd` unless the latest prd gate
    run passed."""
    command = ctx.command
    if not commands.is_stage_complete(command, expect_stage="prd"):
        return HookResult.ok()

    mission_id = commands.mission_id(command)
    if mission_id is None:
        return HookResult.ok()

    if not _latest_prd_gate_pass(ctx, mission_id):
        return HookResult.block(
            "HarnessV2 prd hook BLOCKED: cannot complete prd stage without a PASS "
            "gate run. Run `harness gate run --stage prd --mission <id> ...` first."
        )
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="prd-check-contract-via-cli", event="PreToolUse",
              check=check_contract_via_cli, tools=WRITE),
    HookEntry(id="prd-check-stage-worktree", event="PreToolUse",
              check=check_stage_worktree, tools=WRITE),
    HookEntry(id="prd-mark-pending-recheck", event="PostToolUse",
              check=mark_pending_recheck, tools=WRITE),
    HookEntry(id="prd-check-pending-recheck", event="PreToolUse",
              check=check_pending_recheck, tools=BASH),
    HookEntry(id="prd-check-gate-pass", event="PreToolUse",
              check=check_gate_pass, tools=BASH),
]
"""Per-stage hook check modules.

Each module exposes `ENTRIES: list[HookEntry]` — the checks for one mission
stage. `registry.py` assembles them into the dispatch registry.
"""
