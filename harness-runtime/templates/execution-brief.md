# 执行简报: {{mission_id}}

> **来源**：拆解技能 → `harness-runtime/harness/artifacts/{{mission_id}}/breakdown/execution-brief.md`
> **参考方法论**：OpenSpec 纵向切片（Vertical Slicing，每个任务项是可独立交付的价值纵切片）；测试驱动开发（TDD）的红灯 / 绿灯 / 重构（Red-Green-Refactor）
> **TDD 计划契约**：`.harness/docs/tdd-planning-contract.md`
> **设计原则**：读完这一份文件就能理解任务边界、验收、原子任务（Atomic Task）队列和证据要求。执行简报（`execution-brief.md`）是唯一执行计划产物，不再生成第二份计划文件。
> **上游**：`product/product-definition.md` | `product/use-case-model.md` | `product/acceptance-scenarios.md` | `product/product-domain-model.md` | `product/product-evidence.md` | `solution.md` | `tech-design.md` | `interaction.md`（如适用） | `interaction-spec/use-case-realization.md`（如适用） | `interaction-spec/surface-model.md`（如适用） | `interaction-spec/interaction-contract.md`（如适用） | `mission-contract.md`

**作者:** {{user_name}}
**日期:** {{date}}
**任务 ID:** {{mission_id}}

---

## 控制契约

> 动作契约（Action Contract）是执行 / 代码审查（code-review）/ 验证的任务边界和证据要求索引。它声明必需证据（required evidence），不要求这些证据在拆解阶段已经存在。

- Contract: `contracts/execution-brief.contract.yaml`
- Authority: 外部 YAML 是控制契约权威来源；本文的原子任务队列（`Atomic Task Queue`）是执行队列权威来源。Markdown 不承载 `execution_result`、`role_verdicts` 或门禁（Gate）结果。


---

## TL;DR

> 一句话说清楚：做什么、产出是什么、执行者最需要注意什么。

{{execution_tldr}}

---

## 任务目标

> 从任务契约、用例模型、`SUC-xx-OP-xx` 系统操作和验收场景 / 条件提炼，执行完成后系统处于什么状态。场景 / 条件 ID 只作为下游追溯锚点。
> 目标是完成可验收的生产纵切片，不是做一个演示级 demo。

{{task_objective}}

**对应验收场景 / 条件：**

| 验收场景 / 条件 | 下游追溯锚点 | 摘要 |
|----------------|--------------|------|
| {{acceptance_scenario_1}} | {{trace_anchor_1}} | {{acceptance_summary_1}} |
| {{acceptance_scenario_2}} | {{trace_anchor_2}} | {{acceptance_summary_2}} |

---

## 输入合格性判断

> 拆解阶段（breakdown）只做执行授权，不补造产品行为、方案路线或技术设计。以下任一项不足时，停止拆解并回流对应上游阶段。
>
> **填写约定**：
> - `结论` 只能写：`fit`、`return_to_prd`、`return_to_solution`、`return_to_tech_design`、`return_to_interaction`、`return_to_agent_capability_design`、`needs_decision`。
> - `证据 / 缺口` 必须引用上游文档章节、ID、表格项或稳定标题；不得只写“已确认”“无”“待补充”。
> - `处理` 在 `fit` 时必须说明已从该输入推出了哪些执行义务；在回流或决策（return / decision）时必须说明回流目标、缺少的上游结论，以及继续拆解会造成的执行风险。
> - 判为 `fit` 的输入，至少要能推出一个父任务（Parent task）边界、一个验证义务和一个停止条件；否则不能进入任务拆解。

| 输入判断 | 结论 | 证据 / 缺口 | 处理 |
|---------|------|-------------|------|
| 产品定义包中的系统用例、系统操作、验收场景 / 条件和质量与运行约束足以判断执行义务 | {{product_definition_input_fit}} | {{product_definition_input_fit_evidence}} | {{product_definition_input_fit_action}} |
| 方案路线、禁止路线和风险处理方式已明确 | {{solution_input_fit}} | {{solution_input_fit_evidence}} | {{solution_input_fit_action}} |
| 模块责任、接口契约、数据 / 状态变化和验证策略可执行 | {{tech_design_input_fit}} | {{tech_design_input_fit_evidence}} | {{tech_design_input_fit_action}} |
| 交互 / 前端 / 智能体（Agent）能力边界已满足本轮需要 | {{conditional_input_fit}} | {{conditional_input_fit_evidence}} | {{conditional_input_fit_action}} |

