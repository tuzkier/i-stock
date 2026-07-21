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
    prototype_as_frontend,
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
    # interaction 阶段同时承载 interactive_prototype（design.ENTRIES）与
    # frontend_engineering（prototype_as_frontend.ENTRIES）两条路线；后者的 hook
    # 只在路径/命令指向 prototype-as-frontend 产物时触发，对前者无副作用。
    "interaction": design.ENTRIES + prototype_as_frontend.ENTRIES,
    "technical_analysis": design.ENTRIES,
    "breakdown": breakdown.ENTRIES,
    "execute": execute.ENTRIES,
    "code-review": code_review.ENTRIES,
    "verify": verify.ENTRIES,
    "delivery": delivery.ENTRIES,
    "finishing-branch": finishing_branch.ENTRIES,
    "retrospective": retrospective.ENTRIES,
}
{
  "_comment": "HarnessV2 baseline permission overlay merged into target .claude/settings.json by install.py. Per intake-improvement-plan M1.3: deny runtime YAML edits / dangerous git ops, ask for branch creation, allow harness CLI. User-level deny/ask entries are preserved via field-level merge.",
  "permissions": {
    "deny": [
      "Edit(harness-runtime/harness/mission-status.yaml)",
      "Edit(harness-runtime/harness/work-graph/**)",
      "Edit(harness-runtime/harness/work-graph/mission-slices/**)",
      "Edit(harness-runtime/harness/work-graph/nodes/**)",
      "Write(harness-runtime/harness/mission-status.yaml)",
      "Write(harness-runtime/harness/work-graph/**)",
      "Bash(git push --force *)",
      "Bash(git push --force-with-lease *)",
      "Bash(git reset --hard *)",
      "Bash(rm -rf /*)"
    ],
    "ask": [
      "Bash(git checkout -b *)",
      "Bash(git push *)",
      "Bash(git rebase *)"
    ],
    "allow": [
      "Bash(harness *)",
      "Bash(python3 .claude/hooks/**)"
    ]
  }
}
