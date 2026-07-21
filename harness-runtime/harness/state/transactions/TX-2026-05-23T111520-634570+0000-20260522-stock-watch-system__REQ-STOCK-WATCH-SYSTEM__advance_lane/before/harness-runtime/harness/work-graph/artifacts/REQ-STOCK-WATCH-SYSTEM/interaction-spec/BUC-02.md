# BUC-02 打开标的进入默认看盘布局

## 用户目标
选中 active 标的后直接看到主图、成交量和一个可切换副图，不需要先配置布局。

## Entry / Exit
- Entry: 用户点击自选行的“看盘”或标的行。
- Exit: 详情页展示默认布局，或在数据不足时展示局部降级。

## ASCII Wireframe
```text
[AAPL / US / AAPL] [来源 formal]
主图: K线 + EMA20 + EMA60 + BOLL
成交量: Volume
副图: [MACD][RSI][KDJ][ATR] 当前 MACD
```

## Screen Priority
1. 标的身份、市场和来源状态。
2. 主图价格结构。
3. 成交量常驻。
4. 副图当前指标与不可解释提示。

Primary-secondary content: primary 是主图和成交量；secondary 是副图指标、解释摘要和数据不足提示。

## Actions
- `SelectWatchSymbol`
- `RefreshObservationContext`
- `SwitchSecondaryIndicator`

## Interaction Rules
- 主图、副图和 MTS 必须属于同一 WatchSymbol。
- 数据不足时可显示价格，但不可解释指标标记 `partial/unavailable`。
- 默认布局始终可回退到“主图 + 成交量 + 一个副图”。

## States / Recovery
- `ChartLayout.default`
- `IndicatorSet.ready / partial / unavailable`
- 恢复：若布局粒度未定，回到默认布局。

## E2E Locators
- `symbol-detail-shell`
- `chart-main-panel`
- `chart-volume-panel`
- `chart-secondary-panel`
- `indicator-status-note`

## E2E Obligation / Locator Strategy
P0 path selects `symbol-row-*`, then asserts `chart-main-panel`, `chart-volume-panel`, `chart-secondary-panel` are visible and share the same selected symbol.

| Scenario | Priority | Locator Strategy |
|---|---|---|
| E2E-BUC-02-S01 默认布局首开成功 | P0 | data-testid: `symbol-row-aapl`, `chart-main-panel`, `chart-volume-panel`, `chart-secondary-panel`; aria label: 主图 K 线 |

## Common State Coverage
- STATE-LOADING: 图表加载中显示行情刷新状态。
- STATE-EMPTY: 无可展示 PriceBar 时显示“暂无行情，仍保留自选”。
- STATE-SUCCESS: 默认三层布局完成渲染。
- STATE-ERROR: 数据刷新失败时显示来源错误。
- STATE-PERMISSION: 不需要账号权限；通知权限不影响看盘。
- STATE-DISABLED: 数据不足时副图解释 disabled，但主图仍可观察。

## UX Review Notes
主图、成交量、副图不能互相抢占层级；数据不足提示放在图区附近，避免用户把空白当作正常指标。

## Traces To
US-02, AC-02, BO-001, BO-003, BO-004, BO-008, BR-004, BR-006, BR-015