**输入义务登记表：**

| 来源 | 可推出的执行义务 | 是否足够 | 处理动作 |
|------|------------------|----------|----------|
| {{input_source_1}} | {{derived_execution_obligation_1}} | {{input_obligation_fit_1}} | {{input_obligation_action_1}} |
| {{input_source_2}} | {{derived_execution_obligation_2}} | {{input_obligation_fit_2}} | {{input_obligation_action_2}} |

---

## 迭代授权摘要

> 说明本轮为什么可以进入执行阶段（execute）：交付什么增量、先处理什么风险、授权什么变更集、哪些内容明确不做。
>
> **填写约定**：
> - 本轮增量目标使用句式：`完成 <用户或系统可观察结果>，验证 / 降低 <关键风险>，授权 <变更集范围>`。
> - 风险焦点必须来自方案（solution）、技术设计（tech-design）、项目上下文（project-context）或上游证据；不得写“质量风险”“稳定性风险”这类无法验证的泛化表述。
> - 纳入（Include）/ 排除（Exclude）/ 延后（Deferred）必须写到能力（capability）、作用面（surface）、接口、数据、模块或目录级边界；不得只写“相关代码”。
> - 停止 / 回流条件必须写触发信号和回流目标，例如回产品定义阶段、方案（solution）、技术设计（tech-design）、交互设计（interaction）、智能体能力设计（Agent capability design）或决策门禁（Decision Gate）。

**本轮增量目标：** {{iteration_increment_goal}}

**本轮风险焦点：**
- {{iteration_risk_focus_1}}
- {{iteration_risk_focus_2}}

**授权变更集边界：**
- 纳入（Include）: {{iteration_change_set_include}}
- 排除（Exclude）: {{iteration_change_set_exclude}}
- 延后（Deferred）: {{iteration_change_set_deferred}}

**停止 / 回流条件：**
- {{iteration_return_condition_1}}
- {{iteration_return_condition_2}}

---

## RUP 拆解约定

> 本节把 RUP 的“用例实现 / 迭代计划 / 风险驱动”落到拆解阶段（breakdown）的可执行方法。写执行简报（execution-brief）时必须先建义务映射，再切父任务（Parent task）和原子任务（Atomic Task）。

**执行义务映射：**

| 上游义务 | 来源 | 关联流步骤 / 系统操作 | 执行义务 | 授权变更面 | 验证方式 | 处理方式 |
|----------|------|--------------------|----------|------------|----------|----------|
| {{upstream_obligation_1}} | {{obligation_source_1}} | SUC-01-FLOW-01 / SUC-01-OP-01 | {{execution_obligation_1}} | {{authorized_surface_1}} | {{verification_method_1}} | {{obligation_handling_1}} |
| {{upstream_obligation_2}} | {{obligation_source_2}} | {{flow_or_operation_ref_2}} | {{execution_obligation_2}} | {{authorized_surface_2}} | {{verification_method_2}} | {{obligation_handling_2}} |

**系统操作覆盖检查：**

| 系统操作 ID | 技术设计落点 | 父任务 | 原子任务 | 验证义务 | 覆盖结论 |
|-------------|--------------|--------|----------|----------|----------|
| SUC-01-OP-01 | {{tech_design_landing}} | PT-{{id}} | AT-{{id}} | {{verification_obligation}} | covered / return_to_tech_design |

**父任务（Parent task）切分方法：**

- 合并条件：多个义务只有共享同一用户可观察结果、同一事务一致性边界、同一风险验证目标或同一不可拆变更集时，才能进入同一个父任务（Parent task）。
- 拆分条件：不同验收结果、失败定位、回滚边界、权限 / 数据 / 界面作用面（UI surface）、外部依赖、并行写冲突，必须拆成不同父任务（Parent task）或声明串行依赖。
- 命名约定：`<交付结果> / <风险目标> / <变更边界>`。禁止使用“修改 API”“实现前端”“补测试”这类只描述层或动作的标题。
- 每个父任务（Parent task）必须能回答：本轮交付什么增量，覆盖哪些 `SUC-xx-OP-xx`，处理哪个关键风险，授权哪些变更面，哪些内容明确不做。

