Contract: contracts/solution.contract.yaml

# Solution: 20260522-stock-watch-system

**Author:** Codex
**Date:** 2026-05-23
**mission-id:** `20260522-stock-watch-system`
**Status:** `draft`

## Overview

本次方案把产品明确收束为“本地浏览器里的可解释看盘工作台”，而不是云服务、交易系统或单页行情展示。核心路线是：保留现有 React/Vite/Express 本地栈，使用 `lightweight-charts` 承担图表呈现，行情通过显式 `MarketDataSource` 边界接入并保留可见降级，指标与 MTS 在共享的纯 TypeScript 领域层中计算，提醒通过事件/策略编排，配置与恢复只落在版本化 `localStorage`。

**关键设计判断 / 决策点：**
1. 前端架构边界必须保留在单体本地 SPA + 本地代理，不拆成云服务。
2. 多市场代码识别必须显式处理歧义，不能静默猜市场。
3. 行情源、缓存与降级必须可见，fallback 不能伪装成真实行情。
4. 指标、MTS 与提醒必须走确定性领域流水线，而不是 UI 即时拼装。
5. 本地恢复以标的级为主，默认布局作为回退，不以账号或云同步承载。
6. E2E 必须以 fixture-first 为门禁，live Yahoo 只能做非门禁烟雾验证。
7. `agent_engineering.enabled=true` 只影响治理与下游设计门槛，本产品运行时不引入 Agent。

---

## 控制契约

