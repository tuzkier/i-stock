# 原型交互设计: {{mission_id}}

> **来源**：交互阶段动作 → `harness-runtime/harness/artifacts/{{mission_id}}/interaction/interaction.md`
> **上游**：`product/product-definition.md` | `product/use-case-model.md` | `product/acceptance-scenarios.md` | `product/product-domain-model.md` | `product/product-evidence.md` | `mission-contract.md` | 差量规格 | 项目上下文
> **目的**：把产品定义阶段产出的系统用例、系统行为描述、`SUC-xx-FLOW-xx` 流步骤、`SUC-xx-OP-xx` 系统操作、界面承载要求、验收场景 / 条件和领域模型转成可实现、可预览、可验证的交互路径、状态反馈与原型契约。

**作者：** {{user_name}}
**日期：** {{date}}
**任务编号：** {{mission_id}}
**状态：** `draft` <!-- 状态枚举：draft / in-review / approved / blocked -->

---

## 总览

> 用 2-3 句话说明本次原型交互设计覆盖哪些系统用例、用户目标、领域对象、界面 / 组件和状态边界。

{{interaction_overview}}

| 字段 | 值 |
|------|----|
| 交互范围 | {{interaction_scope}} |
| 主要用户 | {{primary_user}} |
| 关键入口 | {{entry_points}} |
| 不在范围内 | {{out_of_scope}} |

---

## 交互分析方法与约定

> 本节不写字段名清单，而是说明本次交互设计按什么方法完成。详细分析进入固定标准包：`use-case-realization.md` 承载用例实现，`surface-model.md` 承载界面模型，`interaction-contract.md` 承载下游实现合同。

| 方法 | 本次做法 | 主要证据 | 输出位置 |
|------|----------|----------|----------|
| 输入合格检查 | {{input_readiness_method}} | {{input_readiness_evidence}} | `interaction-spec/use-case-realization.md#输入就绪检查` |
| 用例实现分析 | {{use_case_realization_method}} | {{use_case_flow_evidence}} | `interaction-spec/use-case-realization.md#用例流实现` |
| 系统操作覆盖与自洽校验 | {{system_use_case_behavior_method}} | {{system_use_case_behavior_evidence}} | `interaction-spec/use-case-realization.md#系统操作覆盖与自洽校验` |
| 界面边界判断 | {{surface_decision_method}} | {{surface_baseline_evidence}} | `interaction-spec/surface-model.md#界面边界与变更` |
| 信息架构设计 | {{ia_method}} | {{ia_evidence}} | `interaction-spec/surface-model.md#信息架构` |
| 领域到界面映射 | {{domain_ui_method}} | {{domain_ui_evidence}} | `interaction-spec/surface-model.md#领域到界面映射` |
| 状态与交互设计 | {{state_interaction_method}} | {{state_interaction_evidence}} | `interaction-spec/interaction-contract.md#路径状态与交互` |
| 验证义务定义 | {{verification_obligation_method}} | {{verification_evidence}} | `interaction-spec/interaction-contract.md#验证义务` |

| 约定项 | 本次约定 | 例外 / 理由 |
|--------|----------|-------------|
| 编号前缀 | SUC / UIC / SURF / FLOW / STATE / INT / SCN-UI / VAL / E2E / CONS | {{id_exception_reason}} |
| 界面边界命名 | 使用稳定领域语言，不带任务号、日期或版本号 | {{surface_naming_exception}} |
| 追溯规则 | 每条设计记录至少追溯一个系统用例流步骤、系统操作、验收场景 / 条件、领域对象或差量规格 | {{trace_exception_reason}} |
| 中文文案 | 用户可见文字默认中文 | {{copy_exception_reason}} |
| 定位器策略 | P0 / P1 路径声明 `data-testid` 或可访问性定位器 | {{locator_exception_reason}} |

---

## 用例实现基线

> 本节先把产品定义阶段已确认的系统用例流转成交互实现基线，再进入界面边界、信息架构和原型设计。不得用页面清单或组件清单倒推用户路径。

| 系统用例 | 参与者 / 用户目标 | 流步骤范围 | 关联系统操作 | 备选流 | 异常流 | 界面承载要求 | 覆盖验收条件 |
|----------|-------------------|------------|--------------|--------|--------|--------------|------------|
| SUC-01 | {{actor_goal}} | SUC-01-FLOW-01..n | SUC-01-OP-01..n | {{alternative_flow}} | {{exception_flow}} | UIC-01 | {{acceptance_condition_ref}} |

