# BUC-02 打开默认三栏工作台

## 用户目标

选中 active 标的后，直接进入默认三栏工作台：左侧自选，中间图表，右侧来源 / 提醒，不必先配置布局。

## Entry / Exit

- Entry: 用户点击自选行的“看盘”，或选中一个 active 标的。
- Exit: 工作台展示默认三栏布局，或在数据不足时进入可解释降级。

## ASCII Wireframe

```text
┌ Watchlist ─────┐ ┌──── WorkbenchShell ───────────────┐ ┌ Source / Alerts ─┐
│ AAPL  active   │ │ AAPL / US / AAPL                  │ │ 来源: formal      │
│ 0700.HK active │ │ [ChartSurface 主图]               │ │ [AlertRulePanel]  │
│ 600519 archived │ │ [Volume] [IndicatorPanel]         │ │ [MTS card]        │
│                │ │ [MTS card]                         │ │ [RestoreStatus]    │
└─────────────────┘ └────────────────────────────────────┘ └───────────────────┘
```

## Screen Priority

1. 标的身份、市场与来源状态。
2. 主图与成交量。
3. 副图和 OHLC 读数。
4. MTS 与提醒摘要。

Primary / secondary content: primary 是主图、成交量和当前选中标的；secondary 是 OHLC、指标读数和来源说明。

## Actions

- `SelectWatchSymbol`
- `RefreshObservationContext`
- `SwitchSecondaryIndicator`

## Interaction Rules

- 主图、成交量、副图与 MTS 必须属于同一 WatchSymbol。
- 数据不足时可继续显示价格，但不可解释区域必须显式标记 `partial` / `unavailable`。
- 默认布局必须始终可回退；若恢复粒度不明确，则回到可用默认布局。
- 来源健康不是装饰角标，必须参与工作台的标题与说明。

## States

- `ChartLayout.dense`
- `ChartLayout.focus`
- `IndicatorSet.ready / partial / unavailable`
- `PriceSeries.formal / demo_fallback / stale / unavailable`

## Recovery

- 若布局恢复失败，工作台回退到默认三栏与默认副图。
- 若当前标的不可解释，仍保留看盘入口和来源说明，不隐藏全部内容。

## Locator / E2E Obligations

- `workbench-shell`
- `symbol-detail-shell`
- `chart-main-panel`
- `chart-volume-panel`
- `chart-secondary-panel`
- `chart-ohlc-readout`
- `source-status-banner`

P0 E2E seed: 选中 `symbol-row-aapl` 后断言三栏工作台可见，且图表与来源状态共享同一标的上下文。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-02 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-02`
- BO: `BO-001`, `BO-003`, `BO-004`, `BO-007`, `BO-008`
- AC: `AC-02`
- Delta spec: `默认看盘工作台与指标切换`, `来源健康与降级穿透`

## Universal State Coverage

- `STATE-LOADING`: 使用骨架屏、加载标记或保留上一次可解释状态。
- `STATE-EMPTY`: 使用空列表、无数据或无可用规则提示，不留白。
- `STATE-SUCCESS`: 用户动作完成后显示确认反馈并进入下一可操作状态。
- `STATE-ERROR`: 归一失败、数据不可用、重试失败或保存失败时显示可恢复错误。
- `STATE-PERMISSION`: 本地网页不需要账号；云同步、自动交易、外部通知等越权动作显示为不可用或范围外。
- `STATE-DISABLED`: 数据不足、标的归档、来源不可用或布局上下文不适用时禁用相关操作并说明原因。

## Review Notes

- 三栏工作台是任务主路径，不是装饰性排版。
- 主图 / 成交量 / 副图的层级必须稳定，不能互相吞噬信息。
