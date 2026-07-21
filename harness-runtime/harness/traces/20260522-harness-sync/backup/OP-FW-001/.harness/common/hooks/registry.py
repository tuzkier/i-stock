"""Dispatch registry: mission stage -> [HookEntry].

The dispatcher resolves the active mission stage and runs BASELINE entries
plus REGISTRY[stage] entries. Stage keys match Mission Slice
`control_plane.stage` values, with `mission-status.current_stage` retained
only as a legacy/test fallback.
"""

from __future__ import annotations

from checks import (
    baseline,
    breakdown,
    code_review,
    delivery,
    design,
    discovery,
    execute,
    finishing_branch,
    intake,
    prd,
    retrospective,
    verify,
)
from entry import HookEntry

BASELINE: list[HookEntry] = baseline.ENTRIES

REGISTRY: dict[str, list[HookEntry]] = {
    "intake": intake.ENTRIES,
    "discovery": discovery.ENTRIES,
    "prd": prd.ENTRIES,
    "solution": design.ENTRIES,
    "interaction": design.ENTRIES,
    "technical_analysis": design.ENTRIES,
    "breakdown": breakdown.ENTRIES,
    "execute": execute.ENTRIES,
    "code-review": code_review.ENTRIES,
    "verify": verify.ENTRIES,
    "delivery": delivery.ENTRIES,
    "finishing-branch": finishing_branch.ENTRIES,
    "retrospective": retrospective.ENTRIES,
}
