# 探索简报（Discovery Brief）：{{mission_id}}

> **来源**：探索（discovery）技能 → `harness-runtime/harness/artifacts/{{mission_id}}/discovery/discovery-brief.md`
> **参考方法论**：事件风暴（Event Storming）；影响地图（Impact Mapping）；待完成工作（Jobs-to-be-Done）
> **上游**：`harness-runtime/harness/missions/{{mission_id}}/mission-contract.md` | `project-context.md`

- Contract: `contracts/discovery-brief.contract.yaml`
- 结构定义：`.harness/common/schemas/control_contract.v1/discovery_brief_contract.yaml`

> 结构化字段（`affected_capabilities` / `roles` / `scenarios` / `existing_solutions` / `design_assumptions` / `agent_engineering_candidates` / `degradations`）由外部契约 YAML（contract YAML）承载；本文件只保留面向人的叙事段，不得内嵌围栏 YAML（fenced YAML）控制契约段（由 harness-lint 的 `W-discovery-contract` 规则在 M4.2 强校验）。

**作者：** {{user_name}}
**日期：** {{date}}
**任务编号（mission-id）：** {{mission_id}}
**状态：** `draft` <!-- draft / 审查中 / 已批准 -->

---

## 摘要

{{summary}}

---

## 问题空间

### 背景

{{background}}

### 当前现状

{{current_state}}

### 关键约束

| 约束 | 来源 | 影响 |
|------|------|------|
| {{constraint_1}} | {{source_1}} | {{impact_1}} |

---

## 影响面

| 领域 / 模块 | 影响类型 | 置信度 | 证据 |
|-------------|----------|--------|------|
| {{area_1}} | {{impact_type_1}} | 已确认（CONFIRMED）/ 不确定（UNCERTAIN）/ 假设（ASSUMED） | {{evidence_1}} |

---

## 业务对象候选

> 仅记录探索阶段（discovery）发现的业务对象线索，不在本阶段产出最终业务对象模型。正式业务对象分析由产品定义阶段（PRD）的 `business-domain-modeler` 完成。

### 识别方法

1. 从任务契约、待探索问题、用户故事、项目上下文、现有代码、接口材料、数据记录和历史文档中抽取业务名词。
2. 对每个业务名词做五问过滤：业务人员是否会谈论它；是否会操作或追踪它；是否有状态、生命周期或规则；是否与其他业务对象存在关系；它是否不是单纯界面（UI）控件、技术模块、接口端点、数据库表或一次性动作。
3. 只有至少命中一条业务追踪 / 规则 / 生命周期线索，且有来源证据时，才写成候选对象；证据不足但可能重要的内容写入疑点或建模提示。
4. 对命名冲突、边界不清、状态不明和关系不明的问题，只写产品定义阶段（PRD）建模提示，不在探索阶段下结论。

### 约定模板

每个候选对象按以下句式落地：`候选对象 = <业务名词>；来源证据 = <用户表达 / 文档 / 代码 / 接口 / 数据记录>；状态 / 规则 / 关系线索 = <已发现线索>；疑点 = <命名冲突或边界问题>；产品定义阶段（PRD）建模提示 = <需要 business-domain-modeler 判断的问题>`。

| 候选对象 | 来源证据 | 状态 / 规则 / 关系线索 | 疑点或命名冲突 | 产品定义阶段（PRD）建模提示 |
|----------|----------|------------------------|----------------|---------------|
| {{business_object_candidate_1}} | {{business_object_source_1}} | {{business_object_signal_1}} | {{business_object_question_1}} | {{business_object_handoff_1}} |

---

## 业务用例与系统边界线索

> 本节只给产品定义阶段（PRD）的 `use-case-modeler` 提供证据材料，不在探索阶段（discovery）产出最终业务用例、系统用例、验收场景或原型方案。

### 业务活动线索

识别方法：从用户故事、任务目标、当前流程、接口调用、运行日志和代码执行流中抽取“角色为了业务结果做的活动”。每条只写业务活动、参与角色、业务目标 / 结果、来源证据和产品定义阶段（PRD）建模问题，不写系统用例编号、验收场景或页面流程。

