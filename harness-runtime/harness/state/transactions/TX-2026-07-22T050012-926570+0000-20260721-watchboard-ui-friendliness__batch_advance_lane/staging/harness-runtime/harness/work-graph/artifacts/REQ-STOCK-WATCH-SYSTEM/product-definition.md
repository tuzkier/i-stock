# Product Definition: MyInvestment 本地多市场看盘工作台

> **来源**：prd 技能 → `harness-runtime/harness/stages/20260522-stock-watch-system/product/product-definition.md`  
> **上游**：`mission-contract.md` | `discovery-brief.md` | `docs/open-source-ui-reference.md` | `product/business-objects.md` | `product/business-use-cases.md` | `product/scope-strategy.md`

**mission-id:** `20260522-stock-watch-system`  
**状态（Status）:** `rewritten-for-open-source-reference`

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件提供主产品定义正文。

## Business Definition

**业务问题：** 个人投资者跨港股、A 股、美股、韩股看盘时，真正缺少的不是一个单独 K 线页，而是一个可持续使用的本地看盘工作台：自选列表、图表指标、MTS 解释、提醒规则、来源可信度和浏览器重开恢复必须在同一工作流里闭合。

**业务目标：** 交付一个本地网页形态的多市场看盘工作台。用户能按市场管理自选并处理代码歧义，打开标的后进入默认三栏工作台，查看主图/成交量/副图指标、MTS 解释卡、提醒规则和来源健康，并在同一浏览器中恢复自选、提醒、触发历史和基础布局。

**成功信号：**

- 添加标的前，用户能看见市场、原始代码和归一代码；歧义输入不会静默写入。
- 自选列表行展示市场、归一代码、来源状态、最近价和涨跌摘要。
- 标的详情默认呈现主图、成交量 pane、一个可切换副图 pane，并提供 OHLC/指标读数。
- MTS 以趋势状态、分数带、信号类型、提醒等级、原因和 invalidators 表达，不输出收益承诺或确定性买卖建议。
- 提醒规则具备 taxonomy、启停状态、触发状态、触发历史和归档暂停语义。
- 来源健康明确区分 `formal`、`demo_fallback`、`stale`、`unavailable`，并穿透图表、MTS 和提醒。
- 浏览器重开后恢复自选、提醒、触发历史和 ChartLayout；恢复失败时回到可用默认布局。

**Mission fit：** 本定义仍严格位于 Mission 授权内：本地网页、多市场自选、图表与指标、MTS、提醒、本地恢复。它不扩展到账号/云同步、自动交易、收益承诺、外部推送服务、完整基本面、组合管理、完整回测平台或直接复制 AGPL 项目代码。

## Problem Diagnosis

| 业务方表述 | 底层问题 | 受影响用户 / 场景 | 价值假设 | 证据 |
|---|---|---|---|---|
| 做一个多市场股票看盘系统 | 用户需要的是持续工作台，而不是只显示一张 K 线图 | 个人投资者每天打开本地网页维护四市场自选、看趋势、处理提醒 | 将自选、图表、MTS、提醒、来源、恢复组织在同一工作台，能减少工具切换和误判 | Mission Contract、Discovery、开源 UI 参考 |
| 至少界面功能参考开源项目 | 原 PRD 对 UI surface、状态和提醒 taxonomy 描述不足 | 交互设计、solution、technical_analysis 下游都需要明确可见功能边界 | 参考 OpenStock、Ghostfolio、KLineChart、StockAlert 等功能模式后，PRD 应补齐来源健康、提醒分类、布局模式、读数可见性 | `docs/open-source-ui-reference.md` |
| 行情源可能 fallback | 金融数据可信度本身是用户可见产品语义，不能只是后端异常 | 所有看盘用户在 demo/stale/unavailable 下解读图表和提醒 | 把来源健康设为一级对象，可以避免用户把演示数据当正式行情 | `project-context.md`、BO-007、BUC-06 |
| MTS 要从研究设计落地 | 旧“四因子共振指标”无法承载解释性提醒和风险边界 | 研究驱动用户需要知道“为什么是观察/确认/风控” | MTS 卡片字段化后，提醒和验收能稳定追溯到 reason / invalidator | `docs/technical-signal-research-design.md`、BO-005、BUC-04 |

