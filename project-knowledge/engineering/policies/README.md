---
knowledge_type: engineering_policy
status: active
source: template
used_by_stages: discovery,prd,design,execute,code-review,breakdown,verify
tags: engineering,policy,project-lint,stage-rules
---

# Engineering Policies

This directory stores project-owned, machine-readable policies that shape Harness workflows.

- `stage-rules.yaml` defines stage-specific project rules that agents should load as knowledge.
- `project-lint.yaml` defines deterministic project lint rules. Reports generated from it stay under `harness-runtime/harness/traces/`.

