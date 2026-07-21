# Surface Registry

| Surface ID | Surface refs | Operation type | Baseline ref | Carried BUCs | Navigation / Entry | Primary responsibilities | Locator root |
|---|---|---|---|---|---|---|---|
| SURF-WATCHLIST | `WatchlistPanel`, `NormalizationPreview`, `WatchlistRow` | `modify_surface` | `visual-interaction/prototype/index.html` | BUC-01, BUC-07 | App 首屏左侧 / mobile `watchlist` tab | 多市场自选、归一预览、归档 / 恢复、列表摘要 | `watchlist-panel` |
| SURF-WORKBENCH | `WorkbenchShell`, `ChartSurface`, `IndicatorPanel` | `modify_surface` | `visual-interaction/prototype/index.html` | BUC-02, BUC-03, BUC-04, BUC-08 | 选中 active 标的后进入 / mobile `chart` tab | 三栏工作台、主图、成交量、副图、OHLC | `workbench-shell` |
| SURF-MTS | `MtsSignalCard` | `extend_surface` | `visual-interaction/prototype/index.html` | BUC-04, BUC-06 | workbench 中央 / source 降级同步 | 趋势状态、分数带、信号类型、提醒等级、原因、失效条件 | `mts-signal-card` |
| SURF-ALERTS | `AlertRulePanel` | `extend_surface` | `visual-interaction/prototype/index.html` | BUC-05, BUC-06, BUC-07 | 右侧 / mobile `alerts` tab | taxonomy、启停、触发历史、确认动作、归档暂停 | `alerts-panel` |
| SURF-SOURCE | `SourceHealthPanel` | `extend_surface` | `visual-interaction/prototype/index.html` | BUC-06 | 顶部全局状态条 + 右侧来源卡 / mobile `source` tab | formal / demo_fallback / stale / unavailable、降级原因、重试 | `source-status-banner` |
| SURF-LAYOUT | `LayoutController` | `create_surface` | `visual-interaction/prototype/index.html` | BUC-08 | 顶栏布局开关 | dense / focus / mobile_tab 切换与回退 | `layout-controller` |
| SURF-RESTORE | `RestoreStatus` | `extend_surface` | `visual-interaction/prototype/index.html` | BUC-01, BUC-07 | 首屏横幅 / watchlist 顶部 | 本地恢复结果、最近标的、继续看盘入口 | `restore-banner` |

## Navigation

- 桌面：左侧 Watchlist，中间 Workbench，右侧 Alerts / Source / Restore。
- 移动：`mobile_tab` 下按 `watchlist / chart / alerts / source` 访问同一信息架构。
- 所有 surface 的定位器必须稳定，且尽量使用 `data-testid` + 可访问名称双保险。

## State / Permission Notes

- Watchlist 允许新增、归档、恢复；归档会暂停绑定提醒。
- Workbench 允许切换副图和查看 OHLC，但不允许把信号变成交易动作。
- Source 的降级状态必须影响 MTS / 提醒解释，而不是只在顶部提示。
- Layout 切换不改变业务对象，只改变呈现方式。
