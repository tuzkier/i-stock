# Consistency Report

## Summary

| Level | Count | Required Action |
|-------|-------|-----------------|
| BLOCKER | {{blocker_count}} | Must fix before reviewer PASS |
| DECISION | {{decision_count}} | User / PM / product decision required |
| WARNING | {{warning_count}} | May accept with reason |
| PASS | {{pass_count}} | No action |

## Findings

| ID | Level | Area | Finding | Affected Screens / Flows | Required Action | Status |
|----|-------|------|---------|--------------------------|-----------------|--------|
| CONS-001 | BLOCKER / DECISION / WARNING / PASS | copy / copy_language / confirmation / empty / loading / error / permission / validation / navigation | {{finding}} | {{refs}} | {{action}} | open / resolved / accepted |

## Checks

- Button and action copy consistency
- Visible prototype copy uses Chinese by default; non-Chinese exceptions are limited to brand names, product names, code identifiers, common industry acronyms, or upstream-specified copy, and include rationale
- Confirmation, cancel, undo, and destructive action consistency
- Empty, loading, error, permission, disabled, and success state consistency
- Field naming and domain object naming consistency
- Validation and recovery consistency
- Keyboard focus and accessibility consistency
