---
knowledge_type: product
status: draft
source: init
confidence: needs-review
---

# UI Surfaces

Long-lived index of product UI surfaces. Use this to avoid creating duplicate
prototype pages for every mission.

## Surface Index

| Surface ID | Name | Bounded Context / Module | Route / Entry | Last Source Mission | Status |
|------------|------|--------------------------|---------------|---------------------|--------|
| TBD | TBD | TBD | TBD | init | draft |

## Rules

- Surface IDs are stable across missions.
- Do not name surfaces with mission ids, dates, versions, or temporary branch names.
- When a mission modifies UI, interaction stage should reference the existing surface baseline and write a surface changeset.
- Promote only stable surface structure here during retrospective; do not copy whole `interaction-spec/` stage artifacts.

