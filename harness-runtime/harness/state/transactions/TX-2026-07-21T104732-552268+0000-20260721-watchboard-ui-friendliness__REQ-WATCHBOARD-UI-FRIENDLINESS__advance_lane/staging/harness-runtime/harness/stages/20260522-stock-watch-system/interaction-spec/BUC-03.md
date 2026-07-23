# BUC-03 切换主 / 副图指标并读取 OHLC

## 用户目标

在不离开当前标的的情况下切换 MACD、RSI、KDJ、ATR，并能读取 OHLC 与关键指标读数。

## Entry / Exit

- Entry: 用户已在标的详情页，且图表可见。
- Exit: 副图切换完成，主图与成交量保持同一标的上下文。

## ASCII Wireframe

```text
[MACD*] [RSI] [KDJ] [ATR]
OHLC: O 206.2 / H 208.9 / L 204.8 / C 207.8
当前副图：MACD 柱体转强
```

## Screen Priority

1. 当前副图名称与选中态。
2. OHLC 与关键读数。
3. 指标状态 `ready / partial / unavailable`。
4. 解释摘要，而不是公式细节。

Primary / secondary content: primary 是副图切换与 OHLC 读数；secondary 是读数说明和不可计算时的降级文案。

## Actions

- `SwitchSecondaryIndicator`

## Interaction Rules

- 切换副图不能改变 WatchSymbol。
- `partial` 与 `unavailable` 必须说明不可解释原因。
- 指标读数只服务解释，不输出投资建议。
- 副图切换要同时维护焦点和选中态。

## States

- `ready`
- `partial`
- `unavailable`
- `default`
- `customized`

## Recovery

- 若最近切换的副图可恢复，优先恢复最近选择；否则回到 MACD。
- 数据不足时保留主图与成交量，不伪造副图数值。

## Locator / E2E Obligations

- `indicator-panel`
- `indicator-tab-macd`
- `indicator-tab-rsi`
- `indicator-tab-kdj`
- `indicator-tab-atr`
- `indicator-status-note`
- `chart-secondary-panel`
- `chart-ohlc-readout`

P1 E2E seed: 逐个点击 `indicator-tab-*`，断言 `chart-secondary-panel` 文案变化而 `chart-main-panel` 保持可见。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-03 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-03`
- BO: `BO-003`, `BO-004`, `BO-008`
- AC: `AC-02`
- Delta spec: `默认看盘工作台与指标切换`, `自选列表状态摘要`

## Universal State Coverage

- `STATE-LOADING`: 使用骨架屏、加载标记或保留上一次可解释状态。
- `STATE-EMPTY`: 使用空列表、无数据或无可用规则提示，不留白。
- `STATE-SUCCESS`: 用户动作完成后显示确认反馈并进入下一可操作状态。
- `STATE-ERROR`: 归一失败、数据不可用、重试失败或保存失败时显示可恢复错误。
- `STATE-PERMISSION`: 本地网页不需要账号；云同步、自动交易、外部通知等越权动作显示为不可用或范围外。
- `STATE-DISABLED`: 数据不足、标的归档、来源不可用或布局上下文不适用时禁用相关操作并说明原因。

## Review Notes

- 副图切换是分析视角切换，不是标的切换。
- 选中态与焦点态都要明显，避免误操作。
