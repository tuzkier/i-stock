# BUC-03 切换副图指标观察不同分析维度

## 用户目标
在不离开当前标的、不丢失主图和成交量上下文的情况下切换 MACD / RSI / KDJ / ATR。

## Entry / Exit
- Entry: 用户已在标的详情页。
- Exit: 副图刷新为所选指标，主图与成交量保持不变。

## ASCII Wireframe
```text
副图切换: [MACD*] [RSI] [KDJ] [ATR]
----------------------------------
MACD 柱体方向: 转强
状态: ready
```

## Screen Priority
1. 当前副图名称。
2. 指标状态 ready / partial / unavailable。
3. 解释摘要，而非公式细节。

Primary-secondary content: primary 是当前副图指标和状态；secondary 是解释摘要和参数信息。

## Actions
- `SwitchSecondaryIndicator`

## Interaction Rules
- 切换副图不能改变 WatchSymbol。
- partial 状态必须说明不可解释原因。
- 只展示分析维度，不输出投资建议。

## States / Recovery
- `ChartLayout.default <-> customized`
- 恢复：可恢复最近副图；若无记录则默认 MACD。

## E2E Locators
- `indicator-tab-macd`
- `indicator-tab-rsi`
- `indicator-tab-kdj`
- `indicator-tab-atr`
- `chart-secondary-panel`

## E2E Obligation / Locator Strategy
P1 path clicks each `indicator-tab-*`; assertions verify `chart-secondary-panel` text changes while `chart-main-panel` remains visible.

| Scenario | Priority | Locator Strategy |
|---|---|---|
| E2E-BUC-03-S01 副图切换 | P1 | data-testid: `indicator-tab-macd`, `indicator-tab-rsi`, `indicator-tab-kdj`, `indicator-tab-atr`, `chart-secondary-panel`; role=button |

## Common State Coverage
- STATE-LOADING: 切换副图时显示短暂计算中状态。
- STATE-EMPTY: 当前指标无数据时显示空态说明。
- STATE-SUCCESS: 副图切换完成并显示当前指标名。
- STATE-ERROR: 指标计算失败时显示不可解释原因。
- STATE-PERMISSION: 不涉及账号权限；键盘可用方向键或 Tab 聚焦切换。
- STATE-DISABLED: 数据不足的指标 tab 可点击但显示 disabled explanation，不产出结论。

## UX Review Notes
副图切换是分析视角切换，不应改变标的、主图或提醒上下文；按钮需要清楚显示当前选中态和焦点态。

## Traces To
US-02, AC-02, BO-004, BO-008, BR-006, BR-015