## Users and Scenarios

| Scenario-ID | 用户 / 角色 | 场景 | 当前痛点 | 目标行为 |
|---|---|---|---|---|
| SCN-01 | 个人投资者 | 添加并维护四市场自选 | 数字代码易歧义，列表缺少来源与价格摘要 | 添加前预览归一结果；列表展示市场、代码、来源、最近价与涨跌 |
| SCN-02 | 技术分析用户 | 打开标的快速看盘 | 单图或指标堆叠不足以支撑判断 | 默认三栏工作台，主图、成交量、副图指标切换和 OHLC 读数同时可用 |
| SCN-03 | 研究驱动用户 | 解读 MTS 与风险状态 | 总分/箭头无法解释触发原因 | MTS 卡片展示趋势、分带、信号类型、等级、原因、失效条件 |
| SCN-04 | 提醒配置用户 | 管理提醒规则和触发结果 | 简单到价提醒无法覆盖变化、指标、MTS、定时观察 | 创建分类提醒，查看触发时间、理由、确认状态 |
| SCN-05 | 本地使用者 | 关闭并重开浏览器 | 不想登录，也不想重复录入自选和提醒 | 恢复自选、提醒、触发历史和基础布局 |
| SCN-06 | 降级场景用户 | 行情源失败或过期 | 容易把 demo 或旧数据当成正式行情 | 来源健康面板明确状态，并同步降级 MTS/提醒解释 |
| SCN-07 | 移动端或专注看图用户 | 在不同设备或任务下切换布局 | 桌面三栏无法直接适配所有情境 | 桌面 dense/focus，移动端 mobile_tab |

## 业务用例地图（Business Use Case Map）

完整 BUC 详情以 `product/business-use-cases.md` 为准。

| BUC-ID | 名称 | Actor | 业务目标 | 相关 BO | Prototype Required | Traces To |
|---|---|---|---|---|---|---|
| BUC-01 | 管理多市场自选与歧义预览 | 个人投资者 | 添加、归档、恢复四市场自选并处理代码歧义 | BO-001, BO-002, BO-006 | yes | AC-01, AC-05, FR-01 |
| BUC-02 | 打开默认看盘工作台 | 个人投资者、技术分析用户 | 进入默认三栏或移动端等价工作台 | BO-001, BO-003, BO-004, BO-005, BO-007, BO-008 | yes | AC-02, FR-02 |
| BUC-03 | 切换副图指标并读取 OHLC | 技术分析用户 | 切换 MACD/RSI/KDJ/ATR 并读取 OHLC/指标值 | BO-003, BO-004, BO-008 | yes | AC-02, FR-03 |
| BUC-04 | 解读 MTS 多周期趋势信号 | 研究驱动用户 | 解释趋势、分带、等级、原因和失效条件 | BO-003, BO-004, BO-005, BO-007 | yes | AC-03, AC-04, FR-04 |
| BUC-05 | 管理本地提醒规则与触发历史 | 研究驱动用户、本地使用者 | 管理 taxonomy、触发、确认、归档暂停和历史 | BO-001, BO-003, BO-004, BO-005, BO-006 | yes | AC-04, AC-05, FR-05 |
| BUC-06 | 查看来源健康并处理降级 | 所有看盘用户 | 识别 formal/demo/stale/unavailable 和重试语义 | BO-003, BO-005, BO-006, BO-007 | yes | AC-02, AC-03, AC-04, FR-06 |
| BUC-07 | 重开浏览器恢复本地工作台 | 本地使用者 | 恢复自选、提醒、触发历史和 ChartLayout | BO-001, BO-006, BO-008 | yes | AC-05, FR-07 |
| BUC-08 | 切换工作台布局模式 | 桌面/移动端用户 | 使用 dense、focus、mobile_tab 模式 | BO-008 | yes | AC-02, AC-05, FR-08 |
| BUC-09 | 使用冻结样本验收关键路径 | 验证者 | 用可回放样本证明 AC | BO-001~BO-008 | no | AC-01~AC-05, FR-09 |

