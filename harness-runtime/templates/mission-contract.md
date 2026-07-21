# 任务契约: {{mission_id}}

> **来源**：任务接入技能 → `harness-runtime/harness/missions/{{mission_id}}/mission-contract.md`
> **参考方法论**：BMAD 产品简报（Product Brief，清晰愿景）+ OpenSpec 变更提案（Change Proposal，范围边界）

**作者:** {{user_name}}
**日期:** {{date}}
**任务编号:** {{mission_id}}

---

## 控制契约

> 本节只引用外部控制契约。程序化权威在 YAML；Markdown 只保留说明、推理和人工可读摘要。

- Contract: `contracts/mission-contract.contract.yaml`
- **权威来源:** 外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## 摘要

> 一句话概括：做什么、为什么做、完成后的世界有什么不同。

{{tldr}}

---

## 执行意图

> 记录用户自然表达要开始做的依据。没有这个来源，不应创建任务（Mission）或驱动后续阶段。

- **已确认:** {{intake_confirmed}}
- **确认来源:** {{intake_confirmation_source}}
- **确认时间 / 轮次:** {{intake_confirmed_at_or_turn}}

---

## 意图边界 / 来源取证

> 本节说明哪些内容真正进入任务目标，哪些只是工作方式、流程约束或输入材料。目标、交付物和验收条件只能来自真实任务目标。

- **真实任务目标:** {{actual_task_goal}}
- **智能体（Agent）工作指令:** {{agent_instructions}}
- **流程约束:** {{process_constraints}}
- **输入材料（source_materials）:** 本 mission 引用的人提供资料清单——逐条指向项目根 `materials/` 目录下的具体文档（相对路径）；临时外部目录 / 链接先登记到 `materials/_sources.md`，再在此引用其中的条目。这是引用清单，不是自由文本说明。
  - `- materials/<文件名>：<这份资料提供什么前提>`
  - `- materials/<子目录>/<文件名>：<这份资料提供什么前提>`
- **讨论产物:** {{discussion_outputs}}
- **纠偏记录:** {{corrections}}
- **未进入目标的内容:** {{excluded_from_objective}}

---

## 目标

> 核心目标：描述完成后系统/产品的**状态变化**，不写实现方式。
> 好的目标是可以验证的——你能判断"有没有达到"。

{{objective}}

---

## 成功定义

> 本节定义最终以什么效果、什么交付物、什么证据判断任务达标。后续验证阶段和交付阶段以这里为验收口径。

- **期望效果**：{{desired_effect}}
- **主要交付物**：{{success_primary_deliverable}}
- **交付格式**：{{success_delivery_format}}
- **验证证据**：{{validation_evidence}}
- **非目标**：{{success_non_goals}}

---

## 用户故事

> 用户故事回答“谁需要什么、为什么有价值”。前置-动作-结果（GWT）不写在这里；它属于后面的验收条件。
> 每条用户故事必须能追溯到至少一条验收条件；下游追溯锚点使用验收场景 / 条件 ID，不再引入旧式验收缩写作为新的需求类型。
> 每条故事还必须提供产品故事上下文：用户、问题、场景、价值和成功指标；缺失时 产品定义 不应自行补脑。

| 故事编号 | 用户 | 问题 | 场景 | 目标 | 价值 | 成功指标 | 关联验收场景 / 条件 | 下游追溯锚点 |
|----------|------|------|------|------|------|----------|--------------------|--------------|
| US-01 | {{story_user_1}} | {{story_problem_1}} | {{story_scenario_1}} | {{user_goal_1}} | {{story_value_1}} | {{story_success_signal_1}} / {{story_success_target_1}} | {{acceptance_scenario_1}} | {{trace_anchor_1}} |
| US-02 | {{story_user_2}} | {{story_problem_2}} | {{story_scenario_2}} | {{user_goal_2}} | {{story_value_2}} | {{story_success_signal_2}} / {{story_success_target_2}} | {{acceptance_scenario_2}} | {{trace_anchor_2}} |

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

## 待探索问题

> 本节记录任务接入阶段（intake）已识别、但不应在该阶段解决的不确定点，供探索阶段（discovery）建立事实、影响、风险和后续问题。
> 待探索问题不得改写成任务目标、范围内事项、验收条件或业务对象模型结论；若它会阻断目标、交付物或验收口径确认，应回到任务接入决策，而不是交给探索阶段猜测。

### 分流方法

1. 先判断问题是否会影响目标、主要交付物、范围边界或验收口径。如果会，归为阻断型缺口，回到任务接入阶段（intake）决策，不写入本节。
2. 如果问题不阻断任务成立，但会影响探索阶段（discovery）的事实判断、风险判断、业务对象候选、系统边界、依赖或后续产品定义输入，归为探索型缺口，写入本节。
3. 每条探索型缺口必须说明“探索阶段需要查明什么”，同时写清停止边界：探索阶段只补事实、影响、风险和待决策问题，不替产品定义阶段（PRD）完成业务对象模型、系统用例、验收场景或方案设计。

### 约定模板

每行按以下句式落地：`因为 <来源> 暴露了 <问题>，它可能影响 <影响对象>；任务接入阶段只确认任务成立，探索阶段需要查明 <待查事实>；停止边界是 <不得在探索阶段替代完成的下游工作>`。

