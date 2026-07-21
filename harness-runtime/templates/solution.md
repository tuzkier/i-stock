# 方案（solution）：{{mission_id}}

> **来源**：方案阶段产物 → `harness-runtime/harness/artifacts/{{mission_id}}/solution/solution.md`
> **思路来源**：RUP 的细化阶段（Elaboration），尤其是用例驱动、以架构为核心、尽早处理高风险问题；同时参考架构决策记录（ADR）和领域驱动设计（DDD）
> **上游**：`product/product-definition.md` | `product/use-case-model.md` | `product/acceptance-scenarios.md` | `product/product-evidence.md` | `product/product-domain-model.md` | `mission-contract.md` | `project-context.md`

**作者：** {{user_name}}
**日期：** {{date}}
**任务编号：** {{mission_id}}
**状态：** `draft` <!-- draft / in-review / approved -->

---

## 控制契约

- Contract: `contracts/solution.contract.yaml`
- 权威来源：外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

## 概览

> 用 2-3 句话说明本次需求要达成的用户可观察结果、最终选择的实现路线，以及决定这条路线的关键约束。方案阶段不写完整模块设计，不拆执行任务，也不能把“改动少”或“先演示出来”当作路线成立的理由。

{{solution_overview}}

**核心路线：** {{selected_route_summary}}

**关键判断：**
1. {{decision_point_1}}
2. {{decision_point_2}}
3. {{decision_point_3}}

---

## 控制契约

> 外部 YAML 只保存下游必须读取的结构化决策、禁用做法和风险处理方式；本文负责讲清楚这些判断为什么成立。

- 契约文件：`contracts/solution.contract.yaml`
- 权威来源：外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

## 方法执行记录

> 这里记录本方案如何从上游材料推导出路线。不要只写“已检查”“已比较”，必须写出判断方法、证据和结论。

| 步骤 | 本次怎么做 | 证据或来源 | 结论 |
|---|---|---|---|
| 输入合格性判断 | {{input_sufficiency_method}} | {{input_sufficiency_evidence}} | {{input_sufficiency_conclusion}} |
| 上游约定落地 | {{upstream_mapping_method}} | {{upstream_mapping_evidence}} | {{upstream_mapping_conclusion}} |
| 系统操作覆盖与自洽校验 | {{system_use_case_behavior_method}} | {{system_use_case_behavior_evidence}} | {{system_use_case_behavior_conclusion}} |
| 路线驱动因素提炼 | {{route_driver_method}} | {{route_driver_evidence}} | {{route_driver_conclusion}} |
| 决策点筛选 | {{decision_filter_method}} | {{decision_filter_evidence}} | {{decision_filter_conclusion}} |
| 候选路线比较 | {{option_comparison_method}} | {{option_comparison_evidence}} | {{option_comparison_conclusion}} |
| 风险处理安排 | {{risk_treatment_method}} | {{risk_treatment_evidence}} | {{risk_treatment_conclusion}} |
| 技术分析交接 | {{technical_analysis_handoff_method}} | {{technical_analysis_handoff_evidence}} | {{technical_analysis_handoff_conclusion}} |

---

## 路线选择前检查

> 先判断现有材料能不能支撑路线选择。若行为规格、事实证据、风险或项目约束还不足以判断，本阶段必须停止并回流，不得自己补假设。

| 材料 | 是否足够 | 对路线选择的影响 | 缺口怎么处理 |
|---|---|---|---|
| 任务目标与非目标 | {{sufficient_or_gap}} | {{intent_driver}} | {{intent_gap_handling}} |
| 系统用例流步骤、系统操作与验收场景 / 条件 | {{sufficient_or_gap}} | {{behavior_driver}} | {{behavior_gap_handling}} |
| 质量与运行约束 | {{sufficient_or_gap}} | {{quality_runtime_driver}} | {{quality_runtime_gap_handling}} |
| 领域模型与业务规则 | {{sufficient_or_gap}} | {{domain_driver}} | {{domain_gap_handling}} |
| 现状事实与风险 | {{sufficient_or_gap}} | {{fact_risk_driver}} | {{fact_risk_gap_handling}} |
| 项目架构约束 | {{sufficient_or_gap}} | {{architecture_constraint_driver}} | {{architecture_constraint_gap_handling}} |
| 交互路径与界面状态（如适用） | {{sufficient_or_gap}} | {{interaction_driver}} | {{interaction_gap_handling}} |