## Current Workflow Summary

1. 用户在自选区输入代码并选择市场，系统展示归一预览或歧义错误态。
2. 用户确认添加后，自选列表出现市场、归一代码、来源状态、最近价和涨跌摘要。
3. 用户选择标的，进入默认工作台：自选、图表、MTS/提醒/来源。
4. 用户查看主图、成交量和副图指标，必要时切换副图或读取 OHLC。
5. 系统根据 PriceSeries 与 IndicatorSet 生成 MTS 解释卡，并区分观察、确认、强信号、风控。
6. 用户创建和管理本地提醒，系统记录触发时间、原因和确认状态。
7. 来源刷新失败、过期或 fallback 时，来源健康面板与图表/MTS/提醒同步降级。
8. 用户切换 dense/focus/mobile_tab 布局；浏览器重开后恢复工作台。

## Scope and Tradeoffs

| 类型 | 内容 | 理由 | 追溯 |
|---|---|---|---|
| In | 本地网页入口、四市场自选、歧义预览 | Mission 核心目标与跨市场风险点 | SD-01~SD-03 |
| In | 默认三栏工作台、主图/成交量/副图切换、OHLC 可读 | 开源参考证明用户自然期待工作台和指标切换，而不是单图页 | SD-04, SD-05 |
| In | MTS 解释卡、提醒 taxonomy、本地触发历史 | AC-03/04 需要可解释、可追溯的提醒闭环 | SD-06~SD-08 |
| In | 来源健康面板、本地恢复、dense/focus/mobile_tab | 金融可信度、持续使用和设备适配是工作台成立条件 | SD-09~SD-11 |
| In | fixture-first 验证输入 | 下游验证不能依赖不稳定 live 行情 | SD-12 |
| Out | 账号/云同步/数据库多用户、自动交易、收益承诺 | 违反本地化和金融风险边界 | SD-13~SD-15 |
| Out | TradingView iframe 替代本地图表、直接复制 AGPL 代码 | 破坏本地可控验证或带来许可证风险 | SD-16, SD-17 |
| Out | 完整基本面、组合管理、完整回测、外部推送 | 超出第一阶段产品授权 | SD-18~SD-21 |
| Later | KLineChart 替换、高级画线、多源正式供应商、外部通知、桌面封装、完整回测 | 有价值但不属于当前闭环前提 | SD-22~SD-27 |
| Decision Needed | ChartLayout 恢复粒度、移动端默认 tab、来源信息密度、MTS taxonomy | 需要 interaction / solution / technical_analysis 联合定稿 | SD-28~SD-31 |

## 证据摘要（Evidence Summary）

| Evidence Type | Source | Product Decision Impact | Degradation |
|---|---|---|---|
| Mission | `mission-contract.md` | 确认目标、范围、AC、非目标和治理风险 | 无 |
| Discovery | `discovery-brief.md` | 确认不是单页图表，而是持续工作台；确认来源、MTS、恢复风险 | GitNexus 仍不可用，保留降级记录 |
| Open Source UI Reference | `docs/open-source-ui-reference.md` | 补充自选行状态、图表 pane、MTS 卡、提醒 taxonomy、来源健康、布局模式 | 只参考功能与交互，不复制 AGPL 代码 |
| Project Context | `project-context.md` | 明确本地化、fallback 可见、技术信号非投资建议 | 无 |
| Spec | `project-knowledge/specs/_index.md` | `spec.enabled=true`；当前无基线能力规格，需产出 delta spec | Baseline 为 none，首次建立任务差量规格 |
| Product Specialists | `business-objects.md`、`business-use-cases.md`、`scope-strategy.md` | 提供 BO、BUC、范围和下游重对齐边界 | BUC 子 Agent 超时后由主流程补写，后续 reviewer 审查 |

