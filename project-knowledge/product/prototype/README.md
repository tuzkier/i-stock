---
knowledge_type: product
status: draft
source: init
confidence: needs-review
---

# Prototype Project

Long-lived product prototype model. Each mission that reaches interaction stage
produces a patch against this prototype project; accepted, stable changes are
promoted here during retrospective.

## Structure

| Area | Path | Purpose |
|------|------|---------|
| Surface index | `../ui-surfaces/README.md` | Stable UI surface identities |
| Product workflows | `../workflows/README.md` | Long-lived user journeys |
| Capability specs | `../../specs/` | Externally observable behavior |

## Patch Discipline

- Mission stage `interaction-spec/` is a patch, not the long-lived prototype project.
- Every patch declares baseline, operation, affected surfaces, and promotion target.
- Stable surface structure lands in `project-knowledge/product/ui-surfaces/`.
- Stable user journeys land in `project-knowledge/product/workflows/`.
- User-observable behavior lands in `project-knowledge/specs/<capability>/spec.md` when `spec.enabled=true`.
- Do not copy whole mission artifacts into this directory.