---

## 上游约定如何落到方案

> RUP 强调用例驱动。这里不复制产品定义，而是说明用户场景、验收场景 / 条件、领域规则和补充约束如何影响方案路线。

| 上游约定 | 方案中的安排 | 是否改变原意 | 证据或说明 |
|---|---|---|---|
| {{system_use_case_or_acceptance_scenario_1}} | {{solution_support_1}} | 否 / 是，原因：{{semantic_change_reason_1}} | {{evidence_1}} |
| {{quality_runtime_constraint_1}} | {{solution_support_2}} | 否 / 是，原因：{{semantic_change_reason_2}} | {{evidence_2}} |
| {{domain_rule_1}} | {{solution_support_3}} | 否 / 是，原因：{{semantic_change_reason_3}} | {{evidence_3}} |

---

## 系统操作覆盖与自洽校验

> 方案阶段只证明选定路线能够承载 PRD 的系统行为描述、`SUC-xx-FLOW-xx` 流步骤和 `SUC-xx-OP-xx` 系统操作。这里可以决定承载机制、边界和风险处理，但不能新增、删除或改写目标系统操作；发现行为语义不成立时必须回流产品定义或决策门。

| 系统操作 ID | 来源流步骤 / 验收 | 方案承载方式 | 保留的对象 / 状态 / 规则 | 对路线选择的影响 | 不能改变 | 缺口处理 |
|-------------|--------------------|--------------|--------------------------|------------------|----------|----------|
| SUC-01-OP-01 | SUC-01-FLOW-01 / {{acceptance_ref}} | {{solution_support}} | {{object_state_rule_refs}} | {{route_impact}} | {{semantics_to_preserve}} | no_change / return_to_prd / decision_gate |

---

## 原型承载与遵从（如本 mission 有 interaction 原型产物）

> 仅当本 mission 跑过 interaction 阶段、存在原型契约（`behavior-graph.yaml` + `surface-model.md`）时填写；非 UI / 未跑 interaction 的 mission 无原型产物，本节连同覆盖率门一并跳过。
> 方案阶段只对账 `surface-model.md` 的**界面边界（SURF）**层：逐条说明本方案如何承载每个 `SURF-xxx` 标注的界面边界（create / modify / extend / retire），即哪条架构决策覆盖该界面或信息架构；要么承载，要么显式声明改写理由并触发决策门，禁止静默漂移或自由重设计界面。`PS-` 页面状态级的逐条覆盖由 breakdown 阶段对账，本节不展开。

| SURF id | 界面边界（create / modify / extend / retire） | 方案承载 / 改写决策 | traces_to |
|---------|-----------------------------------------------|---------------------|-----------|
| SURF-xxx | {{surface_boundary}} | {{solution_carry_or_rewrite_decision}} | {{traces_to_ref}} |

- 每个 mission SURF 必须被某条架构决策或承载模块 `traces_to` 引用；未承载的 SURF 会被 Gate 报 `SURFACE_NOT_CARRIED`（FAIL 级，mission-local 分母）。
- 确需不承载的界面边界，必须在 `contracts/solution.contract.yaml` 的 `prototype_coverage_exemptions: [{id, reason}]` 中登记并写明理由；缺理由会被报 `PROTOTYPE_EXEMPTION_NO_REASON`。

---

## 路线选择依据

> 把需求、事实和风险转成判断路线的依据。后续每个关键决策都应该能追溯到这里。

