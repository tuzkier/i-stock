# Domain UI Mapping

| Domain Element | UI Placement | User-Visible Rule | Trace |
|---|---|---|---|
| BO-001 WatchSymbol | 自选列表、详情标题、提醒绑定行 | 同时显示市场、原始代码、归一代码；archived 可恢复 | BUC-01 |
| BO-002 Market | 自选分组、代码输入辅助 | US/HK/CN/KR 分组清晰；不可识别不得 active | BUC-01 |
| BO-003 PriceBar | 主图、成交量、来源影响提示 | 可展示价格，但数据不足时不得驱动伪信号 | BUC-02, BUC-07 |
| BO-004 IndicatorSet | 主图指标标签、副图面板、指标切换 | ready/partial/unavailable 必须可见 | BUC-02, BUC-03 |
| BO-005 MtsSignal | MTS 信号卡、提醒候选条件 | 必须包含趋势状态、分数带、信号类型、等级、理由、失效条件 | BUC-04 |
| BO-006 AlertRule | 提醒创建表单、规则列表、触发历史 | 四级语义；风控优先；归档暂停不触发 | BUC-05, BUC-06 |
| BO-007 MarketDataSource | 顶部来源条、图表局部降级说明 | formal/demo_fallback/unavailable 持续可见 | BUC-07 |
| BO-008 ChartLayout | 图表三层布局、副图切换、恢复提示 | 默认布局始终可用；恢复粒度待后续定稿 | BUC-02, BUC-06 |

## Forbidden UI Semantics

- 不出现“保证收益”“胜率”“自动下单”“买入执行”“卖出执行”。
- 不把 MTS 分数解释为收益概率。
- 不把 demo_fallback 当作正式行情。
- 不把归档等同于不可恢复删除。

## Alignment Evidence

| Evidence Type | Covered Refs |
|---|---|
| Entity | BO-001, BO-002, BO-003, BO-004, BO-005, BO-006, BO-007, BO-008 |
| Command | CMD-01, CMD-02, CMD-03, CMD-04, CMD-05, CMD-08, CMD-11 |
| State | STM-01, STM-02, STM-03, STM-05, STM-06, STM-07, STM-10, STM-11 |
| Permission | ACT-01 / ACT-02 / ACT-03 可新增、归档、恢复自选，创建、启停、确认提醒；ACT-04 可刷新观察上下文、评估 MTS、解析提醒；自动交易动作禁止 |
| Invariant | INV-01, INV-04, INV-05, INV-06, INV-07, INV-08, INV-09, INV-10 |
