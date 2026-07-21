# 技术设计: {{mission_id}}

> **来源**：技术分析阶段 → `harness-runtime/harness/artifacts/{{mission_id}}/technical-analysis/tech-design.md`
> **参考方法论**：C4 模型、架构决策记录、领域驱动设计、Arc42、OpenAPI 3.x、数据库规范化、事件溯源、命令查询职责分离
> **上游**：`solution.md` | `product/product-definition.md` | `product/use-case-model.md` | `product/acceptance-scenarios.md` | `product/product-domain-model.md` | `interaction.md`（如适用） | `interaction-spec/use-case-realization.md`（如适用） | `interaction-spec/surface-model.md`（如适用） | `interaction-spec/interaction-contract.md`（如适用） | `mission-contract.md`

**作者:** {{user_name}}
**日期:** {{date}}
**任务 ID:** {{mission_id}}
**状态:** `draft` <!-- 草稿 / 审查中 / 已批准 -->

---

## 总体说明

> 说明本次技术设计如何承载上游方案路线、用户可观察行为、质量与运行约束和关键风险。
> 技术设计必须支撑正式验收，不得只覆盖演示路径或单一正常路径；如果分阶段交付，说明当前阶段的生产可用边界。

{{tech_design_overview}}

**设计范围：** {{design_scope}}
**承载方式摘要：** {{realization_strategy_summary}}

---

## 上游工程义务

> 从任务契约、产品定义、交互产物和方案中提取必须被工程设计承接的义务。
> 如果某条义务没有工程落点，必须写明回流到产品定义、交互、方案或依赖影响分析。

| 来源 | 上游义务 | 工程含义 | 设计落点 | 处理状态 |
|-----|---------|---------|---------|---------|
| {{upstream_ref_1}} | {{obligation_1}} | {{engineering_meaning_1}} | {{design_landing_1}} | 已承接 / 需回流 |

**输入合格判断：** {{input_quality_judgment}}
**需要回流的问题：** {{return_needed_items}}

---

## 系统操作到技术设计映射

> 本节是技术分析承接 PRD 自洽性的核心检查。每个 `SUC-xx-OP-xx` 必须能追溯到来源 `SUC-xx-FLOW-xx`，并落到接口 / 命令 / 事件 / 模块、数据读写、状态迁移、错误处理、原子性 / 并发 / 幂等和验证证据。若某个系统操作没有工程承载，不能继续拆解，必须回流技术设计、方案或产品定义。

| 系统操作 ID | 来源流步骤 | 技术承载（接口 / 命令 / 事件 / 模块） | 读取如何实现 | 写入 / 状态迁移如何实现 | 条件 / 错误码 | 原子性 / 并发 / 幂等 | 验证证据 |
|-------------|------------|--------------------------------------|--------------|------------------------|---------------|---------------------|----------|
| SUC-01-OP-01 | SUC-01-FLOW-01 | {{technical_carrier}} | {{read_design}} | {{write_state_design}} | {{condition_error_design}} | {{atomicity_concurrency_idempotency}} | {{verification_evidence_plan}} |

| 覆盖检查 | 结论 | 缺口处理 |
|----------|------|----------|
| 所有 `SUC-xx-OP-xx` 是否都有技术承载 | 是 / 否 | {{operation_coverage_gap_handling}} |
| 每个读写对象和状态迁移是否能追溯到产品领域模型 | 是 / 否 | {{domain_trace_gap_handling}} |
| 主成功流、备选流、异常流是否都有错误 / 补偿 / 幂等设计 | 是 / 否 | {{flow_variant_gap_handling}} |

---

## 原型承载与遵从（如本 mission 有 interaction 原型产物）

> 仅当本 mission 跑过 interaction 阶段、存在 `behavior-graph.yaml`（原型契约 SSOT）与 `surface-model.md`（界面边界 catalog）时填写；非 UI / 未跑 interaction 的 mission 无 behavior-graph，本节与覆盖率门自动跳过。
> 原型契约里每个 `SURF-xxx`（界面边界）与其 `PS-<surf>-<state>`（page_state，含加载 / 空态 / 错误 / 权限 / 键盘焦点等结局态）是可追溯 ref。技术设计对原型决策【要么承载、要么显式改写并经决策门 + 登记豁免，禁止静默漂移 / 自由重设计界面】。
> 本表与“系统操作到技术设计映射”对称：那里把 `SUC-xx-OP-xx` 落到技术承载，这里把 `SURF-/PS-` 界面边界与状态结局态落到 tech-design 的模块 / 接口 / 组件。每个 mission `SURF` 必须被某决策 / 模块 `traces_to` 承载，否则下游覆盖率门报 `SURFACE_NOT_CARRIED`（FAIL，mission-local 分母）。