## Product Domain Summary

### Core Objects

| BO-ID | 对象 | 说明 | Spec 来源关系 |
|---|---|---|---|
| BO-001 | WatchSymbol / 自选标的 | 用户持续观察的标的，承载列表行摘要和 active/archived 状态 | adjusted |
| BO-002 | Market / 市场 | 代码归一和市场分组语义，不等于供应商 | existing |
| BO-003 | PriceSeries / 行情序列 | 图表、成交量、OHLC、最近价和涨跌摘要的共同输入 | reclassified |
| BO-004 | IndicatorSet / 指标集 | 主图指标、成交量 pane、副图指标和读数状态 | adjusted |
| BO-005 | MtsSignal / MTS 多周期趋势信号 | 趋势状态、分数带、信号类型、提醒等级、原因、失效条件 | adjusted |
| BO-006 | AlertRule / 提醒规则 | 本地提醒 taxonomy、启停状态、触发状态、触发历史 | adjusted |
| BO-007 | MarketDataSource / 行情来源健康 | formal/demo_fallback/stale/unavailable、刷新和重试语义 | reclassified |
| BO-008 | ChartLayout / 工作台布局 | dense/focus/mobile_tab、pane 组织和恢复状态 | adjusted |

### State and Permission Summary

- 用户可添加、归档、恢复 WatchSymbol；系统不得静默处理歧义市场。
- 用户可切换副图、布局模式、提醒启停和确认提醒；系统可刷新来源、评估 MTS、解析提醒触发。
- `demo_fallback`、`stale`、`unavailable` 必须向 PriceSeries、MTS、AlertRule 传播。
- 任何自动交易、收益承诺、账号云同步、外部推送发送均不在权限边界内。

## Product Rules

| Rule-ID | 规则 | 验收方式 | 追溯 |
|---|---|---|---|
| RULE-01 | 新增自选前必须展示市场、原始代码和归一代码；歧义输入不得静默写入 | BUC-01 GWT、四市场/歧义样本 | BR-001, BR-004 |
| RULE-02 | 自选列表行必须可展示市场、归一代码、来源状态、最近价与涨跌摘要 | BUC-01/02 截图 | BR-003 |
| RULE-03 | 默认工作台必须包含主图、成交量 pane 和一个可切换副图 pane | BUC-02/03 页面验证 | BR-006 |
| RULE-04 | OHLC 与关键指标读数必须可读，不能只依赖颜色或曲线 | BUC-03 tooltip/读数验证 | BR-007 |
| RULE-05 | MTS 必须显示 trend_state、score_band、signal_type、alert_level、reason_codes、invalidators | BUC-04 样本验证 | BR-009 |
| RULE-06 | MTS 与提醒不得使用收益承诺、胜率或确定性买卖建议主语义 | 文案审查、BUC-04 | BR-010, BR-011 |
| RULE-07 | 提醒规则 taxonomy 至少覆盖价格型、变化型、技术指标型、MTS 型、定时提醒 | BUC-05 | BR-012 |
| RULE-08 | 提醒必须区分启停状态与触发状态，并记录触发时间、原因、确认状态 | BUC-05、本地恢复验证 | BR-013 |
| RULE-09 | 标的归档时，绑定提醒进入 suspended_by_archive 且不触发；恢复后按原意图恢复 | BUC-01/05/07 | BR-014 |
| RULE-10 | 来源健康必须区分 formal、demo_fallback、stale、unavailable，并穿透图表、MTS、提醒 | BUC-06 降级样本 | BR-016, BR-017 |
| RULE-11 | 桌面至少支持 dense/focus；移动端使用 mobile_tab 或等价导航 | BUC-08 响应式截图 | BR-019 |
| RULE-12 | 浏览器重开后恢复自选、提醒、触发历史和基础布局；失败时回到可用默认布局 | BUC-07 | BR-020 |
| RULE-13 | 旧 LegacyCompositeSignal 不得作为正式 MTS 对外展示 | solution / technical_analysis 审查 | BR-021 |

## Functional Requirements

