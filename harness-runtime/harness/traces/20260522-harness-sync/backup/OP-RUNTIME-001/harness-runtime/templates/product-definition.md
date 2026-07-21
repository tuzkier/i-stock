# Product Definition: {{project_name}}

> **来源**：prd 技能 → `harness-runtime/harness/stages/{{mission_id}}/product/product-definition.md`
> **上游**：`mission-contract.md` | `product-evidence.md` | `product-domain-model.md`（如需要）

**mission-id:** {{mission_id}}
**Status:** `draft`

---

## 控制契约

- Contract: `contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件提供主产品定义正文。

---

## Business Definition

**业务问题：** {{problem_statement}}

**业务目标：** {{business_objective}}

**成功信号：** {{success_signals}}

**Mission fit：** {{mission_fit}}

---

## Problem Diagnosis

| 业务方表述 | 底层问题 | 受影响用户 / 场景 | 价值假设 | 证据 |
|------------|----------|-------------------|----------|------|
| {{requested_solution}} | {{underlying_problem}} | {{user_scenario}} | {{value_hypothesis}} | {{evidence_ref}} |

---

## Users and Scenarios

| Scenario-ID | 用户 / 角色 | 场景 | 当前痛点 | 目标行为 |
|-------------|-------------|------|----------|----------|
| SCN-01 | {{user_role}} | {{scenario}} | {{pain}} | {{target_behavior}} |

---

## Current Workflow Summary

{{current_workflow_summary}}

---

## Scope and Tradeoffs

| 类型 | 内容 | 理由 | 追溯 |
|------|------|------|------|
| In | {{in_scope}} | {{rationale}} | {{trace_ref}} |
| Out | {{out_scope}} | {{rationale}} | {{trace_ref}} |

---

## Evidence Summary

| Evidence Type | Source | Product Decision Impact | Degradation |
|---------------|--------|-------------------------|-------------|
| Knowledge | {{knowledge_ref}} | {{impact}} | {{degradation_or_none}} |
| Spec | {{spec_ref}} | {{impact}} | {{degradation_or_none}} |
| GitNexus | {{gitnexus_ref}} | {{impact}} | {{degradation_or_none}} |

---

## Product Domain Summary

### Core Objects

| Object-ID | 对象 | 说明 |
|-----------|------|------|
| OBJ-01 | {{object}} | {{description}} |

### State and Permission Summary

{{state_permission_summary}}

---

## Product Rules

| Rule-ID | 规则 | 验收方式 | 追溯 |
|---------|------|----------|------|
| RULE-01 | {{rule}} | {{verification}} | {{trace_ref}} |

---

## Functional Requirements

### FR-01: {{fr_title}}

**描述：** {{fr_description}}

**验收标准：**
- **Given** {{precondition}}
- **When** {{action}}
- **Then** {{expected_outcome}}

**关联：** {{trace_ref}}
**优先级：** `{{priority}}`

---

## Non-Functional Requirements

| NFR-ID | 类别 | 要求 | 条件 | 指标 | 测量方式 |
|--------|------|------|------|------|----------|
| NFR-01 | {{category}} | {{requirement}} | {{condition}} | {{metric}} | {{measurement}} |

---

## Agent Capability Requirements

> 仅当 `agent_engineering.enabled=true` 且存在 Agent 组件时填写；否则删除本节。

| ACR-ID | 组件 | 工作权 | 行为要求 | Eval 标准 | 追溯 |
|--------|------|--------|----------|-----------|------|
| ACR-01 | {{component}} | {{work_rights}} | {{behaviour_requirement}} | {{eval_criteria}} | {{trace_ref}} |

---

## Validation and Launch Loop

| 验证阶段 | 验证内容 | 证据 | 成功 / 失败判定 |
|----------|----------|------|-----------------|
| 上线前 | {{pre_launch_check}} | {{evidence}} | {{decision_rule}} |
| 上线后 | {{post_launch_metric}} | {{evidence}} | {{decision_rule}} |

---

## Traceability Matrix

| Mission Story / AC | Scenario | Rule | FR / NFR | Spec / Knowledge | Evidence |
|--------------------|----------|------|----------|------------------|----------|
| US-01 / AC-01 | SCN-01 | RULE-01 | FR-01 | {{spec_or_knowledge_ref}} | {{evidence_ref}} |

---

## Prototype / Interaction Trigger

| Trigger | Required | Reason | Expected Next Artifact |
|---------|----------|--------|------------------------|
| Prototype / User Journey / State Matrix | required / skipped_api_only | {{reason}} | `interaction.md` / `visual-interaction/` |

---

## Open Questions

- {{open_question}}
