# BUC Index

| BUC | 名称 | Priority | Prototype | Surface | HTML Deep Link |
|---|---|---:|---|---|---|
| BUC-01 | 管理多市场自选与归一预览 | P0 | yes | `WatchlistPanel`, `NormalizationPreview`, `WatchlistRow`, `RestoreStatus` | `visual-interaction/prototype/index.html#buc-001` |
| BUC-02 | 打开默认三栏工作台 | P0 | yes | `WorkbenchShell`, `ChartSurface`, `SourceHealthPanel` | `visual-interaction/prototype/index.html#buc-002` |
| BUC-03 | 切换主/副图指标并读取 OHLC | P1 | yes | `IndicatorPanel`, `ChartSurface` | `visual-interaction/prototype/index.html#buc-003` |
| BUC-04 | 解读 MTS 多周期趋势信号 | P0 | yes | `MtsSignalCard` | `visual-interaction/prototype/index.html#buc-004` |
| BUC-05 | 管理本地提醒 taxonomy 与触发历史 | P0 | yes | `AlertRulePanel` | `visual-interaction/prototype/index.html#buc-005` |
| BUC-06 | 查看来源健康并处理降级 | P0 | yes | `SourceHealthPanel`, `ChartSurface`, `MtsSignalCard`, `AlertRulePanel` | `visual-interaction/prototype/index.html#buc-006` |
| BUC-07 | 重开浏览器恢复本地工作台 | P0 | yes | `RestoreStatus`, `WatchlistPanel`, `AlertRulePanel` | `visual-interaction/prototype/index.html#buc-007` |
| BUC-08 | 切换布局模式 | P1 | yes | `LayoutController`, `WorkbenchShell`, `mobile_tab` 导航 | `visual-interaction/prototype/index.html#buc-008` |

## 读法

- BUC-01 先定义写入前的归一预览与归档语义。
- BUC-02 ~ BUC-04 定义看盘主路径。
- BUC-05 ~ BUC-07 定义信号、提醒、来源和恢复的连续性。
- BUC-08 定义桌面 dense / focus 与移动 `mobile_tab` 的布局切换。

## 边界说明

- BUC-09（冻结样本验收）是验证映射，不属于 prototype required 合同，因此不进入本目录的主交互合同。
