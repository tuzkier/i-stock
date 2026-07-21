# 产品领域模型：{{project_name}}

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/{{mission_id}}/product/product-domain-model.md`
> **用途**：按 DDD 方法沉淀产品领域模型。本文定义业务语义、边界、规则、状态和行为契约，不定义数据库、接口、框架、缓存、队列或部署方案。

**任务编号（mission-id）：** {{mission_id}}
**状态：** `draft`

---

## 控制契约

- 控制契约（程序识别标记：Control Contract: `contracts/prd.contract.yaml`）
- 权威来源：外部 YAML 是程序化权威来源；本文件提供产品领域模型解释。

---

## 领域意图

| 项 | 内容 | 追溯 |
|------|---------|-------|
| 业务问题 | {{business_problem}} | {{mission_or_ac_id}} |
| 产品能力 | {{capability}} | {{fr_or_capability_id}} |
| 非目标 | {{non_goal}} | {{scope_out_id}} |
| 建模深度 | {{simple_standard_complex}} | {{reason_and_signal}} |

如果某个 DDD 要素不适用，必须写明 `不适用：原因...`，不得留空。

---

## 产品语义核心模型

> 本节先收束产品阶段必须稳定的业务语义，再按 DDD 结构展开。业务对象、状态机和用例覆盖是同等级输入：业务对象说明“业务上有什么”，状态机说明“它如何变化”，用例说明“谁在什么目标下触发这些变化”。

| 核心模型 | 来源 | 本阶段结论 | 下游必须保留 |
|----------|------|------------|--------------|
| 业务对象 | `business-object-analysis.md` | {{business_object_summary}} | {{business_object_semantics_to_preserve}} |
| 状态机 | `business-object-analysis.md` + `use-case-model.md ## 领域模型反馈` | {{state_machine_summary}} | {{state_machine_semantics_to_preserve}} |
| 用例覆盖 | `use-case-model.md` + `acceptance-scenarios.md` | {{use_case_coverage_summary}} | {{use_case_semantics_to_preserve}} |
| 业务规则 | `business-object-analysis.md` + `acceptance-scenarios.md` | {{business_rule_summary}} | {{business_rule_semantics_to_preserve}} |

### 领域模型反馈处理

| 反馈 ID | 来源 | 处理结论 | 写入的领域元素 | 未采纳原因 / 风险 |
|---------|------|----------|----------------|-------------------|
| DMF-01 | `use-case-model.md` | 已采纳 / 回流 / 用户决策 / 不采纳 | {{domain_element_ref}} | {{reason_or_risk}} |

---

## 战略领域建模（Strategic DDD）

### 领域 / 子域

| 类型 | 名称 | 存在原因 | 核心 / 支撑 / 通用 | 追溯 |
|------|------|---------------|-----------------------------|-------|
| 领域 | {{domain_name}} | {{reason}} | 核心 | {{trace_id}} |
| 子域 | {{subdomain_name}} | {{reason}} | {{core_supporting_generic}} | {{trace_id}} |

### 限界上下文（Bounded Contexts）

| 上下文 ID | 上下文名称 | 责任 | 上下文内语言 | 边界之外 |
|------------|--------------|----------------|-------------|-----------------|
| BC-01 | {{context_name}} | {{responsibility}} | {{terms_owned_here}} | {{not_owned_here}} |

### 上下文映射

| 上游上下文 | 关系 | 下游上下文 | 契约 / 翻译规则 | 风险 |
|------------------|--------------|--------------------|-----------------------------|------|
| {{upstream}} | {{customer_supplier_conformist_acl}} | {{downstream}} | {{contract_or_translation}} | {{risk}} |

### 统一语言

| 术语 | 本上下文定义 | 禁止混淆的含义 | 来源 |
|------|----------------------------|---------------------|--------|
| {{term}} | {{definition}} | {{ambiguous_meaning_to_avoid}} | {{source}} |

### 能力边界

| 能力 ID | 能力 | 新增 / 变更 / 移除 / 复用 | 边界规则 | 追溯 |
|---------------|------------|------------------------------------|---------------|-------|
| CAP-01 | {{capability}} | {{change_type}} | {{boundary_rule}} | {{fr_or_spec_id}} |