- Contract: `contracts/solution.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

## 问题回顾

### 业务目标

- 统一承载港股、A 股、美股、韩股的自选、看盘、指标、MTS 和提醒。
- 保持本地使用、重开恢复、来源降级透明和可解释信号边界。
- 不引入自动交易、收益承诺、账号体系、云同步或完整基本面模块。

### 关键约束

- `project-context.md` 明确：前端由 Vite/React 承载，后端只做本地 Express 静态服务与行情代理；代码归一必须遵守 Yahoo 风格；技术信号必须演进到 `MTS`；持久化边界是浏览器 `localStorage`。
- 交互合同已固定七个 surface：`SURF-WATCHLIST`、`SURF-WORKBENCH`、`SURF-MTS`、`SURF-ALERTS`、`SURF-SOURCE`、`SURF-LAYOUT`、`SURF-RESTORE`；主原型合同覆盖 BUC-01 ~ BUC-08 的 flow/state/locator。
- 默认呈现必须是日常看盘 focus；dense 仅在诊断 / 验收时展开。这里调整的是信息架构与布局策略，不改变 PRD 语义、BO、AC 或用户目标。
- BUC-09 仅是冻结样本验收与验证映射，不属于 prototype required 主交互合同，也不额外引入新的产品语义。
- 领域模型已固定 6 个限界上下文：自选身份、看盘观察、信号与提醒、来源治理、本地连续使用与布局、验收样本与可验证性。

## 目标驱动设计

### 限界上下文与上下游关系（Context Map）

| Bounded Context | 核心对象 | 上游 / 下游关系 | 主要策略 |
|---|---|---|---|
| BC-01 自选身份 | `WatchSymbol`, `Market` | 上游：用户输入；下游：观察、提醒、恢复 | 市场识别与代码归一必须显式化，归档是可恢复状态，不是删除。 |
| BC-02 看盘观察 | `PriceSeries`, `IndicatorSet`, `ChartLayout` | 上游：来源治理；下游：MTS 与提醒 | 只承载观察状态与布局偏好，不吞并信号和提醒规则。 |
| BC-03 信号与提醒 | `MtsSignal`, `AlertRule` | 上游：观察上下文；下游：UI 提醒层 | 规则与信号分离，提醒优先级由策略决定，不由组件临时判断。 |
| BC-04 来源治理 | `MarketDataSource` | 上游：外部供应商；下游：观察/信号/提醒 | 作为 ACL/adapter 边界，负责正式/演示/降级语义传递。 |
| BC-05 本地连续使用与布局 | `ChartLayout`, 版本化 workspace snapshot | 上游：所有本地状态；下游：Watchlist/Workbench/Alerts 首屏 | 以可迁移快照恢复，不依赖账号或云同步。 |
| BC-06 验收样本与可验证性 | frozen fixture, validation scenario | 上游：PRD / interaction / domain model；下游：technical_analysis / verify | 只定义可回放证据边界，不进入产品 runtime。 |

### 事件与策略

- 事件：`WatchSymbolAdded`、`WatchSymbolArchived`、`WatchSymbolRestored`、`ObservationContextRefreshed`、`SourceDegraded`、`MtsSignalEvaluated`、`AlertRuleTriggered`、`LocalWorkspaceRestored`。
- 策略：`MarketNormalizationPolicy`、`SourceDegradationPolicy`、`MtsInterpretationPolicy`、`AlertPriorityPolicy`、`RestoreFallbackPolicy`。
- 一致性边界：`WatchSymbol`、`ObservationSession`、`MtsSignal`、`AlertRule` 必须各自独立成边界，避免把行情、指标、信号、提醒和恢复状态揉成一个不可测的大对象。

---

## 关键决策

### D-01：前端架构边界与图表库路线

**问题描述**

当前需要决定的是：是否继续在现有本地 React SPA 上演进，还是把看盘能力拆成更重的前后端服务边界并更换图表库。

**可行路线**

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A: 本地单体 SPA + `lightweight-charts` 延续 | 保持 React/Vite/Express，图表继续用 `lightweight-charts`，以 panes/叠层承载主图、成交量和副图。 | 与现有栈一致，迁移成本最低，已验证可运行，符合本地网页边界。 | 复杂金融交互能力不如更完整的金融图表库，需要后续在组件层补齐交互。 |
| B: 迁移到 `KLineChart` 或更重的图表栈 | 将图表层重构为更完整的金融图表实现。 | 内建金融能力更强，长远交互上限更高。 | 迁移成本高，容易把方案拖进技术改造而非产品收敛。 |

**选择：** 路线 A

**理由：**
- 当前目标是把多市场看盘闭环收束到一个可解释、可验证、本地可持续使用的工作台，不是立即重写图表引擎。
- `lightweight-charts` 已能覆盖本阶段主图/成交量/副图的合同，且与现有工程依赖一致。
- 图表库替换会放大验证成本，但不会更好地解决 MTS、提醒和本地恢复这三个产品核心问题。

**traces_to：** `AC-02`、`AC-03`、`AC-05`、`FR-02`、`FR-03`、`FR-05`、`BUC-02`、`BUC-03`、`BUC-04`、`BUC-08`、`BO-003`、`BO-004`、`BO-008`、`SURF-WORKBENCH`、`SURF-LAYOUT`、`chart-main-panel`、`chart-volume-panel`、`chart-secondary-panel`、`indicator-tab-*`、`project-context.md` 中 `ARCH-001`、`ARCH-003`

**适配性评估**

| 路线 | 目标完成度 | DDD 适配 | 维护成本 | 验证难度 | 结论 |
|---|---|---|---|---|---|
| A | 高 | 高 | 中 | 中 | 采用 |
| B | 高 | 中 | 高 | 高 | 作为后续备选，不进入本阶段主路由 |

---

### D-02：多市场代码识别与自选准入

**问题描述**

港股、A 股、韩股都存在数字代码，静默自动猜市场会制造歧义，尤其会把“加入自选”误导成“已正确识别”。

**可行路线**

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A: 静默自动猜测市场 | 输入代码后默认猜一个市场并直接入库。 | 操作快。 | 容易误归一，且用户看不到最终识别结果。 |
| B: 显式市场提示 + 归一结果预览 + 歧义门禁 | 输入时展示市场选择或归一预览，遇到数字代码歧义时要求用户确认。 | 可解释、可审计，避免市场误判。 | 交互略重。 |

**选择：** 路线 B

**理由：**
- 自选标的是领域主键，不能靠“猜对了就算”处理。
- 交互已要求列表里同时显示市场、原始代码和归一代码，必须让用户看见最终识别结果。
- 这条路线直接缓解多市场数字代码歧义风险，避免后续提醒和恢复都建立在错误 identity 上。

**traces_to：** `AC-01`、`AC-05`、`FR-01`、`BUC-01`、`BO-001`、`BO-002`、`BR-001`、`BR-002`、`BR-016`、`SURF-WATCHLIST`、`FLOW-WATCHLIST-MANAGE`、`STATE-ERROR`、`watchlist-add-input`、`watchlist-add-button`、`symbol-row-<normalized>`、`project-context.md` 中 PIT-002

**适配性评估**

| 路线 | 目标完成度 | DDD 适配 | 维护成本 | 验证难度 | 结论 |
|---|---|---|---|---|---|
| A | 低 | 低 | 低 | 中 | 拒绝 |
| B | 高 | 高 | 中 | 中 | 采用 |

---

### D-03：行情源、缓存与降级边界

**问题描述**

需要决定行情来源是“隐藏 fallback 的单一数据管线”，还是“显式可替换来源层 + 可见降级语义”。

**可行路线**

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A: 隐式 fallback | 上游失败后静默回退到演示数据，只保证页面能跑。 | 开发快。 | 伪装风险高，用户可能把 demo 当真实行情。 |
| B: `MarketDataSource` 显式边界 + 本地 TTL cache + 可见降级 | 通过来源声明对象、适配器和短 TTL 缓存管理数据，页面明确展示 formal / demo_fallback / unavailable。 | 可信、可替换、可审计。 | 需要维护来源状态穿透。 |

**选择：** 路线 B

**理由：**
- 任务明确要求不能把 fallback 伪装成真实行情。
- 行情供应商未锁定，必须把供应商差异隔离在来源边界，而不是写进观察、指标或提醒对象。
- TTL cache 只服务短时可用性，不承担本地持久化职责；持久化只保留工作台配置，不缓存行情数据。
- 来源状态要进入 `SURF-SOURCE` 与局部降级提示，保持“能继续看盘，但知道结论不可解释”的语义。

**traces_to：** `FR-06`、`AC-02`、`AC-03`、`AC-04`、`BUC-06`、`BO-003`、`BO-007`、`BR-004`、`BR-005`、`BR-016`、`SURF-SOURCE`、`SURF-WORKBENCH`、`SURF-MTS`、`SURF-ALERTS`、`source-status-banner`、`source-mode-label`、`degradation-reason`、`data-insufficient-note`

**适配性评估**

| 路线 | 目标完成度 | DDD 适配 | 维护成本 | 验证难度 | 结论 |
|---|---|---|---|---|---|
| A | 部分 | 低 | 低 | 低 | 拒绝 |
| B | 高 | 高 | 中 | 中 | 采用 |

---

### D-04：图表指标与 MTS 计算位置

**问题描述**

需要决定指标和 MTS 是在后端计算、前端临时计算，还是共享纯领域层计算。

**可行路线**

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A: 后端预计算 | 由 Express 代理顺手算出指标和信号，再把结果下发。 | 便于集中处理。 | 容易把本地代理变成计算中心，且和前端状态分裂。 |
| B: 共享纯 TS 领域层 + 浏览器端计算（必要时 worker） | 价格条进入前端后，由纯函数计算指标、MTS 和提醒输入，必要时再放入 worker。 | deterministic、易回放、易做 fixture、便于 e2e。 | 需要控制性能与内存。 |

**选择：** 路线 B

**理由：**
- MTS 和提醒要求同输入同输出，不能让 UI 事件时序影响结果。
- 共享纯 TS 领域层便于复用到 unit / replay / e2e，减少前后端重复实现。
- 后端只负责来源适配和缓存，不承担策略计算，能保持 `ARCH-001` 的职责边界。
- 这也避免手写核心 K 线引擎；图表渲染交给库，指标和信号只处理领域计算。

**traces_to：** `FR-02`、`FR-03`、`FR-04`、`BUC-02`、`BUC-03`、`BUC-04`、`BUC-08`、`BO-003`、`BO-004`、`BO-005`、`BR-004`、`BR-006`、`BR-007`、`BR-008`、`BR-009`、`BR-010`、`BR-011`、`NFR-06`、`SURF-WORKBENCH`、`SURF-MTS`、`mts-signal-card`

**适配性评估**

| 路线 | 目标完成度 | DDD 适配 | 维护成本 | 验证难度 | 结论 |
|---|---|---|---|---|---|
| A | 部分 | 中 | 中 | 中 | 拒绝 |
| B | 高 | 高 | 中 | 低 | 采用 |

---

### D-05：MTS 信号与提醒规则编排

**问题描述**

需要决定 MTS、价格型提醒、信号型提醒、归档暂停和风控优先级由谁来编排。

**可行路线**

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A: 组件内直接判断 | UI 组件按渲染时机直接写入信号与提醒状态。 | 代码短。 | 容易把策略散落到界面层，难以验证和回放。 |
| B: 聚合 + Policy + Domain Event 流水线 | `ObservationContextRefreshed` 触发 `MtsSignalEvaluated`，再由 `AlertPriorityPolicy` 解析提醒结果，`AlertRule` 独立成聚合。 | 可解释、可测试、可审计。 | 设计更结构化。 |

**选择：** 路线 B

**理由：**
- `MtsSignal` 必须是解释性结果，不是 UI 拼接文案。
- `AlertRule` 必须保持独立聚合，归档暂停与恢复意图不能靠界面状态临时猜。
- 风控优先级必须由策略决定，避免低优先级提醒覆盖高风险结论。
- MTS 的 `reason_codes` / `invalidators` 采用“稳定语义类别 + 版本化登记”的方式，不在 solution 阶段冻结全部枚举，但也不退化成自由文本。

**traces_to：** `AC-03`、`AC-04`、`FR-03`、`FR-04`、`BUC-04`、`BUC-05`、`BUC-06`、`BO-005`、`BO-006`、`BR-008`、`BR-009`、`BR-010`、`BR-011`、`BR-012`、`BR-013`、`BR-014`、`INV-07`、`INV-09`、`INV-10`、`SURF-MTS`、`SURF-ALERTS`、`SURF-WORKBENCH`、`mts-signal-card`、`mts-reasons`、`mts-invalidators`、`alert-create-form`、`alert-rule-row-*`

**适配性评估**

| 路线 | 目标完成度 | DDD 适配 | 维护成本 | 验证难度 | 结论 |
|---|---|---|---|---|---|
| A | 低 | 低 | 低 | 低 | 拒绝 |
| B | 高 | 高 | 中 | 中 | 采用 |

---

### D-06：本地持久化与恢复粒度

**问题描述**

需要决定 `localStorage` 是只存零散字段，还是以版本化快照承载自选、提醒与布局恢复；同时要决定 ChartLayout 的恢复粒度。

**可行路线**

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A: 整体一把梭的非版本化存储 | 把整个应用状态直接序列化进去。 | 快。 | schema 演进困难，恢复失败风险高。 |
| B: 版本化 snapshot + 标的级布局恢复 + 默认布局回退 | 按 workspace snapshot 持久化 watchlist / alert / last-selected-symbol / layout policy，布局以标的级为主，缺失时回到默认布局。 | 可迁移、可回退、符合本地连续使用。 | 需要迁移器与回退逻辑。 |

**选择：** 路线 B

**理由：**
- `localStorage` 是项目定义的边界，但不能等同于“把所有 UI 状态都塞进去”。
- 标的级布局更符合看盘习惯：不同标的可有不同副图与观察节奏；但若历史数据缺失或 schema 失败，仍必须能回到默认布局。
- 版本号和迁移器是本地长期使用的关键，不然一次 schema 改动就会破坏连续性。

**traces_to：** `AC-05`、`FR-05`、`FR-07`、`FR-08`、`BUC-01`、`BUC-02`、`BUC-05`、`BUC-07`、`BUC-08`、`BO-001`、`BO-006`、`BO-008`、`BR-002`、`BR-015`、`SD-25`、`SURF-WATCHLIST`、`SURF-WORKBENCH`、`SURF-ALERTS`、`SURF-RESTORE`、`SURF-LAYOUT`、`restore-banner`、`restore-summary`、`restore-continue-button`、`layout-toggle-*`

**适配性评估**

| 路线 | 目标完成度 | DDD 适配 | 维护成本 | 验证难度 | 结论 |
|---|---|---|---|---|---|
| A | 低 | 低 | 低 | 中 | 拒绝 |
| B | 高 | 高 | 中 | 中 | 采用 |

---

### D-07：可验证性与 E2E 方案

**问题描述**

需要决定验证是依赖真实行情在线跑通，还是用可回放 fixture 和稳定 locator 构建门禁。

**可行路线**

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A: live-source E2E 为门禁 | 直接用 Yahoo Finance / 在线行情做端到端。 | 接近真实。 | 不稳定，受限流和授权影响大。 |
| B: fixture-first E2E + live smoke | 以 frozen bars、mock source、localStorage 回放为门禁，live 只做非门禁烟雾测试。 | 稳定、可重复、便于截图和回归。 | 不能证明线上供应商长期稳定。 |

**选择：** 路线 B

**理由：**
- 行情源本身不稳定，不能把外部供应商可用性当作产品门禁。
- 交互合同已经提供稳定 `data-testid`：`watchlist-add-input`、`symbol-row-*`、`chart-main-panel`、`chart-volume-panel`、`chart-secondary-panel`、`indicator-tab-*`、`mts-signal-card`、`alert-create-form`、`alert-rule-row-*`、`source-status-banner`、`restore-banner`。
- `VIZ-001` 已覆盖 BUC-01 到 BUC-08 的主交互路径，并把 BUC-09 作为冻结样本验收映射，因此 fixture-first E2E 可以直接对齐 surface / state / flow 合同。

**traces_to：** `BUC-01`~`BUC-09`、`AC-01`~`AC-05`、`FR-09`、`NFR-05`、`SURF-WATCHLIST`、`SURF-WORKBENCH`、`SURF-MTS`、`SURF-ALERTS`、`SURF-SOURCE`、`SURF-LAYOUT`、`SURF-RESTORE`、`FLOW-WATCHLIST-MANAGE`、`FLOW-OPEN-DETAIL`、`FLOW-SWITCH-INDICATOR`、`FLOW-READ-MTS`、`FLOW-MANAGE-ALERT`、`FLOW-RESTORE-WORKSPACE`、`FLOW-SOURCE-DEGRADED`、`FLOW-SWITCH-LAYOUT`、`FLOW-FIXTURE-VALIDATION`、`VIZ-001`

**适配性评估**

| 路线 | 目标完成度 | DDD 适配 | 维护成本 | 验证难度 | 结论 |
|---|---|---|---|---|---|
| A | 低 | 低 | 高 | 高 | 拒绝 |
| B | 高 | 高 | 中 | 低 | 采用 |

---

### D-08：Agent 运行时边界

**问题描述**

`agent_engineering.enabled=true` 会触发设计与审查流程，但任务契约已经明确“涉及 Agent 组件：否”。因此需要决定产品运行时是否引入 Agent。

**可行路线**

| 路线 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| A: 产品运行时引入 Agent | 用 Agent 自动解释行情、生成提醒或辅助决策。 | 看起来更“智能”。 | 违反 deterministic、解释边界和非交易约束，风险高。 |
| B: 产品运行时不引入 Agent，仅保留阶段治理 Agent | Agent 只用于 solution / technical_analysis / review 等阶段，不进入用户可见产品。 | 保持确定性，符合任务契约。 | 不提供自动化决策幻想。 |

**选择：** 路线 B

**理由：**
- 本产品的信号和提醒必须 deterministic，不能把策略输出交给 Agent 随机解释。
- 任务目标不包含 Agent 组件；`agent_engineering.enabled=true` 只意味着设计流程要检查该门类，而不是把 Agent 变成产品能力。
- 若未来引入 Agent，也只能作为明确的、可关闭的、只读辅助层，不得触碰信号生成、提醒触发或任何交易动作。

**traces_to：** `mission-contract.md` 中“涉及 Agent 组件：否”、`product/product-definition.md` 中 `Agent Capability Requirements` 不适用、`NFR-06`、`AUD-01`、`AUD-04`、`BUC-04`、`BUC-05`、`FR-03`、`FR-04`

**适配性评估**

| 路线 | 目标完成度 | DDD 适配 | 维护成本 | 验证难度 | 结论 |
|---|---|---|---|---|---|
| A | 低 | 低 | 高 | 高 | 拒绝 |
| B | 高 | 高 | 低 | 低 | 采用 |

---

## 适配性评估

本方案的适配性判断可以归纳为四条主线：

| 路线族 | 适配结论 | 说明 |
|---|---|---|
| 本地单体 React SPA + `lightweight-charts` | 采用 | 与现有工程栈一致，最符合本地网页和可持续恢复边界；Workbench / MTS / Alerts / Restore 通过统一信息架构承载。 |
| 共享纯 TS 指标 / MTS / 提醒流水线 | 采用 | 维持 deterministic，方便 fixture、回放与 E2E。 |
| 版本化 `localStorage` + 标的级恢复 + 默认回退 | 采用 | 符合本地连续使用，且对 schema 演进更稳。 |
| fixture-first E2E + live smoke | 采用 | 抵抗 Yahoo 限流和授权不确定性，保证验证稳定。 |
| 运行时 Agent | 拒绝 | 违反确定性、解释边界和任务授权。 |

---

## 所选路线与理由

### 总体路线

1. 以本地 React SPA 作为唯一产品入口，Express 只负责本地静态服务与行情代理。
2. 图表继续使用 `lightweight-charts`，不在本阶段迁移到更重的图表栈。
3. 行情适配通过 `MarketDataSource` 边界显式管理，允许正式 / 演示 / 降级状态穿透到 UI。
4. 指标与 MTS 在共享纯 TS 域层中计算，提醒通过事件和策略编排，不让 UI 写业务规则。
5. 本地恢复以版本化 `localStorage` 快照完成，布局以标的级为主并有默认回退。
6. 验证以 fixture-first E2E 和回放样本为门禁，live source 只做非门禁烟雾验证。
7. 产品运行时不引入 Agent。
8. 默认看盘信息架构采用 focus，dense 仅作为诊断 / 验收展开，不改变产品语义，只改变 surface 组织方式。

### 为什么不是“更快但更浅”的路线

- 不能把 demo/fallback 当真实行情；这会直接破坏信任边界。
- 不能把指标写成投资建议；这会违反产品定位与审计要求。
- 不能用账号/云同步替代本地恢复；这会改变产品边界并引入不必要的复杂度。
- 不能让技术指标或 MTS 退化成旧 composite signal 的简单替身；那会使研究设计失去落地语义。

### 允许保留的 accepted alternatives

- `KLineChart`：作为后续在图表交互上限不足时的替换候选，不进入本阶段主路由。
- 未来正式行情供应商：作为 `MarketDataSource` 的可替换实现，不写死在领域模型里。
- IndexedDB：仅在 `localStorage` 容量或迁移确实不足时，作为后续单独决策的替代存储层；当前不启用。
- 未来 Agent：仅能作为非默认、只读、阶段性辅助，不得进入产品 runtime 主流程。

---

## 禁止路径

1. **禁止把 fallback 伪装成真实行情。**
   - demo / fallback 必须显式可见，并穿透到 `SURF-SOURCE` 与局部降级提示。
2. **禁止引入账号、云同步、跨设备同步或自动交易。**
   - 这些能力会改变任务授权边界。
3. **禁止把技术指标或 MTS 写成投资建议、收益承诺或胜率表达。**
   - 分数带只用于排序与提醒强度。
4. **禁止忽略多市场代码歧义。**
   - 数字代码必须有市场确认或可见预览，不能静默猜测。
5. **禁止手写核心 K 线引擎。**
   - 图表渲染交给成熟库，领域层只处理计算与解释。
6. **禁止用 Agent 生成或替代信号/提醒。**
   - Agent 只可存在于阶段治理，不可进入 runtime 决策链。

---

## 风险、缓解与 Gate

| 风险 | 影响 | 缓解 | Gate / 证据 |
|---|---|---|---|
| Yahoo Finance 非授权与限流 | 来源不稳定、可能触发降级 | 以 `MarketDataSource` 作为可替换边界；缓存只做短 TTL；页面必须显示 formal / demo_fallback / unavailable。 | 需要提供降级截图、source banner、刷新失败日志和 fixture 回放证据。 |
| 市场代码歧义 | 自选 identity 错误会污染提醒和恢复 | 输入时要求市场确认或展示归一预览；歧义必须阻断 active 化。 | 需要证明 `watchlist-add-input`、`symbol-row-*`、市场选择、错误态可见。 |
| MTS taxonomy 待定 | 影响 reason code / invalidator 一致性 | 采用“稳定语义类别 + 版本化登记”，技术分析阶段再细化枚举，不让自由文本进入主逻辑。 | 需要提供 reason/invalidator 字典草案、fixture 及断言。 |
| localStorage schema 演进 | 重开恢复可能失效或丢状态 | 采用版本号、迁移器、默认布局回退和快照校验；失败时不阻断看盘主路径。 | 需要提供迁移测试、旧版本回放和恢复成功证据。 |
| E2E 缺基础设施 | live 依赖会导致测试不稳定 | 以 fixture-first + mock source + 稳定 locator 为门禁，live 只做 smoke。 | 需要提供本地浏览器回归、截图、`data-testid` 断言。 |

---

## 影响面

### 产品层

- 自选、Workbench、MTS、提醒、来源状态、布局、恢复这七条 surface 主路径都要保持同一份领域语义。
- `SURF-WATCHLIST`、`SURF-WORKBENCH`、`SURF-MTS`、`SURF-ALERTS`、`SURF-SOURCE`、`SURF-LAYOUT`、`SURF-RESTORE` 必须共享统一的状态词汇，不能各写各的。

### 技术层

- 前端需要一个清晰的领域模块边界，而不是把规则散落在组件里。
- 后端只承担本地服务、来源适配、短 TTL cache 和可替换上游，不承担业务策略。
- 指标与信号引擎必须可回放、可 fixture 化、可 deterministic。

### 验证层

- 需要对 market normalization、source degradation、indicator readiness、MTS 解释、alert priority、restore fallback 做确定性测试。
- 需要将 interaction-spec 的 locators 直接用于 E2E，避免靠脆弱 DOM 结构验证。

---

## 下游 technical_analysis 输入

技术分析阶段必须展开的内容：

1. **模块边界**
   - `market-normalization`
   - `market-data-source`
   - `observation-context`
   - `indicator-engine`
   - `mts-interpreter`
   - `alert-resolution`
   - `workspace-recovery`

2. **接口方向**
   - `MarketDataSource` 只输出来源声明与 price bars，不直接输出策略结论。
   - `ObservationContext` 接收 bars、source mode、layout policy，输出 ready/partial/unavailable。
   - `MtsSignal` 必须携带 trend state、score band、signal type、alert level、reason codes、invalidators。
   - `AlertRule` 必须支持 enabled/disabled/suspended_by_archive 与 idle/triggered/acknowledged。

3. **数据流 / 状态流**
   - `ObservationContextRefreshed -> MtsSignalEvaluated -> AlertRuleTriggered` 的事件顺序必须 deterministic。
   - `WatchSymbolArchived` 必须暂停绑定提醒，恢复后按原意图恢复。
   - `SourceDegraded` 必须向下游传播，不得被 UI 截断。

4. **验证重点**
   - 歧义市场输入的拒绝路径。
   - demo/fallback 透明显示。
   - MTS 不退化成单一买卖箭头。
   - 风控优先级高于观察类提醒。
   - 标的级布局恢复失败时能回退到默认布局。
   - fixture-first E2E 与 `VIZ-001` 覆盖一致。

---

## Agent 架构

本任务**不引入产品运行时 Agent**。`agent_engineering.enabled=true` 只表示方案与技术分析阶段需要对 Agent 维度做显式审查，但本 mission 的产品语义已经明确为“无 Agent 组件”。因此：

- 不存在自动分析行情、自动生成提醒、自动下单或自动解释信号的 Agent runtime。
- 任何后续若出现 Agent，只能作为非默认、只读、可关闭的阶段治理或辅助工具，且不得接入 MTS、AlertRule 或交易路径。
- 这一决策与 `NFR-06`、`AUD-01`、`AUD-04` 一致：信号链路必须 deterministic，且不能把分析结果伪装为建议或概率。

---

## 已知遗留问题

| 问题 | 当前决定 | 后续处理建议 |
|---|---|---|
| MTS reason code / invalidator 的完整枚举 | 采用稳定语义类别 + 版本化登记，不冻结全部全集 | technical_analysis 再细化字段、枚举和 fixture。 |
| formal provider 的最终品牌与授权 | 不锁定 | 保持 `MarketDataSource` 可替换，后续再做供应商决策。 |
| localStorage 容量与迁移细节 | 先以版本化 snapshot 实现 | 技术分析补迁移器和回退策略。 |
