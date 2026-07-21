# 原型交互设计: {{mission_id}}

> **来源**：interaction lane action → `harness-runtime/harness/stages/{{mission_id}}/interaction.md`
> **上游**：`product/product-definition.md` | `product/product-domain-model.md` | `product/product-evidence.md` | `mission-contract.md` | delta specs | project context
> **目的**：把 PRD 阶段产出的产品定义、AC 和领域模型转成可实现、可预览、可验证的原型界面与交互契约。

**Author:** {{user_name}}
**Date:** {{date}}
**mission-id:** {{mission_id}}
**Status:** `draft` <!-- draft / in-review / approved / blocked -->

---

## Overview

> 用 2-3 句话说明本次原型交互设计覆盖哪些用户目标、哪些领域对象、哪些界面 / 组件、哪些状态边界。

{{interaction_overview}}

| 字段 | 值 |
|------|----|
| 交互范围 | {{interaction_scope}} |
| 主要用户 | {{primary_user}} |
| 关键入口 | {{entry_points}} |
| 不在范围内 | {{out_of_scope}} |

---

## 领域模型到原型映射

> 从 `product/product-domain-model.md` 抽取关键实体、实体状态、用户动作、业务规则和权限边界，说明它们如何被原型界面承载。

| 领域对象 / 动作 / 状态 | 业务含义 | 原型承载位置 | 关联 Flow / State | AC / Scenario |
|------------------------|----------|--------------|-------------------|---------------|
| {{domain_entity_or_action}} | {{business_meaning}} | {{screen_or_component}} | {{flow_or_state_ref}} | AC-{{id}} / {{scenario_ref}} |

---

## 控制契约

> 交互指导契约记录用户路径、状态模型、可视化资产和审查义务，供拆解 / 执行 / code-review / verify 消费。