| 用例流步骤 | 关联系统操作 | 交互边界 / 界面边界 | 用户动作 | 系统反馈 | 状态变化 | 恢复路径 | 验证义务 |
|------------|--------------|--------------------|----------|----------|----------|----------|----------|
| SUC-01-FLOW-01 | SUC-01-OP-01 / 不适用：{{reason}} | {{surface_or_boundary}} | {{user_action}} | {{visible_feedback}} | STATE-{{id}} | {{recovery_path}} | E2E-{{id}} / {{acceptance_condition_ref}} |

---

## 系统操作覆盖与自洽校验

> 本节只校验和承载 PRD 的 `SUC-xx-FLOW-xx` 流步骤与 `SUC-xx-OP-xx` 系统操作。交互阶段可以补充用户路径、界面状态、反馈和验证义务，但不得新增、删除或改写目标系统操作；发现必须改变系统行为时，进入产品定义回流检查。

| 系统操作 ID | 来源流步骤 | 交互路径 / 界面边界 | 用户动作 | 系统反馈 | 状态变化 | 是否保持 PRD 语义 | 缺口处理 |
|-------------|------------|--------------------|----------|----------|----------|-------------------|----------|
| SUC-01-OP-01 | SUC-01-FLOW-01 | FLOW-001 / SURF-001 | {{user_action}} | {{visible_feedback}} | STATE-{{id}} | 是 / 否，原因：{{semantic_change_reason}} | no_change / needs_prd_update / decision_gate |

---

## 领域模型到原型映射

> 从 `product/product-domain-model.md` 抽取关键实体、实体状态、用户动作、业务规则和权限边界，说明它们如何被原型界面承载。

| 领域对象 / 动作 / 状态 | 业务含义 | 原型承载位置 | 关联路径 / 状态 | 验收场景 / 条件 |
|------------------------|----------|--------------|-------------------|---------------|
| {{domain_entity_or_action}} | {{business_meaning}} | {{screen_or_component}} | {{flow_or_state_ref}} | {{acceptance_condition_ref}} / {{scenario_ref}} |

---

## 控制契约

> 交互指导契约记录用户路径、状态模型、可视化资产和审查义务，供拆解、执行、代码审查和验证消费。

- 控制契约（程序识别标记：Control Contract: `contracts/interaction.contract.yaml`）
- 权威来源：外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

## 原型合同与阅读顺序

> 长期原型视为一个原型工程；`interaction-spec/` 是本次任务对该原型工程的固定标准包。`use-case-realization.md` 说明用例如何落到交互，`surface-model.md` 说明界面如何承载领域语义，`interaction-contract.md` 说明下游如何实现和验证。主可操作原型必须在项目持有的独立原型工程目录（`prototype.interactive_prototype.prototype_project_root`，默认建议 `prototype/`，git 跟踪、随 Mission 分支隔离，不在 `project-knowledge/` 下、不在 mission artifact 下）持续迭代，阶段产物不再新增一套 `visual-interaction/prototype/` 主原型副本。说明、状态覆盖、组件清单和追溯信息只作为内部证据，不默认生成可见页面。评审反馈必须先回写固定标准包和本文件，再修改同一个独立原型工程入口。

| 顺序 | 读者 | 路径 | 用途 | 权威性 |
|------|------|------|------|--------|
| 1 | 人 / 智能体 | `interaction.md` | 阶段总览、范围、关键决策、沉淀候选 | 入口 |
| 2 | 智能体 / 门禁 | `contracts/interaction.contract.yaml` | 程序化契约、义务、追溯关系 | 程序化权威 |
| 3 | 智能体实现者 | `interaction-spec/use-case-realization.md` | 系统用例到交互实现基线 | 权威规格 |
| 4 | 智能体实现者 | `interaction-spec/surface-model.md` | 界面边界、信息架构和领域到界面映射 | 权威规格 |
| 5 | 智能体实现者 | `interaction-spec/interaction-contract.md` | 路径、状态、交互、验证义务和一致性体检 | 权威合同 |
| 6 | 人类确认 | 独立原型工程目录入口（`prototype_project_root`，默认建议 `prototype/`，由 `harness config snapshot` 解析） | 高还原可操作前端原型唯一默认入口 | 主原型 |
| 7 | 门禁 / 审查员 | `visual-interaction/visual-interaction-manifest.json` | 可视化资产索引和覆盖元数据 | 内部证据 |

