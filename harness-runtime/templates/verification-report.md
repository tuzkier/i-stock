# 验证报告: {{mission_id}}

> **来源**：验证技能 → `harness-runtime/harness/artifacts/{{mission_id}}/verify/verification-report.md`
> **上游**：`harness-runtime/harness/missions/{{mission_id}}/mission-contract.md` | `harness-runtime/harness/artifacts/{{mission_id}}/breakdown/execution-brief.md`

**作者:** {{user_name}}
**日期:** {{date}}
**任务标识:** {{mission_id}}
**状态:** `draft` <!-- draft / ready / 阻塞 -->

---

## 控制契约

> 验证证据契约是验收证据索引。验收场景 / 条件标记为通过时必须引用具体证据；阻塞时必须写明原因、影响和下一步。

- Contract: contracts/verification-report.contract.yaml
- Control Contract: `contracts/verification-report.contract.yaml`
- 权威来源：外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

## 结论摘要（TL;DR）

> 一句话说明本次验证范围、结论、未验证项和剩余风险。

{{verification_summary}}

| 项 | 结论 |
|----|------|
| 本轮验证范围 | {{verified_scope_summary}} |
| 总体结论 | 通过 / 失败 / 阻塞 / 带风险通过 |
| 阻断项数量 | {{blocking_count}} |
| 未验证项数量 | {{unverified_count}} |
| 残留风险 | {{residual_risk_summary}} |

---

## 验证依据目录

> 列出本报告消费了哪些上游依据。不要只写文件名；要说明这些依据为验证提供了什么判断标准。

| 来源产物 | 已消费内容 | 验证用途 | 缺口处理 |
|----------|------------|----------|----------|
| `mission-contract.md` | 验收条件、成功标准、范围边界 | 定义预期结果和验收边界 | {{mission_contract_gap}} |
| `product-definition.md` | 系统责任、用例、场景、质量与运行约束、验收口径 | 建立行为验证和质量约束验证依据 | {{product_definition_gap}} |
| `use-case-model.md` | 业务用例、已确认系统用例、`SUC-xx-FLOW-xx` 流步骤、`SUC-xx-OP-xx` 系统操作、界面承载要求 | 建立用例路径和系统操作验证依据 | {{use_case_model_gap}} |
| `acceptance-scenarios.md` | 验收场景 / 条件、下游追溯锚点（场景 / 条件 ID） | 建立验收判定依据 | {{acceptance_scenarios_gap}} |
| `interaction.md` / `interaction-spec/` | 用户路径、界面状态、端到端验证义务 | 建立界面和用户旅程验证依据 | {{interaction_gap}} |
| `tech-design.md` | 系统操作到技术设计映射、验证策略、架构风险、接口和数据验证要求 | 建立验证层次和风险验证依据 | {{tech_design_gap}} |
| `execution-brief.md` | 系统操作覆盖、任务、授权范围、必需证据、停止条件 | 建立执行证据和验证边界 | {{execution_brief_gap}} |
| `code-review.md` | 发现项、修复状态、已接受风险 | 判断是否存在未关闭阻断风险 | {{code_review_gap}} |
| 项目测试约定 | 测试命令、运行环境、报告位置 | 选择命令和证据收集方式 | {{project_testing_gap}} |

---

## 验证目标

> 明确本报告验证哪些验收场景 / 条件、用例路径、质量与运行约束、风险和任务项，不扩大到未授权范围。

### 本轮包含

| 类型 | 编号 / 名称 | 来源 | 验证目标 |
|------|-------------|------|----------|
| 验收场景 / 条件 | {{acceptance_id}} | {{acceptance_source}} | {{acceptance_goal}} |
| 用例路径 | {{use_case_id}} | {{use_case_source}} | {{use_case_goal}} |
| 系统操作 | SUC-01-OP-01 | `use-case-model.md#系统行为描述` / `tech-design.md#系统操作到技术设计映射` | {{system_operation_verification_goal}} |
| 质量与运行约束 | {{constraint_id}} | {{constraint_source}} | {{constraint_goal}} |
| 风险验证项 | {{risk_id}} | {{risk_source}} | {{risk_goal}} |
| 任务项 | {{task_id}} | {{task_source}} | {{task_goal}} |

