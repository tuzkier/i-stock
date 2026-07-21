# 业务对象分析：{{project_name}}

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/{{mission_id}}/product/business-object-analysis.md`
> **用途**：从业务材料中识别业务对象、状态机、属性、引用关系、业务规则和建模取舍，供用例模型、产品定义、领域模型和验收场景消费。本文不定义数据库表、字段、接口、缓存、队列或服务模块。

**任务编号（mission-id）：** {{mission_id}}
**状态：** `draft`

---

## 模板约定

- 业务对象编号固定使用 `OBJ-xx`，属性使用 `ATTR-xx`，引用关系使用 `REF-xx`，状态机使用 `STM-xx`，业务规则使用 `BR-xx`，排除项使用 `EXC-xx`。
- 每个核心业务对象必须说明来源、业务身份、生命周期、状态机、引用关系和承载规则。
- 状态机是与业务对象同等级的产品语义模型；每条迁移必须写成 `起始状态 ->[事件 / 命令 / 守卫]-> 目标状态`，并说明非法迁移和失败行为。
- 只有被业务持续识别、管理、追踪或受规则约束的概念才能成为业务对象。
- UI 控件、页面、按钮、弹窗、接口、数据库表、服务、缓存和消息队列不得作为业务对象。
- 不适用项必须写 `不适用：原因...`，证据不足项必须写 `待澄清：原因...`。

---

## 使用者与使用时机

| 使用者 | 使用时机 | 使用方式 | 不做什么 |
|--------|----------|----------|----------|
| `business-domain-modeler` | PRD 第 1 步生成 `product/business-object-analysis.md` 时 | 按本模板识别对象、状态机、属性、引用、规则、取舍和下游消费提示 | 不设计数据库、接口或技术模型 |
| `use-case-modeler` | 建立用例模型前 | 读取本产物中的对象、状态和规则，作为业务用例、系统边界和责任切分的语义来源 | 不重新发明业务对象 |
| `acceptance-scenario-designer` | 推导验收场景时 | 读取对象状态变化、规则和异常，转成可观察验收条件 | 不从未确认规则生成验收场景 |
| `senior-product-expert` | 综合产品定义包时 | 检查本产物是否可被消费，并吸收到 `product-definition.md` 和 `product-domain-model.md` | 不把模板内容机械粘贴成最终 PRD |
| `product-definition-reviewer` / harness-lint | PRD 审查和框架一致性检查时 | 检查方法章节、模板约定、编号、追溯和下游消费是否完整 | 不替子 Agent 补写业务模型 |

---

## 建模方法

| 步骤 | 方法 | 产出位置 | 阻断条件 |
|------|------|----------|----------|
| 1 | 从任务契约、探索简报、业务材料中提取高频主语 / 宾语、被追踪名词、规则承载体、生命周期载体 | 候选对象清单 | 核心名词无来源 |
| 2 | 过滤纯动作、UI 概念、技术实现名词、一次性流程词和无法独立存在的属性 | 排除对象记录 | 业务概念和技术概念无法区分 |
| 3 | 为每个对象定义业务身份、说明、生命周期、所有者和存在原因 | 业务对象详情 | 对象存在原因不清 |
| 4 | 区分一般属性、状态属性、计算属性、引用关系和外部标识 | 属性与引用关系 | 把外键或被引用对象属性误写成本对象属性 |
| 5 | 建立状态机：归属对象 / 聚合、状态集合、触发事件 / 命令、前置条件 / 守卫、合法迁移、非法迁移、终态和失败行为 | 状态机总览 | 状态冲突、缺少触发事件或缺少非法迁移 |
| 6 | 建立业务规则，说明承载对象、触发事件、前置条件、约束结果和来源 | 业务规则 | 规则无法追溯来源 |
| 7 | 标记下游消费：哪些对象 / 状态 / 规则必须进入用例、验收、产品领域模型或方案约束 | 下游消费提示 | 下游关键语义无法追溯 |

---

## 输入合格性判断

| 输入 | 来源 | 是否足以建模 | 缺口 | 处理 |
|------|------|--------------|------|------|
| 任务契约 | {{mission_contract_ref}} | 足够 / 不足 | {{mission_gap}} | {{mission_gap_handling}} |
| 探索简报 | {{discovery_ref}} | 足够 / 不足 / 不适用 | {{discovery_gap}} | {{discovery_gap_handling}} |
| 项目知识 / 规格 | {{knowledge_spec_ref}} | 足够 / 不足 / 不适用 | {{knowledge_gap}} | {{knowledge_gap_handling}} |
| 业务材料 | {{business_source_ref}} | 足够 / 不足 | {{business_material_gap}} | {{business_material_gap_handling}} |

---

## 候选对象清单

| 候选 ID | 候选名词 | 来源 | 成为业务对象的理由 | 排除 / 保留结论 |
|---------|----------|------|--------------------|----------------|
| CAND-01 | {{candidate_term}} | {{source_ref}} | {{object_reason}} | 保留为 OBJ-01 / 排除为 EXC-01 |

---

## 业务对象详情

### OBJ-01：{{object_name}}

| 项 | 内容 |
|----|------|
| 业务定义 | {{business_definition}} |
| 存在原因 | {{reason_to_exist}} |
| 业务身份 | {{business_identity}} |
| 生命周期 | {{lifecycle}} |
| 所有者 / 管理者 | {{owner_or_manager}} |
| 主要使用场景 | {{use_cases}} |
| 来源 | {{evidence_refs}} |

### 属性

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-01 | {{attribute}} | 一般属性 / 状态属性 / 计算属性 / 外部标识 | {{ownership_reason}} | 是 / 否 | {{rule_or_constraint}} | {{source_ref}} |

### 引用关系

| 引用 ID | 本对象 | 被引用对象 | 引用角色 | 数量关系 | 是否影响生命周期 | 规则 | 来源 |
|---------|--------|------------|----------|----------|------------------|------|------|
| REF-01 | OBJ-01 | {{referenced_object}} | {{reference_role}} | 1:1 / 1:N / N:M | 是 / 否，原因：{{lifecycle_impact}} | {{rule}} | {{source_ref}} |

---

## 状态机总览

> 本节是业务领域模型草案的核心部分，不是对象详情附录。若用例展开发现新的状态、迁移或规则，必须在 `use-case-model.md ## 领域模型反馈` 中回流，由 senior-product-expert 统一裁剪进最终产品领域模型。