### FR-01: 多市场自选与归一预览

**描述：** 系统必须支持 US/HK/CN/KR 自选管理，在添加前展示市场、原始代码和归一代码，并阻止歧义或不可识别输入静默进入 active 列表。

**验收标准：**
- **Given** 用户输入支持市场的代码
- **When** 用户选择市场或系统能明确归一
- **Then** 页面展示市场、原始代码、归一代码预览，并在确认后加入 active 自选
- **And** 歧义或不可识别输入停在错误/确认状态

**关联：** BUC-01, BO-001, BO-002, RULE-01  
**优先级：** `P0`

### FR-02: 自选列表状态摘要

**描述：** 自选列表必须展示名称、市场、归一代码、来源状态、最近价和涨跌摘要，支持 active/archived 与恢复。

**验收标准：**
- **Given** 用户已有自选标的
- **When** 工作台加载或行情刷新
- **Then** 自选列表行展示市场、归一代码、来源状态、最近价和涨跌摘要
- **And** archived 标的可恢复且不丢失绑定提醒语义

**关联：** BUC-01, BO-001, BO-003, BO-006, BO-007, RULE-02, RULE-09  
**优先级：** `P0`

### FR-03: 默认看盘工作台与指标切换

**描述：** 用户选择 active 标的后，系统必须进入默认工作台，展示主图、成交量 pane、可切换副图 pane，并提供 OHLC 与关键指标读数。

**验收标准：**
- **Given** 用户选择 active 标的
- **When** 工作台打开
- **Then** 页面展示主图、成交量 pane 和副图指标
- **And** 用户可在 MACD、RSI、KDJ、ATR/波动候选中切换至少一类副图指标
- **And** OHLC 与指标读数通过 tooltip、读数表或等价 UI 可见

**关联：** BUC-02, BUC-03, BO-003, BO-004, BO-008, RULE-03, RULE-04  
**优先级：** `P0`

### FR-04: MTS 解释性信号卡

**描述：** 系统必须以 MTS 解释卡展示趋势状态、分数、分数带、信号类型、提醒等级、原因和 invalidators；数据不足或来源降级时不得输出伪信号。

**验收标准：**
- **Given** PriceSeries 与 IndicatorSet 可解释
- **When** 系统完成 MTS 评估
- **Then** 页面展示 trend_state、mts_score、score_band、signal_type、alert_level、reason_codes、invalidators
- **And** 文案不使用收益承诺、胜率或确定性买卖建议

**关联：** BUC-04, BO-005, RULE-05, RULE-06  
**优先级：** `P0`

### FR-05: 本地提醒 taxonomy 与触发历史

**描述：** 系统必须支持价格型、变化型、技术指标型、MTS 型、定时提醒的本地规则模型，记录启停状态、触发状态、触发时间、原因和确认状态。

**验收标准：**
- **Given** 用户正在查看 active 标的
- **When** 用户创建或更新提醒
- **Then** 系统保存提醒 taxonomy、条件、启停状态
- **And** 条件命中时记录触发时间、触发理由和确认状态

**关联：** BUC-05, BO-006, RULE-07, RULE-08  
**优先级：** `P0`

### FR-06: 来源健康与降级穿透

**描述：** 系统必须把来源健康作为一级 UI 状态，区分 formal、demo_fallback、stale、unavailable，并将降级语义同步到图表、MTS 和提醒。

**验收标准：**
- **Given** 来源刷新成功、失败、过期或不可用
- **When** 工作台更新来源健康
- **Then** 页面显示来源状态、上次刷新或降级原因
- **And** 图表、MTS、提醒区域同步显示可解释性限制

**关联：** BUC-06, BO-007, RULE-10  
**优先级：** `P0`

### FR-07: 本地恢复

**描述：** 系统必须在同一浏览器配置下恢复自选、提醒启停/触发/确认状态、触发历史和基础 ChartLayout。

**验收标准：**
- **Given** 用户已保存自选、提醒和布局状态
- **When** 用户关闭并重新打开浏览器
- **Then** 系统恢复自选、提醒、触发历史和基础布局
- **And** 布局恢复失败时回到默认可用工作台

