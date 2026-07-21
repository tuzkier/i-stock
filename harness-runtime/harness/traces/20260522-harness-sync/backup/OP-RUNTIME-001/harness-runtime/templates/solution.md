# Solution: {{mission_id}}

> **来源**：设计技能 Step 1 → `harness-runtime/harness/stages/{{mission_id}}/solution.md`
> **参考方法论**：BMAD Tech-规格（方案评估）+ OpenSpec Proposal（可行性分析）+ ADRs
> **上游**：`product/product-definition.md` | `mission-contract.md` | `project-context.md`

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Status:** `draft` <!-- draft / in-审查 / 已批准 -->

---

## Overview

> 用 2-3 句话说明：本次设计要达成什么目标，核心设计路线是什么，哪些约束决定了这个路线。
> 设计必须先围绕任务目标、约束、风险和维护成本展开；只有存在真实路线分歧时，才进行方案选择。不要把"改动最小"或"先做 demo"当作默认设计理由。

{{solution_overview}}

**关键设计判断 / 决策点：**
1. {{decision_point_1}}
2. {{decision_point_2}}
3. {{decision_point_3}}

---

## 控制契约

> Solution 指导契约记录下游必须遵守的方案决策、禁止路径和风险缓解，不复制正文论证。

- Contract: `contracts/solution.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## 目标驱动设计

### 问题与目标回顾

{{problem_and_goal_recap}}

### 设计路线

{{design_route}}

### 目标与约束对照

| 目标/约束 | 设计如何满足 | 证据/说明 |
|----------|-------------|----------|
| {{goal_or_constraint_1}} | {{design_response_1}} | {{evidence_1}} |

---

## 关键决策 1: {{decision_title_1}}

> 仅当存在多条实质可行路线时填写候选路线对比；如果没有真实分歧，说明设计判断依据即可，不要为凑格式制造候选方案。
> 参考 bmad tech-规格结构：Problem → Options → Decision → Risks

### 问题描述

{{decision_problem_1}}

**来自 产品定义：** FR-{{fr_id}} / NFR-{{nfr_id}}

### 可行路线

| 路线 | 描述 | 优点 | 缺点 | 适用条件 |
|-----|------|------|------|---------|
| 路线 A: {{option_a_name}} | {{option_a_desc}} | {{option_a_pros}} | {{option_a_cons}} | {{option_a_condition}} |
| 路线 B: {{option_b_name}} | {{option_b_desc}} | {{option_b_pros}} | {{option_b_cons}} | {{option_b_condition}} |

### 适配性评估

| 路线 | 目标完成度 | 架构适配 | 长期维护成本 | 主要风险 | 是否仅为 demo/MVP |
|-----|-----------|---------|-------------|---------|------------------|
| 路线 A | 完整/部分/不足 | 高/中/低 | 高/中/低 | {{option_a_risk}} | 是/否 |
| 路线 B | 完整/部分/不足 | 高/中/低 | 高/中/低 | {{option_b_risk}} | 是/否 |

### 所选路线

**选择：** 路线 {{recommended_option}}

**理由：** {{recommendation_rationale}}

**为什么不是最小改动/demo 路线：** {{why_not_minimal_or_demo}}

**Tradeoff 说明：** {{tradeoff_explanation}}

### 风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|-----|--------|------|---------|
| {{risk_1}} | 高/中/低 | {{impact_1}} | {{mitigation_1}} |

---

## 关键决策 2: {{decision_title_2}}

### 问题描述

{{decision_problem_2}}

### 可行路线

| 路线 | 描述 | 优点 | 缺点 |
|-----|------|------|------|
| 路线 A: {{option_a_name}} | {{option_a_desc}} | {{option_a_pros}} | {{option_a_cons}} |
| 路线 B: {{option_b_name}} | {{option_b_desc}} | {{option_b_pros}} | {{option_b_cons}} |

### 所选路线

**选择：** 路线 {{recommended_option}}

**理由：** {{recommendation_rationale}}

---

## Agent 架构

> 仅当 `agent_engineering.enabled=true` 且任务契约标记了 Agent 组件时填写；由 `agent-capability-designer` 产出，`agent-capability-reviewer` 审查。

<!-- 如不涉及 Agent 组件，删除此节 -->

### Agent 组件概览

| Agent | 职责 | 工作权范围 | 依赖 |
|-------|------|-----------|------|
| {{agent_1}} | {{agent_1_role}} | {{agent_1_scope}} | {{agent_1_deps}} |

### 组件间交互

{{agent_interaction_description}}

---

## 技术约束汇总

> 来自 project-context.md 和任务契约的硬性约束，已在上述决策中体现。

| 约束 | 来源 | 对本次选型的影响 |
|-----|------|--------------|
| {{constraint_1}} | {{source_1}} | {{impact_1}} |

---

## 已知遗留问题

> 如存在经用户确认降级通过的问题，在此记录。

<!-- 如无遗留问题，删除此节 -->

| 问题 | 用户决策 | 后续处理建议 |
|-----|---------|-----------|
| {{issue_1}} | 接受/降级 | {{followup_1}} |

---

## 审查摘要

> 由设计技能在审查循环结束后自动附加。

<!-- 设计技能自动填写 -->
