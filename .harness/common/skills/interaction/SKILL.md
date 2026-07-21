---
name: interaction
description: '当产品定义包表明任务涉及 UI / 用户旅程 / 原型设计，需要根据产品定义阶段产出的产品定义、验收场景 / 条件、差量 spec 和 DDD 领域模型，把需求转成固定标准的交互合同、页面 / 状态 / 操作流，并覆盖加载、空态、错误、权限、键盘焦点等路径时使用。仅处理 Mission Slice control_plane.stage=interaction 且 prototype.delivery_mode=interactive_prototype（默认）路线；frontend_engineering 路线请用 prototype-as-frontend skill。通常发生在 prd 之后、solution 之前。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# Interaction — stage: interaction（原型 + 交互设计）

## 概述

`control_plane.stage=interaction` 专属 skill。把产品定义阶段产出的产品定义、验收场景 / 条件、用户旅程、业务规则、差量 spec 和 DDD 领域模型转化为**行为图**（page_states/steps/edges/flows），产出 `interaction.md` + `interaction-spec/surface-model.md`（容器轴 + surface 目录 + **布局骨架区域树**）+ `interaction-spec/behavior-graph.yaml`（手写真相源，page_state 对象落区）+ `interaction-spec/views/*`（`harness interaction project` 生成）+ `contracts/interaction.contract.yaml`，并对项目持有的独立原型工程目录（`prototype_project_root`）按 R1–R8（先有布局骨架再写 HTML）做增量修改；原型阶段必须有人类在走查驾驶舱以 operation-walk 确认，`harness interaction prototype-check` 是唯一 lint，由 `interaction-reviewer` 审查。

本阶段的目标不是只写交互说明或画页面，而是在进入 solution / technical_analysis 之前，把需求转成**行为图**（page_states/steps/edges/flows）这一可理解、可追溯、可审查、可被下游 AI 实现的真相源，并让人在走查驾驶舱实际确认原型表达。`interaction-spec/behavior-graph.yaml`（SSOT）+ `surface-model.md`（容器轴 + surface 目录机器段）是本次 mission 的 AI handoff canonical 来源；`views/` 是其机器派生。主可操作原型必须在**项目持有的独立原型工程目录**持续迭代（`prototype.interactive_prototype.prototype_project_root`，默认建议 `prototype/`，git 跟踪、随 Mission 分支隔离），它既不在 `project-knowledge/` 下也不在 mission artifact 下。阶段产物不得另起一套 `visual-interaction/prototype/` 副本。`visual-interaction/visual-interaction-manifest.json` 通过外向路径 / `absolute_path` 引用独立原型工程主入口，只记录证据、覆盖范围和入口指针。

## 何时使用

- Mission Slice `control_plane.stage=interaction`（**每个 mission 默认进入本阶段**，不再由 PRD 用例模型 `UIC-xx` 前置门控）
- `harness config snapshot` 返回 `prototype.delivery_mode=interactive_prototype`（默认值；项目未显式配置时即此路线）
- **要不要原型在本阶段内判**：进入后 step-0 先做原型必要性判断——能明确判的自动判（纯后端/接口/数据/CLI/重构→判否跳过；明显有界面/用户旅程→判是做完整原型），灰色地带才问用户，结论写 `prototype-necessity.json`
- 用户说"做原型 / 做交互 / 用户路径 / state matrix / 视觉变体"

## 何时不使用

- `harness config snapshot` 返回 `prototype.delivery_mode=frontend_engineering` → 转到 `prototype-as-frontend` skill（产可运行前端工程 + MSW + shared types draft，详见 `docs/methodologies/prototype-as-frontend-delivery.md`）
- （注意：「任务无界面」**不再是不进入本阶段的理由**——默认进入、由 step-0 判否跳过，跳过逻辑在阶段内，不在路由前置）
- `control_plane.stage=solution` → 转到 `solution` skill
- `control_plane.stage=technical_analysis` → 转到 `technical_analysis` skill

## 设计原则