**原子任务（Atomic Task）切分方法：**

- 一个原子任务（Atomic Task）只能有一个工程行动或一个验证行动；如果需要不同验证命令、改动多个独立作用面（surface），或失败时无法定位原因，继续拆分。
- 每个原子任务（Atomic Task）必须写明输入、输出、关联 `SUC-xx-OP-xx`、读写范围、参考样板、验证命令、证据路径和停止条件。
- 原子任务（Atomic Task）不能是纯准备、纯清理或纯待办（TODO）；必须产出代码、测试、配置、迁移演练、评估脚本或可验收证据之一。

---

## 硬性约束

> 硬性限制，违反任何一条都是阻断性问题。来自上游文档提炼。

| 约束 | 来源 | 说明 |
|-----|------|------|
| {{constraint_1}} | 任务契约 / 产品定义包 / 技术设计（tech-design） | {{constraint_1_desc}} |
| {{constraint_2}} | project-context | {{constraint_2_desc}} |

**编码规范要点：** {{coding_standards}}
**技术选择限制：** {{tech_constraints}}
**已知的坑：** {{known_pitfalls}}

---

## 接口与数据变更速查

> 从技术设计（tech-design）提炼接口和数据变更，方便执行时快速查阅。

### 新增/修改接口

| 接口 | 变更类型 | 签名摘要 |
|-----|---------|---------|
| {{interface_1}} | 新增/修改 | {{interface_1_signature}} |

### 数据模型变更

| 模型/表 | 变更类型 | 字段摘要 |
|-------|---------|---------|
| {{model_1}} | 新增/修改 | {{model_1_fields}} |

---

## 风险优先级与任务顺序

> 任务顺序按依赖和风险消减共同决定。高风险 / 高不确定性任务应先验证，避免后续实现依赖未经证明的假设。
>
> **排序方法**：
> 1. 先做依赖拓扑排序：接口、数据、权限、状态机、外部依赖、智能体（Agent）约束和端到端（E2E）用户路径的前置关系必须显式写出。
> 2. 再做风险前置调整：会影响后续任务是否成立的假设验证，排在依赖它的实现任务之前。
> 3. 如果两个任务写入范围冲突，必须串行化并说明原因；不能用并行执行掩盖冲突。

| 顺序 | 父任务（Parent task） | 优先原因 | 处理的风险 / 不确定性 | 下游依赖 |
|-----|-------------|----------|-----------------------|----------|
| 1 | {{risk_order_task_1}} | {{risk_order_reason_1}} | {{risk_order_risk_1}} | {{risk_order_downstream_1}} |
| 2 | {{risk_order_task_2}} | {{risk_order_reason_2}} | {{risk_order_risk_2}} | {{risk_order_downstream_2}} |

---

## 原子任务队列（Atomic Task Queue）规则

> 执行简报（execution-brief）用执行单元（`Execution Units`）一次性承载父任务（Parent task）及其内嵌执行队列。父任务永远是交付切片 / 工作图任务节点（Work Graph TASK）边界；原子任务（Atomic Task）永远是执行阶段（execute）的实际执行单位。简单父任务也必须至少有 1 个原子任务。
>
> **生成规则**：拆解阶段（breakdown）首次写入本文件前，必须完成父任务（Parent task）+ 父任务本地 `atomic_task_queue` 的联合设计。不得先写父任务骨架，再把原子任务队列（Atomic Task Queue）作为拆解后的常规补丁追加。
>
> **冲突处理**：父任务（Parent task）的任务边界 / 验收 / 必需证据（required evidence）是权威边界；内嵌原子任务队列（Atomic Task Queue）负责文件级行动、测试驱动开发范围（TDD scope）、测试夹具（fixture）、命令、证据和停止条件。若原子任务与父任务边界冲突、缺失覆盖或无法映射，停止执行（execute），回到拆解阶段（breakdown）修复计划或发起决策门禁（Decision Gate）。