---

## 战术领域建模（Tactical DDD）

### 参与者

| 参与者 ID | 参与者 / 角色 | 目标 | 允许访问的上下文 |
|----------|--------------|------|------------------|
| ACT-01 | {{actor}} | {{goal}} | {{contexts}} |

### 聚合（Aggregates）

| 聚合 ID | 聚合 | 聚合根 | 一致性边界 | 负责的不变量 |
|--------------|-----------|----------------|----------------------|------------------|
| AGG-01 | {{aggregate}} | {{aggregate_root}} | {{consistency_boundary}} | {{invariant_ids}} |

### 实体

| 实体 ID | 实体 | 身份标识 | 生命周期 | 所属聚合 |
|-----------|--------|----------|-----------|-----------|
| ENT-01 | {{entity}} | {{identity}} | {{lifecycle}} | {{aggregate_id}} |

### 值对象

| 值对象 ID | 值对象 | 属性 | 相等性 / 校验规则 | 使用方 |
|----------------|--------------|------------|----------------------------|---------|
| VO-01 | {{value_object}} | {{attributes}} | {{rule}} | {{entity_or_command}} |

### 领域命令（Domain Commands）

| 命令 ID | 命令 | 参与者 / 系统 | 目标聚合 | 前置条件 | 结果 |
|------------|---------|----------------|------------------|---------------|--------|
| CMD-01 | {{command}} | {{actor}} | {{aggregate_id}} | {{preconditions}} | {{result}} |

### 领域事件（Domain Events）

| 事件 ID | 事件 | 产生方 | 业务含义 | 消费方 / 后续动作 |
|----------|-------|-----------|---------|-----------------------|
| EVT-01 | {{event}} | {{command_or_aggregate}} | {{business_fact}} | {{consumer_or_policy}} |

### 不变量（Invariants）

| 不变量 ID | 不变量 | 聚合 / 上下文 | 保护的命令 | 失败行为 | 追溯 |
|--------------|-----------|---------------------|--------------------|------------------|-------|
| INV-01 | {{invariant}} | {{aggregate_or_context}} | {{command_ids}} | {{reject_compensate_escalate}} | {{fr_or_ac_id}} |

### 策略

| 策略 ID | 策略 | 触发条件 | 决策输入 | 结果 | 追溯 |
|-----------|--------|---------|-----------------|---------|-------|
| POL-01 | {{policy}} | {{event_or_command}} | {{inputs}} | {{outcome}} | {{trace_id}} |

### 领域服务

| 服务 ID | 领域服务 | 为什么不归属实体 | 输入 | 输出 / 事件 |
|------------|----------------|----------------------|--------|----------------|
| DS-01 | {{domain_service}} | {{reason}} | {{inputs}} | {{output}} |

### 状态机（State Machines）

| 状态机 ID | 实体 / 聚合 | 起始状态（From State） | 目标状态（To State） | 触发（Trigger）命令 / 事件 | 参与者（Actor） | 前置条件（Preconditions） / 守卫 | 迁移动作 / 业务结果 | 终态 | 非法迁移（Invalid Transitions） | 追溯 |
|-----------------|--------------------|----------------------|--------------------|-------------------------------|----------------|----------------------------------|----------------------|------|--------------------------------|------|
| STM-01 | {{entity_or_aggregate}} | {{from_state}} | {{to_state}} | {{command_or_event}} | {{actor}} | {{preconditions_or_guard}} | {{transition_result}} | {{terminal_state_or_na}} | {{invalid_transitions}} | {{use_case_or_rule_ref}} |

---

## 规则与约束

### 权限矩阵（Permission Matrix）

| 参与者 | 命令 | 目标聚合 / 实体 | 状态 | 是否允许 | 原因 / 规则 | 是否需要审计 |
|-------|---------|---------------------------|-------|---------|---------------|----------------|
| {{actor}} | {{command_id}} | {{target}} | {{state}} | {{yes_no}} | {{reason}} | {{yes_no}} |

### 异常 / 补偿 / 幂等

