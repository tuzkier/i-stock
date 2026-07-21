# Product Domain Model: {{project_name}}

> **来源**：prd 技能 → `harness-runtime/harness/stages/{{mission_id}}/product/product-domain-model.md`
> **用途**：按 DDD 方法沉淀产品领域模型。本文定义业务语义、边界、规则、状态和行为契约，不定义数据库、接口、框架、缓存、队列或部署方案。

**mission-id:** {{mission_id}}
**Status:** `draft`

---

## 控制契约

- Contract: `contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件提供产品领域模型解释。

---

## Domain Intent

| Item | Content | Trace |
|------|---------|-------|
| Business Problem | {{business_problem}} | {{mission_or_ac_id}} |
| Product Capability | {{capability}} | {{fr_or_capability_id}} |
| Non-Goals | {{non_goal}} | {{scope_out_id}} |
| Modeling Depth | {{simple_standard_complex}} | {{reason_and_signal}} |

如果某个 DDD 要素不适用，必须写明 `N/A because ...` 或 `不适用：原因...`，不得留空。

---

## Strategic DDD

### Domain / Subdomain

| Type | Name | Why It Exists | Core / Supporting / Generic | Trace |
|------|------|---------------|-----------------------------|-------|
| Domain | {{domain_name}} | {{reason}} | Core | {{trace_id}} |
| Subdomain | {{subdomain_name}} | {{reason}} | {{core_supporting_generic}} | {{trace_id}} |

### Bounded Contexts

| Context-ID | Context Name | Responsibility | In Language | Out of Boundary |
|------------|--------------|----------------|-------------|-----------------|
| BC-01 | {{context_name}} | {{responsibility}} | {{terms_owned_here}} | {{not_owned_here}} |

### Context Map

| Upstream Context | Relationship | Downstream Context | Contract / Translation Rule | Risk |
|------------------|--------------|--------------------|-----------------------------|------|
| {{upstream}} | {{customer_supplier_conformist_acl}} | {{downstream}} | {{contract_or_translation}} | {{risk}} |

### Ubiquitous Language

| Term | Definition in This Context | Forbidden Ambiguity | Source |
|------|----------------------------|---------------------|--------|
| {{term}} | {{definition}} | {{ambiguous_meaning_to_avoid}} | {{source}} |

### Capability Boundary

| Capability-ID | Capability | Added / Changed / Removed / Reused | Boundary Rule | Trace |
|---------------|------------|------------------------------------|---------------|-------|
| CAP-01 | {{capability}} | {{change_type}} | {{boundary_rule}} | {{fr_or_spec_id}} |

---

## Tactical DDD

### Actors

| Actor-ID | Actor / Role | Goal | Allowed Contexts |
|----------|--------------|------|------------------|
| ACT-01 | {{actor}} | {{goal}} | {{contexts}} |

### Aggregates

| Aggregate-ID | Aggregate | Aggregate Root | Consistency Boundary | Invariants Owned |
|--------------|-----------|----------------|----------------------|------------------|
| AGG-01 | {{aggregate}} | {{aggregate_root}} | {{consistency_boundary}} | {{invariant_ids}} |

### Entities

| Entity-ID | Entity | Identity | Lifecycle | Aggregate |
|-----------|--------|----------|-----------|-----------|
| ENT-01 | {{entity}} | {{identity}} | {{lifecycle}} | {{aggregate_id}} |

### Value Objects

| ValueObject-ID | Value Object | Attributes | Equality / Validation Rule | Used By |
|----------------|--------------|------------|----------------------------|---------|
| VO-01 | {{value_object}} | {{attributes}} | {{rule}} | {{entity_or_command}} |

### Domain Commands

| Command-ID | Command | Actor / System | Target Aggregate | Preconditions | Result |
|------------|---------|----------------|------------------|---------------|--------|
| CMD-01 | {{command}} | {{actor}} | {{aggregate_id}} | {{preconditions}} | {{result}} |

### Domain Events

| Event-ID | Event | Raised By | Meaning | Consumers / Follow-up |
|----------|-------|-----------|---------|-----------------------|
| EVT-01 | {{event}} | {{command_or_aggregate}} | {{business_fact}} | {{consumer_or_policy}} |

### Invariants

| Invariant-ID | Invariant | Aggregate / Context | Commands Protected | Failure Behavior | Trace |
|--------------|-----------|---------------------|--------------------|------------------|-------|
| INV-01 | {{invariant}} | {{aggregate_or_context}} | {{command_ids}} | {{reject_compensate_escalate}} | {{fr_or_ac_id}} |

### Policies

| Policy-ID | Policy | Trigger | Decision Inputs | Outcome | Trace |
|-----------|--------|---------|-----------------|---------|-------|
| POL-01 | {{policy}} | {{event_or_command}} | {{inputs}} | {{outcome}} | {{trace_id}} |

### Domain Services

| Service-ID | Domain Service | Why Not Entity-Owned | Inputs | Output / Event |
|------------|----------------|----------------------|--------|----------------|
| DS-01 | {{domain_service}} | {{reason}} | {{inputs}} | {{output}} |

### State Machines

| StateMachine-ID | Entity / Aggregate | From State | To State | Trigger Command / Event | Actor | Preconditions | Invalid Transitions |
|-----------------|--------------------|------------|----------|-------------------------|-------|---------------|---------------------|
| STM-01 | {{entity_or_aggregate}} | {{from_state}} | {{to_state}} | {{command_or_event}} | {{actor}} | {{preconditions}} | {{invalid_transitions}} |

---

## Rules & Constraints

### Permission Matrix

| Actor | Command | Target Aggregate / Entity | State | Allowed | Reason / Rule | Audit Required |
|-------|---------|---------------------------|-------|---------|---------------|----------------|
| {{actor}} | {{command_id}} | {{target}} | {{state}} | {{yes_no}} | {{reason}} | {{yes_no}} |

### Exception / Compensation / Idempotency

| Case-ID | Case | Trigger | Expected Handling | Idempotency / Conflict Rule | Trace |
|---------|------|---------|-------------------|-----------------------------|-------|
| EXC-01 | {{exception_case}} | {{trigger}} | {{handling}} | {{rule}} | {{trace_id}} |

### Compliance / Security / Audit

| Rule-ID | Rule | Applies To | Evidence / Audit Requirement | Trace |
|---------|------|------------|------------------------------|-------|
| AUD-01 | {{rule}} | {{object_or_command}} | {{evidence_required}} | {{trace_id}} |

---

## Traceability

| Product Requirement / Scenario | Domain Element | Element Type | Why It Covers the Requirement |
|--------------------------------|----------------|--------------|-------------------------------|
| FR-01 | CMD-01 | Command | {{coverage_reason}} |
| AC-01 | INV-01 | Invariant | {{coverage_reason}} |

---

## Downstream Guidance

| Consumer | Must Preserve / Consume | Source Domain Element | Notes |
|----------|--------------------------|-----------------------|-------|
| interaction | Objects, states, commands, permission-restricted actions | {{agg_cmd_state_ids}} | {{notes}} |
| solution | Bounded contexts, policies, events, consistency boundaries | {{bc_policy_event_ids}} | {{notes}} |
| technical_analysis | Aggregates, commands, events, invariants, idempotency rules | {{agg_cmd_event_inv_ids}} | {{notes}} |
| breakdown / test | Invariants, state transitions, permissions, exception cases | {{inv_stm_perm_exc_ids}} | {{notes}} |

---

## Open Questions & Modeling Risks

| Risk-ID | Question / Risk | Impact | Decision Needed By | Owner |
|---------|------------------|--------|--------------------|-------|
| RISK-01 | {{question_or_risk}} | {{impact}} | {{stage_or_date}} | {{owner}} |