**原子任务队列（Atomic task queue）:** 每个父任务（Parent task）下都必须有 `atomic_task_queue:`，有效状态只能是 `ready`。若出现缺失、空队列或 `incomplete`，本文件不得进入阶段门禁（Stage Gate）。

| 检查项 | 状态 | 说明 |
|-------|------|------|
| single_action | {{ready_or_missing}} | {{single_action_note}} |
| explicit_inputs_outputs | {{ready_or_missing}} | {{explicit_inputs_outputs_note}} |
| parent_task_coverage | {{ready_or_missing}} | {{parent_task_coverage_note}} |
| acceptance_scenario_coverage | {{ready_or_missing}} | {{acceptance_scenario_coverage_note}} |
| code_pattern_references | {{ready_or_missing}} | {{code_pattern_references_note}} |
| interface_or_data_contracts | {{ready_or_missing}} | {{interface_or_data_contracts_note}} |
| test_fixtures_and_seed_data | {{ready_or_missing}} | {{test_fixtures_and_seed_data_note}} |
| validation_commands | {{ready_or_missing}} | {{validation_commands_note}} |
| transaction_or_state_boundaries | {{ready_or_missing}} | {{transaction_or_state_boundaries_note}} |
| evidence_requirements | {{ready_or_missing}} | {{evidence_requirements_note}} |
| stop_conditions | {{ready_or_missing}} | {{stop_conditions_note}} |
| migration_or_route_boundaries | {{ready_or_missing}} | {{migration_or_route_boundaries_note}} |

**队列完整性（Queue completeness）:** {{atomic_task_queue_completeness}}
**缺口处理：** {{atomic_task_queue_gap_handling}}

---

## 已知风险与注意事项

> 来自方案（solution）、技术设计（tech-design）和项目上下文（project-context）中标注的风险。

| 风险 | 可能性 | 缓解措施 |
|-----|--------|---------|
| {{risk_1}} | 高/中/低 | {{mitigation_1}} |
| {{risk_2}} | 高/中/低 | {{mitigation_2}} |

---

## Execution Units

> 这是唯一执行计划结构。执行阶段（execute）只按本节遍历：先按父任务（Parent task）顺序，再按该父任务内的 `atomic_task_queue.execution_units[]` 执行。
> 父任务（Parent task）和原子任务（Atomic Task）不并列、不独立；原子任务必须嵌在对应父任务下。不得在文件其他位置维护第二份全局队列。简单父任务使用一个原子任务表达。
> 测试驱动开发范围（TDD scope）必须按 `.harness/docs/tdd-planning-contract.md` 设计：先定义行为模型、红灯失败目标（Red）、绿灯边界（Green）、重构边界（Refactor）、禁止范围、断言、测试数据、测试替身（test doubles）和故障 / 变异信号（fault / mutation），再进入执行阶段（execute）。
>
> **父任务（Parent task）填写约定**：
> - 标题使用 `<交付结果> / <风险目标> / <变更边界>`，并能追溯到验收场景 / 条件、Scenario、domain rule 或 tech-design ID。
> - `本轮增量价值` 写用户或系统可观察结果，不写“完成后端开发”“补齐能力”。
> - `风险处理目标` 写要降低、验证或隔离的具体风险，并说明证据来源。
> - `授权变更集边界` 写纳入（Include）/ 排除（Exclude）/ 延后（Deferred）；如果边界不能写清，回技术设计（tech-design）或决策门禁（Decision Gate）。
> - 同一个父任务（Parent task）合并多个作用面（surface）时，必须说明共享的可观察结果、事务一致性边界或风险验证目标；否则拆分。

<!-- 对每个父任务（Parent task）重复使用以下完整结构。不得为第 2 个或后续任务省略字段。 -->

### {{parent_task_id}}: {{parent_task_title}}