| SURF / PS id | 原型决策（界面边界 / 状态 / 流程） | tech-design 落点（模块 / 接口 / 组件） | traces_to |
|--------------|-----------------------------------|----------------------------------------|-----------|
| SURF-{{id}} | {{surface_boundary_decision}} | {{surface_tech_landing}} | SURF-{{id}} |
| PS-{{surf}}-{{state}} | {{pagestate_outcome_decision}} | {{pagestate_tech_landing}} | PS-{{surf}}-{{state}} |

| 覆盖检查 | 结论 | 缺口处理 |
|----------|------|----------|
| 每个 mission `SURF` 是否都被某模块 / 接口 / 组件承载（其界面边界与 page_state 的加载 / 空 / 错误 / 权限 / 键盘焦点等结局态） | 是 / 否 | {{surface_coverage_gap_handling}} |
| 对原型决策的任何改写是否已经决策门并登记豁免理由 | 是 / 否 / 无改写 | {{prototype_rewrite_gap_handling}} |

> 改写原型界面边界 / 状态结局态：必须先经决策门（Decision Gate），并在原型契约 `prototype_coverage_exemptions: [{id, reason}]` 登记被改写 / N/A 的 `SURF-/PS-` id 与理由（缺理由报 `PROTOTYPE_EXEMPTION_NO_REASON`）；不得在本阶段静默重设计界面。

---

## 方案路线承接

> 技术分析只在已选方案路线内落成可实施设计，不得重新选择架构路线。若发现方案路线不可承载，必须回流方案阶段或决策门，而不是在本阶段静默换路线。

| 方案决策 / 禁止路径 | 工程设计承接 | 不得改变的边界 | 技术分析处理 |
|--------------------|--------------|----------------|--------------|
| DEC-{{id}} {{solution_decision}} | {{engineering_realization}} | {{non_reselectable_boundary}} | 已承接 / 需回流 |
| 禁止路径：{{forbidden_path}} | {{avoidance_design}} | {{forbidden_boundary}} | 已规避 / 需回流 |

| 方案风险处理计划 | 本阶段设计落点 | 验证或接受证据 | 回流条件 |
|------------------|----------------|----------------|----------|
| {{solution_risk_treatment}} | {{risk_design_landing}} | {{risk_evidence_plan}} | {{risk_return_condition}} |

---

## 控制契约

> 技术指导契约将方案决策转成模块、接口、数据和验证边界，供拆解、执行、代码审查和验证消费。

- 控制契约（程序识别标记：Control Contract: `contracts/tech-design.contract.yaml`）
- 权威来源：外部 YAML 是程序化权威来源；Markdown 只作解释说明。


---

## 模块划分

> 每个模块说明职责、禁止职责、依赖方向和涉及文件。职责是“由谁承担什么工程义务”，不是实现细节。
> 每个模块必须可追溯到方案决策、`SUC-xx-OP-xx` 系统操作、系统用例、验收场景 / 条件、业务规则或质量与运行约束。

| 模块 | 职责 | 禁止职责 | 追溯来源 | 涉及文件 / 路径 |
|-----|------|---------|---------|----------------|
| {{module_1}} | {{module_1_responsibility}} | {{module_1_forbidden_responsibility}} | {{trace_ref_1}} | {{module_1_files}} |
| {{module_2}} | {{module_2_responsibility}} | {{module_2_forbidden_responsibility}} | {{trace_ref_2}} | {{module_2_files}} |

### 模块 1: {{module_1_name}}

**职责：** {{module_1_desc}}

**关键约束：**
- {{module_1_constraint_1}}
- {{module_1_constraint_2}}

**依赖方向：** {{module_1_dependency_direction}}

**涉及文件：**
| 文件 | 变更类型 | 说明 |
|-----|---------|------|
| {{file_1}} | 新增/修改/删除 | {{file_1_desc}} |

---

## 关键接口定义

> 只定义接口边界，不写内部实现。接口必须让调用方、实现方和测试方不需要猜测。

### 接口 1: {{interface_1_name}}

