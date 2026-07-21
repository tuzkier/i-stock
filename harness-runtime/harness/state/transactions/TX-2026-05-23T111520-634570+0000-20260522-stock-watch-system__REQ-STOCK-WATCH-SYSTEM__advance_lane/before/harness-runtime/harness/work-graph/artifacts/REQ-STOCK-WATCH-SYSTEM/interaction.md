# Interaction: MyInvestment 多市场股票看盘系统

Contract: contracts/interaction.contract.yaml

**mission-id:** `20260522-stock-watch-system`  
**stage:** `interaction`  
**artifact tier:** `standard`  
**主入口:** `visual-interaction/prototype/index.html`

## 阶段目标

把 PRD 产品定义包中的 7 个需要原型化的 BUC，转化为可实现、可验证、可追溯的界面交互合同。本文与 `interaction-spec/` 是下游 AI 的权威界面合同；HTML 原型只作为人类走查入口和视觉证据。

## 输入摘要

| 输入 | 消费方式 |
|---|---|
| `mission-contract.md` | 确认本地网页、多市场、自选、图表、MTS、提醒、本地恢复和非目标边界 |
| `product/product-definition.md` | 消费 FR-01 ~ FR-06、NFR-01 ~ NFR-06 和范围取舍 |
| `product/business-objects.md` | 消费 BO-001 ~ BO-008、BR-001 ~ BR-016 |
| `product/business-use-cases.md` | 以 BUC-01 ~ BUC-07 作为原型组织轴 |
| `product/product-domain-model.md` | 消费 BC、Aggregate、Command、Event、State Machine 和 Invariant |
| `project-context.md` | 消费本地网页、Yahoo Finance fallback、localStorage、非投资建议等项目约束 |

## Artifact Tier

选择 `standard`：全部 7 个 BUC 都标记 `Prototype Required=yes`，且涉及共享 surface、状态降级、提醒优先级、本地恢复和用户信任边界。仅写 light 合同不足以支撑后续 solution / technical_analysis；deep 级别暂不需要，因为当前不做真实前端工程和 E2E 自动化。

## Surface / BUC 覆盖

| Surface | 承载 BUC | 说明 |
|---|---|---|
| `SURF-WATCHLIST` 自选工作台 | BUC-01, BUC-06, BUC-07 | 市场分组、自选新增、归档/恢复、来源状态摘要 |
| `SURF-DETAIL` 标的看盘详情 | BUC-02, BUC-03, BUC-04, BUC-07 | 主图、成交量、副图、MTS、来源降级 |
| `SURF-ALERTS` 提醒管理面板 | BUC-05, BUC-06 | 价格型 / 信号型提醒、四级语义、风控优先、启停和确认 |
| `SURF-SOURCE` 来源状态条 | BUC-07 | formal / demo_fallback / unavailable 与不可解释对象提示 |

完整覆盖矩阵见 `interaction-spec/buc-coverage.md`。

## 关键流程

1. 用户在自选工作台输入股票代码，系统展示市场识别、原始代码、归一代码和加入结果。
2. 用户选择 active 标的后进入看盘详情，默认看到主图、成交量和一个副图指标。
3. 用户切换 MACD / RSI / KDJ / ATR，主图和成交量上下文不丢失。
4. 系统在详情页展示 MTS 趋势状态、分数带、信号类型、提醒等级、理由与失效条件。
5. 用户创建价格型或信号型提醒，系统按观察 / 确认 / 强信号 / 风控四级语义展示规则和触发结果。
6. 用户重开浏览器后，界面先恢复本地自选、提醒和最近观察上下文；若布局恢复粒度未定，则回到默认看盘布局。
7. 来源降级时，界面保留基础观察入口，但明确说明来源模式、降级原因，以及 MTS / 指标 / 提醒的不可解释状态。

## 状态矩阵