### 固定产物标准

| 产物 | 是否默认生成 | 说明 |
|------|--------------|------|
| `interaction.md` | 是 | 阶段入口、人读摘要、关键决策、开放问题和沉淀候选 |
| `interaction-spec/use-case-realization.md` | 是 | 用例实现：输入合格性、系统用例到交互实现矩阵、用例流实现和产品定义回流条件 |
| `interaction-spec/surface-model.md` | 是 | 界面模型：界面边界、基线判断、信息架构、领域到界面映射和权限 / 状态承载 |
| `interaction-spec/interaction-contract.md` | 是 | 智能体交互实现合同：路径 / 状态 / 交互、验证义务、可视化证据和一致性体检 |
| 长期原型工程主入口 | 是 | 原型阶段必须有人确认；主可操作原型在独立原型工程目录持续迭代 |

`interaction-spec/` 只允许上述三份标准文档。其它说明、证据或临时材料必须归入三份标准文档的对应章节；可视化证据归入 `visual-interaction/evidence/**`。`visual-interaction/prototype/**` 不再作为主原型默认写入位置。

---

## 界面边界基线与变更范围

> 原型阶段必须判断当前任务是在已有界面上修改，还是创建新的系统界面边界。若修改既有界面，必须引用基线；不得每次生成一套孤立的新页面。

| 界面边界编号 | 限界上下文 / 模块 | 操作 | 基线引用 | 变更摘要 | 追溯 |
|------------|--------------------------|-----------|--------------|----------------|-------|
| SURF-001 | {{bounded_context}} | create_surface / modify_surface / extend_surface / retire_surface | {{existing_surface_ref_or_none}} | {{change_summary}} | {{acceptance_condition_ref}} / SCN-{{id}} |

---

## 原型工程增量变更

> 本节说明本次任务对长期原型工程的影响。主可操作原型在独立原型工程目录持续迭代；阶段产物只保存增量变更证据、manifest 和确认记录。

| 变更编号 | 原型区域 | 操作 | 基线 | 变更后原型状态 | 沉淀目标 |
|----------|----------------|-----------|----------|---------------------------|------------------|
| PATCH-001 | {{prototype_area}} | 创建 / 修改 / 扩展 / 废弃 | {{baseline_ref}} | {{result_summary}} | prototype_project_root（随分支合并）/ product/ui-surfaces / 不沉淀 |

---

## 原型与可视化交互资产

> 原型阶段必须提供长期原型工程主入口作为唯一默认人类入口，并在阶段完成前获得用户确认。复杂界面可补充截图、状态覆盖或录屏作为内部证据；人要看的仍然只有主原型页面。
> 视觉风格必须继承所在项目的设计系统、组件库和现有页面模式；如果没有设计系统，应在本节记录临时设计基线，不能让生成器默认审美覆盖项目风格。
> 主原型页面只呈现产品界面本身，不得混入阅读顺序、验收场景 / 追溯、路径 / 状态展板、审查员指引、清单说明或组件目录；这些内容进入 `interaction-spec/interaction-contract.md` 或内部 `visual-interaction/evidence/**`。
> 原型、HTML / SVG 变体和预览中的用户可见文字默认必须使用中文；品牌名、产品专名、代码标识、行业通用英文缩写或上游明确指定的外语文案可保留原文，但必须在一致性体检中说明。

| 资产编号 | 类型 | 路径 / 内容 | 覆盖范围 | 状态 |
|---------|------|-------------|----------|------|
| VIZ-001 | Mermaid 用户流程图 | 见下方 `用户流程图` | P0 用户路径 | 草稿 |
| VIZ-002 | 可操作原型 | 独立原型工程目录入口（`prototype_project_root`，默认建议 `prototype/`，由 `harness config snapshot` 解析） | P0 可点击路径 / 关键状态 / 桌面端和移动端 | 草稿 / 就绪 / 用户已确认 |
| VIZ-003 | 内部证据 | {{visual_artifact_path}} | {{covered_screen_or_flow_or_state}} | 草稿 / 就绪 |
| VIZ-MANIFEST | 资产清单 | `visual-interaction/visual-interaction-manifest.json` | 全部可视化资产索引 | 就绪 |