- **领域驱动**：原型界面必须从产品定义、差量 spec 和 DDD 领域模型推导关键实体、关系、状态、动作、权限和规则，不得只凭视觉直觉画界面
- **界面表达**：领域驱动是语义约束，不替代界面设计。必须判断信息架构、内容层级、控件选择、主次操作、反馈节奏、容错恢复、可访问性和用户认知负担；domain mapping 正确但界面难懂、难用或反馈不友好时不得通过
- **Surface 优先**：必须先判断本次是新建、修改、扩展还是废弃既有系统界面；修改既有 UI 时必须引用 baseline，不能每次按任务堆一套新原型
- **独立原型工程目录**：主可操作原型必须在项目持有的独立原型工程目录（`prototype_project_root`，默认建议 `prototype/`，git 跟踪、随 Mission 分支隔离）持续迭代，不在 `project-knowledge/` 下、不在 mission artifact 下；阶段 artifact 只保存增量说明、manifest 和证据，不保存新的主原型副本
- **原型搭法（R1–R8）**：以 `.harness/docs/prototype-standard.md` 为权威标准。原型是「行为图 ⊗ 布局骨架」的可视化实现——按 surface 切页、按 page-state 切 `data-state` 态块；每条 edge 是真实产品操作，系统事件 edge 由产品输入诱发并声明 `edge.via`（禁 dev 开关条）；从 surface 入口逐条执行 edge 必须走到每个 page-state（无"仅 teleport 可达"）；内容静态、JS 只做胶水并暴露当前激活 `data-pagestate`；走查驾驶舱导航 SUC→flow→step 三层封顶
- **组成轴（R8，线框级）**：先有布局骨架再写 HTML（compose-before-HTML）。每个 surface 在 surface-model「布局骨架机器段」声明区域树（区域 × 嵌套 × 排布 × 优先级 × 角色 × 扫描序），每个可见对象用 `objects[].region` 落区、非 OBJ 内容用 `placements` 落区，原型区域打 `data-region`；对象不落区 / 整页一坨 / 原型与骨架不符均 FAIL。不从白纸即兴排控件——新建从 `references/layout-patterns/` 选基底 pattern
- **组成基线 + 从组件库装配（迭代系统）**：原型挂在 `ui-design-system`（`design-system/interaction-framework`）的应用外壳里，区域树排版，**区域里放业务组件**（复用 `business-components.md`，无则定义新组件绑 OBJ/SUC、由基础组件组成、列全状态），组件全用 `design-spec` 登记 token——不从裸控件堆。改 / 扩既有 surface 必须继承累积图 `regions` 区域树 + 既有外壳 / 组件、不重造，贴合 `principles` + `design-spec` 设计语言；合并图回归校验沉淀区域 / 组件仍被渲染，删除走 `retired`。本次新业务组件沉淀进 `design-system/business-components.md`。保证原型与既有界面一致、下游实现无歧义
- **人类确认强制**：阶段完成前必须让用户在走查驾驶舱以 operation-walk 走查确认；审查员 PASS 不能替代用户确认
- **真相源优先**：唯一手写真相源是 `behavior-graph.yaml`（四张规范化表）+ `surface-model.md`（容器轴 + surface 目录机器段）；HTML / 图片不能作为下游 AI 的主依据
- **标准包闭合**：`interaction-spec/` 手写的只有 `surface-model.md` + `behavior-graph.yaml`；`views/by-suc|by-surface|by-object.md` 由 `harness interaction project` 生成、禁止手写；不得再拆出额外手写规格
- **中文文案**：原型用户可见文字默认中文；品牌名、产品专名、代码标识、行业通用英文缩写或上游指定外语文案可保留，并在 interaction.md 一致性体检说明
- **状态完整**：每个 page-state 覆盖（加载、空态、错误、权限、键盘焦点按需），且 operation-walk 可达
- **可追溯**：每个 step / page-state 追溯到验收场景 / 条件（step.acceptance_refs），并说明关联领域实体或领域动作
- **trace 脊柱（下沉行为图）**：SURF↔SUC↔OBJ↔SCN↔state 完整绑定以 `behavior-graph.yaml` 为唯一真相源（page_states/steps/edges/flows）；原型植入 `data-step`/`data-pagestate`/`data-via` 锚点（system_event edge 的 via 控件带 data-via）；ID 引用上游真源、不在本阶段新造业务态。旧 `surface_bindings` 已废弃
- **覆盖颗粒下沉 step**：`harness interaction prototype-check` 在 step / page-state 颗粒对账（派生分母 + 三双射 + 四方锚点），不再坍缩到 SUC base——一个 SUC 含多个分支/状态时每个结局都被单独要求
- **trace 脊柱双向可导航**：既能反查（原型 data-step/data-pagestate → 上游）也能正查（给定 SUC/OBJ/step → 承载它的 page_state + `page_entry` + `anchor_root`，经 `harness interaction resolve-feedback`，消费 `behavior-graph.yaml`）。正向导航由工具层承载，不得在主原型页面加按 SUC/step 选择跳转的可见入口
- **manifest 强制**：可视化资产必须经 `harness evidence visual manifest` CLI 生成，不得直写 manifest.json
- **E2E obligation 强制**：每个用户路径必须有 E2E locator / data-testid
- **PRD 回流**：原型设计发现需要新增/修改验收场景 / 条件、用户旅程、领域实体/状态/动作或范围时，必须停止并回流产品定义阶段 / Decision Gate，不得在 interaction 阶段静默改产品定义
- **长期沉淀**：被审查通过的原型模式、界面信息架构、领域对象到界面的映射和可复用交互约束，必须在 retrospective / 收尾时作为 project-knowledge 或 spec 候选沉淀

## 快速参考

| 步骤 | 产出 |
|------|------|
| Stage 初始化 + UI 触发判断 | inputs |
| 读产品定义包 + 领域模型 + delta spec + Mission Contract + project context + pattern | inputs |
| 把需求转成行为图 + 走查驾驶舱可走查的原型 | interaction.md + surface-model.md + behavior-graph.yaml（手写）+ views/*（生成）|
| 迭代独立原型工程目录的主原型并生成 visual-interaction manifest | prototype_project_root/**（默认 prototype/）+ manifest.json + variants/ |
| reviewer 循环（无轮次放行） | role_verdicts |
| 用户原型确认 checkpoint | user_prototype_confirmation |
| Artifact Gate 自检 | gate run PASS |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#interaction`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Surface | Frontend execution / E2E Review | 页面边界漂移或重复造界面 |
| Layout Skeleton（区域树·组成轴） | Frontend execution / Prototype | 无骨架→控件乱堆、对象无家、迭代不继承既有布局 |
| User Journey | Prototype / E2E | 只画页面，不证明路径 |
| UI State | Frontend / E2E | 交互缺少失败 / 边界状态 |
| Domain-UI Mapping | Solution / Tech Design / Frontend | UI 表达脱离业务语义 |
| Design System Baseline（设计语言） | Frontend / Interaction Eng | 原型与既有界面不一致、下游实现有歧义 |
| E2E Obligation | Code Review / Verify | 后续无法用真实路径验证 |

按 `workflow.md` 执行详细步骤。
