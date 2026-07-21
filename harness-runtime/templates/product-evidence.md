# 产品证据记录：{{project_name}}

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/{{mission_id}}/product/product-evidence.md`
> **用途**：记录产品定义使用过的项目知识、规格、代码影响分析和降级情况。

**任务编号（mission-id）：** {{mission_id}}
**状态：** `draft`

---

## 控制契约

- 控制契约（程序识别标记：Control Contract: `contracts/prd.contract.yaml`）
- 权威来源：外部 YAML 是程序化权威来源；本文件只记录证据和解释。

---

## 任务输入

| 输入 | 路径 / 来源 | 使用方式 | 结论 |
|------|-------------|----------|------|
| 任务契约（Mission Contract） | `harness-runtime/harness/missions/{{mission_id}}/mission-contract.md` | {{usage}} | {{finding}} |
| 探索简报（Discovery Brief） | {{path}} | {{usage}} | {{finding}} |
| 项目上下文（Project Context） | {{path}} | {{usage}} | {{finding}} |

---

## 项目知识证据

| 证据 ID | 来源 | 相关主题 | 产品判断影响 | 置信度 |
|-------------|------|----------|--------------|--------|
| KE-01 | {{knowledge_ref}} | {{topic}} | {{impact}} | {{confidence}} |

---

## 规格对齐

| 能力 | 基线规格 | 变更类型 | 对需求 / 场景的影响 | 决策 |
|------------|---------------|-------------|-------------------------------|----------|
| {{capability}} | {{spec_ref}} | {{added_modified_removed}} | {{impact}} | {{decision}} |

---

## 用例建模证据

| 证据 ID | 支撑内容 | 来源 | 支撑的业务用例 / 系统用例 | 判断结果 |
|-------------|----------|------|-----------------------------|----------|
| UCE-01 | {{boundary_or_responsibility_evidence}} | {{source_ref}} | BUC-01 / SUC-01 | {{confirmed_or_blocked}} |

## 系统责任澄清

| 问题 | 影响的业务用例 / 系统用例 | 为什么不能假设 | 需要谁确认 | 当前处理 |
|------|---------------------------|----------------|------------|----------|
| {{clarification_question}} | {{use_case_ref}} | {{risk_of_assumption}} | {{owner}} | {{blocked_or_deferred}} |

---

## Graphify 证据

> 既有项目、现有代码影响、模块边界、调用链或兼容性不确定时必须填写；不可用时写入 Degradations。

| 证据 ID | Graphify 查询 / 输出 | 影响面 | 产品判断 |
|-------------|----------------------|--------|----------|
| GN-01 | {{graphify_ref}} | {{impact_area}} | {{product_decision}} |

---

## 影响方案路线的事实与风险

> 本节只收集会影响方案阶段路线选择的事实、约束和风险。这里不选择路线，只说明哪些事实足够可靠、哪些假设不能带入方案、哪些缺口必须回流或由用户决策。

| 事实 / 风险 | 来源 | 影响的用例 / 约束 | 对方案路线的影响 | 证据是否足够 | 不足时怎么处理 |
|-------------|------|-------------------|------------------|--------------|----------------|
| {{solution_relevant_fact_or_risk_1}} | {{source_ref_1}} | {{affected_requirement_or_constraint_1}} | {{route_impact_1}} | 足够 / 不足，原因：{{evidence_sufficiency_reason_1}} | {{gap_handling_1}} |

## 不得带入方案阶段的假设

| 假设 | 为什么不能假设 | 影响范围 | 处理方式 |
|------|----------------|----------|----------|
| {{assumption_1}} | {{why_not_assume_1}} | {{impact_scope_1}} | 回流探索 / 用户决策 / 明确排除 / 延后观察 |

---

## 降级记录

| 缺失证据 | 原因 | 风险 | 补救动作 | 负责人 |
|----------|------|------|----------|-------|
| {{missing_evidence}} | {{reason}} | {{risk}} | {{mitigation}} | {{owner}} |
