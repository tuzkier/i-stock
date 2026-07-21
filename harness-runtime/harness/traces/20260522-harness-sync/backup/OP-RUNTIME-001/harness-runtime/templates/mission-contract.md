# 任务契约: {{mission_id}}

> **来源**：任务接入技能 → `harness-runtime/harness/missions/{{mission_id}}/mission-contract.md`
> **参考方法论**：BMAD Product Brief（清晰愿景）+ OpenSpec Change Proposal（范围边界）

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}

---

## 控制契约

> 本节只引用外部控制契约。程序化权威在 YAML；Markdown 只保留说明、推理和人工可读摘要。

- Contract: `contracts/mission-contract.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## TL;DR

> 一句话概括：做什么、为什么做、完成后的世界有什么不同。

{{tldr}}

---

## 执行意图

> 记录用户自然表达要开始做的依据。没有这个来源，不应创建 Mission 或驱动后续阶段。

- **Confirmed:** {{intake_confirmed}}
- **Confirmation Source:** {{intake_confirmation_source}}
- **Confirmed At / Turn:** {{intake_confirmed_at_or_turn}}

---

## 意图边界 / 来源取证

> 本节说明哪些内容真正进入任务目标，哪些只是工作方式、流程约束或输入材料。Objective、交付物和 AC 只能来自真实任务目标。

- **Actual Task Goal:** {{actual_task_goal}}
- **Agent Instructions:** {{agent_instructions}}
- **Process Constraints:** {{process_constraints}}
- **Source Materials:** {{source_materials}}
- **Discussion Outputs:** {{discussion_outputs}}
- **Corrections:** {{corrections}}
- **Excluded From Objective:** {{excluded_from_objective}}

---

## Objective

> 核心目标：描述完成后系统/产品的**状态变化**，不写实现方式。
> 好的 Objective 是可以验证的——你能判断"有没有达到"。

{{objective}}

---

## 成功定义

> 本节定义最终以什么效果、什么交付物、什么证据判断任务达标。后续 verify / delivery 以这里为验收口径。

- **期望效果**：{{desired_effect}}
- **主要交付物**：{{success_primary_deliverable}}
- **交付格式**：{{success_delivery_format}}
- **验证证据**：{{validation_evidence}}
- **非目标**：{{success_non_goals}}

---

## 用户故事

> 用户故事回答“谁需要什么、为什么有价值”。GWT 不写在这里；GWT 属于后面的验收标准。
> 每条用户故事必须能追溯到至少一条 AC，后续 产品定义 会继续追溯到 Journey / FR / Scenario。
> 每条故事还必须提供产品故事上下文：用户、问题、场景、价值和成功指标；缺失时 产品定义 不应自行补脑。

| Story-ID | 用户 | 问题 | 场景 | 目标 | 价值 | 成功指标 | 关联 AC |
|----------|------|------|------|------|------|----------|---------|
| US-01 | {{story_user_1}} | {{story_problem_1}} | {{story_scenario_1}} | {{user_goal_1}} | {{story_value_1}} | {{story_success_signal_1}} / {{story_success_target_1}} | AC-01 |
| US-02 | {{story_user_2}} | {{story_problem_2}} | {{story_scenario_2}} | {{user_goal_2}} | {{story_value_2}} | {{story_success_signal_2}} / {{story_success_target_2}} | AC-02 |

---

## 范围内

> 明确列出本次任务 **包含**的内容。每条说明**做什么**，不说怎么做。

- {{scope_in_item_1}}
- {{scope_in_item_2}}

---

## 范围外

> 明确列出**不做**的事项，并附理由（防止范围蔓延）。

| 不做的事 | 理由 |
|---------|------|
| {{scope_out_1}} | {{reason_1}} |

---

## 验收标准

> 每条 AC 用 Given/When/Then 格式写，确保可测试、可验证。
> AC 是本任务的"结业考试"，执行者和验证者以此为准。

**AC-01:** {{ac_01_description}}
- **Given** {{precondition}}
- **When** {{action}}
- **Then** {{expected_outcome}}

**AC-02:** {{ac_02_description}}
- **Given** {{precondition}}
- **When** {{action}}
- **Then** {{expected_outcome}}

---

## 执行治理级别

> 根据治理风险评估确定（见任务接入工作流 Phase 3）。治理级别是 AI 自主推进授权边界，不是文件数或角色数量的简单映射。

- **Level:** `{{autonomy_level}}` <!-- 快速执行 / 专家确认 / 受控推进 -->
- **Governance Risk:** `{{governance_risk}}` <!-- low / medium / high -->
- **Rationale:** {{autonomy_rationale}}
- **Skippable Stages:** {{skippable_stages}} <!-- 来自 execution_governance.levels.<autonomy_level>.skippable_stages，可按任务覆盖 -->
- **Reviewer PASS Sufficient:** {{reviewer_pass_sufficient}} <!-- 专家审查通过后可自动继续的阶段 -->

### 治理风险依据

| 类别 | 结论 | 依据 |
|------|------|------|
| Hard Triggers | {{hard_triggers}} | {{hard_trigger_rationale}} |
| 决策权 | {{decision_authority_risk}} | {{decision_authority_rationale}} |
| 可逆性 | {{reversibility_risk}} | {{reversibility_rationale}} |
| 影响面 | {{blast_radius_risk}} | {{blast_radius_rationale}} |
| 验证可靠性 | {{verification_reliability_risk}} | {{verification_reliability_rationale}} |
| 数据 / 权限 | {{data_permission_risk}} | {{data_permission_rationale}} |
| 外部依赖 | {{external_dependency_risk}} | {{external_dependency_rationale}} |
| Agent 行动权 | {{agent_authority_risk}} | {{agent_authority_rationale}} |
| 不确定性 | {{uncertainty_risk}} | {{uncertainty_rationale}} |

### 规模信号

| 信号 | 结论 | 说明 |
|------|------|------|
| 变更范围 | {{change_surface_signal}} | {{change_surface_rationale}} |
| 用户角色 | {{user_roles_signal}} | {{user_roles_rationale}} |
| 模块跨度 | {{module_span_signal}} | {{module_span_rationale}} |

### 治理确认

- **Decision Rule:** {{governance_decision_rule}}
- **User Confirmation Required:** {{governance_confirmation_required}}
- **Downgrade / Checkpoint Removal Approval:** {{governance_downgrade_approval}}

---

## Work Graph

> Mission 是一次执行切片；Work Graph node 是长期工作对象。新 Mission 必须引用本次推进的 primary node。

- **Primary Nodes:** {{work_graph_primary_nodes}} <!-- 例如 [REQ-001] / [TASK-001, TASK-002] -->
- **Related Nodes:** {{work_graph_related_nodes}} <!-- 例如 [EPIC-001, 产品定义-001] -->
- **Operation:** `{{work_graph_operation}}` <!-- advance_lane / implement_batch / review_batch / verify_batch / deliver_slice -->
- **From Lane:** `{{work_graph_from_lane}}`
- **To Lane:** `{{work_graph_to_lane}}`
- **Board Source:** `harness-runtime/harness/work-graph/boards/main.yaml`

---

## 必需 Checkpoint

> 哪些阶段需要暂停等待用户确认。默认来自 `harness.yaml` 的 `execution_governance.levels.<autonomy_level>.human_checkpoints`。旧 `A1` / `A2` / `A3` 只能按 `legacy_level_aliases` 归一化为新治理级别，不读取旧 Checkpoint 配置。任务契约可按任务风险显式覆盖。

| Checkpoint | 触发条件 | 预期产出 |
|-----------|---------|---------|
| prd | {{prd_checkpoint_condition}} | product/product-definition.md 审查通过 |
| solution | {{solution_checkpoint_condition}} | solution.md 审查通过 |
| interaction | {{interaction_checkpoint_condition}} | interaction.md 确认（默认需要；仅 API-only / 无界面时可跳过） |
| tech-design | {{tech_design_checkpoint_condition}} | tech-design.md 审查通过 |
| execution-brief | {{brief_checkpoint_condition}} | execution-brief.md 确认 |
| 验证报告 | {{verification_checkpoint_condition}} | `verification-report.md` 证据确认 |
| 验收结果 | 默认最终验收 | `acceptance-result.md` 用户结果验收 |
| 交付包 | {{delivery_package_checkpoint_condition}} | `delivery-package.md` 内部归档确认 |

---

## 升级规则

> 什么情况下必须停下来请求用户介入，不能自行决策。

- **阻断性技术风险**：{{escalation_tech_risk}}
- **范围扩展**：{{escalation_scope_creep}}
- **外部依赖失效**：{{escalation_dependency_failure}}

---

## 约束

> 硬性约束，执行过程中不得违反。注明来源和"如果不成立的影响"。

| 约束 | 来源 | 违反影响 |
|-----|------|---------|
| {{constraint_1}} | {{source_1}} | {{impact_1}} |

---

## 交付预期

> 本次任务预期产出什么，以什么形式交付。
> 必须与「成功定义」一致；如果后续阶段发现交付预期无法支撑验收，回 intake 或触发 Decision Gate。

- **主要产出**：{{primary_deliverable}}
- **辅助产出**：{{secondary_deliverable}}
- **交付格式**：{{delivery_format}}

---

## Agent 工程

> 仅当 `agent_engineering.enabled=true` 且本任务涉及 Agent 组件时填写。

<!-- 如不涉及 Agent 组件，删除此节 -->

- **涉及 Agent 组件**：{{agent_components}}
- **Agent 能力设计专家**：必须调用 `agent-capability-designer` + `agent-capability-reviewer` / 不涉及

---

## 审查摘要

> 由任务接入技能在审查循环结束后自动附加，记录各 Agent 的审查结论。

<!-- 任务接入技能自动填写 -->