| 问题 | 来源 | 影响 | 交给探索阶段的原因 | 边界 / 停止条件 |
|------|------|------|----------------------|----------------|
| {{open_intent_question_1}} | {{open_intent_source_1}} | {{open_intent_impact_1}} | {{open_intent_discovery_reason_1}} | {{open_intent_boundary_1}} |

---

## 验收条件

> 每条验收条件用前置条件、触发动作、预期结果格式写，确保可测试、可验证。
> 验收条件是本任务的达标判断依据；下游执行、验证和交付证据统一追溯到验收场景 / 条件 ID。

**验收条件：{{acceptance_condition_1}}**
- **下游追溯锚点** {{trace_anchor_1}}
- **前置条件** {{precondition}}
- **触发动作** {{action}}
- **预期结果** {{expected_outcome}}

**验收条件：{{acceptance_condition_2}}**
- **下游追溯锚点** {{trace_anchor_2}}
- **前置条件** {{precondition}}
- **触发动作** {{action}}
- **预期结果** {{expected_outcome}}

---

## 执行治理级别

> 根据治理风险评估确定（见任务接入工作流第 3 阶段）。治理级别是 AI 自主推进授权边界，不是文件数或角色数量的简单映射。

- **级别:** `{{autonomy_level}}` <!-- 快速执行 / 专家确认 / 受控推进 -->
- **治理风险:** `{{governance_risk}}` <!-- low / medium / high -->
- **依据:** {{autonomy_rationale}}
- **可跳过阶段:** {{skippable_stages}} <!-- 来自 execution_governance.levels.<autonomy_level>.skippable_stages，可按任务覆盖 -->
- **专家通过即可继续的阶段:** {{reviewer_pass_sufficient}} <!-- 专家审查通过后可自动继续的阶段 -->

### 治理风险依据

| 类别 | 结论 | 依据 |
|------|------|------|
| 硬触发项 | {{hard_triggers}} | {{hard_trigger_rationale}} |
| 决策权 | {{decision_authority_risk}} | {{decision_authority_rationale}} |
| 可逆性 | {{reversibility_risk}} | {{reversibility_rationale}} |
| 影响面 | {{blast_radius_risk}} | {{blast_radius_rationale}} |
| 验证可靠性 | {{verification_reliability_risk}} | {{verification_reliability_rationale}} |
| 数据 / 权限 | {{data_permission_risk}} | {{data_permission_rationale}} |
| 外部依赖 | {{external_dependency_risk}} | {{external_dependency_rationale}} |
| 智能体（Agent）行动权 | {{agent_authority_risk}} | {{agent_authority_rationale}} |
| 不确定性 | {{uncertainty_risk}} | {{uncertainty_rationale}} |

### 规模信号

| 信号 | 结论 | 说明 |
|------|------|------|
| 变更范围 | {{change_surface_signal}} | {{change_surface_rationale}} |
| 用户角色 | {{user_roles_signal}} | {{user_roles_rationale}} |
| 模块跨度 | {{module_span_signal}} | {{module_span_rationale}} |

### 治理确认

- **判定规则:** {{governance_decision_rule}}
- **需要用户确认:** {{governance_confirmation_required}}
- **降级 / 移除检查点需审批:** {{governance_downgrade_approval}}

---

## 工作图

> 任务（Mission）是一次执行切片；工作图节点是长期工作对象。新任务必须引用本次推进的主节点。

- **主节点:** {{work_graph_primary_nodes}} <!-- 例如 [REQ-001] / [TASK-001, TASK-002] -->
- **相关节点:** {{work_graph_related_nodes}} <!-- 例如 [EPIC-001, 产品定义-001] -->
- **操作:** `{{work_graph_operation}}` <!-- advance_lane / implement_batch / review_batch / verify_batch / deliver_slice -->
- **来源泳道:** `{{work_graph_from_lane}}`
- **目标泳道:** `{{work_graph_to_lane}}`
- **看板来源:** `harness-runtime/harness/work-graph/boards/main.yaml`

---

## 必需检查点

> 哪些阶段需要暂停等待用户确认。默认来自 `harness.yaml` 的 `execution_governance.levels.<autonomy_level>.human_checkpoints`。旧 `A1` / `A2` / `A3` 只能按 `legacy_level_aliases` 归一化为新治理级别，不读取旧检查点配置。任务契约可按任务风险显式覆盖。

| 检查点 | 触发条件 | 预期产出 |
|-----------|---------|---------|
| prd | {{prd_checkpoint_condition}} | product/product-definition.md 审查通过 |
| solution | {{solution_checkpoint_condition}} | solution.md 审查通过 |
| interaction | {{interaction_checkpoint_condition}} | interaction.md 确认（默认需要；仅 API（API-only）/ 无界面时可跳过） |
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
> 必须与「成功定义」一致；如果后续阶段发现交付预期无法支撑验收，回到任务接入阶段或触发决策关口。

- **主要产出**：{{primary_deliverable}}
- **辅助产出**：{{secondary_deliverable}}
- **交付格式**：{{delivery_format}}

---

## 智能体工程

> 仅当 `agent_engineering.enabled=true` 且本任务涉及智能体（Agent）组件时填写。

<!-- 如不涉及智能体（Agent）组件，删除此节 -->

- **涉及智能体（Agent）组件**：{{agent_components}}
- **智能体（Agent）能力设计专家**：必须调用 `agent-capability-designer` + `agent-capability-reviewer` / 不涉及

---

## 审查摘要

> 由任务接入技能在审查循环结束后自动附加，记录各智能体（Agent）的审查结论。

<!-- 任务接入技能自动填写 -->
