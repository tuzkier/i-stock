# Domain UI Mapping

| Domain element / rule | UI surface / object | User-visible rule | Trace |
|---|---|---|---|
| `BO-001 WatchSymbol` | `WatchlistPanel`, `WatchlistRow`, `RestoreStatus`, `WorkbenchShell` 标题 | 同时显示市场、原始代码、归一代码；archived 可恢复 | BUC-01, BUC-07 |
| `BO-002 Market` | `NormalizationPreview`, 市场分组标签 | US / HK / CN / KR 四市场明确；歧义输入不得静默写入 active | BUC-01 |
| `BO-003 PriceSeries` | `ChartSurface`, `chart-main-panel`, `chart-volume-panel`, `chart-ohlc-readout` | 可展示价格，但数据不足时不得伪造正式结论 | BUC-02, BUC-03, BUC-06 |
| `BO-004 IndicatorSet` | `IndicatorPanel`, `chart-secondary-panel` | 默认主图 + 成交量 + 单一副图；partial / unavailable 必须可见 | BUC-02, BUC-03 |
| `BO-005 MtsSignal` | `MtsSignalCard` | 必须同时显示趋势状态、分数带、信号类型、提醒等级、原因、失效条件 | BUC-04, BUC-06 |
| `BO-006 AlertRule` | `AlertRulePanel`, `alert-rule-row-*`, `daily-dock` | 日常模式显示提醒摘要，诊断 / 验收模式展开 taxonomy、启停、触发历史、确认动作、归档暂停 | BUC-05, BUC-07 |
| `BO-007 MarketDataSource` | `SourceHealthPanel`, `source-status-banner` | formal / demo_fallback / stale / unavailable 必须穿透到图表、MTS、提醒 | BUC-06 |
| `BO-008 ChartLayout` | `LayoutController`, `WorkbenchShell`, `mobile_tab` 导航 | dense / focus / mobile_tab 只改变布局，不改变业务对象 | BUC-08 |

## Commands / UI actions

| Domain command / intent | UI action | Feedback | Trace |
|---|---|---|---|
| `AddWatchSymbol` | 点击“加入” | 先给出归一预览，再写入 active | BUC-01 |
| `ArchiveWatchSymbol` | 点击“归档” | 变为 archived，并暂停绑定提醒 | BUC-01 |
| `RestoreWatchSymbol` | 点击“恢复” | 恢复 active 与归档前启停意图 | BUC-01, BUC-07 |
| `SelectWatchSymbol` | 点击“看盘”或行本身 | Workbench 切换到同一标的上下文 | BUC-02 |
| `SwitchSecondaryIndicator` | 点击 MACD / RSI / KDJ / ATR | 副图和说明立即切换 | BUC-03 |
| `EvaluateMtsSignal` | 数据刷新后自动触发 | 显示完整 MTS 卡或 data_insufficient | BUC-04 |
| `CreateAlertRule` | 提醒表单提交 | 新规则进入列表并显示 taxonomy | BUC-05 |
| `UpdateAlertRuleState` | 启用 / 停用 / 确认 | 规则状态与历史同步 | BUC-05 |
| `RestoreLocalWorkspace` | 重新打开应用 | 恢复 banner 与最近上下文 | BUC-07 |
| `SwitchWorkspaceLayout` | 点击 dense / focus / mobile_tab | 列宽 / tab / 单列切换 | BUC-08 |

## Forbidden UI semantics

- 不出现“保证收益”“胜率”“自动下单”“买入执行”“卖出执行”。
- 不把 MTS 分数解释为收益概率。
- 不把 demo_fallback 当作正式行情。
- 不把归档等同于不可恢复删除。
