# 执行简报: {{mission_id}}

> **来源**：拆解技能 → `harness-runtime/harness/stages/{{mission_id}}/execution-brief.md`
> **参考方法论**：OpenSpec Vertical Slicing（每个任务项是可独立交付的价值纵切片）；TDD Red-Green-Refactor
> **TDD 计划契约**：`.harness/docs/tdd-planning-contract.md`
> **设计原则**：读完这一份文件就能理解任务边界、验收、Atomic Task 队列和证据要求。`execution-brief.md` 是唯一执行计划产物，不再生成第二份计划文件。
> **上游**：`product/product-definition.md` | `solution.md` | `tech-design.md` | `mission-contract.md`

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}

---

## 控制契约

> Action Contract 是执行 / code-review / 验证的任务边界和证据要求索引。它声明 required evidence，不要求这些 evidence 在拆解阶段已经存在。

- Contract: `contracts/execution-brief.contract.yaml`
- Authority: 外部 YAML 是控制契约权威来源；本文的 `Atomic Task Queue` 是执行队列权威来源。Markdown 不承载 `execution_result`、`role_verdicts` 或 Gate 结果。


---

## TL;DR

> 一句话说清楚：做什么、产出是什么、执行者最需要注意什么。

{{execution_tldr}}

---

## 任务目标

> 从任务契约 AC 提炼，执行完成后系统处于什么状态。
> 目标是完成可验收的生产纵切片，不是做一个演示级 demo。

{{task_objective}}

**对应 AC：**
- AC-01: {{ac_01_summary}}
- AC-02: {{ac_02_summary}}

---

## 硬性约束

> 硬性限制，违反任何一条都是阻断性问题。来自上游文档提炼。

| 约束 | 来源 | 说明 |
|-----|------|------|
| {{constraint_1}} | 任务契约 / prd / tech-design | {{constraint_1_desc}} |
| {{constraint_2}} | project-context | {{constraint_2_desc}} |

**编码规范要点：** {{coding_standards}}
**技术选择限制：** {{tech_constraints}}
**已知的坑：** {{known_pitfalls}}

---

## 接口与数据变更速查

> 从 tech-design 提炼接口和数据变更，方便执行时快速查阅。

### 新增/修改接口

| 接口 | 变更类型 | 签名摘要 |
|-----|---------|---------|
| {{interface_1}} | 新增/修改 | {{interface_1_signature}} |

### 数据模型变更

| 模型/表 | 变更类型 | 字段摘要 |
|-------|---------|---------|
| {{model_1}} | 新增/修改 | {{model_1_fields}} |

---

## Atomic Task Queue 规则

> execution-brief 用 `Execution Units` 一次性承载 Parent task 及其内嵌执行队列。Parent task 永远是交付切片 / Work Graph TASK 边界；Atomic Task 永远是 execute 的实际执行单位。简单 Parent task 也必须至少有 1 个 Atomic Task。
>
> **生成规则**：breakdown 首次写入本文件前，必须完成 Parent task + parent-local `atomic_task_queue` 的联合设计。不得先写 Parent task 骨架，再把 Atomic Task Queue 作为 breakdown 后的常规补丁追加。
>
> **冲突处理**：Parent task 的任务边界 / 验收 / required evidence 是权威边界；内嵌 Atomic Task Queue 负责文件级行动、TDD scope、fixture、命令、证据和停止条件。若 Atomic Task 与父任务边界冲突、缺失覆盖或无法映射，停止 execute，回到 breakdown 修复计划或发起 Decision Gate。

**Atomic task queue:** 每个 Parent task 下都必须有 `atomic_task_queue:`，有效状态只能是 `ready`。若出现缺失、空队列或 `incomplete`，本文件不得进入 Stage Gate。

| 检查项 | 状态 | 说明 |
|-------|------|------|
| single_action | {{ready_or_missing}} | {{single_action_note}} |
| explicit_inputs_outputs | {{ready_or_missing}} | {{explicit_inputs_outputs_note}} |
| parent_task_coverage | {{ready_or_missing}} | {{parent_task_coverage_note}} |
| ac_scenario_coverage | {{ready_or_missing}} | {{ac_scenario_coverage_note}} |
| code_pattern_references | {{ready_or_missing}} | {{code_pattern_references_note}} |
| interface_or_data_contracts | {{ready_or_missing}} | {{interface_or_data_contracts_note}} |
| test_fixtures_and_seed_data | {{ready_or_missing}} | {{test_fixtures_and_seed_data_note}} |
| validation_commands | {{ready_or_missing}} | {{validation_commands_note}} |
| transaction_or_state_boundaries | {{ready_or_missing}} | {{transaction_or_state_boundaries_note}} |
| evidence_requirements | {{ready_or_missing}} | {{evidence_requirements_note}} |
| stop_conditions | {{ready_or_missing}} | {{stop_conditions_note}} |
| migration_or_route_boundaries | {{ready_or_missing}} | {{migration_or_route_boundaries_note}} |

**Queue completeness:** {{atomic_task_queue_completeness}}
**缺口处理：** {{atomic_task_queue_gap_handling}}

---

## 已知风险与注意事项

> 来自 solution、tech-design 和 project-context 中标注的风险。

| 风险 | 可能性 | 缓解措施 |
|-----|--------|---------|
| {{risk_1}} | 高/中/低 | {{mitigation_1}} |
| {{risk_2}} | 高/中/低 | {{mitigation_2}} |