| 场景 ID | 场景 | 触发条件 | 期望处理 | 幂等 / 冲突规则 | 追溯 |
|---------|------|---------|-------------------|-----------------------------|-------|
| EXC-01 | {{exception_case}} | {{trigger}} | {{handling}} | {{rule}} | {{trace_id}} |

### 合规 / 安全 / 审计

| 规则 ID | 规则 | 适用对象 | 证据 / 审计要求 | 追溯 |
|---------|------|------------|------------------------------|-------|
| AUD-01 | {{rule}} | {{object_or_command}} | {{evidence_required}} | {{trace_id}} |

---

## 追溯关系

| 产品需求 / 场景 | 领域元素 | 元素类型 | 覆盖原因 |
|--------------------------------|----------------|--------------|-------------------------------|
| SYS-RESP-01 | CMD-01 | Command | {{coverage_reason}} |
| SCN-01 | INV-01 | Invariant | {{coverage_reason}} |

---

## 给方案阶段的领域边界

> 本节把会影响实现路线的领域语义集中说明。它不决定技术实现方式，只说明方案阶段必须保留哪些业务边界、规则和状态语义，哪些做法会破坏领域模型。

| 领域元素 | 方案必须保留的语义 | 后续不能采用的做法 | 影响的用例 / 规则 | 破坏后的风险 |
|----------|--------------------|--------------------|------------------|--------------|
| 限界上下文 {{bc_ref}} | {{bounded_context_semantics}} | {{forbidden_context_shortcut}} | {{use_case_or_rule_ref}} | {{context_violation_risk}} |
| 聚合 / 一致性边界 {{aggregate_ref}} | {{aggregate_consistency_semantics}} | {{forbidden_aggregate_shortcut}} | {{use_case_or_rule_ref}} | {{aggregate_violation_risk}} |
| 策略 / 领域事件 {{policy_or_event_ref}} | {{policy_event_semantics}} | {{forbidden_policy_shortcut}} | {{use_case_or_rule_ref}} | {{policy_violation_risk}} |
| 不变量 {{invariant_ref}} | {{invariant_semantics}} | {{forbidden_invariant_shortcut}} | {{use_case_or_rule_ref}} | {{invariant_violation_risk}} |
| 状态机 / 权限 {{state_permission_ref}} | {{state_permission_semantics}} | {{forbidden_state_permission_shortcut}} | {{use_case_or_rule_ref}} | {{state_permission_violation_risk}} |

## 领域问题对方案阶段的影响

| 问题 / 风险 | 影响的领域元素 | 是否阻断方案路线选择 | 处理方式 |
|-------------|----------------|----------------------|----------|
| {{domain_solution_question_1}} | {{domain_element_ref_1}} | 是 / 否，原因：{{blocks_solution_reason_1}} | 回流产品定义 / 回流探索 / 用户决策 / 作为方案阶段风险输入 |

---

## 下游消费指引（Downstream Guidance）

| 消费方 | 必须保留 / 消费的内容 | 来源领域元素 | 备注 |
|----------|--------------------------|-----------------------|-------|
| 用例模型 | 参与者、命令、状态机、业务规则、人工 / 系统 / 外部责任边界 | {{actor_cmd_state_rule_ids}} | {{notes}} |
| 交互设计 | 对象、状态机、命令、受权限限制的操作 | {{agg_cmd_state_ids}} | {{notes}} |
| 方案设计 | 限界上下文、策略、事件、一致性边界 | {{bc_policy_event_ids}} | {{notes}} |
| 技术分析 | 聚合、命令、事件、不变量、幂等规则 | {{agg_cmd_event_inv_ids}} | {{notes}} |
| 拆解 / 测试 | 不变量、状态迁移、权限、异常场景 | {{inv_stm_perm_exc_ids}} | {{notes}} |

---

## 待澄清问题与建模风险

| 风险 ID | 问题 / 风险 | 影响 | 决策期限 | 负责人 |
|---------|------------------|--------|--------------------|-------|
| RISK-01 | {{question_or_risk}} | {{impact}} | {{stage_or_date}} | {{owner}} |