### 本轮不包含

| 范围 | 原因 | 对交付判断的影响 | 后续处理 |
|------|------|------------------|----------|
| {{out_of_scope_item}} | {{out_of_scope_reason}} | {{out_of_scope_impact}} | {{out_of_scope_next_step}} |

---

## 验证模型

> 验证模型说明“如何判断当前增量成立”。它先于命令运行存在，不能由测试结果倒推。

### 验收判定矩阵

| 验收场景 / 条件 | 来源 | 预期结果 | 实际观察方式 | 验证动作 | 命令证据 | 结果证据 | 失败判定 | 回流建议 |
|--------|------|----------|--------------|----------|----------|----------|----------|----------|
| {{acceptance_id}} | {{acceptance_source}} | {{expected_result}} | {{observable_result}} | {{verification_action}} | {{command_evidence_id}} | {{result_evidence_id}} | {{failure_condition}} | {{return_recommendation}} |

### 系统操作覆盖与自洽矩阵

| 系统操作 ID | 来源流步骤 | 预期读取 / 写入 / 状态迁移 | 预期错误 / 补偿 / 幂等 | 技术设计落点 | 执行任务 | 证据 | 结论 |
|-------------|------------|--------------------------|----------------------|--------------|----------|------|------|
| SUC-01-OP-01 | SUC-01-FLOW-01 | {{expected_read_write_state}} | {{expected_error_compensation_idempotency}} | {{tech_design_landing}} | AT-{{id}} | {{evidence_refs}} | 通过 / 失败 / 阻塞 |

### 验证层次选择

| 验证目标 | 选择层次 | 选择理由 | 不适用层次与理由 | 证据要求 |
|----------|----------|----------|------------------|----------|
| {{verification_target}} | 单元 / 集成 / 端到端 / 质量验证 / 人工验收 / 智能体（Agent）能力评估 | {{layer_rationale}} | {{not_applicable_layers}} | {{evidence_requirement}} |

### 风险与质量约束验证计划

| 编号 | 类型 | 来源 | 验证方法 | 通过标准 | 当前结论 | 残留风险 / 回流 |
|------|------|------|----------|----------|----------|----------------|
| {{risk_or_constraint_id}} | 风险 / 质量与运行约束 | {{risk_or_constraint_source}} | {{verification_method}} | {{pass_standard}} | 通过 / 失败 / 阻塞 / 不适用 | {{risk_or_constraint_follow_up}} |

---

## 验证方法

> 记录实际采用的命令、浏览器路径、接口调用、数据检查、文件比对或人工验收方法。命令证据只能证明验证动作运行过；结果证据才证明实际结果。

| 层级 | 命令 / 方法 | 工作目录 / 环境 | 证据编号 | 结果 | 覆盖目标 |
|------|-------------|-----------------|----------|------|----------|
| 单元 | `{{unit_command}}` | {{unit_cwd_or_env}} | CMD-UNIT-001 | 通过 / 失败 / 阻塞 | {{unit_coverage_target}} |
| 集成 | `{{integration_command}}` | {{integration_cwd_or_env}} | CMD-INT-001 | 通过 / 失败 / 阻塞 | {{integration_coverage_target}} |
| 端到端 | `{{e2e_command_or_path}}` | {{e2e_env}} | CMD-E2E-001 | 通过 / 失败 / 阻塞 / 不适用 | {{e2e_coverage_target}} |
| 质量验证 | `{{quality_runtime_command_or_method}}` | {{quality_runtime_env}} | CMD-QR-001 | 通过 / 失败 / 阻塞 / 不适用 | {{quality_runtime_target}} |
| 人工验收 | {{manual_method}} | {{manual_context}} | MANUAL-001 | 通过 / 失败 / 阻塞 / 不适用 | {{manual_target}} |

---

## 验证结果

> 每条验收场景 / 条件必须有预期结果、实际观察结果、命令证据和结果证据。不能用“测试通过”替代用户可观察结果。

| 验收场景 / 条件 | 预期结果 | 实际观察结果 | 命令证据 | 结果证据 | 结论 | 缺口 / 风险 |
|--------|----------|--------------|----------|----------|------|-------------|
| {{acceptance_id}} | {{expected_result}} | {{actual_result}} | {{command_evidence_id}} | {{result_evidence_id}} | 通过 / 失败 / 阻塞 / 不适用 | {{acceptance_gap_or_risk}} |