**关联：** BUC-07, BO-001, BO-006, BO-008, RULE-12  
**优先级：** `P0`

### FR-08: 工作台布局模式

**描述：** 桌面端至少支持 dense 与 focus；移动端采用 mobile_tab 或等价单列导航，保证自选、图表、提醒、来源均可访问。

**验收标准：**
- **Given** 用户在桌面端或移动端打开工作台
- **When** 用户切换布局或视口进入移动宽度
- **Then** 桌面端可在 dense/focus 间切换，移动端可通过 tab 或等价导航访问自选、图表、提醒、来源

**关联：** BUC-08, BO-008, RULE-11  
**优先级：** `P1`

### FR-09: Fixture-first 验收输入

**描述：** 后续验证必须具备四市场标的、歧义输入、指标充足/不足、MTS 风险/强信号、提醒触发、来源降级、浏览器重开恢复样本。

**验收标准：**
- **Given** 验证阶段准备验收 AC-01 到 AC-05
- **When** 执行验证
- **Then** 验证证据使用可回放样本覆盖核心路径
- **And** live 行情只作为非门禁烟雾参考

**关联：** BUC-09, SD-12  
**优先级：** `P0`

## Non-Functional Requirements

| ID | 类别 | 要求 | 条件 | 指标 | 测量方式 |
|---|---|---|---|---|---|
| NFR-01 | 可解释性 | MTS 与提醒必须展示原因和失效条件，不能只显示颜色、箭头或单分数 | 所有有效 MTS/提醒场景 | trend_state、score_band、reason_codes、invalidators 可见 | BUC-04 截图和样本 |
| NFR-02 | 金融风险边界 | 不输出收益承诺、胜率、确定性买卖建议或自动交易动作 | 全部页面与提醒文案 | 无越界词汇和交易执行入口 | 文案审查 |
| NFR-03 | 降级透明 | demo/stale/unavailable 必须可见并影响解释 | 来源异常或过期 | 来源状态与降级原因可见；MTS/提醒不伪装正式 | BUC-06 验证 |
| NFR-04 | 本地连续性 | 不依赖账号或云同步恢复核心状态 | 同一浏览器配置 | 自选、提醒、触发历史、基础布局恢复 | 浏览器重开验证 |
| NFR-05 | 可验证性 | 核心验收使用 fixture-first，不以 live 行情作为门禁 | 验证阶段 | 冻结样本覆盖 AC-01~AC-05 | 验证报告 |
| NFR-06 | 许可边界 | 开源项目只参考功能与交互，不复制 AGPL 代码 | solution / execute | 选型与实现记录未直接复用 AGPL 代码 | 审查 |
| NFR-07 | 响应式可用 | dense/focus/mobile_tab 在桌面和移动视口不互相遮挡 | UI 验收 | 核心文本和控件可读可点 | 桌面/移动截图 |
| NFR-08 | 确定性 | MTS 与提醒在相同输入下输出一致 | 冻结 PriceSeries 与规则样本 | 结果稳定可复算 | fixture 验证 |

## Agent Capability Requirements

不适用。`agent_engineering.enabled=true` 只影响 Harness 阶段治理；Mission Contract 已明确产品运行时不包含 Agent 组件。本 PRD 不补造自动行情分析、自动提醒生成、自动交易或 Agent 决策能力。

## Validation and Launch Loop

| 验证阶段 | 验证内容 | 证据 | 成功 / 失败判定 |
|---|---|---|---|
| PRD 后重对齐 | 旧 solution 是否覆盖新 BO/BUC/范围 | solution 重对齐记录 | 若仍引用旧 PriceBar、简单提醒或 notice-only 来源，则需重写 solution |
| 原型 / 交互 | 歧义预览、三栏工作台、指标切换、MTS 卡、提醒 taxonomy、来源健康、布局模式 | interaction spec、截图、走查记录 | 每个 P0 BUC 有可走查路径 |
| 技术设计前 | PriceSeries、MarketDataSource、AlertRule 双状态机、ChartLayout 模式是否被技术对象承载 | tech-design | 缺字段或状态机则 HOLD |
| 验证阶段 | AC-01~AC-05 fixture-first 验收 | 命令证据、截图、浏览器重开证据 | 每条 AC 有 command evidence 与 result evidence |