### 用户原型确认

| 项 | 结果 |
|----|------|
| 主原型入口 | {{prototype_entry_path_or_url}} |
| 确认范围 | {{confirmed_flows_states_viewports}} |
| 用户反馈 | {{user_feedback_summary}} |
| 结论 | PASS / FAIL |
| 记录 | `harness-runtime/harness/traces/{{mission_id}}/user-prototype-confirmation.md` |

### 风格来源

| 来源 | 路径 / 证据 | 本次如何继承 |
|------|-------------|--------------|
| 设计系统 / 主题 | {{design_system_path}} | {{style_inheritance}} |
| 既有页面 / 组件 | {{existing_ui_refs}} | {{component_pattern_reuse}} |

### 用户流程图

```mermaid
flowchart TD
  A["{{entry_state}}"] --> B["{{user_action}}"]
  B --> C{"{{decision_or_system_state}}"}
  C -->|{{success_condition}}| D["{{success_state}}"]
  C -->|{{error_condition}}| E["{{error_state}}"]
  E --> F["{{recovery_action}}"]
```

### 屏幕 / 组件地图

| 屏幕 / 组件 | 角色 | 承载领域对象 | 主要操作 | 进入条件 | 退出条件 |
|-------------|------|--------------|----------|----------|----------|
| {{screen_or_component}} | {{role}} | {{domain_entities}} | {{main_actions}} | {{entry_condition}} | {{exit_condition}} |

---

## 用户路径

| 路径编号 | 用户目标 | 前置条件 | 用户动作 | 预期结果 | 验收场景 / 条件 |
|---------|----------|-------|------|------|---------------|
| FLOW-001 | {{user_goal}} | {{given_context}} | {{user_steps}} | {{expected_result}} | {{acceptance_condition_ref}} / {{scenario_ref}} |

### 主路径

1. {{主路径步骤_1}}
2. {{主路径步骤_2}}
3. {{主路径步骤_3}}

### 替代路径

| 路径编号 | 触发条件 | 用户行为 | 系统反馈 | 结果 |
|---------|----------|----------|----------|------|
| ALT-001 | {{condition}} | {{user_action}} | {{system_feedback}} | {{result}} |

### 异常 / 恢复路径

| 路径编号 | 异常 | 用户可见反馈 | 恢复动作 | 端到端 / 组件验证 |
|---------|------|--------------|----------|----------------|
| ERR-001 | {{error_case}} | {{visible_feedback}} | {{recovery_action}} | {{test_ref}} |

---

## 状态模型

| 状态编号 | 状态 | 触发条件 | 界面表现 | 可操作项 | 退出条件 |
|---------|------|----------|---------|----------|----------|
| STATE-EMPTY | 空态 | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-LOADING | 加载中 | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-SUCCESS | 成功 | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-ERROR | 错误 | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-DISABLED | 禁用 | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-PERMISSION | 权限不足 | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |

```mermaid
stateDiagram-v2
  [*] --> {{initial_state}}
  {{initial_state}} --> {{loading_state}}: {{action}}
  {{loading_state}} --> {{success_state}}: {{success_event}}
  {{loading_state}} --> {{error_state}}: {{failure_event}}
  {{error_state}} --> {{loading_state}}: {{retry_action}}
```

---

## 信息架构与内容

### 文案语言策略

| 项 | 要求 / 结果 |
|----|-------------|
| 默认语言 | 中文 |
| 覆盖范围 | 原型界面、HTML / SVG 变体、预览、空态、错误、权限、确认、帮助、状态反馈 |
| 允许例外 | 品牌名、产品专名、代码标识、行业通用英文缩写、上游明确指定的外语文案 |
| 例外说明 | {{copy_language_exceptions}} |

| 区域 | 内容 / 数据 | 来源 | 空态文案 | 错误文案 |
|------|-------------|------|----------|----------|
| {{area}} | {{content_or_data}} | {{source}} | {{empty_copy}} | {{error_copy}} |

---

## 一致性体检