- Contract: `contracts/interaction.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

## 原型合同与阅读顺序

> 长期原型视为一个 prototype project；`interaction-spec/` 是本次 mission 对该 prototype project 的 canonical patch 和 AI 实现合同。目录内部必须按真实系统 surface 组织，而不是按任务或版本堆页面。`visual-interaction/prototype/index.html` 是给人确认的唯一默认入口，必须像真实前端页面。说明、状态覆盖、组件清单和 trace 信息只作为内部证据，不默认生成可见页面。评审反馈必须先回写 `interaction-spec/` 和本文件，再重建 prototype。

| 顺序 | 读者 | 路径 | 用途 | 权威性 |
|------|------|------|------|--------|
| 1 | 人 / AI | `interaction.md` | 阶段总览、范围、关键决策、沉淀候选 | 入口 |
| 2 | AI / Gate | `contracts/interaction.contract.yaml` | 程序化契约、obligation、traceability | 程序化权威 |
| 3 | AI 实现者 | `interaction-spec/README.md` | AI handoff 阅读顺序、更新规则、非目标 | canonical |
| 4 | AI 实现者 | `interaction-spec/**` | surface / flow / state / scenario / view model / validation 合同 | canonical |
| 5 | 人类确认 | `visual-interaction/prototype/index.html` | 高还原可操作前端原型唯一默认入口 | primary prototype |
| 6 | Gate / reviewer | `visual-interaction/visual-interaction-manifest.json` | 可视化资产索引和覆盖元数据 | internal evidence |

### AI Handoff 文件清单

| 文件 | 必填 | 说明 |
|------|------|------|
| `interaction-spec/source-trace.md` | yes | PRD、领域模型、delta spec、project-knowledge 来源追溯 |
| `interaction-spec/surface-index.md` | yes | 受影响系统 surface 清单，按 bounded context / module / navigation node 组织 |
| `interaction-spec/surface-baseline.md` | yes | 判断本次是新增、修改、扩展还是废弃既有界面的依据 |
| `interaction-spec/surface-changeset.md` | yes | 本次对每个 surface 的 create / modify / extend / retire 操作 |
| `interaction-spec/information-architecture.md` | yes | 模块、导航、页面层级、入口与返回路径 |
| `interaction-spec/domain-ui-mapping.md` | yes | DDD 对象 / 关系 / 状态 / Domain Command / 权限 / 规则到 UI 的映射 |
| `interaction-spec/surfaces/<bounded-context>/<surface-id>.md` | yes | 每个系统 surface 的职责、区域 / slot、数据、状态、动作、错误、权限、焦点、traces_to |
| `interaction-spec/flows.md` | yes | 用户路径串联，覆盖主路径、替代路径和恢复路径 |
| `interaction-spec/states.md` | yes | loading / empty / error / permission / success / disabled / conflict 等状态 |
| `interaction-spec/interactions.md` | yes | 鼠标、键盘、焦点、手势、确认、撤销、反馈和防重复提交 |
| `interaction-spec/scenarios.md` | yes | Given / When / Then 场景矩阵，追溯 AC / spec Scenario |
| `interaction-spec/validation-rules.md` | yes | 表单、业务限制、错误提示和阻断策略 |
| `interaction-spec/view-models.ts` | yes | UI ViewModel / FormModel / StateModel，不绑定后端接口或数据库 |
| `interaction-spec/consistency-report.md` | yes | BLOCKER / DECISION / WARNING / PASS 一致性体检 |

---

## Surface Baseline 与变更范围

> 原型阶段必须判断当前任务是在已有界面上修改，还是创建新的系统 surface。若修改既有界面，必须引用 baseline；不得每次生成一套孤立的新页面。

| Surface ID | Bounded Context / Module | Operation | Baseline Ref | Change Summary | Trace |
|------------|--------------------------|-----------|--------------|----------------|-------|
| SURF-001 | {{bounded_context}} | create_surface / modify_surface / extend_surface / retire_surface | {{existing_surface_ref_or_none}} | {{change_summary}} | AC-{{id}} / SCN-{{id}} |

---

## Prototype Project Patch

> 本节说明本次 mission 对长期 prototype project 的影响。Stage 产物只保存 patch 证据；稳定结果在 retrospective 后提炼进 `project-knowledge/product/prototype/`。

| Patch ID | Prototype Area | Operation | Baseline | Resulting Prototype State | Promotion Target |
|----------|----------------|-----------|----------|---------------------------|------------------|
| PATCH-001 | {{prototype_area}} | create / modify / extend / retire | {{baseline_ref}} | {{result_summary}} | project-knowledge/product/prototype / product/ui-surfaces / none |

---

## 原型与可视化交互资产

> 必须提供 `visual-interaction/prototype/index.html` 作为唯一默认人类入口。复杂 UI 可补充截图、状态覆盖或录屏作为内部证据；人要看的仍然只有主原型页面。
> 视觉风格必须继承所在项目的设计系统、组件库和现有页面模式；如果没有设计系统，应在本节记录临时设计基线，不能让生成器默认审美覆盖项目风格。
> 主原型页面只呈现产品界面本身，不得混入阅读顺序、AC / trace、Flow / State 展板、reviewer 指引、manifest 说明或组件目录；这些内容进入 `interaction-spec/` 或内部 `visual-interaction/evidence/**`。
> 原型、HTML / SVG 变体和 preview 中的用户可见文字默认必须使用中文；品牌名、产品专名、代码标识、行业通用英文缩写或上游明确指定的外语文案可保留原文，但必须在一致性体检中说明。

| 资产 ID | 类型 | 路径 / 内容 | 覆盖范围 | 状态 |
|---------|------|-------------|----------|------|
| VIZ-001 | Mermaid user flow | 见下方 `用户流程图` | P0 用户路径 | draft |
| VIZ-002 | operable prototype | `visual-interaction/prototype/index.html` | P0 可点击路径 / 关键状态 / desktop+mobile | draft / ready |
| VIZ-003 | internal evidence | {{visual_artifact_path}} | {{covered_screen_or_flow_or_state}} | draft / ready |
| VIZ-MANIFEST | manifest | `visual-interaction/visual-interaction-manifest.json` | 全部可视化资产索引 | ready |

### 风格来源

| 来源 | 路径 / 证据 | 本次如何继承 |
|------|-------------|--------------|
| 设计系统 / theme | {{design_system_path}} | {{style_inheritance}} |
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

| Flow ID | 用户目标 | Given | When | Then | AC / Scenario |
|---------|----------|-------|------|------|---------------|
| FLOW-001 | {{user_goal}} | {{given_context}} | {{user_steps}} | {{expected_result}} | AC-{{id}} / {{scenario_ref}} |

### 主路径

1. {{happy_path_step_1}}
2. {{happy_path_step_2}}
3. {{happy_path_step_3}}

### 替代路径

| Path ID | 触发条件 | 用户行为 | 系统反馈 | 结果 |
|---------|----------|----------|----------|------|
| ALT-001 | {{condition}} | {{user_action}} | {{system_feedback}} | {{result}} |

### 异常 / 恢复路径

| Path ID | 异常 | 用户可见反馈 | 恢复动作 | E2E / 组件验证 |
|---------|------|--------------|----------|----------------|
| ERR-001 | {{error_case}} | {{visible_feedback}} | {{recovery_action}} | {{test_ref}} |

---

## 状态模型

| 状态 ID | 状态 | 触发条件 | UI 表现 | 可操作项 | 退出条件 |
|---------|------|----------|---------|----------|----------|
| STATE-EMPTY | empty | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-LOADING | loading | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-SUCCESS | success | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-ERROR | error | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-DISABLED | disabled | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |
| STATE-PERMISSION | permission_denied | {{trigger}} | {{ui_feedback}} | {{actions}} | {{exit_condition}} |

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
| 覆盖范围 | 原型界面、HTML / SVG 变体、preview、空态、错误、权限、确认、帮助、状态反馈 |
| 允许例外 | 品牌名、产品专名、代码标识、行业通用英文缩写、上游明确指定的外语文案 |
| 例外说明 | {{copy_language_exceptions}} |

| 区域 | 内容 / 数据 | 来源 | 空态文案 | 错误文案 |
|------|-------------|------|----------|----------|
| {{area}} | {{content_or_data}} | {{source}} | {{empty_copy}} | {{error_copy}} |

---

## 一致性体检

> 结论来源于 `interaction-spec/consistency-report.md`。BLOCKER 必须修复；DECISION 必须进入用户或产品裁决；WARNING 可以接受但要记录理由。体检必须包含原型可见文案是否默认中文，以及非中文例外是否有来源和理由。

| Finding ID | 等级 | 检查项 | 发现 | 处理 |
|------------|------|--------|------|------|
| CONS-001 | BLOCKER / DECISION / WARNING / PASS | {{copy_or_state_or_permission_or_validation}} | {{finding}} | {{resolution}} |

---

## 可访问性与键盘路径

| 项 | 要求 | 验证方式 |
|----|------|----------|
| 焦点顺序 | {{focus_order}} | keyboard walkthrough / E2E |
| 可访问名称 | {{accessible_names}} | locator / accessibility smoke |
| 错误播报 | {{error_announcement}} | aria-live / role=alert 检查 |
| 键盘操作 | {{keyboard_actions}} | Tab / Enter / Escape / Arrow keys |

---

## PRD 回流检查

> 原型阶段只能表达和细化已确认的产品定义。若原型设计发现必须新增/修改 AC、用户旅程、领域实体、实体状态、用户动作、权限规则或范围，必须回流 PRD / Decision Gate，不能在本阶段静默改产品定义。

| 检查项 | 结论 | 依据 | 处理 |
|--------|------|------|------|
| AC 是否需要调整 | no_change / needs_prd_update | {{ac_feedback_basis}} | {{ac_feedback_action}} |
| 用户旅程是否需要调整 | no_change / needs_prd_update | {{journey_feedback_basis}} | {{journey_feedback_action}} |
| 领域模型是否需要调整 | no_change / needs_prd_update | {{domain_feedback_basis}} | {{domain_feedback_action}} |
| 范围是否需要调整 | no_change / needs_decision | {{scope_feedback_basis}} | {{scope_feedback_action}} |

---

## 沉淀候选

> 复盘 / 收尾时，审查通过且具有长期价值的原型模式、界面信息架构、领域对象到界面的映射和交互约束，应提炼到 `project-knowledge/`；若它改变或确立用户可观察行为，并且 `spec.enabled=true`，应进入对应能力 spec。

| 候选 | 类型 | 来源 | 建议目标 | 原因 |
|------|------|------|----------|------|
| {{prototype_pattern}} | prototype_pattern / ia / domain_ui_mapping / interaction_constraint / behaviour_spec | {{source_ref}} | project-knowledge / spec / none | {{reason}} |

### 沉淀规则

- 用户可观察行为进入 `project-knowledge/specs/<capability>/spec.md`。
- 稳定 prototype project 结构进入 `project-knowledge/product/prototype/`。
- 稳定系统 surface 结构进入 `project-knowledge/product/ui-surfaces/`。
- 稳定交互模式进入 `project-knowledge/product/workflows/` 或 `project-knowledge/design/interaction-patterns/`。
- 领域对象到 UI 的稳定映射进入 `project-knowledge/product/` 或能力 spec。
- 工程实现样板进入 `project-knowledge/engineering/patterns/`。
- 设计取舍进入 `project-knowledge/design/decisions/`。
- 不得整份复制本阶段产物；每条沉淀必须保留 source mission、status、confidence。

---

## E2E / 组件验证义务

| Obligation ID | Flow / State | required_capabilities | evidence_required | data-testid / locator | AC / Scenario |
|---------------|--------------|-----------------------|-------------------|------------------------|---------------|
| E2E-001 | FLOW-001 | browser_flow, user_visible_assertion | e2e_run_report, assertion_summary | {{locator_or_testid}} | AC-{{id}} |

---

## Open Questions

| ID | 问题 | 影响 | 需要谁决策 |
|----|------|------|------------|
| Q-001 | {{question}} | {{impact}} | 用户 / PM / Tech |

---

## 审查摘要

> 由 interaction-reviewer 审查循环结束后附加。

{{interaction_review_summary}}
