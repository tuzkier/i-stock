# Source Trace

| Source | Path | Consumed Sections | Impact | Gaps |
|--------|------|-------------------|--------|------|
| Product Definition | `../product/product-definition.md` | {{sections}} | {{impact}} | {{gaps_or_none}} |
| Domain Model | `../product/product-domain-model.md` | Core Objects / Relationships / State Machine / Permission Matrix / Business Rules | {{impact}} | {{gaps_or_none}} |
| Product Evidence | `../product/product-evidence.md` | {{sections}} | {{impact}} | {{gaps_or_none}} |
| Delta Spec | `../specs/{{capability}}/spec.md` | Requirements / Scenarios | {{impact}} | {{gaps_or_none}} |
| Project Knowledge | `project-knowledge/{{path}}` | {{sections}} | {{impact}} | {{gaps_or_none}} |

## Trace Rules

- Every screen, flow, state, scenario, validation rule, and E2E obligation must trace to PRD AC, domain model item, or delta spec scenario.
- If a domain object / state / action is intentionally not represented in UI, record the reason in `domain-ui-mapping.md`.

