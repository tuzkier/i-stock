# BUC-04 解读 MTS 多周期趋势信号

## 用户目标

用趋势状态、分数带、信号类型、提醒等级、原因和失效条件理解当前标的状态，而不是把信号看成单一买卖箭头。

## Entry / Exit

- Entry: 数据刷新完成，或用户打开标的详情页。
- Exit: MTS 卡给出可解释信号，或明确 `data_insufficient`。

## ASCII Wireframe

```text
MTS 趋势状态：多头修复中    分数带：+68   提醒等级：强信号
信号类型：收敛突破买点      当前结论：可解释
理由：EMA20 上行 / MACD 柱体转强 / 成交量放大
失效条件：跌破 EMA20 或 ATR 风控线
```

## Screen Priority

1. 趋势状态与提醒等级。
2. 分数带与信号类型。
3. 原因与失效条件。
4. 数据不足或来源降级时的不可解释说明。

Primary / secondary content: primary 是趋势状态、分数带、信号类型和提醒等级；secondary 是原因、失效条件与解释限制。

## Actions

- `EvaluateMtsSignal`
- `RefreshObservationContext`

## Interaction Rules

- MTS 不是自动买卖指令。
- 分数带不得解释为胜率或收益概率。
- 必须同时显示 `trend_state`、`score_band`、`signal_type`、`alert_level`、`reason_codes`、`invalidators`。
- 风控优先级高于观察类提醒。

## States

- `interpretable`
- `data_insufficient`
- `watch`
- `confirm`
- `strong_signal`
- `risk`

## Recovery

- 数据不足时保留可读说明，不输出伪信号。
- 来源降级时，MTS 卡降级为解释限制提示，而不是空白。

## Locator / E2E Obligations

- `mts-signal-card`
- `mts-trend-state`
- `mts-score-band`
- `mts-signal-type`
- `mts-alert-level`
- `mts-reasons`
- `mts-invalidators`
- `data-insufficient-note`

P0 E2E seed: 断言 MTS 卡包含六要素；当来源或数据不足时断言 `data-insufficient-note` 显示。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-04 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-04`
- BO: `BO-003`, `BO-004`, `BO-005`
- AC: `AC-03`, `AC-04`
- Delta spec: `MTS 解释性信号`, `来源健康与降级穿透`

## Universal State Coverage

- `STATE-LOADING`: 使用骨架屏、加载标记或保留上一次可解释状态。
- `STATE-EMPTY`: 使用空列表、无数据或无可用规则提示，不留白。
- `STATE-SUCCESS`: 用户动作完成后显示确认反馈并进入下一可操作状态。
- `STATE-ERROR`: 归一失败、数据不可用、重试失败或保存失败时显示可恢复错误。
- `STATE-PERMISSION`: 本地网页不需要账号；云同步、自动交易、外部通知等越权动作显示为不可用或范围外。
- `STATE-DISABLED`: 数据不足、标的归档、来源不可用或布局上下文不适用时禁用相关操作并说明原因。

## Review Notes

- 不出现“强买”“强卖”“收益保证”“胜率”这类主语义。
- 风控与观察要分层呈现，避免用户误解。