> 结论来源于 `interaction-spec/interaction-contract.md#一致性体检`。阻断项必须修复；决策项必须进入用户或产品裁决；警告项可以接受但要记录理由。体检必须包含原型可见文案是否默认中文，以及非中文例外是否有来源和理由。

| 发现编号 | 等级 | 检查项 | 发现 | 处理 |
|------------|------|--------|------|------|
| CONS-001 | BLOCKER / DECISION / WARNING / PASS | {{copy_or_state_or_permission_or_validation}} | {{finding}} | {{resolution}} |

---

## 可访问性与键盘路径

| 项 | 要求 | 验证方式 |
|----|------|----------|
| 焦点顺序 | {{focus_order}} | 键盘走查 / 端到端验证 |
| 可访问名称 | {{accessible_names}} | 定位器 / 可访问性冒烟检查 |
| 错误播报 | {{error_announcement}} | aria-live / role=alert 检查 |
| 键盘操作 | {{keyboard_actions}} | Tab / Enter / Escape / Arrow keys |

---

## 产品定义回流检查

> 原型阶段只能表达和细化已确认的产品定义。若原型设计发现必须新增或修改验收场景 / 条件、用户旅程、领域实体、实体状态、用户动作、权限规则或范围，必须回流产品定义阶段或决策门，不能在本阶段静默改产品定义。

| 检查项 | 结论 | 依据 | 处理 |
|--------|------|------|------|
| 系统用例流步骤或系统操作是否需要调整 | no_change / needs_prd_update | {{system_operation_feedback_basis}} | {{system_operation_feedback_action}} |
| 验收场景 / 条件是否需要调整 | no_change / needs_prd_update | {{acceptance_feedback_basis}} | {{acceptance_feedback_action}} |
| 用户旅程是否需要调整 | no_change / needs_prd_update | {{journey_feedback_basis}} | {{journey_feedback_action}} |
| 领域模型是否需要调整 | no_change / needs_prd_update | {{domain_feedback_basis}} | {{domain_feedback_action}} |
| 范围是否需要调整 | no_change / needs_decision | {{scope_feedback_basis}} | {{scope_feedback_action}} |

---

## 沉淀候选

> 复盘 / 收尾时，审查通过且具有长期价值的原型模式、界面信息架构、领域对象到界面的映射和交互约束，应提炼到 `project-knowledge/`；若它改变或确立用户可观察行为，并且 `spec.enabled=true`，应进入对应能力规格。

| 候选 | 类型 | 来源 | 建议目标 | 原因 |
|------|------|------|----------|------|
| {{prototype_pattern}} | prototype_pattern / ia / domain_ui_mapping / interaction_constraint / behaviour_spec | {{source_ref}} | project-knowledge / spec / none | {{reason}} |

### 沉淀规则

- 用户可观察行为进入 `project-knowledge/specs/<capability>/spec.md`。
- 主可操作原型本体留在独立原型工程目录（`prototype_project_root`，随分支合并晋升）；promote 不复制原型，provenance 看该目录 git log。
- 稳定系统界面边界结构进入 `project-knowledge/product/ui-surfaces/`。
- 稳定交互模式进入 `project-knowledge/product/workflows/` 或 `project-knowledge/design/interaction-patterns/`。
- 领域对象到界面的稳定映射进入 `project-knowledge/product/` 或能力规格。
- 工程实现样板进入 `project-knowledge/engineering/patterns/`。
- 设计取舍进入 `project-knowledge/design/decisions/`。
- 不得整份复制本阶段产物；每条沉淀必须保留来源任务、状态和置信度。

---

## 端到端 / 组件验证义务

| 义务编号 | 路径 / 状态 | required_capabilities | evidence_required | data-testid / 定位器 | 验收场景 / 条件 |
|---------------|--------------|-----------------------|-------------------|------------------------|---------------|
| E2E-001 | FLOW-001 | browser_flow, user_visible_assertion | e2e_run_report, assertion_summary | {{locator_or_testid}} | {{acceptance_condition_ref}} |

---

## 开放问题

| ID | 问题 | 影响 | 需要谁决策 |
|----|------|------|------------|
| Q-001 | {{question}} | {{impact}} | 用户 / 产品负责人 / 技术负责人 |

---

## 审查摘要

> 由 interaction-reviewer 审查循环结束后附加。

{{interaction_review_summary}}
