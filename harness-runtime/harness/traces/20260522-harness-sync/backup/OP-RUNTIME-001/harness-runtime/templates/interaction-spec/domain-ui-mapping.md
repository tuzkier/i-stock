# Domain UI Mapping

## Core Objects

| Domain Ref | Kind | Business Meaning | UI Representation | Screen / Component | Trace |
|------------|------|------------------|-------------------|--------------------|-------|
| OBJ-01 | object | {{meaning}} | {{ui_representation}} | SCREEN-{{id}} | AC-{{id}} |

## Relationships

| Relationship | UI Structure | Navigation / Grouping Rule | Trace |
|--------------|--------------|----------------------------|-------|
| {{from}} → {{to}} | {{ui_structure}} | {{rule}} | {{trace_ref}} |

## States

| Entity | Domain State | UI State | Visible Feedback | Available Actions | Trace |
|--------|--------------|----------|------------------|-------------------|-------|
| {{entity}} | {{domain_state}} | STATE-{{id}} | {{feedback}} | {{actions}} | {{trace_ref}} |

## Commands And Permissions

| Actor | Domain Command / Action | Guard / Permission | UI Control | Disabled / Denied Feedback | Trace |
|-------|--------------------------|--------------------|------------|----------------------------|-------|
| {{actor}} | {{command}} | {{guard}} | {{control}} | {{feedback}} | {{trace_ref}} |

## Business Rules

| Rule Ref | UI Enforcement | Error / Recovery | Trace |
|----------|----------------|------------------|-------|
| RULE-01 | {{enforcement}} | {{error_or_recovery}} | {{trace_ref}} |

## Explicit Non-UI Items

| Domain Ref | Reason Not Represented In UI | Alternative Evidence |
|------------|------------------------------|----------------------|
| {{ref}} | {{reason}} | {{evidence_ref}} |