```yaml
parent_task:
  id: "{{parent_task_id}}"
  title: "{{parent_task_title}}"
  depends_on:
    - "{{parent_task_dependency_id}}"
  authorized_path_summary:
    - "{{parent_task_authorized_path_1}}"
  required_evidence:
    - "{{parent_task_required_evidence}}"
  atomic_task_queue:
    status: "ready" # 只有有效 execution-brief 才能写 ready；incomplete 会阻断阶段门禁（Stage Gate）
    review_status: "{{atomic_task_queue_review_status}}" # pending | pass | hold
    execution_units:
      - id: "{{atomic_task_id}}"
        title: "{{atomic_task_title}}"
        execution_order: {{atomic_execution_order}}
        depends_on:
          - "{{atomic_dependency_id}}"
        write_scope:
          - "{{atomic_write_scope_path}}"
        read_scope:
          - "{{atomic_read_scope_path}}"
        detail_ref: "{{atomic_task_id}}"
        reviewer_verdict: "{{atomic_reviewer_verdict}}" # pending | pass | hold
        evidence_required:
          - red_report
          - green_report
          - regression_report
```

**依赖（Depends on）：** {{parent_task_dependencies}} # none / T001 / T001,T002

**本轮增量价值：** {{parent_task_increment_value}}

**风险处理目标：** {{parent_task_risk_burn_down}}

**授权变更集边界：**
- 纳入（Include）: {{parent_task_change_set_include}}
- 排除（Exclude）: {{parent_task_change_set_exclude}}
- 延后（Deferred）: {{parent_task_change_set_deferred}}

**目标：** 完成后系统的变化：{{parent_task_outcome}}

**完成边界：** {{parent_task_completion_boundary}}

**父任务级实现边界（Parent-level implementation boundary）：**
> 这里只写模块 / 作用面（surface）级边界，不写文件级步骤。文件级行动、写入范围（write_scope）、测试夹具（fixture）、命令和停止条件必须写在本父任务（Parent task）的原子任务详情（Atomic Task details）中。
- {{parent_task_impl_boundary_1}}
- {{parent_task_impl_boundary_2}}

**测试要求：**
- **Given** {{parent_task_given}}
- **When** {{parent_task_when}}
- **Then** {{parent_task_then}}

**测试驱动开发范围契约（TDD Scope Contract）：**
> 本节定义父任务（Parent task）的测试驱动开发（TDD）行为边界，不允许执行阶段（execute）临场改写测试目标。测试文件、测试夹具（fixture）、命令和红灯 / 绿灯（Red/Green）细节必须在该父任务的原子任务详情（Atomic Task details）中展开。

| 项 | 内容 |
|----|------|
| Behavior under test | {{parent_task_behavior_under_test}} |
| Red scope | {{parent_task_red_scope}} |
| Green scope | {{parent_task_green_scope}} |
| Refactor scope | {{parent_task_refactor_scope}} |
| Out of scope | {{parent_task_tdd_out_of_scope}} |
| Required assertions | {{parent_task_required_assertions}} |
| Test data boundary | {{parent_task_test_data_boundary}} |
| Allowed test doubles | {{parent_task_allowed_test_doubles}} |
| Forbidden shortcuts | {{parent_task_forbidden_shortcuts}} |
| Fault / mutation signal | {{parent_task_fault_or_mutation_signal}} |
| Command source | parent_local_atomic_task_queue |
| Red command / queue refs | {{parent_task_red_command_or_atomic_task_refs}} |
| Green command / queue refs | {{parent_task_green_command_or_atomic_task_refs}} |
| Regression command / queue refs | {{parent_task_regression_command_or_atomic_task_refs}} |

**测试义务（Test Obligation）：**
```yaml
risk_level: "{{parent_task_test_risk_level}}" # low | medium | high
surfaces:
  - "{{parent_task_test_surface}}"
required_capabilities:
  - "{{parent_task_required_test_capability}}"
evidence_required:
  - "{{parent_task_required_test_evidence}}"
accepted_alternatives:
  "{{parent_task_test_capability}}":
    - "{{parent_task_accepted_test_alternative}}"
```

