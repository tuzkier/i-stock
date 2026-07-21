# BUC-04 解读 MTS 多周期趋势信号

## 用户目标
用趋势状态、分数带、信号类型、提醒等级、理由和失效条件理解当前标的状态。

## Entry / Exit
- Entry: 数据刷新完成或进入标的详情页。
- Exit: MTS 卡展示可解释信号，或明确 `data_insufficient`。

## ASCII Wireframe
```text
MTS 趋势: 多头修复中    分数带: +68 强信号
信号类型: 收敛突破买点  提醒等级: 强信号
理由: EMA20 上行 / MACD 柱体转强 / 成交量放大
失效条件: 跌破 EMA20 或 ATR 风控线
```

## Screen Priority
1. 趋势状态与提醒等级。
2. 分数带和信号类型。
3. 理由与失效条件。
4. 数据不足或来源降级时的不可解释说明。

Primary-secondary content: primary 是趋势状态、分数带、信号类型和提醒等级；secondary 是理由、失效条件和不可解释说明。

## Actions
- `EvaluateMtsSignal`
- `RefreshObservationContext`

## Interaction Rules
- MTS 不是自动买卖指令。
- 分数带不得解释为胜率或收益概率。
- 买点必须区分趋势回调买点 / 收敛突破买点。
- 风险必须区分趋势破坏 / 动量衰竭 / 风控止损。

## States / Recovery
- `interpretable`
- `watch / confirmed / strong / risk`
- `data_insufficient`

## E2E Locators
- `mts-signal-card`
- `mts-trend-state`
- `mts-score-band`
- `mts-signal-type`
- `mts-alert-level`
- `mts-reasons`
- `mts-invalidators`

## E2E Obligation / Locator Strategy
P0 path asserts `mts-signal-card` includes trend state, score band, signal type, alert level, reasons and invalidators; degraded path asserts `data-insufficient-note`.

| Scenario | Priority | Locator Strategy |
|---|---|---|
| E2E-BUC-04-S01 输出解释性 MTS | P0 | data-testid: `mts-signal-card`, `mts-trend-state`, `mts-score-band`, `mts-signal-type`, `mts-alert-level`, `mts-reasons`, `mts-invalidators` |
| E2E-BUC-04-S04 数据不足不输出伪信号 | P0 | data-testid: `data-insufficient-note`, `source-status-banner`; aria live region recommended |

## Common State Coverage
- STATE-LOADING: MTS 评估中显示“正在评估趋势”。
- STATE-EMPTY: 无足够历史数据时不显示有效 MTS。
- STATE-SUCCESS: 可解释 MTS 展示完整六要素。
- STATE-ERROR: 来源失败或计算失败时展示不可解释原因。
- STATE-PERMISSION: 不涉及交易权限，且不能出现自动下单入口。
- STATE-DISABLED: data_insufficient 时信号型提醒触发 disabled。

## UX Review Notes
MTS 卡必须防止误读为交易指令；风控与强信号在视觉上区分，且分数带不表达胜率。

## Traces To
US-03, AC-03, AC-04, BO-003, BO-004, BO-005, BR-008, BR-009, BR-010, BR-011, BR-014