约定模板：`业务活动 = <角色在业务语境下完成的活动>；目标 / 结果 = <业务上要达成的结果>；来源证据 = <材料或代码事实>；产品定义阶段（PRD）建模问题 = <需要 use-case-modeler 判断的问题>`。

| 业务场景 / 活动 | 参与角色 | 业务目标 / 结果 | 来源证据 | 产品定义阶段（PRD）建模问题 |
|-----------------|----------|-----------------|----------|--------------|
| {{business_activity_1}} | {{actor_1}} | {{business_goal_result_1}} | {{activity_evidence_1}} | {{activity_modeling_question_1}} |

### 系统边界与责任划分线索

责任划分方法：对每个业务活动分别判断人工、当前系统、目标系统、外部系统和不在本轮范围内的责任。只有有用户表达、项目文档、代码行为、接口契约或运行证据支撑的责任，才能标为已确认（CONFIRMED）；由流程或代码迹象推导但没有直接证据的标为推断（INFERRED）；仅为工作假设的标为假设（ASSUMED）。

责任划分约定模板：`业务活动 = <活动>；人工责任 = <人仍要完成的判断或操作>；当前系统责任 = <现有系统已承担的行为>；目标系统责任线索 = <本任务可能改变或新增的系统责任>；外部系统责任 = <外部依赖或边界>；证据等级 = CONFIRMED / INFERRED / ASSUMED；待澄清点 = <会影响 PRD 系统用例边界的问题>`。

| 业务场景 / 活动 | 人工责任 | 当前系统责任 | 目标系统责任线索 | 外部系统责任 | 证据等级 | 待澄清点 |
|-----------------|----------|--------------|------------------|--------------|----------|----------|
| {{business_activity_1}} | {{manual_responsibility_1}} | {{current_system_responsibility_1}} | {{target_system_responsibility_signal_1}} | {{external_system_responsibility_1}} | 已确认（CONFIRMED）/ 推断（INFERRED）/ 假设（ASSUMED） | {{system_boundary_question_1}} |

### 原型承载线索

识别方法：只记录哪些业务任务可能需要界面（UI）或原型承载，以及用户完成任务时需要看到什么信息、输入什么业务数据、触发什么操作、感知什么状态 / 错误 / 权限 / 反馈。不决定页面数量、组件、布局、导航或视觉方案。

原型承载线索模板：`场景 / 任务 = <业务任务>；可能需要界面承载 = 是 / 否 / 不清楚；需要展示的信息 = <业务信息>；需要输入 / 操作 = <业务输入或动作>；状态 / 错误 / 权限 / 反馈线索 = <交互必须表达的业务状态>；证据 / 疑点 = <来源或待澄清问题>`。

| 场景 / 任务 | 可能需要界面（UI）承载 | 需要展示的信息 | 需要输入 / 操作 | 状态 / 错误 / 权限 / 反馈线索 | 证据 / 疑点 |
|-------------|------------------|----------------|-----------------|--------------------------------|-------------|
| {{task_1}} | 是 / 否 / 不清楚 | {{information_1}} | {{input_or_action_1}} | {{state_error_permission_feedback_1}} | {{ui_evidence_or_question_1}} |

---

## 关键发现

| 编号（ID） | 发现 | 证据 | 对后续工作 / 工作图（Work Graph）的影响 |
|----|------|------|------------------|
| DIS-001 | {{finding_1}} | {{evidence_1}} | {{downstream_impact_1}} |

---

## 风险与未知

| ID | 风险 / 未知 | 严重度 | 处理建议 |
|----|-------------|--------|----------|
| RISK-001 | {{risk_1}} | 高 / 中 / 低 | {{mitigation_1}} |

---

## 产品定义阶段（PRD）输入建议

| 主题 | 建议写入产品定义阶段（PRD）的内容 | 依据 |
|------|--------------------|------|
| {{topic_1}} | {{prd_input_1}} | {{basis_1}} |

---

## 证据索引

| 证据 | 类型 | 路径 / 命令 / 来源 |
|------|------|-------------------|
| {{evidence_id_1}} | 代码 / 文档 / 命令 / 外部材料 | {{evidence_ref_1}} |