**端到端义务（E2E Obligation）：**
```yaml
risk_level: "{{parent_task_e2e_risk_level}}" # none | low | medium | high
user_surfaces:
  - "{{parent_task_user_surface}}"
required_capabilities:
  - "{{parent_task_required_e2e_capability}}"
evidence_required:
  - "{{parent_task_required_e2e_evidence}}"
accepted_alternatives:
  "{{parent_task_e2e_capability}}":
    - "{{parent_task_accepted_e2e_alternative}}"
```

**授权路径摘要（Authorized path summary）：**
> 这里只是父任务（Parent task）级授权范围摘要，真实写入范围（write scope）必须来自本父任务的 `atomic_task_queue.execution_units[]`。
| 文件 | 变更类型 |
|-----|---------|
| {{parent_task_authorized_path_1}} | 新增/修改 |

**父任务完成清单（Parent completion checklist）：**
- [ ] 本父任务（Parent task）下的全部原子任务（Atomic Tasks）已完成红灯 → 绿灯 → 重构 → 回归（Red → Green → Refactor → Regression）。
- [ ] 父任务的完成边界、完成定义（DoD）、必需证据（required evidence）和停止条件（stop conditions）均被满足。
- [ ] 验收相关行为和高风险行为已有测试有效性证据（fault injection / mutation / 等价证明）
- [ ] `test_obligation` 的 required capabilities 均有工具证据或等价证据
- [ ] `e2e_obligation` 的 required capabilities 均有 E2E 工具证据、API/contract 证据或已接受替代证据

**原子任务详情（Atomic Task details）：**
> 每个 `atomic_task_queue.execution_units[]` 必须有一个同 ID 的详情块。结构块和详情块的 `id`、`execution_order`、`depends_on`、`write_scope` 必须一致；不一致时停止执行（execute），回到拆解阶段（breakdown）修复计划或发起决策门禁（Decision Gate）。
> 原子任务详情（Atomic Task detail）不是表格索引，也不重复 `atomic_task_queue.execution_units[]` 的调度元数据。它必须是可直接供执行阶段（execute）生成派发计划（dispatch plan）的任务说明块。表格只能用于局部清单，例如文件或代码模式参考。
>
> **原子任务（Atomic Task）填写约定**：
> - 一个任务只写一个工程行动或一个验证行动；“实现接口和前端并补测试”必须拆分。
> - `执行边界` 必须先写纳入（Include）/ 排除（Exclude）/ 停止前置点（Stop before），避免执行阶段（execute）临场扩大范围。
> - `文件行动` 必须与队列（queue）的写入范围（`write_scope`）对齐；新增文件、修改文件、删除文件要分别说明目的。
> - `代码模式参考` 必须指向真实可读路径；没有样板时，`pattern_type` 写 `no_match` 并说明搜索范围。
> - `执行期验证命令` 必须能产出 `证据` 中声明的路径或报告；无法提供命令时必须写已接受替代方案（accepted alternative）和审批需求。

#### {{atomic_task_id}}

**标题：** {{atomic_task_title}}

**父任务（Parent task）：** {{parent_task_id}} - {{parent_task_title}}

**队列元数据：** 见 `atomic_task_queue.execution_units[]` 中 `detail_ref: "{{atomic_task_id}}"` 对应项。

**目标**

{{atomic_task_goal}}

**执行边界**

- 纳入（Include）: {{atomic_scope_include}}
- 排除（Exclude）: {{atomic_scope_exclude}}
- 停止前置点（Stop before）: {{atomic_stop_before}}

**文件行动**

```yaml
files:
  - path: "{{atomic_file_1}}"
    action: "create | modify | delete"
    purpose: "{{atomic_file_1_purpose}}"
```

**输入**
- {{atomic_input_1}}

**输出**
- {{atomic_output_1}}

**代码模式参考**

```yaml
references:
  - path: "{{reference_file}}"
    pattern_type: "showroom | same_surface | test_pattern | migration_pattern | no_match"
    symbol: "{{reference_symbol}}"
    observed_convention: "{{observed_convention}}"
    apply_to_this_task: "{{apply_to_this_task}}"
    do_not_copy: "{{do_not_copy}}"
```

**接口 / 数据契约**

{{atomic_interface_or_data_contract}}

**TDD 范围**