| 判断依据 | 来源 | 路线压力 | 对方案的影响 | 不满足时的后果 |
|---|---|---|---|---|
| 用户目标 | {{source_1}} | {{route_pressure_1}} | {{impact_1}} | {{failure_mode_1}} |
| 系统操作 | {{system_operation_refs}} | {{system_operation_route_pressure}} | {{system_operation_solution_impact}} | {{system_operation_failure_mode}} |
| 质量与运行约束 | {{source_2}} | {{route_pressure_2}} | {{impact_2}} | {{failure_mode_2}} |
| 领域边界 | {{source_3}} | {{route_pressure_3}} | {{impact_3}} | {{failure_mode_3}} |
| 现有架构约束 | {{source_4}} | {{route_pressure_4}} | {{impact_4}} | {{failure_mode_4}} |
| 高优先级风险 | {{source_5}} | {{route_pressure_5}} | {{impact_5}} | {{failure_mode_5}} |

---

## 影响架构走向的决策

> 只记录会改变实现路线、系统边界、关键机制、风险处理方式或后续技术分析方向的决策。若不存在真实备选路线，必须说明其他路线为什么不成立；不要为了凑格式制造候选项。

### 决策 DEC-01：{{decision_title_1}}

**为什么必须在方案阶段决定：** {{why_decide_in_solution}}

**依据来自哪里：** {{upstream_basis}}

**候选路线：**

| 路线 | 承载方式 | 取舍 | 适用条件 | 主要风险 | 验证难度 |
|---|---|---|---|---|---|
| 路线 A：{{option_a_name}} | {{option_a_realization}} | {{option_a_tradeoff}} | {{option_a_condition}} | {{option_a_risk}} | {{option_a_validation_difficulty}} |
| 路线 B：{{option_b_name}} | {{option_b_realization}} | {{option_b_tradeoff}} | {{option_b_condition}} | {{option_b_risk}} | {{option_b_validation_difficulty}} |

**取舍矩阵：**

| 取舍维度 | 路线 A | 路线 B | 本次判断 |
|---|---|---|---|
| 用户目标承载 | {{option_a_user_goal_fit}} | {{option_b_user_goal_fit}} | {{user_goal_tradeoff}} |
| 领域边界影响 | {{option_a_domain_impact}} | {{option_b_domain_impact}} | {{domain_tradeoff}} |
| 现有架构兼容 | {{option_a_architecture_fit}} | {{option_b_architecture_fit}} | {{architecture_tradeoff}} |
| 质量与运行约束 | {{option_a_quality_runtime_fit}} | {{option_b_quality_runtime_fit}} | {{quality_runtime_tradeoff}} |
| 迁移 / 回滚成本 | {{option_a_migration_cost}} | {{option_b_migration_cost}} | {{migration_tradeoff}} |
| 风险验证难度 | {{option_a_risk_validation}} | {{option_b_risk_validation}} | {{risk_validation_tradeoff}} |

**无实质备选时的说明：**

| 被排除路线 | 排除原因 | 对后续实现的约束 |
|---|---|---|
| {{excluded_option_1}} | {{excluded_reason_1}} | {{excluded_implementation_constraint_1}} |

**选定路线：** {{selected_option}}

**为什么选它：** {{selection_rationale}}

**被拒绝路线及原因：**

| 路线 | 拒绝原因 | 对后续实现的约束 |
|---|---|---|
| {{rejected_option_1}} | {{rejected_reason_1}} | {{forbidden_implication_1}} |

**后续不能采用的做法：**
- {{forbidden_path_1}}
- {{forbidden_path_2}}

**风险怎么处理：**

| 风险 | 处理方式 | 后续责任阶段 | 必需证据 |
|---|---|---|---|
| {{risk_1}} | 验证 / 接受 / 阻断 / 降级 / 回流 | {{owner_stage_1}} | {{required_evidence_1}} |

**交给技术分析阶段（technical_analysis）继续展开的内容：**
- {{technical_analysis_obligation_1}}
- {{technical_analysis_obligation_2}}

---

## 选定路线的边界和准则