### 命令证据清单

| 证据编号 | 命令 / 方法 | 退出码 / 状态 | 产物路径 | 说明 |
|----------|-------------|---------------|----------|------|
| {{command_evidence_id}} | `{{command_or_method}}` | {{exit_code_or_status}} | {{command_artifact_path}} | {{command_summary}} |

### 结果证据清单

| 证据编号 | 关联验收场景 / 条件 | 证据类型 | 可观察结果 | 产物路径 | 结论 |
|----------|------------|----------|------------|----------|------|
| {{result_evidence_id}} | {{acceptance_id}} | 截图 / 视频 / 接口响应 / 命令输出 / 数据状态 / 文件差异 / 日志片段 | {{observable_result_summary}} | {{result_artifact_path}} | 通过 / 失败 / 阻塞 |

---

## 端到端验证结果

> 涉及界面或用户旅程时必须填写。引用 `e2e-status.json` 作为控制面事实；无界面范围时写“不适用”和原因；阻塞时引用决策门原因。

| 字段 | 值 |
|------|----|
| 端到端状态产物 | `harness-runtime/harness/traces/{{mission_id}}/e2e/e2e-status.json` |
| 状态 | 通过 / 警告 / 失败 / 阻塞 / 不适用 |
| 网页报告（HTML） | {{e2e_html_report}} |
| 追踪 / 视频 / 截图 | {{e2e_artifacts}} |
| 不适用 / 阻塞 / 决策门 | {{e2e_na_blocked_or_decision_gate}} |

| 验收场景 / 条件 | 用户路径 / 替代证据 | 结果证据 | 结论 | 缺口 / 风险 |
|--------|--------------------|----------|------|-------------|
| {{acceptance_id}} | {{e2e_scenario_or_alternative}} | {{e2e_result_evidence_id}} | 通过 / 失败 / 阻塞 / 不适用 | {{e2e_gap_or_risk}} |

{{e2e_result}}

---

## 风险与质量约束验证

> 风险和质量与运行约束必须有验证、接受、阻断或回流结论。不要只复制上游风险列表。

| 编号 | 类型 | 预期 / 约束 | 验证证据 | 实际结果 | 结论 | 后续 |
|------|------|-------------|----------|----------|------|------|
| {{risk_or_constraint_id}} | 风险 / 性能 / 安全 / 兼容性 / 可观测性 / 可维护性 | {{expected_constraint_or_risk_resolution}} | {{evidence_refs}} | {{actual_constraint_or_risk_result}} | 已验证 / 已接受 / 阻塞 / 回流 | {{risk_next_step}} |

---

## 未覆盖范围

| 范围 | 原因 | 影响 | 下一步 |
|------|------|------|--------|
| {{gap_scope}} | {{gap_reason}} | {{gap_impact}} | {{gap_next_step}} |

---

## 遗留问题

| 问题 | 严重级别 | 状态 | 处理方式 |
|------|----------|------|----------|
| {{issue}} | 高 / 中 / 低 | open / accepted / 延后 | {{handling}} |

---

## 验证评价摘要

> 这是面向交付阶段的判断摘要。只基于本报告证据，不重新解释交付范围。

| 评价项 | 结论 | 证据 / 理由 |
|--------|------|-------------|
| 验收场景 / 条件是否逐项验证 | 是 / 否 | {{acceptance_evaluation_reason}} |
| 命令证据是否完整 | 是 / 否 | {{command_evidence_reason}} |
| 结果证据是否完整 | 是 / 否 | {{result_evidence_reason}} |
| 验证层次是否匹配风险 | 是 / 否 | {{layer_evaluation_reason}} |
| 质量与运行约束是否处理 | 是 / 否 / 不适用 | {{quality_runtime_evaluation_reason}} |
| 高优先级风险是否闭环 | 是 / 否 / 不适用 | {{risk_evaluation_reason}} |
| 是否可以进入交付 | 可以 / 不可以 / 需用户接受风险 | {{delivery_readiness_reason}} |