## 追溯矩阵（Traceability Matrix）

| Mission Story / AC | BO | BUC | Scenario | Rule | FR / NFR | Spec / Knowledge | Evidence |
|---|---|---|---|---|---|---|---|
| US-01 / AC-01 | BO-001, BO-002 | BUC-01 | BUC-01-S01/S02 | RULE-01, RULE-02 | FR-01, FR-02 | delta spec `local-stock-watch-workbench` | 四市场/歧义样本 |
| US-02 / AC-02 | BO-003, BO-004, BO-008 | BUC-02, BUC-03, BUC-08 | BUC-02-S01, BUC-03-S01/S02, BUC-08-S01/S02 | RULE-03, RULE-04, RULE-11 | FR-03, FR-08 | delta spec `local-stock-watch-workbench` | 图表/布局截图 |
| US-03 / AC-03 | BO-005 | BUC-04 | BUC-04-S01/S04 | RULE-05, RULE-06 | FR-04, NFR-01, NFR-02 | research design, delta spec | MTS fixture |
| US-03 / AC-04 | BO-005, BO-006, BO-007 | BUC-04, BUC-05, BUC-06 | BUC-04-S03, BUC-05-S02, BUC-06-S02 | RULE-06, RULE-08, RULE-10 | FR-04, FR-05, FR-06 | delta spec | 提醒/降级样本 |
| US-04 / AC-05 | BO-001, BO-006, BO-008 | BUC-01, BUC-05, BUC-07 | BUC-01-S03, BUC-05-S03, BUC-07-S01/S02 | RULE-09, RULE-12 | FR-07, NFR-04 | project-context, delta spec | 浏览器重开证据 |

## Prototype / Interaction Trigger

| Trigger | Required | Reason | Expected Next Artifact |
|---|---|---|---|
| UI surfaces | required | 工作台、图表、提醒、来源、布局均为用户可见 surface | `interaction.md`、`interaction-spec/`、visual prototype |
| State matrix | required | active/archived、source health、MTS、AlertRule、ChartLayout 状态复杂 | `interaction-spec/_shared/view-models.ts` 或等价状态合同 |
| Responsive walkthrough | required | dense/focus/mobile_tab 是范围内能力 | 桌面/移动截图与走查 |
| Fixture-first verification mapping | required | PRD 明确要求可回放验收输入 | 验证矩阵与后续 E2E obligation |

## Open Questions

| ID | 问题 | 影响 | 决策时机 |
|---|---|---|---|
| OQ-01 | ChartLayout 恢复粒度是全局、市场、标的还是混合 | 持久化模型、验收样本、交互文案 | interaction 原型后、solution 重写前 |
| OQ-02 | 移动端默认 tab 是自选、图表、提醒还是来源 | 移动端首屏和恢复默认值 | interaction |
| OQ-03 | 来源健康信息密度展示到哪一层 | UI 密度、用户可信度、降级说明 | interaction + solution |
| OQ-04 | MTS reason / invalidator taxonomy 首批枚举 | fixture、字段、文案和测试矩阵 | solution / technical_analysis |
| OQ-05 | 提醒配置表单的默认分组与排序 | 不影响五类提醒进入范围，但影响配置效率和移动端信息密度 | interaction / solution |

## PRD 回改说明

当前 Mission Slice 已处于 `solution` 阶段。本 PRD 是按用户要求基于开源界面功能参考进行的上游回改。后续不得继续直接推进旧 solution；必须先让 solution 重新消费本 PRD 中的 `PriceSeries`、`MarketDataSource`、`AlertRule taxonomy`、`ChartLayout dense/focus/mobile_tab`、`source health panel` 和 `fixture-first` 约束。
