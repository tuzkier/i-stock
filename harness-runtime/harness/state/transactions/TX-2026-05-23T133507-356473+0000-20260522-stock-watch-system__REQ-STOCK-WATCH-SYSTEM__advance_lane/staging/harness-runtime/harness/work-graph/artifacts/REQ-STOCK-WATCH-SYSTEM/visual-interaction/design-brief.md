# Visual Interaction Design Brief

## 目标

用一个可操作的静态原型，验证本地多市场看盘工作台的信息架构：默认首屏服务日常看盘，只保留自选、核心图表、MTS 摘要和简短状态入口；提醒 taxonomy、来源健康、本地恢复和布局验收信息进入诊断 / 验收模式。

## 布局策略

- **桌面 focus（日常看盘）**：默认模式，只显示左侧自选与中间工作台；图表下方给出提醒、来源、验收的三项摘要入口，避免把所有诊断信息常驻摊开。
- **桌面 dense（诊断 / 验收）**：展开提醒、来源、恢复和布局细节，用于验证 BUC-05 到 BUC-08 以及状态穿透。
- **移动 mobile_tab**：切换为单列分栏访问，四个 tab 分别访问自选、图表、提醒和来源。

## 关键状态

- 自选：`active / archived`，写入前必须看到归一预览。
- 图表：主图、成交量、副图、OHLC、`ready / partial / unavailable`。
- MTS：`interpretable / data_insufficient`，以及 `watch / confirm / strong_signal / risk`。
- 提醒：`enabled / disabled / suspended_by_archive`，以及 `idle / triggered / acknowledged`。
- 来源：`formal / demo_fallback / stale / unavailable`，并穿透到图表、MTS、提醒。
- 布局：`dense / focus / mobile_tab`。
- 恢复：`restored / partial restore / default fallback`。

## 中文文案策略

- 默认中文；仅保留股票代码、市场代码、指标名与行业缩写等必要英文。
- 允许保留的例外：`AAPL`、`0700.HK`、`600519.SS`、`005930.KS`、`MACD`、`RSI`、`KDJ`、`ATR`、`MTS`、`OHLC`、`EMA`、`BOLL`、`Yahoo Finance`；布局状态以“中文（English）”呈现。
- 不出现收益承诺、胜率、自动交易、买入执行、卖出执行等措辞。

## Deep Links

- `#buc-001` 自选与归一预览
- `#buc-002` 日常看盘工作台
- `#buc-003` 主 / 副图指标切换
- `#buc-004` MTS 解释卡
- `#buc-005` 提醒 taxonomy 与触发历史
- `#buc-006` 来源健康与降级
- `#buc-007` 本地恢复状态
- `#buc-008` 布局切换
