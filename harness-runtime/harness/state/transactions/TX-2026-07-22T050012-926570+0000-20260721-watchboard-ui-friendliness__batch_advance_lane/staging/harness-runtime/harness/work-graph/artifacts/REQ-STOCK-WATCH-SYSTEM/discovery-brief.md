# Discovery Brief: 20260522-stock-watch-system

**Author:** discovery-analyst  
**Date:** 2026-05-22  
**mission-id:** 20260522-stock-watch-system  
**Status:** draft

- Contract: `contracts/discovery-brief.contract.yaml`

## TL;DR

本任务的真实问题不是“做一个单页股票图表”，而是把港股、A股、美股、韩股的自选、行情、图表、指标、MTS 信号和提醒收束到一个本地可持续使用的看盘入口里。当前草稿已经证明了本地自选、代码归一、图表渲染、基础指标和提醒草稿可行，但数据供应商、MTS 语义、图表分窗路线和是否保留自研指标层仍未定稿，适合在 PRD / solution 阶段继续收敛。

## 问题空间摘要

### 背景

用户要的是一个本地网页形态的多市场看盘系统，重点是跨市场自选管理、价格与指标共看、MTS 多周期趋势信号、买卖/风控提醒，以及可本地持久化的使用体验。第一阶段明确不做自动交易、收益承诺、云同步或完整基本面模块。

### 当前现状

- 当前 package 里已是 React 19.2.3、Vite 7.2.7、lightweight-charts 5.0.9、Express 5.2.1、lucide-react。
- `server/index.js` 直接拉 Yahoo Finance 非官方 chart endpoint，失败时回退到 demo 数据。
- `src/data/markets.ts` 已支持 US/HK/CN/KR 和 Yahoo 风格后缀归一。
- `src/lib/indicators.ts` 已手写 SMA / EMA / RSI / MACD / BOLL / ATR / OBV。
- `src/lib/signals.ts` 仍是旧的 composite signal，不是最终 MTS。
- `src/App.tsx` 已有轻量图表、成交量、图层化信号展示、本地自选与提醒草稿。

### 关键约束

