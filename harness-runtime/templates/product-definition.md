# 产品定义：{{project_name}}

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/{{mission_id}}/product/product-definition.md`
> **上游 / 专业输入**：`mission-contract.md` | `product-evidence.md` | `product-domain-model.md` | `product/business-object-analysis.md` | `product/use-case-model.md` | `product/acceptance-scenarios.md` | `product/scope-strategy.md`

**任务编号（mission-id）：** {{mission_id}}
**状态：** `draft`

---

## 控制契约

- 控制契约（程序识别标记：Control Contract: `contracts/prd.contract.yaml`）
- 权威来源：外部 YAML 是程序化权威来源；本文件提供主产品定义正文。

---

## 业务定义

**业务问题：** {{problem_statement}}

**业务目标：** {{business_objective}}

**成功信号：** {{success_signals}}

**任务契约匹配度：** {{mission_fit}}

---

## 问题诊断

| 业务方表述 | 底层问题 | 受影响用户 / 场景 | 价值假设 | 证据 |
|------------|----------|-------------------|----------|------|
| {{requested_solution}} | {{underlying_problem}} | {{user_scenario}} | {{value_hypothesis}} | {{evidence_ref}} |

---

## 用户与场景

| 场景 ID | 用户 / 角色 | 场景 | 当前痛点 | 目标行为 |
|-------------|-------------|------|----------|----------|
| SCN-01 | {{user_role}} | {{scenario}} | {{pain}} | {{target_behavior}} |

---

## 当前流程摘要

{{current_workflow_summary}}

---

## 系统边界

| 边界项 | 本次责任 | 说明 | 证据 / 来源 |
|--------|----------|------|-------------|
| 目标系统 / 产品能力 | {{target_system_or_capability}} | {{system_boundary_description}} | {{evidence_ref}} |
| 人工活动 | {{manual_activity}} | {{manual_responsibility}} | {{evidence_ref}} |
| 外部系统 / 第三方 | {{external_system}} | {{external_responsibility}} | {{evidence_ref}} |
| 不在本轮范围 | {{out_of_scope_responsibility}} | {{reason}} | {{trace_ref}} |
| 待澄清系统责任 | {{unclear_system_responsibility}} | {{why_decision_needed}} | {{owner_or_decision_ref}} |

---

## 业务用例模型

### BUC-01: {{business_use_case_title}}

**业务参与者：** {{business_actor}}

**业务目标：** {{business_goal}}

**触发条件：** {{business_trigger}}

**前置业务状态：** {{business_precondition}}

**主业务流程：**
1. {{business_basic_flow_step_1}}
2. {{business_basic_flow_step_2}}
3. {{business_basic_flow_step_3}}

**扩展 / 异常业务路径：**
- {{business_alternative_or_exception_flow}}

**后置业务结果：** {{business_postcondition}}

**关联业务对象 / 规则：** {{business_object_rule_refs}}

---

## 系统用例模型

> 系统用例只记录已确认的目标系统责任。未确认的流程、权限、自动化程度或系统边界不得作为系统用例进入本节。

### SUC-01: {{system_use_case_title}}

**参与者：** {{system_actor}}

**目标：** {{actor_goal_with_system}}

**覆盖业务用例：** {{business_use_case_refs}}

**前置条件：** {{system_preconditions}}

**触发：** {{system_trigger}}

**主成功流：**
1. {{system_basic_flow_step_1}}
2. {{system_basic_flow_step_2}}
3. {{system_basic_flow_step_3}}

**备选流：**
- {{system_alternative_flow}}

**异常流：**
- {{system_exception_flow}}

**后置结果：** {{system_postconditions}}

**涉及对象 / 状态 / 规则：** {{object_state_rule_refs}}

**关联系统操作：** {{system_operation_refs}}

**关联验收场景 / 条件：** {{acceptance_refs}}

**是否需要 UI 承载：** {{ui_required_yes_no_and_reason}}

---

## 范围与取舍

| 类型 | 内容 | 理由 | 追溯 |
|------|------|------|------|
| 范围内 | {{in_scope}} | {{rationale}} | {{trace_ref}} |
| 范围外 | {{out_scope}} | {{rationale}} | {{trace_ref}} |

---

## 证据摘要

| 证据类型 | 来源 | 对产品判断的影响 | 降级情况 |
|---------------|--------|-------------------------|-------------|
| 项目知识 | {{knowledge_ref}} | {{impact}} | {{degradation_or_none}} |
| 规格 | {{spec_ref}} | {{impact}} | {{degradation_or_none}} |
| Graphify | {{graphify_ref}} | {{impact}} | {{degradation_or_none}} |

---

## 产品领域摘要

### 核心对象

| 对象 ID | 对象 | 说明 |
|-----------|------|------|
| OBJ-01 | {{object}} | {{description}} |

### 状态与权限摘要

{{state_permission_summary}}

---

## 产品规则

| Rule-ID | 规则 | 验收方式 | 追溯 |
|---------|------|----------|------|
| RULE-01 | {{rule}} | {{verification}} | {{trace_ref}} |

---

## 系统责任与可观察行为

> 本节不是功能清单。这里只把已确认系统用例中目标系统必须承担的责任，整理成下游可消费的系统行为描述。不要把编号当作 PRD 主表达；编号只用于追溯、引用和验收。系统操作必须是 `SUC` 的从属编号，例如 `SUC-01-OP-01`；它不能成为独立于系统用例的第二套需求编号。交互、方案、技术分析、拆解和验证阶段只能校验、承载和细化这些行为；若需要新增或修改系统行为，必须回流产品定义或决策门。

### 系统行为描述

| 系统操作 ID | 来源流步骤 | 触发者 / 触发事件 | 目标系统操作 | 读取 / 写入 / 状态迁移 | 规则 / 守卫 | 用户 / 业务可观察结果 | 异常 / 失败处理 | 下游不可改变 |
|-------------|------------|-------------------|--------------|----------------------|-------------|------------------------|----------------|--------------|
| SUC-01-OP-01 | SUC-01-FLOW-01 | {{actor_or_event}} | {{system_operation}} | {{read_write_state_transition_refs}} | {{rule_guard_refs}} | {{observable_result}} | {{failure_handling}} | {{semantics_to_preserve}} |

### {{system_responsibility_title}}

**来源系统用例：** {{system_use_case_refs}}

**关联系统操作：** {{system_operation_refs}}

**目标系统责任：** {{target_system_responsibility}}

**用户 / 业务可观察结果：** {{observable_result}}

**关联验收场景 / 条件：** {{acceptance_refs}}

**关联业务对象 / 规则：** {{object_rule_refs}}

**追溯锚点（可选）：** {{requirement_anchor}}

**优先级：** `{{priority}}`

---

## 质量与运行约束

> 只记录会影响用户可观察结果、业务规则或后续方案路线的质量约束。不要为了填空罗列泛化的“性能好、体验好、安全好”。

| 约束项 | 类别 | 绑定用例 / 路径 | 可观察指标或判定 | 测量 / 验证方式 | 不满足影响 |
|--------|------|----------------|------------------|----------------|------------|
| {{quality_constraint}} | {{category}} | {{system_use_case_or_flow_ref}} | {{observable_metric_or_decision_rule}} | {{measurement}} | {{impact_if_missed}} |

---

## 界面承载要求

> 本节定义原型设计必须承载的用户任务、信息、输入、状态和反馈，不决定页面拆分、布局、组件或导航方案。

| 承载 ID | 关联系统用例 | 用户任务 | 必需展示信息 | 必需输入 / 操作 | 状态 / 错误 / 权限 / 反馈要求 |
|------------|--------------|----------|--------------|-----------------|------------------------------|
| UIC-01 | SUC-01 | {{user_task}} | {{required_information}} | {{required_input_or_action}} | {{state_error_permission_feedback}} |

---

## Agent 能力要求

> 仅当 `agent_engineering.enabled=true` 且存在 Agent 组件时填写；否则删除本节。

| 能力要求 ID | 组件 | 工作权 | 行为要求 | 评估标准 | 追溯 |
|--------|------|--------|----------|-----------|------|
| AGENT-REQ-01 | {{component}} | {{work_rights}} | {{behaviour_requirement}} | {{eval_criteria}} | {{trace_ref}} |

---

## 验证与发布闭环

| 验证阶段 | 验证内容 | 证据 | 成功 / 失败判定 |
|----------|----------|------|-----------------|
| 上线前 | {{pre_launch_check}} | {{evidence}} | {{decision_rule}} |
| 上线后 | {{post_launch_metric}} | {{evidence}} | {{decision_rule}} |

---

## 方案阶段输入

> 本节把产品定义中会影响实现路线的内容集中交给方案阶段。这里只说明产品语义、业务边界、约束和风险，不选择技术路线，不预设模块、接口、存储或部署方式。

| 方案需要判断的输入 | 来源 | 对路线选择的影响 | 不能改变 / 不能假设 | 不清楚时怎么处理 |
|--------------------|------|------------------|----------------------|------------------|
| 核心系统用例 | {{system_use_case_refs}} | {{solution_impact_from_use_cases}} | {{use_case_semantics_to_preserve}} | {{use_case_gap_handling}} |
| 系统操作 | {{system_operation_refs}} | {{solution_impact_from_system_operations}} | {{system_operation_semantics_to_preserve}} | {{system_operation_gap_handling}} |
| 关键验收场景 / 条件 | {{acceptance_refs}} | {{solution_impact_from_acceptance}} | {{acceptance_semantics_to_preserve}} | {{acceptance_gap_handling}} |
| 质量与运行约束 | {{quality_constraint_refs}} | {{solution_impact_from_quality}} | {{quality_boundary_to_preserve}} | {{quality_gap_handling}} |
| 领域边界与规则 | {{domain_refs}} | {{solution_impact_from_domain}} | {{domain_boundary_to_preserve}} | {{domain_gap_handling}} |
| 范围取舍 | {{scope_refs}} | {{solution_impact_from_scope}} | {{scope_boundary_to_preserve}} | {{scope_gap_handling}} |
| 外部系统 / 依赖 | {{dependency_refs}} | {{solution_impact_from_dependencies}} | {{dependency_assumptions_to_avoid}} | {{dependency_gap_handling}} |
| 高优先级风险 | {{risk_refs}} | {{solution_impact_from_risks}} | {{risk_assumptions_to_avoid}} | {{risk_gap_handling}} |
| 界面承载要求（如适用） | {{ui_carrier_refs}} | {{solution_impact_from_ui}} | {{ui_semantics_to_preserve}} | {{ui_gap_handling}} |
| Agent 能力要求（如适用） | {{agent_requirement_refs}} | {{solution_impact_from_agent_requirements}} | {{agent_product_boundary_to_preserve}} | {{agent_gap_handling}} |

### 会阻断方案路线选择的问题

> 只记录会影响方案路线的问题。若问题会改变用户可观察行为、系统边界、质量与运行约束、领域规则、范围取舍或风险处理方式，PRD 阶段不能放行到方案阶段。

| 问题 | 影响的产品语义 | 为什么会影响方案路线 | 当前处理 |
|------|----------------|----------------------|----------|
| {{solution_blocking_question_1}} | {{affected_product_semantics_1}} | {{why_blocks_solution_route_1}} | 回流任务契约 / 回流探索 / 需要用户决策 / 已明确不阻断，原因：{{reason_1}} |

---

## 追溯矩阵

| 任务故事 / 验收场景 | 业务用例 | 系统用例 | 业务规则 / 质量约束 | 系统责任 | 界面承载 | 规格 / 项目知识 | 证据 |
|----------------------|----------|----------|---------------------|----------|----------|------------------|----------|
| US-01 / SCN-01 | BUC-01 | SUC-01 | RULE-01 / {{quality_constraint_ref}} | {{system_responsibility_ref}} | UIC-01 | {{spec_or_knowledge_ref}} | {{evidence_ref}} |

---

## 原型 / 交互交接

| 交接项 | 是否必需 | 来源 | 原型设计必须处理 | 不由 PRD 决定 |
|--------------|----------|--------|------------------|--------------|
| UI 承载用例 | 必需 / 跳过（仅 API） | SUC-01 / UIC-01 | {{task_info_state_feedback}} | 页面拆分、布局、组件、导航 |
| 业务对象与状态 | 必需 | OBJ-01 / STM-01 | {{object_state_visibility}} | 数据库表、接口、存储方案 |
| 异常 / 权限 / 空态 | 必需 | SUC-01 异常流 | {{error_permission_empty_state}} | 具体视觉样式 |

---

## 待澄清问题

- {{open_question}}