| 状态机 ID | 归属对象 / 聚合 | 状态组 | 状态集合 | 触发事件 / 命令 | 前置条件 / 守卫 | 合法迁移 | 非法迁移 / 失败行为 | 终态 | 影响的规则 / 用例 |
|-----------|----------------|--------|----------|----------------|----------------|----------|-------------------|------|-------------------|
| STM-01 | OBJ-01 | {{state_group}} | {{states}} | {{trigger_event_or_command}} | {{guard_or_precondition}} | {{from_state}} ->[{{event_or_command}} / {{guard}}]-> {{to_state}} | {{invalid_transition_or_failure}} | {{terminal_state_or_na}} | {{rule_or_use_case_ref}} |

---

## 业务规则

| 规则 ID | 规则 | 承载对象 | 触发事件 | 前置条件 | 约束结果 | 失败 / 例外处理 | 来源 |
|---------|------|----------|----------|----------|----------|----------------|------|
| BR-01 | {{business_rule}} | OBJ-01 | {{trigger_event}} | {{precondition}} | {{constrained_result}} | {{failure_or_exception}} | {{source_ref}} |

---

## 建模取舍

| 排除 ID | 候选对象 / 规则 | 排除原因 | 风险 | 后续处理 |
|---------|----------------|----------|------|----------|
| EXC-01 | {{excluded_candidate}} | {{exclusion_reason}} | {{risk}} | {{follow_up}} |

---

## 下游消费提示

| 消费方 | 必须消费的对象 / 状态 / 规则 | 消费方式 | 不得假设的内容 |
|--------|------------------------------|----------|----------------|
| 用例模型 | {{object_state_rule_refs}} | {{use_case_consumption}} | {{use_case_assumption_to_avoid}} |
| 验收场景 | {{rule_state_refs}} | {{acceptance_consumption}} | {{acceptance_assumption_to_avoid}} |
| 产品领域模型 | {{domain_model_refs}} | {{domain_consumption}} | {{domain_assumption_to_avoid}} |
| 方案 / 技术分析 | {{solution_technical_refs}} | {{downstream_consumption}} | {{technical_assumption_to_avoid}} |
