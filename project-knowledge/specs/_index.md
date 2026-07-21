---
knowledge_type: specs
status: draft
source: init
confidence: needs-review
---

# Behavior Specifications

Behavior specs are long-lived, verifiable contracts. They are promoted from
delta specs and PRD outcomes after a task is accepted.

## Capability Specs

| Capability | Path | Last Source Mission | Status |
|---|---|---|---|
| TBD | TBD | init | draft |

## Format

```markdown
# <Capability Name> Specification

## Purpose
One sentence describing the externally observable responsibility.

## Requirements

### Requirement: <Name>
The system SHALL <externally observable behavior>.

#### Scenario: <Scenario name>
- **GIVEN** <precondition>
- **WHEN** <trigger>
- **THEN** <observable result>
```
