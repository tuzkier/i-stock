"""Stage hook checks: solution / interaction / technical_analysis.

Migrated from .harness/common/runtime-overlay/hooks/design.{solution,interaction,
technical_analysis}/*.py. The 9 legacy design hooks are 3 checks x 3 lanes that
are near-verbatim clones differing only in the contract filename, the design
doc filename, and the lane token.

This module keeps a single implementation per check; the active lane is
resolved from ``ctx.stage``. The dispatcher invokes this module for
``solution``, ``interaction``, and ``technical_analysis``, so each check just
applies lane-specific path / command filters. ENTRIES therefore holds 3
HookEntry rows (one per check), not 9.
"""

from __future__ import annotations

import json
from pathlib import Path

from context import HookContext
from entry import BASH, HookEntry, WRITE
from result import HookResult
from lib import commands, contracts

# lane -> contract filename
_LANE_CONTRACT = {
    "solution": "solution.contract.yaml",
    "interaction": "interaction.contract.yaml",
    "technical_analysis": "tech-design.contract.yaml",
}
# lane -> design doc filename whose edit triggers pending_reviewer_recheck
_LANE_DOC = {
    "solution": "solution.md",
    "interaction": "interaction.md",
    "technical_analysis": "tech-design.md",
}
# lane -> reviewer role surfaced in the recheck-block message (legacy text)
_LANE_REVIEWER = {
    "solution": "solution-effectiveness-reviewer",
    "interaction": "interaction-reviewer",
    "technical_analysis": "technical-design-effectiveness-reviewer",
}

_RECHECK_FIELD = "effectiveness_review.pending_reviewer_recheck"


def _lane(ctx: HookContext) -> str | None:
    stage = (ctx.stage or "").strip()
    return stage if stage in _LANE_CONTRACT else None


def _mission_id(ctx: HookContext) -> str | None:
    return commands.mission_id(ctx.command) or ctx.mission_id


def _design_gate_passed(cwd: Path, mission_id: str, lane: str) -> bool:
    """True when the latest design gate report for this lane shows PASS.

    Legacy design hooks read gate reports from the per-stage location
    ``stages/<mission>/gate-reports/`` (not the shared state/gate-reports tree
    that runtime.latest_gate_report uses), so this preserves that path.
    Conservative: a missing / unreadable report counts as not-passed.
    """
    gate_dir = cwd / "harness-runtime" / "harness" / "stages" / mission_id / "gate-reports"
    traces_dir = cwd / "harness-runtime" / "harness" / "stages" / mission_id / "traces"
    if lane == "interaction":
        if not (traces_dir / "interaction_gate_pass.flag").exists():
            return False
        if not (traces_dir / "alignment_pass.flag").exists():
            return False
    if not gate_dir.is_dir():
        return False
    try:
        candidates = sorted(
            list(gate_dir.glob(f"{lane}*.json"))
            + list(gate_dir.glob(f"design.{lane}*.json"))
            + list(gate_dir.glob("design*.json")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return False
    for report in candidates:
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, ValueError):
            continue
        return isinstance(data, dict) and data.get("status") == "PASS"
    return False


# --- checks ----------------------------------------------------------------
def mark_pending_recheck(ctx: HookContext) -> HookResult:
    """PostToolUse: flip pending_reviewer_recheck=true on the lane contract
    after the lane's design doc is edited."""
    try:
        lane = _lane(ctx)
        if lane is None:
            return HookResult.ok()
        rel = ctx.rel_path()
        doc = _LANE_DOC[lane]
        if not (rel == doc or rel.endswith(f"/{doc}")):
            return HookResult.ok()
        marker = "harness-runtime/harness/stages/"
        if marker not in rel:
            return HookResult.ok()
        mission_id = rel.split(marker, 1)[1].split("/", 1)[0] or None
        if not mission_id:
            return HookResult.ok()
        contract_path = contracts.stage_contract_path(
            ctx.cwd, mission_id, _LANE_CONTRACT[lane]
        )
        contracts.set_pending_recheck(contract_path, True, field_path=_RECHECK_FIELD)
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def check_pending_recheck(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: block `harness gate/contract advance` when the lane
    contract still carries pending_reviewer_recheck=true."""
    try:
        lane = _lane(ctx)
        if lane is None:
            return HookResult.ok()
        if not commands.is_advance(ctx.command):
            return HookResult.ok()
        mission_id = _mission_id(ctx)
        if not mission_id:
            return HookResult.ok()
        contract_path = contracts.stage_contract_path(
            ctx.cwd, mission_id, _LANE_CONTRACT[lane]
        )
        if contracts.pending_recheck(contract_path, field_path=_RECHECK_FIELD):
            return HookResult.block(
                f"HarnessV2 design+{lane} hook BLOCKED: {_LANE_CONTRACT[lane]} "
                "has pending_reviewer_recheck=true. Re-run "
                f"{_LANE_REVIEWER[lane]} before advancing."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


def check_gate_pass(ctx: HookContext) -> HookResult:
    """PreToolUse Bash: block `harness mission stage complete <lane>` when
    the latest gate run for this lane is not PASS."""
    try:
        lane = _lane(ctx)
        if lane is None:
            return HookResult.ok()
        if not commands.is_stage_complete(ctx.command, lane):
            return HookResult.ok()
        mission_id = _mission_id(ctx)
        if not mission_id:
            return HookResult.ok()
        if not _design_gate_passed(ctx.cwd, mission_id, lane):
            return HookResult.block(
                f"HarnessV2 design+{lane} hook BLOCKED: gate report for "
                f"design/{lane} lane (mission={mission_id}) is missing or has "
                f"status != PASS. Run `harness gate run --stage {lane}` and "
                "ensure PASS before completing."
            )
    except Exception:  # noqa: BLE001 — fail-open
        return HookResult.ok()
    return HookResult.ok()


ENTRIES: list[HookEntry] = [
    HookEntry(id="design-mark-pending-recheck", event="PostToolUse",
              check=mark_pending_recheck, tools=WRITE),
    HookEntry(id="design-check-pending-recheck", event="PreToolUse",
              check=check_pending_recheck, tools=BASH),
    HookEntry(id="design-check-gate-pass", event="PreToolUse",
              check=check_gate_pass, tools=BASH),
]
