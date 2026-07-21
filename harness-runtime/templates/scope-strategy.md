# 范围策略：{{project_name}}

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/{{mission_id}}/product/scope-strategy.md`
> **用途**：基于任务契约、用例模型、验收场景、业务对象和风险，判断范围内、范围外、延后和需要决策的事项。本文不选择技术路线，不拆执行任务。

**任务编号（mission-id）：** {{mission_id}}
**状态：** `draft`

---

## 模板约定

- 范围项编号固定使用 `SCOPE-xx`，范围决策使用 `IN` / `OUT` / `LATER` / `DECISION_NEEDED`。
- 每个范围判断必须引用业务用例、系统用例、界面承载要求、验收场景 / 条件、业务规则、风险或任务契约。
- 范围取舍必须说明业务价值、风险、证据、任务契约追溯、验证影响和对方案路线的影响。
- 不得默认压缩范围；不得为了实现便利把核心业务闭环切断。
- 不适用项必须写 `不适用：原因...`，证据不足项必须写 `待澄清：原因...`。

---

## 使用者与使用时机

| 使用者 | 使用时机 | 使用方式 | 不做什么 |
|--------|----------|----------|----------|
| `product-scope-strategist` | PRD 第 1 步生成 `product/scope-strategy.md` 时 | 按本模板判断授权边界、范围决策、用例闭环、风险依赖、阶段化和方案路线约束 | 不替方案阶段选择技术路线 |
| `senior-product-expert` | 综合产品定义包时 | 把范围内 / 外 / 延后 / 待决策项、判断理由和风险吸收到主产品定义 | 不默认压缩范围 |
| 方案 / 交互 / 技术分析 / 拆解阶段 | PRD 通过后消费范围边界时 | 读取产出的 `product/scope-strategy.md` 或主产品定义中的范围章节 | 不直接使用模板重新裁剪范围 |
| `product-definition-reviewer` / harness-lint | PRD 审查和框架一致性检查时 | 检查授权来源、用例闭环、范围理由、依赖风险和下游边界是否完整 | 不替范围专家做取舍 |

---

## 判断方法

| 步骤 | 方法 | 产出位置 | 阻断条件 |
|------|------|----------|----------|
| 1 | 从任务契约识别授权目标、成功定义、非目标、约束和验证口径 | 授权边界 | 授权边界不清 |
| 2 | 检查业务用例、系统用例、界面承载要求和验收场景是否能形成闭环 | 用例范围闭环 | 核心用例被切断 |
| 3 | 按业务价值、风险、规则完整性、验证闭环和依赖判断范围优先级 | 范围决策表 | 判断会改变用户可见结果但缺少决策 |
| 4 | 识别范围膨胀、范围收缩、隐含优化和未授权需求 | 范围风险 | 未授权需求进入范围 |
| 5 | 区分已确认依赖、假设依赖、开放风险和已接受风险 | 依赖与风险 | 依赖无证据但影响下游 |
| 6 | 标记会影响方案路线的范围取舍、非目标、风险和不能带入下游的假设 | 方案阶段路线约束 | 会影响路线选择但缺少证据或用户决策 |
| 7 | 如需阶段化，说明每阶段覆盖的用例、用户可见结果、验证证据和不能跨越的边界 | 阶段化策略 | 阶段无法形成可验证结果 |

---

## 授权边界

| 项 | 内容 | 来源 | 结论 |
|----|------|------|------|
| 授权目标 | {{authorized_goal}} | {{source_ref}} | {{decision}} |
| 成功定义 | {{success_definition}} | {{source_ref}} | {{decision}} |
| 非目标 | {{non_goal}} | {{source_ref}} | {{decision}} |
| 约束 | {{constraint}} | {{source_ref}} | {{decision}} |
| 验证口径 | {{verification_boundary}} | {{source_ref}} | {{decision}} |

---

## 范围决策表

| 范围项 ID | 决策 | 内容 | 覆盖 / 排除的用例 | 业务价值 | 风险 | 证据 | 追溯 |
|-----------|------|------|------------------|----------|------|------|------|
| SCOPE-01 | IN / OUT / LATER / DECISION_NEEDED | {{scope_item}} | {{use_case_refs}} | {{business_value}} | {{risk}} | {{evidence_ref}} | {{trace_ref}} |

---

## 用例范围闭环

| 业务用例 | 系统用例 | 界面承载 | 验收场景 / 条件 | 范围决策 | 闭环是否成立 | 不成立时处理 |
|----------|----------|----------|--------|----------|--------------|--------------|
| BUC-01 | SUC-01 | UIC-01 / 不适用 | {{acceptance_scenario_or_condition_ref}} / {{trace_anchor_if_needed}} | SCOPE-01 | 是 / 否，原因：{{closure_reason}} | {{gap_handling}} |

---

## 判断理由

| 范围项 | 任务契约授权 | 业务价值 | 规则完整性 | 验证闭环 | 可逆性 | 取舍理由 |
|--------|--------------|----------|------------|----------|--------|----------|
| SCOPE-01 | {{authorization_ref}} | {{value_reason}} | {{rule_completeness}} | {{verification_reason}} | {{reversibility}} | {{tradeoff_reason}} |

---

## 依赖与风险

| 依赖 / 风险 ID | 类型 | 内容 | 状态 | 证据 | 对范围的影响 | 处理方式 |
|----------------|------|------|------|------|--------------|----------|
| RISK-01 | 已确认依赖 / 假设依赖 / 开放风险 / 已接受风险 | {{risk_or_dependency}} | {{status}} | {{evidence_ref}} | {{scope_impact}} | {{handling}} |

---

## 阶段化策略

| 阶段 | 覆盖用例 / 范围项 | 用户可见结果 | 必需验证证据 | 不能跨越的边界 |
|------|------------------|--------------|--------------|----------------|
| P1 | {{phase_scope_refs}} | {{user_visible_result}} | {{required_evidence}} | {{boundary}} |

---

## 方案阶段路线约束

| 范围 / 风险 / 非目标 | 对方案路线的影响 | 方案阶段不能假设 | 不清楚时处理 |
|----------------------|------------------|------------------|--------------|
| {{scope_or_risk_ref}} | {{solution_impact}} | {{assumption_to_avoid}} | 回流产品定义 / 回流探索 / 用户决策 / 明确延后 |

---

## 下游边界

| 消费方 | 必须保留的范围语义 | 不得越界的内容 | 缺口处理 |
|--------|--------------------|----------------|----------|
| 交互 / 原型 | {{interaction_scope_boundary}} | {{interaction_out_of_scope}} | {{interaction_gap_handling}} |
| 方案 | {{solution_scope_boundary}} | {{solution_out_of_scope}} | {{solution_gap_handling}} |
| 技术分析 | {{technical_scope_boundary}} | {{technical_out_of_scope}} | {{technical_gap_handling}} |
| 拆解 / 验证 | {{execution_verification_boundary}} | {{execution_out_of_scope}} | {{execution_gap_handling}} |