| 对象 | 状态 | 界面表达 | 追溯 |
|---|---|---|---|
| WatchSymbol | `active` | 可选中、可看盘、可创建提醒 | BUC-01, BUC-02 |
| WatchSymbol | `archived` | 在归档区显示，可恢复；绑定提醒暂停 | BUC-01, BUC-06 |
| IndicatorSet | `ready` | 副图显示读数和解释摘要 | BUC-02, BUC-03 |
| IndicatorSet | `partial/unavailable` | 图区内显示“数据不足，当前不可解释” | BUC-02, BUC-07 |
| MtsSignal | `watch/confirmed/strong/risk` | 信号卡按四级语义展示，不使用收益承诺 | BUC-04, BUC-05 |
| MtsSignal | `data_insufficient` | 显示不可解释原因，不显示有效信号等级 | BUC-04, BUC-07 |
| AlertRule | `enabled/disabled` | 开关、状态标签和最近触发原因 | BUC-05 |
| AlertRule | `suspended_by_archive` | 标注“因标的归档暂停”，不触发 | BUC-01, BUC-06 |
| MarketDataSource | `formal/demo_fallback/unavailable` | 顶部来源状态条 + 受影响对象说明 | BUC-07 |

## 领域 UI 映射

详见 `interaction-spec/_shared/domain-ui-mapping.md`。核心规则：

- WatchSymbol 进入自选列表项和详情页标题；必须同时显示市场、原始代码和归一代码。
- PriceBar 和 IndicatorSet 进入图表区；数据不足必须影响指标状态。
- MtsSignal 进入解释卡；必须同时包含趋势状态、分数带、信号类型、提醒等级、理由和失效条件。
- AlertRule 进入提醒面板；风控提醒优先级最高。
- MarketDataSource 进入全局状态条和局部降级说明，不得只做装饰角标。
- ChartLayout 进入详情页布局和副图切换控件；未定恢复粒度不阻塞默认布局。

## E2E Locator 策略

所有关键路径使用稳定 `data-testid`，并补充可访问名称：

| Locator | 用途 |
|---|---|
| `watchlist-add-input` / `watchlist-add-button` | 新增自选 |
| `market-group-us/hk/cn/kr` | 市场分组 |
| `symbol-row-<normalized>` | 自选标的行 |
| `chart-main-panel` / `chart-volume-panel` / `chart-secondary-panel` | 默认看盘布局 |
| `indicator-tab-macd/rsi/kdj/atr` | 副图切换 |
| `mts-signal-card` | MTS 解释结果 |
| `alert-create-form` / `alert-rule-row-*` | 提醒创建与规则列表 |
| `source-status-banner` | 来源状态和降级说明 |
| `restore-banner` | 本地恢复结果 |

## PRD 回流检查

结论：无 PRD 回流需求。本阶段只把已授权的 BUC、BO、状态和规则表达为界面合同，没有新增 AC、用户目标、业务对象、权限、自动交易、收益承诺、云同步或账号体系。

待 solution / technical_analysis 定稿但不阻塞 interaction 的事项：

- ChartLayout 恢复粒度：本原型采用“恢复最近标的 + 回退默认布局”的表达，保留全局 / 市场 / 标的粒度决策。
- MarketDataSource 信息密度：本原型采用顶部常驻状态条 + 局部不可解释提示。
- MTS reason code / invalidator：本原型定义展示槽位和示例文案，不定稿完整枚举全集。

## 可视化交互资产

| 资产 | 路径 | 说明 |
|---|---|---|
| 主可操作原型 | `visual-interaction/prototype/index.html` | 唯一默认人类入口，支持 `#buc-01` ~ `#buc-07` |
| 设计说明 | `visual-interaction/design-brief.md` | 记录视觉和交互取舍，不作为用户入口 |
| 视觉 manifest | `visual-interaction/visual-interaction-manifest.json` | 由 Harness CLI 生成，不手写 |

## 沉淀候选

| 候选 | 建议目标 | 理由 |
|---|---|---|
| 多市场自选 + 详情一体化 surface | `project-knowledge/product/ui-surfaces/README.md` | 后续任务应复用同一 Watchlist / Detail / Alerts 结构 |
| 来源降级状态条模式 | `project-knowledge/product/prototype/README.md` | 金融数据可信度需要跨页面一致表达 |
| MTS 解释卡结构 | `project-knowledge/product/workflows/README.md` | MTS 不是买卖箭头，而是趋势、分数、类型、等级、理由和失效条件的组合 |
| 归档导致提醒暂停模式 | `project-knowledge/specs/` 候选 | 这是可观察行为，应在后续规格中固化 |
