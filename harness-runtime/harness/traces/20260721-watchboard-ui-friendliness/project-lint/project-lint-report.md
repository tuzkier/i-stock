# Project Lint Report

Status: FAIL
Gate Effect: block
Generated At: 2026-07-22T14:34:44.290404+00:00

## Findings

### P001 FAIL

Changed files include protected Harness framework assets.

Remediation: Do not edit installed .harness framework assets inside a target project. Use the Harness install/update workflow or move the change into project runtime config.

Paths:
- `.harness/common/skills/stage-gate/scripts/check_contracts.py`

### P003 WARN

Agent instruction file lacks project guidance keywords for: test, delivery.

Remediation: Update AGENTS.md so future agents can find setup commands, test commands, code style, and delivery checks without rediscovery.

Paths:
- `AGENTS.md`