| 约束 | 来源 | 影响 |
|------|------|------|
| 不做自动交易、收益承诺、云同步、完整基本面模块 | mission contract | 直接限定系统边界，提醒只能服务观察与风控。 |
| 优先考虑成熟、维护活跃、许可合适的开源库 | 用户新增约束 | 图表、指标和行情供应商不能默认自研，要先做方案比较。 |
| project-context.md 缺失 | 已采集事实 | 需要用 project-knowledge/context/* 临时代替，后续补齐项目上下文。 |
| gitnexus 不可用 | 已采集事实 | 本次只能用手动代码搜索作为证据，后续补 `npx gitnexus analyze`。 |
| 供应商、回测和成本模型未定稿 | mission contract / research | 不应在 discovery 锁死正式行情源。 |

## 受影响 capability 与置信度

| Capability | 置信度 | 证据 / 推断 |
|---|---|---|
| 多市场自选管理与代码归一 | CONFIRMED | `src/data/markets.ts` 已定义 US/HK/CN/KR 与 `normalizeTicker`；`src/App.tsx` 通过 watchlist + localStorage 维持本地自选。 |
| 图表主图 / 成交量 / 指标展示 | CONFIRMED | `src/App.tsx` 已用 lightweight-charts 绘制 K 线、EMA、BOLL 和 volume scale。 |
| 指标计算层 | CONFIRMED | `src/lib/indicators.ts` 已实现 SMA / EMA / RSI / MACD / BOLL / ATR / OBV。 |
| MTS 多周期趋势信号与提醒语义 | UNCERTAIN | `docs/technical-signal-research-design.md` 已定义 MTS，但 `src/lib/signals.ts` 仍是 legacy composite signal，不能直接当最终 MTS。 |
| 本地持久化与重开恢复 | CONFIRMED | `src/lib/storage.ts` 直接读写 `localStorage`，`src/App.tsx` 持久化 watchlist / alerts。 |
| 数据供应商可插拔与 fallback fixture | ASSUMED | 当前只有 Yahoo 非官方 endpoint + demo fallback，没有显式 `DataProvider` 接口，需 PRD / solution 定义。 |
| 图表分窗 / Pane 布局 | UNCERTAIN | 当前是单图 + 价格刻度的实现；TradingView Lightweight Charts 5.2 文档显示 panes 可支持主图 / 成交量 / 指标分窗。 |

## 业务对象候选

| 候选 ID | 候选对象 | 置信度 | 证据 / 关系线索 | PRD 处理建议 |
|---|---|---|---|---|
| BO-CAND-001 | WatchSymbol / 自选标的 | CONFIRMED | `src/types.ts`、`src/App.tsx`、`src/lib/storage.ts` 都在操作它；是用户直接创建、删除、重排的核心对象。 | promote_to_bo_registry |
| BO-CAND-002 | Market / MarketCode / 市场 | CONFIRMED | `src/types.ts` 与 `src/data/markets.ts` 已明确 US/HK/CN/KR；承担分组与代码归一规则。 | promote_to_bo_registry |
| BO-CAND-003 | PriceBar / OHLCV | CONFIRMED | `server/index.js` 输出 bars，`src/lib/indicators.ts` 以 bars 为计算输入；是图表与指标的基础载体。 | promote_to_bo_registry |
| BO-CAND-004 | IndicatorSet / 指标集 | CONFIRMED | `docs/technical-signal-research-design.md` 定义 EMA / BOLL / MACD / RSI / KDJ / ATR 等组合；`src/App.tsx` 已在 UI 暴露指标快照。 | promote_to_bo_registry |
| BO-CAND-005 | MtsSignal / MTS 多周期趋势信号 | UNCERTAIN | 研究文档已定义状态、评分带、买卖/风控语义，但代码里还未形成最终对象。 | needs_decision |
| BO-CAND-006 | AlertRule / 提醒规则 | CONFIRMED | `src/types.ts`、`src/App.tsx` 已有 price / signal 触发、启停和触发时间的规则草稿。 | promote_to_bo_registry |
| BO-CAND-007 | DataProvider / 行情适配器 | ASSUMED | `server/index.js` 说明当前只是单一上游 + fallback；产品要求“可插拔数据源”，但接口边界未定。 | needs_decision |
| BO-CAND-008 | ChartLayout / Pane / 图表布局 | ASSUMED | 当前 UI 已显式区分主图 / 副图需求；是否持久化布局和如何映射 panes 需要 PRD 决策。 | needs_decision |
| BO-CAND-009 | LegacyCompositeSignal / 旧复合信号 | CONFIRMED | `src/lib/signals.ts` 的输出不是最终 MTS，适合回收为样例代码 / fixture / 回归测试素材。 | exclude_or_reclassify |

## 依赖约束

- 图表库有两条现实路线：继续增强当前 `lightweight-charts`，或评估引入 / 替换为 `KLineChart`。
- `lightweight-charts` 的低迁移路线是继续保留当前技术栈，并利用 5.2 的 panes 能力拆分主图、成交量和指标。
- `KLineChart` 在 Apache-2.0、TypeScript、零依赖、内置指标和画线模型、移动端支持上更贴近金融看盘，但迁移成本需要单独评估。
- `technicalindicators` 可以作为指标参考或局部替代，但它的 npm 元数据显示维护较旧，不适合在没有评估的情况下直接把整个指标层迁过去。
- 行情供应商不要在 discovery 阶段锁死；EODHD、Alpha Vantage、Finnhub、Marketstack 都只能作为候选，Marketstack V1 还要注意 2025-06-30 后的弃用提醒。
- MTS 和提醒层必须保持 deterministic，不应先 agentize。

## 用户角色画像

| 角色 | 核心需要 | 典型频率 | 技术熟悉度 | 说明 |
|---|---|---|---|---|
| 个人投资者 | 跨市场自选管理与快速切换 | 高 | 低 | 需要把港股、A 股、美股、韩股统一到一个本地入口。 |
| 技术分析用户 | 主图 / 副图指标共看 | 高 | 中 | 需要在一屏里判断趋势、动量和波动边界。 |
| 策略观察者 | MTS 解释性信号与风控提醒 | 中 | 中 | 关注的是可解释的趋势、确认和风险语义。 |
| 本地使用者 | 不建账号、重开可恢复 | 高 | 低 | 最关心本地持久化与隐私边界。 |

## 现有方案分析

1. 当前草稿实现是最直接的参考基线，已经覆盖自选、本地存储、行情拉取、指标计算和提醒 UI，但 `server/index.js` 依赖 Yahoo 非官方 chart endpoint，`src/lib/signals.ts` 仍是旧复合信号，不能直接当作最终 MTS。
2. [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/) 是低迁移路线。它开源且 Apache-2.0，5.2 文档已经明确 panes 能分隔主图 / 成交量 / 指标，因此可以在现有栈上继续扩展。
3. [KLineChart](https://github.com/klinecharts/KLineChart) 更贴近金融看盘成品形态，Apache-2.0、TypeScript、零依赖，并且内置多个指标和画线模型；如果后续确认需要更强的金融交互，它是更重但更完整的替换候选。
4. [technicalindicators](https://www.npmjs.com/package/technicalindicators) 可以覆盖 SMA / EMA / MACD / RSI / BOLL / ATR 等常见指标，但维护节奏偏旧，更适合作为参考或局部替代，而不是默认首选。
5. EODHD / Alpha Vantage / Finnhub / Marketstack 都可以进入供应商评估矩阵，但 discovery 阶段不应锁定正式供应商。

## 关键发现

- 现有代码已经证明“本地自选 + 本地持久化 + 图表 + 指标快照 + 提醒草稿”这条产品链路是可工作的，但它离最终系统还差一个正式的 MTS 语义层和数据供应层。
- 旧 `composite signal` 不是 MTS，应该回收成测试 fixture 或迁移样例，而不是直接升级为产品信号。
- 图表路线不必立即推翻当前实现；`lightweight-charts` 先走 panes 增强是低迁移策略，`KLineChart` 适合在需要更多内置金融能力时再评估替换。
- 由于 `project-context.md` 缺失且 gitnexus 不可用，本轮证据是“代码直读 + 外部资料 + 任务输入”的组合证据，足够做 discovery，但不足以直接拍板供应商和最终信号实现。
- 数据适配、指标计算、MTS 和提醒都应保持 deterministic；第一阶段不应 agentize 核心链路。

## PRD 输入建议

| 主题 | 建议写入 PRD 的内容 | 依据 |
|---|---|---|
| 数据供应商 | 定义 `DataProvider` 接口、供应商评估矩阵、demo fixture 兜底策略，不要在 discovery 锁死单一供应商。 | 当前只有 Yahoo 非官方 endpoint + demo fallback，且外部供应商差异明显。 |
| 图表路线 | 明确是继续增强 `lightweight-charts` 的 panes，还是迁移 / 引入 `KLineChart`。 | 现有栈已可运行，但金融看盘能力与迁移成本需要取舍。 |
| MTS 语义 | 定义 `MtsSignal` 的状态、分数带、触发条件、失败条件和提醒文案，明确它不是简单买卖箭头。 | 研究文档已给出规则，但代码还只是旧 composite signal。 |
| 业务对象注册表 | 把 WatchSymbol、Market、PriceBar、IndicatorSet、MtsSignal、AlertRule、DataProvider、ChartLayout 的边界写成正式对象定义。 | 当前对象边界散落在 `types.ts`、UI 和服务端。 |
| 本地化体验 | 明确 localStorage、通知、刷新和重开恢复的行为契约。 | 这是用户的持续使用前提。 |
| 旧信号回收 | 把 `src/lib/signals.ts` 的旧输出改成 fixture / 样例 / 回归素材的候选，而不是最终产品语义。 | 避免把过渡实现写死为产品定义。 |

## 风险与未知

- `project-context.md` 缺失，后续需要补上下文或用 `project-knowledge/context/*` 临时代替，否则下游会缺少长期约束。
- gitnexus 当前不可用，后续应跑 `npx gitnexus analyze` 再补一次索引证据，尤其是 brownfield 影响面。
- 行情供应商、交易成本和授权边界尚未定稿，不能在 PRD 之前把供应商或成本模型写死。
- `technicalindicators`、`KLineChart`、`lightweight-charts` 都有可用性，但它们的最佳组合仍需 PRD / solution 决策，而不是 discovery 直接替用户选完。

## 证据索引

| 证据 | 类型 | 路径 / 来源 |
|---|---|---|
| 任务契约与范围 | doc | [mission-contract.md](</Users/hanbin/Workspace/AI/MyInvestment/harness-runtime/harness/missions/20260522-stock-watch-system/mission-contract.md>) |
| 结构化意图 | doc | [mission-contract.contract.yaml](</Users/hanbin/Workspace/AI/MyInvestment/harness-runtime/harness/missions/20260522-stock-watch-system/contracts/mission-contract.contract.yaml>) |
| 当前实现现状 | code | [server/index.js](</Users/hanbin/Workspace/AI/MyInvestment/server/index.js>), [src/App.tsx](</Users/hanbin/Workspace/AI/MyInvestment/src/App.tsx>), [src/lib/indicators.ts](</Users/hanbin/Workspace/AI/MyInvestment/src/lib/indicators.ts>), [src/lib/signals.ts](</Users/hanbin/Workspace/AI/MyInvestment/src/lib/signals.ts>), [src/data/markets.ts](</Users/hanbin/Workspace/AI/MyInvestment/src/data/markets.ts>) |
| 技术信号研究 | doc | [technical-signal-research-design.md](</Users/hanbin/Workspace/AI/MyInvestment/docs/technical-signal-research-design.md>) |
| 图表库资料 | web | [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/), [Panes 文档](https://tradingview.github.io/lightweight-charts/docs/panes), [KLineChart](https://github.com/klinecharts/KLineChart), [KLineChart 文档](https://klinecharts.com), [technicalindicators](https://www.npmjs.com/package/technicalindicators) |
