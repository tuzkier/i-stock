# 技术设计: {{mission_id}}

> **来源**：设计技能 Step 2 → `harness-runtime/harness/stages/{{mission_id}}/tech-design.md`
> **参考方法论**：C4 Model、ADRs、DDD、Arc42；OpenAPI 3.x；Database Normalization、Event Sourcing、CQRS
> **上游**：`solution.md` | `product/product-definition.md` | `mission-contract.md`

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Status:** `draft` <!-- draft / in-审查 / 已批准 -->

---

## Overview

> 一段话说明：本次技术设计要实现什么，整体实现路径是什么，与上游 solution 的设计路线和关键决策对应关系。
> 技术设计必须支撑正式验收，不得只覆盖 demo happy path；如果分阶段交付，说明当前阶段的生产可用边界。

{{tech_design_overview}}

**设计范围：** {{design_scope}}
**实现策略摘要：** {{implementation_strategy_summary}}

---

## 控制契约

> 技术指导契约将方案决策转成模块、接口、数据和验证边界，供拆解 / 执行 / code-review 消费。

- Contract: `contracts/tech-design.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## 模块划分

> 每个模块说明职责，不写实现细节。职责是"能做什么"，不是"怎么做"。
> 每个模块必须可追溯到 solution.md 中的某个决策。

| 模块 | 职责 | 来自决策 | 涉及文件/路径 |
|-----|------|---------|-------------|
| {{module_1}} | {{module_1_responsibility}} | 决策 {{decision_ref_1}} | {{module_1_files}} |
| {{module_2}} | {{module_2_responsibility}} | 决策 {{decision_ref_2}} | {{module_2_files}} |

### 模块 1: {{module_1_name}}

**职责：** {{module_1_desc}}

**关键约束：**
- {{module_1_constraint_1}}
- {{module_1_constraint_2}}

**涉及文件：**
| 文件 | 变更类型 | 说明 |
|-----|---------|------|
| {{file_1}} | 新增/修改/删除 | {{file_1_desc}} |

---

## 关键接口定义

> 参考 bmad tech-规格的接口设计格式。只定义接口边界，不定义内部实现。

### 接口 1: {{interface_1_name}}

```
{{interface_1_signature}}
```

**输入：**
| 参数 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| {{param_1}} | {{type_1}} | 是/否 | {{param_1_desc}} |

**输出：**
| 字段 | 类型 | 说明 |
|-----|------|------|
| {{field_1}} | {{type_1}} | {{field_1_desc}} |

**错误情况：**
| 错误码 | 触发条件 | 处理方式 |
|-------|---------|---------|
| {{error_1}} | {{condition_1}} | {{handling_1}} |

---

## 数据模型 / 状态流转

> 如果涉及数据库变更或状态机，在此描述。

### 数据模型变更

```
{{data_model_changes}}
```

**迁移策略：** {{migration_strategy}}

### 状态流转

```
{{state: initial}} --[{{trigger}}]--> {{state: next}}
```

---

## 实现策略

> 先做什么、后做什么、为什么这个顺序。确保可以直接分解为 execution-brief 中的任务项。
> 实现策略应按要求准确落地，而不是选择最省事路径：所有 AC/NFR、错误路径、兼容性和回归验证都要有明确落点。

### 实现顺序

1. **{{impl_step_1}}**
 - 理由：{{impl_step_1_rationale}}
 - 产出：{{impl_step_1_output}}

2. **{{impl_step_2}}**
 - 理由：{{impl_step_2_rationale}}
 - 产出：{{impl_step_2_output}}

3. **{{impl_step_3}}**
 - 理由：{{impl_step_3_rationale}}
 - 产出：{{impl_step_3_output}}

### 测试策略

> 如何验证每个模块的实现。

| 模块 | 测试类型 | 关键测试场景 |
|-----|---------|-----------|
| {{module_1}} | 单元/集成/端到端 | {{test_scenario_1}} |

### 生产就绪要求

| 要求 | 落地设计 | 验证方式 |
|-----|---------|---------|
| 错误处理/异常路径 | {{error_handling_design}} | {{error_handling_verification}} |
| 兼容性/迁移 | {{compatibility_design}} | {{compatibility_verification}} |
| 可观测性/日志 | {{observability_design}} | {{observability_verification}} |
| 回滚/降级 | {{rollback_design}} | {{rollback_verification}} |

---

## 对现有系统的影响

> 仅棕地项目填写。说明对哪些现有模块有影响，影响的性质（接口变更/行为变更/数据变更）。

| 现有模块 | 影响类型 | 描述 | 向后兼容性 |
|--------|---------|------|---------|
| {{existing_module_1}} | {{impact_type_1}} | {{impact_desc_1}} | 兼容/破坏性变更 |

**破坏性变更处理：** {{breaking_change_strategy}}

---

## Agent 实现

> 仅当 `agent_engineering.enabled=true` 且 solution.md 存在 `## Agent 架构` 段落时填写；由 `agent-capability-designer` 产出，`agent-capability-reviewer` 审查。

<!-- 如不涉及 Agent 组件，删除此节 -->

### Agent: {{agent_name}}

**Role 文本草稿：** {{agent_role_text}}

**Judgment Framework：**
- {{judgment_1}}
- {{judgment_2}}

**边界规则：**
- {{boundary_rule_1}}
- {{boundary_rule_2}}

**技能工作流骨架：**
```
Step 1: {{workflow_step_1}}
Step 2: {{workflow_step_2}}
```

**Eval 测试设计：**
| 场景 | 输入 | 预期输出 | 通过条件 |
|-----|------|---------|---------|
| 正常路径 | {{normal_input}} | {{normal_output}} | {{pass_condition}} |
| 边界场景 | {{edge_input}} | {{edge_output}} | {{pass_condition}} |
| 对抗场景 | {{adversarial_input}} | {{adversarial_output}} | {{pass_condition}} |

---

## 已知遗留问题

<!-- 如无遗留问题，删除此节 -->

| 问题 | 用户决策 | 后续处理建议 |
|-----|---------|-----------|
| {{issue_1}} | 接受/降级 | {{followup_1}} |

---

## 审查摘要

> 由设计技能在审查循环结束后自动附加。

<!-- 设计技能自动填写 -->