**调用方：** {{interface_1_caller}}
**所属模块：** {{interface_1_module}}
**变更类型：** 新增 / 修改 / 替换 / 删除

**变更前：**
```text
{{interface_1_before}}
```

**变更后：**
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
| 错误码 / 错误类型 | 触发条件 | 调用方可观察行为 | 处理方式 |
|-------------------|---------|------------------|---------|
| {{error_1}} | {{condition_1}} | {{observable_behavior_1}} | {{handling_1}} |

**兼容策略：** {{compatibility_strategy}}
**迁移路径：** {{interface_migration_path}}

---

## 数据模型 / 状态流转

> 如果涉及数据结构、文件格式、状态机、权限状态、缓存或外部存储，在此描述；不涉及时必须写明理由。

### 数据模型变更

```
{{data_model_changes}}
```

**迁移策略：** {{migration_strategy}}
**回滚策略：** {{rollback_strategy}}
**不变量校验：** {{invariant_checks}}

### 状态流转

```
{{state: initial}} --[{{trigger}}]--> {{state: next}}
```

**异常路径：** {{state_exception_paths}}
**幂等 / 并发 / 补偿设计：** {{idempotency_concurrency_compensation}}

---

## 实施策略

> 说明先做什么、后做什么、为什么这个顺序。这里给实施流和停止条件，不生成原子任务队列。
> 实施策略应按上游义务准确落地，而不是选择最省事路径：所有验收场景 / 条件、质量与运行约束、错误路径、兼容性和回归验证都要有明确落点。

### 实现顺序

1. **{{impl_step_1}}**
 - 理由：{{impl_step_1_rationale}}
 - 产出：{{impl_step_1_output}}
 - 停止条件：{{impl_step_1_stop_condition}}

2. **{{impl_step_2}}**
 - 理由：{{impl_step_2_rationale}}
 - 产出：{{impl_step_2_output}}
 - 停止条件：{{impl_step_2_stop_condition}}

3. **{{impl_step_3}}**
 - 理由：{{impl_step_3_rationale}}
 - 产出：{{impl_step_3_output}}
 - 停止条件：{{impl_step_3_stop_condition}}

### 验证策略

> 验证策略要说明证明什么行为、约束或风险结论，不能只列测试类型。

| 验证对象 | 验证层次 | 证明内容 | 关键场景 | 证据形式 |
|---------|---------|---------|---------|---------|
| {{verification_target_1}} | 单元 / 集成 / 端到端 / 迁移演练 / 人工验收 | {{proof_1}} | {{test_scenario_1}} | {{evidence_1}} |

### 生产就绪要求

| 要求 | 落地设计 | 验证方式 |
|-----|---------|---------|
| 错误处理/异常路径 | {{error_handling_design}} | {{error_handling_verification}} |
| 兼容性/迁移 | {{compatibility_design}} | {{compatibility_verification}} |
| 可观测性/日志 | {{observability_design}} | {{observability_verification}} |
| 回滚/降级 | {{rollback_design}} | {{rollback_verification}} |

---

## 风险验证与回流条件

> 关键架构风险必须被验证、接受、阻断或回流。不能只写“注意风险”。

| 风险 | 来源 | 处理方式 | 验证 / 接受证据 | 回流条件 |
|-----|------|---------|---------------|---------|
| {{risk_1}} | {{risk_source_1}} | 验证 / 接受 / 阻断 / 回流 | {{risk_evidence_1}} | {{risk_return_condition_1}} |

---

## 对现有系统的影响

> 仅既有项目填写。说明对哪些现有模块有影响，影响的性质（接口变更/行为变更/数据变更）。

| 现有模块 | 影响类型 | 描述 | 向后兼容性 | 回归面 |
|--------|---------|------|------------|-------|
| {{existing_module_1}} | {{impact_type_1}} | {{impact_desc_1}} | 兼容/破坏性变更 | {{regression_surface_1}} |

**破坏性变更处理：** {{breaking_change_strategy}}

---

## Agent 实现

> 仅当 `agent_engineering.enabled=true` 且 solution.md 存在 `## Agent 架构` 段落时填写；由 `agent-capability-designer` 产出，`agent-capability-reviewer` 审查。

<!-- 如不涉及 Agent 组件，删除此节 -->

### Agent：{{agent_name}}

### 触发与责任边界

