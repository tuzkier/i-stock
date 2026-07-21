# 开源项目界面功能参考

**调研日期:** 2026-05-23  
**关联任务:** `20260522-stock-watch-system`  
**目的:** 为 MyInvestment 多市场股票看盘系统补充开源产品与图表库参考，重点提炼可借鉴的界面功能、交互状态和不应采用的方向。

## 当前结论

当前方案选择“本地 React SPA + `lightweight-charts` + 显式行情来源状态 + 本地持久化”仍然成立。开源参考主要补强三个方面：

1. 看盘工作台不应只是“K 线 + 右侧信号”，还需要清晰的自选列表状态、来源健康状态、提醒规则状态和恢复状态。
2. 图表层可以继续以 `lightweight-charts` 为主，但应保留 `KLineChart` 作为后续高级图表交互候选，尤其是内置指标、移动端手势、绘图工具和多 pane 能力。
3. 提醒功能不应只做“价格上穿 / 下破”，应采用可分类的提醒类型、触发理由、启停状态和来源可用性约束。

## 参考项目

| 项目 | 类型 | 许可证 / 活跃度 | 可借鉴点 | 不采用点 |
|---|---|---|---|---|
| [OpenStock](https://github.com/Open-Dev-Society/OpenStock) | 股票市场 Web App | AGPL-3.0；GitHub API 显示约 11.5k stars，2026-05 仍有提交 | 实时价格、个性化提醒、公司信息、市场新闻、TradingView widget、shadcn/ui + Tailwind 的现代金融界面组织 | 账号、MongoDB、Better Auth、云服务边界过重；AGPL 对复用代码有传染性，适合作为产品功能参考，不宜直接拷贝实现 |
| [Invester](https://github.com/onur-celik/invester) | 可定制投资仪表盘 | MIT；约 38 stars，最近提交较旧 | Widget 化工作台：Ticker、Mini Chart、Chart Box、可添加 / 移除模块；适合参考“自定义看盘屏” | 维护活跃度弱，TradingView iframe / widget 思路不适合本项目的确定性 fixture 验证 |
| [Ghostfolio](https://github.com/ghostfolio/ghostfolio) | 自托管财富管理 | AGPL-3.0；约 8.5k stars，2026-05 仍活跃 | 数据所有权、隐私、自托管、移动优先、Dark Mode、Zen Mode、组合绩效区间、风险静态分析、导入导出 | Angular/Nest/Postgres/Redis 架构过重；它是组合管理，不是实时看盘，不应引入账号/数据库边界 |
| [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) | 金融图表库 | Apache-2.0；约 15.9k stars，v5.2.0 于 2026-04-24 发布 | 高性能 Canvas、金融图表、插件示例、分析指标示例；与现有依赖一致 | 需要满足 TradingView attribution 要求；内置高级技术指标和绘图工具不如专业 K 线库完整 |
| [KLineChart](https://github.com/klinecharts/KLineChart) | K 线图表库 | Apache-2.0；约 3.8k stars，2026-05 仍活跃 | 零依赖、移动端支持、内置 MA/EMA/BOLL/VOL/MACD/KDJ/RSI 等指标、可自定义指标、绘图扩展 | 若现在迁移会扩大技术设计范围；应作为后续图表能力不足时的替换候选 |
| [StockAlert.pro Open Source](https://github.com/stockalert-pro) | 股票提醒 SDK / 集成 | SDK 和集成仓库，2026-03 仍有提交 | 提醒类型 taxonomy：价格、百分比变化、新高/新低、MA crossover、RSI、成交量、基本面、定时提醒；多渠道通知概念 | 依赖其云 API 与账号；本项目第一阶段只应借鉴提醒类型，不接入外部通知服务 |
| [stonks-cli](https://github.com/igoropaniuk/stonks-cli) | 终端投资组合看板 | MIT；约 49 stars，2026-04 仍有提交 | 自动刷新、PRE/AH/CLS 会话标签、watchlist 行弱化显示、doctor 健康检查、并排 portfolio、导入校验 | TUI 不是 Web UI；AI chat、组合持仓和交易导入不在当前范围 |

## 可落地的界面功能参考

### 1. 自选列表

从 OpenStock、Invester、stonks-cli 提炼：

- 自选列表行应展示：名称、归一代码、市场、来源状态、最近价、涨跌幅。
- 数字代码存在多市场歧义时，添加前显示“市场 + 归一结果预览”，而不是提交后才发现错误。
- watchlist 与持仓不同，本项目没有持仓概念；可参考 stonks-cli 的“弱化显示”做归档 / 暂停提醒状态，而不是删除即消失。

建议落地：

- `WatchSymbol` 增加 `status: active | archived` 或等价状态。
- 左侧列表增加来源 / 会话状态小标签，例如 `Yahoo`、`演示`、`不可用`。
- 输入框下方增加归一预览和歧义错误态。

### 2. 图表与指标区

从 Lightweight Charts 与 KLineChart 提炼：

- 本阶段继续用 `lightweight-charts`，保留主图、成交量、指标叠层。
- 副图指标需要显式 tab / segmented control，不应把所有指标只塞到下方 metric strip。
- KLineChart 的内置指标列表证明用户会自然期待 MA、EMA、BOLL、VOL、MACD、KDJ、RSI 这类常用切换能力；MTS 应作为解释层叠加，而不是替代传统指标。

建议落地：

- `SURF-DETAIL` 明确拆成主图 pane、成交量 pane、副图 pane。
- 指标切换控件至少支持 `MACD`、`RSI`、`KDJ`、`ATR/波动` 的视图切换。
- 给 OHLC 与指标提供表格式或 tooltip 读数，避免只靠颜色和曲线。

### 3. MTS 信号卡

从 Ghostfolio 的风险分析、StockAlert 的提醒分类、当前研究设计提炼：

- MTS 不要只显示一个大分数；应展示趋势状态、分数带、提醒等级、触发理由、invalidators。
- “强买 / 强卖”这类词要谨慎，界面上建议改为“强信号 / 强风险”或“技术提醒”，保持非投资建议边界。
- 风控提醒需要视觉优先级高于观察类提醒。

建议落地：

- 将现有“四因子共振指标”文案替换为“MTS 多周期趋势评分”。
- MTS 卡片字段：`trend_state`、`score_band`、`signal_type`、`alert_level`、`reason_codes`、`invalidators`。
- 风险态使用明确的 banner / icon / reason，不只改变颜色。

### 4. 提醒规则

从 StockAlert.pro 提炼：

- 提醒类型应分组：价格型、变化型、技术指标型、MTS 型、定时提醒。
- 每条提醒应有 enabled / disabled / triggered / acknowledged 状态。
- 提醒触发需要显示触发理由和触发时间；不能只显示“几条已触发”。

建议落地：

- 当前 `AlertRule` 从 `direction + price + signal` 扩展为 `type + condition + threshold + status + lastTriggeredAt + reason`。
- 第一阶段不做外部通知渠道，但 UI 可以预留“本地提醒规则”与“触发历史”两个区域。
- 归档标的时自动暂停绑定提醒，恢复标的时按原意图恢复。

### 5. 行情来源与健康状态

从 OpenStock 的非券商 / 延迟数据说明、Ghostfolio 的数据所有权、stonks-cli 的 doctor 检查提炼：

- 来源状态应成为一级 UI 元素，不应只有一条黄色 notice。
- 需要区分 `formal`、`demo_fallback`、`unavailable`、`stale`。
- 数据健康检查可以独立成小面板：上次刷新、数据源、延迟 / fallback、可重试动作。

建议落地：

- `SURF-SOURCE` 固定为工作台顶部或右侧面板中的来源状态组件。
- live Yahoo 失败时显示“演示数据”标签，并在图表、MTS、提醒区域同步降级。
- 增加“重试来源”按钮，但不把重试失败当作页面 crash。

### 6. 工作台布局

从 Invester 的 widget 工作台和 Ghostfolio 的 Zen Mode 提炼：

- 本项目不需要复杂拖拽布局，但可以保留“密集看盘 / 专注看图”两种模式。
- 卡片不要过多嵌套；金融看盘界面应优先信息密度、扫描效率和状态一致性。

建议落地：

- 桌面端保持三栏：自选、图表、信号/提醒。
- 移动端改为底部或顶部 tab：自选、图表、提醒、来源。
- 增加“专注图表”模式：隐藏左侧和右侧，只保留图表、指标切换、来源状态。

## 对现有方案的建议修订

1. 在 `solution.md` 的 D-01 中补充开源参考依据：`lightweight-charts` 继续作为主路由，`KLineChart` 作为后续候选不是凭空假设，而是来自两者能力 / 许可 / 活跃度对比。
2. 在 D-05 中补充提醒 taxonomy 参考：价格、百分比变化、新高/新低、技术指标、MTS、定时提醒；本阶段只实现本地提醒，不做通知渠道。
3. 在 D-07 中补充来源健康与 fixture 验证：来源状态必须可截图、可断言，不能只靠接口返回字段。
4. 在下游 technical_analysis 输入中新增 UI 功能模块：`source-health-panel`、`indicator-switcher`、`alert-rule-taxonomy`、`focus-chart-mode`。

## 明确不采用

- 不采用 OpenStock / Ghostfolio 的账号体系、云同步、数据库和多用户权限模型。
- 不采用交易平台或算法交易系统中的下单、策略执行、broker 集成和自动交易 UI。
- 不直接复用 AGPL 项目的代码；只做功能与交互模式参考。
- 不用 TradingView iframe 替代本项目图表层，因为这会削弱 fixture-first E2E、MTS 叠加和来源降级可控性。

## 来源

- [OpenStock GitHub](https://github.com/Open-Dev-Society/OpenStock)
- [Invester GitHub](https://github.com/onur-celik/invester)
- [Ghostfolio GitHub](https://github.com/ghostfolio/ghostfolio)
- [TradingView Lightweight Charts GitHub](https://github.com/tradingview/lightweight-charts)
- [Lightweight Charts indicator examples](https://tradingview.github.io/lightweight-charts/indicator-examples/)
- [KLineChart GitHub](https://github.com/klinecharts/KLineChart)
- [KLineChart technical indicator documentation](https://klinecharts.com/en-US/guide/indicator)
- [StockAlert.pro GitHub organization](https://github.com/stockalert-pro)
- [stonks-cli GitHub](https://github.com/igoropaniuk/stonks-cli)

## 降级记录

- `gitnexus_unavailable`: 当前会话没有可用的 GitNexus MCP 查询工具，无法读取 `gitnexus://repo/{name}/context` 或执行 `gitnexus_query`。
- `compensating_action`: 本轮用 `README.md`、`project-context.md`、`package.json`、`src/App.tsx`、`src/types.ts`、`server/index.js` 和当前 `solution.md` 做临时代码证据；后续如需正式进入 discovery / solution reviewer，可运行 `npx gitnexus analyze` 后补齐 GitNexus evidence。
