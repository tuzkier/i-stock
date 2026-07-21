# BUC-07 行情来源降级下继续看盘

## 用户目标
正式来源不可用时仍能继续基础观察，同时清楚知道当前来源、降级原因和哪些结论不可解释。

## Entry / Exit
- Entry: 来源刷新失败、覆盖不足或进入演示数据。
- Exit: 来源状态条和受影响对象同步更新。

## ASCII Wireframe
```text
[来源降级] Yahoo Finance 本次不可用，当前展示演示 K 线
可继续观察: 主图价格结构
当前不可解释: MTS / 强信号提醒 / 部分指标
```

## Screen Priority
1. 来源模式 formal / demo_fallback / unavailable。
2. 降级原因和更新时间。
3. 可继续观察内容。
4. 不可解释对象。

Primary-secondary content: primary 是来源模式和降级原因；secondary 是受影响对象和仍可观察的内容。

## Actions
- `RefreshObservationContext`
- `EvaluateMtsSignal`
- `ResolveAlertOutcome`

## Interaction Rules
- demo_fallback 不得伪装成正式实时行情。
- 来源降级必须传播到 IndicatorSet、MtsSignal、AlertRule。
- 降级不改变“不做自动交易、不承诺收益”的产品边界。

## States / Recovery
- `MarketDataSource.available -> degraded / unavailable`
- `PriceBar.live_or_formal -> demo_fallback`
- `MtsSignal.data_insufficient`
- `AlertRule` 保留规则但不产出伪触发。

## E2E Locators
- `source-status-banner`
- `source-mode-label`
- `degradation-reason`
- `affected-object-list`
- `data-insufficient-note`

## E2E Obligation / Locator Strategy
P0 degraded path asserts `source-status-banner`, `source-mode-label`, `degradation-reason`, `affected-object-list` and `data-insufficient-note`.

| Scenario | Priority | Locator Strategy |
|---|---|---|
| E2E-BUC-07-S01 正式来源失败后切入降级模式 | P0 | data-testid: `source-status-banner`, `source-mode-label`, `degradation-reason`, `affected-object-list` |
| E2E-BUC-07-S02 降级导致信号不可解释 | P0 | data-testid: `data-insufficient-note`, `mts-signal-card`; aria live region recommended |

## Common State Coverage
- STATE-LOADING: 来源刷新中显示刷新状态。
- STATE-EMPTY: 无任何可用行情时显示不可用空态。
- STATE-SUCCESS: formal 来源可用时显示正式状态。
- STATE-ERROR: 来源失败时显示 degraded/unavailable 原因。
- STATE-PERMISSION: 不涉及账号权限；外部行情授权不足时只表达来源不可用。
- STATE-DISABLED: 降级导致 MTS 和强信号提醒 disabled，不产出伪触发。

## UX Review Notes
来源状态条必须持续可见但不压缩图表核心区域；“可继续观察”和“当前不可解释”要同时表达。

## Traces To
US-02, US-03, AC-02, AC-03, AC-04, BO-007, BO-003, BO-004, BO-005, BO-006, BR-004, BR-005, BR-016