| 项 | 内容 |
|---|---|
| 能力要求来源 | {{agent_requirement_refs}} |
| 任务对象 | {{agent_task_object}} |
| 非目标 | {{agent_non_goals}} |
| 触发信号 | {{activation_signal}} |
| 停止条件 | {{stop_conditions}} |
| 人类确认点 | {{human_confirmation_points}} |

### 六种工作权

| 工作权 | 默认行为 | 证据来源 | 允许判断 / 行动 | 必须停止或上报 | 责任输出 |
|--------|----------|----------|------------------|----------------|----------|
| 感知权 | {{perception_default}} | {{perception_evidence}} | {{perception_allowed}} | {{perception_stop}} | {{perception_accountability}} |
| 解释权 | {{interpretation_default}} | {{interpretation_evidence}} | {{interpretation_allowed}} | {{interpretation_stop}} | {{interpretation_accountability}} |
| 判断权 | {{judgment_default}} | {{judgment_evidence}} | {{judgment_allowed}} | {{judgment_stop}} | {{judgment_accountability}} |
| 行动权 | {{action_default}} | {{action_evidence}} | {{action_allowed}} | {{action_stop}} | {{action_accountability}} |
| 边界权 | {{boundary_default}} | {{boundary_evidence}} | {{boundary_allowed}} | {{boundary_stop}} | {{boundary_accountability}} |
| 责任权 | {{accountability_default}} | {{accountability_evidence}} | {{accountability_allowed}} | {{accountability_stop}} | {{accountability_output}} |

### 承载物分配

| 承载物 | 设计内容 | 设计力度 | 位置 / 路径 | 失败时表现 |
|--------|----------|----------|-------------|------------|
| Agent definition | {{agent_definition_design}} | knowledge / preference / enforcement | {{agent_definition_path}} | {{agent_definition_failure}} |
| Skill | {{skill_design}} | knowledge / preference / enforcement | {{skill_path}} | {{skill_failure}} |
| Tool / MCP | {{tool_mcp_design}} | knowledge / preference / enforcement | {{tool_mcp_path}} | {{tool_mcp_failure}} |
| Policy / hook | {{policy_hook_design}} | enforcement | {{policy_hook_path}} | {{policy_hook_failure}} |
| Runtime | {{runtime_design}} | enforcement | {{runtime_config_ref}} | {{runtime_failure}} |
| Eval | {{eval_design_summary}} | evidence | {{eval_path}} | {{eval_failure}} |
| Worker | {{worker_design}} | knowledge / preference / enforcement | {{worker_ref}} | {{worker_failure}} |

### 制度层约束

| 约束 | 机械执行位置 | 拦截 / 降级行为 | 失败关闭策略 | 审计证据 |
|------|--------------|----------------|--------------|----------|
| {{enforcement_rule}} | {{enforcement_location}} | {{block_or_degrade_behavior}} | {{fail_closed_strategy}} | {{audit_evidence}} |

### Runtime 与可观测性

| 项 | 内容 |
|---|---|
| 激活条件 | {{runtime_activation}} |
| 禁用条件 | {{runtime_disable}} |
| 降级路径 | {{runtime_fallback}} |
| 记录字段 | {{observability_fields}} |
| 证据消费者 | {{evidence_consumers}} |
| 失败定位方式 | {{failure_diagnosis_path}} |

### Eval 设计

| 场景类别 | 输入 | 预期行为 | 禁止行为 | 通过阈值 | 失败诊断 |
|----------|------|----------|----------|----------|----------|
| 正常路径 | {{normal_input}} | {{normal_expected_behavior}} | {{normal_forbidden_behavior}} | {{normal_threshold}} | {{normal_failure_diagnosis}} |
| 边界场景 | {{boundary_input}} | {{boundary_expected_behavior}} | {{boundary_forbidden_behavior}} | {{boundary_threshold}} | {{boundary_failure_diagnosis}} |
| 对抗场景 | {{adversarial_input}} | {{adversarial_expected_behavior}} | {{adversarial_forbidden_behavior}} | {{adversarial_threshold}} | {{adversarial_failure_diagnosis}} |
| 歧义场景 | {{ambiguous_input}} | {{ambiguous_expected_behavior}} | {{ambiguous_forbidden_behavior}} | {{ambiguous_threshold}} | {{ambiguous_failure_diagnosis}} |

### 回滚 / 降级策略

| 触发 | 处理 | 用户可见结果 | 后续修复 |
|------|------|--------------|----------|
| {{rollback_trigger}} | {{rollback_action}} | {{user_visible_result}} | {{repair_followup}} |

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