> 这里说明技术分析阶段（technical_analysis）必须沿着哪条路线继续展开。方案阶段只给方向、边界和不得改变的判断，不写完整模块实现。

| 维度 | 当前决定 | 不得改变的边界 | 后续需细化内容 |
|---|---|---|---|
| 系统边界 | {{system_boundary_baseline}} | {{system_boundary_forbidden_change}} | {{system_boundary_followup}} |
| 关键机制 | {{key_mechanism_baseline}} | {{key_mechanism_forbidden_change}} | {{key_mechanism_followup}} |
| 领域边界 | {{domain_boundary_baseline}} | {{domain_boundary_forbidden_change}} | {{domain_boundary_followup}} |
| 集成方向 | {{integration_baseline}} | {{integration_forbidden_change}} | {{integration_followup}} |
| 数据与状态方向 | {{data_state_baseline}} | {{data_state_forbidden_change}} | {{data_state_followup}} |
| 兼容与迁移方向 | {{compatibility_baseline}} | {{compatibility_forbidden_change}} | {{compatibility_followup}} |
| 验证重点 | {{validation_focus_baseline}} | {{validation_forbidden_change}} | {{validation_followup}} |

---

## Agent 架构

> 仅当任务涉及 Agent 能力时保留。本节只判断 Agent 能力是否影响系统路线，以及它的责任边界和不可越过的范围；组件工作权、约束机制和评估场景由技术分析阶段（technical_analysis）的 Agent 能力子流程继续展开。

| Agent 组件 | 架构责任 | 工作权边界方向 | 不得越过的边界 | 后续需细化内容 |
|---|---|---|---|---|
| {{agent_component_1}} | {{agent_responsibility_1}} | {{agent_rights_direction_1}} | {{agent_forbidden_boundary_1}} | {{agent_followup_1}} |

**Agent 相关路线判断：** {{agent_architecture_decision_summary}}

---

## 关键风险怎么处理

> 风险不能只写“后续缓解”。每个高优先级风险都必须说明本轮到底是验证、接受、阻断、降级还是回流。

| 风险 | 来源 | 优先级 | 处理方式 | 依据 | 后续责任 | 必需证据 |
|---|---|---|---|---|---|---|
| {{risk_id_1}} {{risk_statement_1}} | {{risk_source_1}} | 高 / 中 / 低 | 验证 / 接受 / 阻断 / 降级 / 回流 | {{risk_basis_1}} | {{risk_owner_stage_1}} | {{risk_required_evidence_1}} |

---

## 交给技术分析继续展开的内容

> 后续技术分析阶段（technical_analysis）应在本方案确定的路线内细化模块、接口、数据、依赖、迁移、错误处理和验证策略；不得重新选择架构路线。

| 后续主题 | 必须细化的问题 | 来源决策 | 停止或回流条件 |
|---|---|---|---|
| 模块边界 | {{module_boundary_question}} | {{decision_ref_1}} | {{return_condition_1}} |
| 接口方向 | {{interface_question}} | {{decision_ref_2}} | {{return_condition_2}} |
| 数据 / 状态流 | {{data_state_question}} | {{decision_ref_3}} | {{return_condition_3}} |
| 依赖与迁移 | {{dependency_migration_question}} | {{decision_ref_4}} | {{return_condition_4}} |
| 验证策略 | {{verification_question}} | {{decision_ref_5}} | {{return_condition_5}} |

---

## 已知遗留问题

> 仅记录已经明确接受、且不会影响进入技术分析阶段（technical_analysis）的问题。会影响路线选择的问题不能留到这里。

| 问题 | 接受依据 | 影响 | 后续处理建议 |
|---|---|---|---|
| {{issue_1}} | {{acceptance_basis_1}} | {{impact_1}} | {{followup_1}} |

---

## 审查摘要

> 由方案阶段在审查循环结束后补充。摘要只能说明审查结论和残留风险，不得替代上面的路线决策和风险处理。

{{review_summary}}
