# Surface Registry

| Surface ID | 名称 | Entry | Carried BUCs | Primary BO | Locator Root |
|---|---|---|---|---|---|
| SURF-WATCHLIST | 自选工作台 | 应用首屏左侧 / 移动端顶部 | BUC-01, BUC-06, BUC-07 | WatchSymbol, Market, MarketDataSource | `watchlist-shell` |
| SURF-DETAIL | 标的看盘详情 | 选中 active 标的后 | BUC-02, BUC-03, BUC-04, BUC-07 | PriceBar, IndicatorSet, MtsSignal, ChartLayout | `symbol-detail-shell` |
| SURF-ALERTS | 提醒管理面板 | 详情页右侧 / 移动端提醒页签 | BUC-05, BUC-06 | AlertRule, MtsSignal, WatchSymbol | `alerts-shell` |
| SURF-SOURCE | 来源状态条 | 全局顶部 + 详情局部说明 | BUC-07 | MarketDataSource, PriceBar | `source-status-banner` |

## Navigation

- 桌面：三栏密度工作台，左侧自选，中间图表详情，右侧信号与提醒。
- 移动：顶部来源状态，分段切换“自选 / 看盘 / 提醒”，保持同一信息架构。
- 主入口只展示产品界面，不嵌入评审说明或合同说明。
