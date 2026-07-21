# Discovery Brief: {{mission_id}}

> **来源**：discovery 技能 → `harness-runtime/harness/stages/{{mission_id}}/discovery-brief.md`
> **参考方法论**：Event Storming；Impact Mapping；Jobs-to-be-Done
> **上游**：`harness-runtime/harness/missions/{{mission_id}}/mission-contract.md` | `project-context.md`

- Contract: `contracts/discovery-brief.contract.yaml`
- Schema: `.harness/common/schemas/control_contract.v1/discovery_brief_contract.yaml`

> 结构化字段（affected_capabilities / roles / scenarios / existing_solutions / design_assumptions / agent_engineering_candidates / degradations）由外部 contract YAML 承载；本文件只保留面向人的叙事段，不得内嵌 fenced YAML 控制契约段（由 harness-lint W-discovery-contract 规则在 M4.2 强校验）。

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Status:** `draft` <!-- draft / in-审查 / 已批准 -->

---

## TL;DR

{{summary}}

---

## 问题空间

### 背景

{{background}}

### 当前现状

{{current_state}}

### 关键约束

| 约束 | 来源 | 影响 |
|------|------|------|
| {{constraint_1}} | {{source_1}} | {{impact_1}} |

---

## 影响面

| 领域 / 模块 | 影响类型 | 置信度 | 证据 |
|-------------|----------|--------|------|
| {{area_1}} | {{impact_type_1}} | CONFIRMED / UNCERTAIN / ASSUMED | {{evidence_1}} |

---

## 关键发现

| ID | 发现 | 证据 | 对后续工作 / Work Graph 的影响 |
|----|------|------|------------------|
| DIS-001 | {{finding_1}} | {{evidence_1}} | {{downstream_impact_1}} |

---

## 风险与未知

| ID | 风险 / 未知 | 严重度 | 处理建议 |
|----|-------------|--------|----------|
| RISK-001 | {{risk_1}} | High / Medium / Low | {{mitigation_1}} |

---

## PRD 输入建议

| 主题 | 建议写入 PRD 的内容 | 依据 |
|------|--------------------|------|
| {{topic_1}} | {{prd_input_1}} | {{basis_1}} |

---

## 证据索引

| 证据 | 类型 | 路径 / 命令 / 来源 |
|------|------|-------------------|
| {{evidence_id_1}} | code / doc / command / external | {{evidence_ref_1}} |