- Behavior under test: {{atomic_behavior_under_test}}
- Red scope: {{atomic_red_scope}}
- Green scope: {{atomic_green_scope}}
- Refactor scope: {{atomic_refactor_scope}}
- Out of scope: {{atomic_tdd_out_of_scope}}
- Required assertions: {{atomic_required_assertions}}
- Test data boundary: {{atomic_test_data_boundary}}
- Test doubles boundary: {{atomic_test_doubles_boundary}}
- Fault / mutation signal: {{atomic_fault_or_mutation_signal}}

**执行期验证命令**

```yaml
commands:
  red:
    cwd: "{{atomic_red_command_cwd}}"
    command: "{{atomic_red_command}}"
    expected_signal: "{{atomic_red_expected_signal}}"
  green:
    cwd: "{{atomic_green_command_cwd}}"
    command: "{{atomic_green_command}}"
    expected_signal: "{{atomic_green_expected_signal}}"
  regression:
    cwd: "{{atomic_regression_command_cwd}}"
    command: "{{atomic_regression_command}}"
    expected_signal: "{{atomic_regression_expected_signal}}"
```

**证据**

- red_report: {{atomic_red_report_path}}
- green_report: {{atomic_green_report_path}}
- regression_report: {{atomic_regression_report_path}}
- {{additional_evidence}}: {{additional_evidence_path}}

**停止条件**

- {{atomic_stop_condition_1}}

---

<!-- 重复上面的完整父任务（Parent task）结构，直到覆盖全部任务项。 -->

## Definition of Done

> 所有任务项完成后，必须满足以下全部条件，阶段门禁（Stage Gate）才能把当前任务节点（task node）推进到代码审查 / 验证泳道动作（code-review / verification lane action）。

- [ ] 所有 Parent completion checklist 全部勾选
- [ ] 所有验收场景 / 条件均有对应测试覆盖
- [ ] 无回归（现有测试全部通过）
- [ ] 代码已提交，branch 干净
- [ ] {{custom_completion_criteria_1}}

---

## 验收场景 / 条件速查

> 从任务契约和验收场景复制，执行者随时对照。场景 / 条件 ID 只作为下游追溯锚点，不是新的需求类型。

| 验收场景 / 条件 | 下游追溯锚点 | Given | When | Then |
|----------------|--------------|-------|------|------|
| {{acceptance_scenario_1}} | {{trace_anchor_1}} | {{given_1}} | {{when_1}} | {{then_1}} |
| {{acceptance_scenario_2}} | {{trace_anchor_2}} | {{given_2}} | {{when_2}} | {{then_2}} |

---

## 上游文档引用

> 快速链接，执行过程中如需查阅上游决策，直接跳转。

| 文档 | 路径 | 章节 |
|-----|------|---------|
| 任务契约 | `harness-runtime/harness/missions/{{mission_id}}/mission-contract.md` | 验收场景 / 条件、质量与运行约束 |
| 产品定义 | `harness-runtime/harness/artifacts/{{mission_id}}/product/product-definition.md` | 系统责任、质量与运行约束 |
| 用例模型 | `harness-runtime/harness/artifacts/{{mission_id}}/product/use-case-model.md` | 已确认系统用例、界面承载要求 |
| 验收场景 | `harness-runtime/harness/artifacts/{{mission_id}}/product/acceptance-scenarios.md` | 验收场景 / 条件、验收追溯锚点 |
| 方案 | `harness-runtime/harness/artifacts/{{mission_id}}/solution/solution.md` | 决策 1、决策 2 |
| 技术设计 | `harness-runtime/harness/artifacts/{{mission_id}}/technical-analysis/tech-design.md` | 模块划分、接口定义 |
| 交互用例实现 | `harness-runtime/harness/artifacts/{{mission_id}}/interaction/interaction-spec/use-case-realization.md` | 用例到交互路径的执行边界 |
| 界面模型 | `harness-runtime/harness/artifacts/{{mission_id}}/interaction/interaction-spec/surface-model.md` | 界面、信息架构和领域映射 |
| 交互合同 | `harness-runtime/harness/artifacts/{{mission_id}}/interaction/interaction-spec/interaction-contract.md` | 路径、状态和端到端义务 |
