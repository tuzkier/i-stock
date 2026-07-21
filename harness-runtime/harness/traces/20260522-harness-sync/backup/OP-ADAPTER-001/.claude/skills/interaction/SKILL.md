---
name: interaction
description: '当产品定义包表明任务涉及 UI / 用户旅程 / 原型设计，需要根据 PRD 阶段产出的产品定义、AC、差量 spec 和 DDD 领域模型，把需求转成结构化原型合同、页面 / 状态 / 操作流，并覆盖加载、空态、错误、权限、键盘焦点等路径时使用。仅处理 Mission Slice control_plane.stage=interaction 且 prototype.delivery_mode=interactive_prototype（默认）路线；frontend_engineering 路线请用 prototype-as-frontend skill。通常发生在 prd 之后、solution 之前。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# Interaction — stage: interaction（原型 + 交互设计）

## 概述

`control_plane.stage=interaction` 专属 skill。把 PRD 阶段产出的产品定义、AC、用户旅程、业务规则、差量 spec 和 DDD 领域模型转化为结构化原型合同、页面/状态/操作流 + 可视化交互资产，产出 `interaction.md` + `interaction-spec/` + `contracts/interaction.contract.yaml` + `visual-interaction/` manifest，由 `interaction-reviewer` 审查。

本阶段的目标不是只写交互说明或画页面，而是在进入 solution / technical_analysis 之前，让需求以可理解、可追溯、可审查、可被下游 AI 实现的原型合同呈现出来。`interaction-spec/` 是本次 mission 的 AI handoff canonical 来源，必须按真实系统 surface / bounded context / navigation node 组织；`visual-interaction/prototype/index.html` 是唯一默认人类确认入口。

## 何时使用

- Mission Slice `control_plane.stage=interaction`
- `harness config snapshot` 返回 `prototype.delivery_mode=interactive_prototype`（默认值；项目未显式配置时即此路线）
- PRD 阶段已产出 `product/product-definition.md`、`product/product-domain-model.md`，且任务没有明确声明 API-only / 无界面 / 纯后端 / CLI-only
- mission-contract / 产品定义包含 `frontend_ui` / `user_journey` / E2E obligation / prototype trigger 信号时必须使用（可由 `harness interaction check-ui-trigger` 自动判断）
- 用户说"做原型 / 做交互 / 用户路径 / state matrix / 视觉变体"

## 何时不使用

- `harness config snapshot` 返回 `prototype.delivery_mode=frontend_engineering` → 转到 `prototype-as-frontend` skill（产可运行前端工程 + MSW + shared types draft，详见 `docs/methodologies/prototype-as-frontend-delivery.md`）
- mission-contract / 产品定义明确说明 API-only / 无界面 / 纯后端 / CLI-only，且 `harness interaction check-ui-trigger` 返回 requires_interaction=false
- `control_plane.stage=solution` → 转到 `solution` skill
- `control_plane.stage=technical_analysis` → 转到 `technical_analysis` skill

## 设计原则

- **领域驱动**：原型界面必须从产品定义、差量 spec 和 DDD 领域模型推导关键实体、关系、状态、动作、权限和规则，不得只凭视觉直觉画界面
- **界面表达**：领域驱动是语义约束，不替代界面设计。必须判断信息架构、内容层级、控件选择、主次操作、反馈节奏、容错恢复、可访问性和用户认知负担；domain mapping 正确但界面难懂、难用或反馈不友好时不得通过
- **Surface 优先**：必须先判断本次是新建、修改、扩展还是废弃既有系统界面；修改既有 UI 时必须引用 baseline，不能每次按任务堆一套新原型
- **合同优先**：`interaction-spec/` 必须以结构化 Markdown / TypeScript / 场景矩阵表达信息架构、screen、flow、state、interaction、view model 和 consistency report；HTML / 图片不能作为下游 AI 的主依据
- **中文文案**：原型、HTML / SVG 变体中的用户可见文字默认必须使用中文；只有品牌名、产品专名、代码标识、行业通用英文缩写或上游明确指定的外语文案可以保留原文，并必须在一致性体检中说明
- **状态完整**：必须覆盖加载、空态、错误、权限、键盘焦点
- **可追溯**：每个 surface / flow / state 必须 traces_to AC，并说明关联领域实体或领域动作
- **manifest 强制**：可视化资产必须经 `harness evidence visual manifest` CLI 生成，不得直写 manifest.json
- **E2E obligation 强制**：每个用户路径必须有 E2E locator / data-testid
- **PRD 回流**：原型设计发现需要新增/修改 AC、用户旅程、领域实体/状态/动作或范围时，必须停止并回流 PRD / Decision Gate，不得在 interaction 阶段静默改产品定义
- **长期沉淀**：被审查通过的原型模式、界面信息架构、领域对象到界面的映射和可复用交互约束，必须在 retrospective / 收尾时作为 project-knowledge 或 spec 候选沉淀

## 快速参考

| 步骤 | 产出 |
|------|------|
| Stage 初始化 + UI 触发判断 | inputs |
| 读产品定义包 + 领域模型 + delta spec + Mission Contract + project context + pattern | inputs |
| 设计按系统 surface 组织的结构化原型合同、交互流程 + state matrix | interaction.md + interaction-spec/ |
| 生成可操作原型和 visual-interaction manifest | prototype/index.html + manifest.json + variants/ |
| reviewer 循环 (max_rounds=3) | role_verdicts |
| Artifact Gate 自检 | gate run PASS |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#interaction`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Surface | Frontend execution / E2E Review | 页面边界漂移或重复造界面 |
| User Journey | Prototype / E2E | 只画页面，不证明路径 |
| UI State | Frontend / E2E | 交互缺少失败 / 边界状态 |
| Domain-UI Mapping | Solution / Tech Design / Frontend | UI 表达脱离业务语义 |
| E2E Obligation | Code Review / Verify | 后续无法用真实路径验证 |

按 `workflow.md` 执行详细步骤。