---

## Execution Units

> 这是唯一执行计划结构。execute 只按本节遍历：先按 Parent task 顺序，再按该 Parent task 内的 `atomic_task_queue.execution_units[]` 执行。
> Parent task 和 Atomic Task 不并列、不独立；Atomic Tasks 必须嵌在对应 Parent task 下。不得在文件其他位置维护第二份全局队列。简单 Parent task 使用一个 Atomic Task 表达。
> TDD scope 必须按 `.harness/docs/tdd-planning-contract.md` 设计：先定义行为模型、Red 失败目标、Green 边界、Refactor 边界、禁止范围、断言、测试数据、test doubles 和 fault / mutation 信号，再进入 execute。

<!-- 对每个 Parent task 重复使用以下完整结构。不得为第 2 个或后续任务省略字段。 -->

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
    status: "ready" # ready only for a valid execution-brief; incomplete blocks Stage Gate
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

**Depends on:** {{parent_task_dependencies}} # none / T001 / T001,T002

**目标：** 完成后系统的变化：{{parent_task_outcome}}

**完成边界：** {{parent_task_completion_boundary}}

**Parent-level implementation boundary：**
> 这里只写模块 / surface 级边界，不写文件级步骤。文件级行动、write_scope、fixture、命令和停止条件必须写在本 Parent task 的 Atomic Task details 中。
- {{parent_task_impl_boundary_1}}
- {{parent_task_impl_boundary_2}}

**测试要求：**
- **Given** {{parent_task_given}}
- **When** {{parent_task_when}}
- **Then** {{parent_task_then}}

**TDD Scope Contract：**
> 本节定义 Parent task 的 TDD 行为边界，不允许 execute 阶段临场改写测试目标。测试文件、fixture、命令和 Red/Green 细节必须在该 Parent task 的 Atomic Task details 中展开。

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

**Test Obligation：**
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

**E2E Obligation：**
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

**Authorized path summary：**
> 这里只是 Parent 级授权范围摘要，真实 write scope 必须来自本 Parent task 的 `atomic_task_queue.execution_units[]`。
| 文件 | 变更类型 |
|-----|---------|
| {{parent_task_authorized_path_1}} | 新增/修改 |

**Parent completion checklist：**
- [ ] 本 Parent task 下的全部 Atomic Tasks 已完成 Red → Green → Refactor → Regression。
- [ ] Parent task 的完成边界、DoD、required evidence 和 stop conditions 均被满足。
- [ ] 验收相关行为和高风险行为已有测试有效性证据（fault injection / mutation / 等价证明）
- [ ] `test_obligation` 的 required capabilities 均有工具证据或等价证据
- [ ] `e2e_obligation` 的 required capabilities 均有 E2E 工具证据、API/contract 证据或已接受替代证据

**Atomic Task details：**
> 每个 `atomic_task_queue.execution_units[]` 必须有一个同 ID 的详情块。结构块和详情块的 `id`、`execution_order`、`depends_on`、`write_scope` 必须一致；不一致时停止 execute，回到 breakdown 修复计划或发起 Decision Gate。
> Atomic Task detail 不是表格索引，也不重复 `atomic_task_queue.execution_units[]` 的调度元数据。它必须是可直接供 execute 生成 dispatch plan 的任务说明块。表格只能用于局部清单，例如文件或代码模式参考。

#### {{atomic_task_id}}

**标题：** {{atomic_task_title}}

**Parent task：** {{parent_task_id}} - {{parent_task_title}}

**队列元数据：** 见 `atomic_task_queue.execution_units[]` 中 `detail_ref: "{{atomic_task_id}}"` 对应项。

**目标**

{{atomic_task_goal}}

**执行边界**

- Include: {{atomic_scope_include}}
- Exclude: {{atomic_scope_exclude}}
- Stop before: {{atomic_stop_before}}

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

<!-- 重复上面的完整 Parent task 结构，直到覆盖全部任务项。 -->

## Definition of Done

> 所有任务项完成后，必须满足以下全部条件，Stage Gate 才能把当前 task node 推进到 code-review / verification lane action。

- [ ] 所有 Parent completion checklist 全部勾选
- [ ] 所有 AC 均有对应测试覆盖
- [ ] 无回归（现有测试全部通过）
- [ ] 代码已提交，branch 干净
- [ ] {{custom_completion_criteria_1}}

---

## 验收标准速查

> 从任务契约复制，执行者随时对照。

| AC-ID | 描述 | Given | When | Then |
|-------|------|-------|------|------|
| AC-01 | {{ac_01_desc}} | {{ac_01_given}} | {{ac_01_when}} | {{ac_01_then}} |
| AC-02 | {{ac_02_desc}} | {{ac_02_given}} | {{ac_02_when}} | {{ac_02_then}} |

---

## 上游文档引用

> 快速链接，执行过程中如需查阅上游决策，直接跳转。

| 文档 | 路径 | 章节 |
|-----|------|---------|
| 任务契约 | `harness-runtime/harness/missions/{{mission_id}}/mission-contract.md` | AC、约束 |
| 产品定义 | `harness-runtime/harness/stages/{{mission_id}}/product/product-definition.md` | FR、NFR |
| Solution | `harness-runtime/harness/stages/{{mission_id}}/solution.md` | 决策 1、决策 2 |
| Tech 设计 | `harness-runtime/harness/stages/{{mission_id}}/tech-design.md` | 模块划分、接口定义 |
