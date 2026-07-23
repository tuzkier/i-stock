# 业务用例与验收场景

**mission-id:** `20260522-stock-watch-system`  
**stage:** `PRD / Product Definition`  
**artifact:** `business-use-cases.md`  
**status:** `rewritten-for-open-source-reference`

## 输入与取舍

本文件基于以下输入重写：

- `harness-runtime/harness/missions/20260522-stock-watch-system/mission-contract.md`
- `harness-runtime/harness/stages/20260522-stock-watch-system/discovery-brief.md`
- `harness-runtime/harness/stages/20260522-stock-watch-system/product/business-objects.md`
- `harness-runtime/harness/stages/20260522-stock-watch-system/product/scope-strategy.md`
- `docs/open-source-ui-reference.md`
- `project-context.md`

本次重写的核心变化：PRD 不再只描述“自选 + K 线 + 信号 + 简单提醒”，而是定义一个本地看盘工作台（workbench）。用户可观察的闭环必须覆盖自选列表状态、行情来源健康、默认三栏工作台、指标切换、MTS 解释卡、提醒 taxonomy、本地触发历史、布局模式和浏览器重开恢复。

## BUC 粒度规则

- 一个 BUC 对应用户可独立触发或清晰感知的业务闭环，不拆成单个按钮动作。
- P0/P1、高风险、多状态、异常恢复、原型驱动路径展开 Detail；简单切换保留在 Index 或并入主路径。
- BUC 的验收标准必须能由页面状态、持久化状态、冻结样本或截图证明。
- 不把账号、云同步、自动交易、外部推送、完整基本面、组合管理或完整回测写成当前 BUC。

## BUC Index

| BUC-ID | 名称 | Actor | Goal | Trigger | Related BO | 关键状态变化 | Priority | Detail Level | Prototype Required | Traces To |
|---|---|---|---|---|---|---|---|---|---|---|
| BUC-01 | 管理多市场自选与歧义预览 | 个人投资者 | 把四市场标的纳入本地工作台，并在写入前看见市场与归一结果 | 用户输入、添加、归档或恢复标的 | BO-001, BO-002, BO-006 | WatchSymbol `active/archived`；AlertRule `suspended_by_archive` | P0 | detail | yes | AC-01, AC-05, SD-02, SD-03 |
| BUC-02 | 打开默认看盘工作台 | 个人投资者、技术分析用户 | 进入标的后直接获得自选、图表、MTS、提醒、来源状态的一屏工作台 | 用户选择 active 标的 | BO-001, BO-003, BO-004, BO-005, BO-007, BO-008 | ChartLayout `dense/default`；PriceSeries `ready/stale/unavailable` | P0 | detail | yes | AC-02, SD-04, SD-05 |
| BUC-03 | 切换副图指标并读取 OHLC | 技术分析用户 | 在不离开主图上下文的情况下切换 MACD/RSI/KDJ/ATR，并能读取 OHLC/指标读数 | 用户切换副图或查看 tooltip/读数 | BO-003, BO-004, BO-008 | IndicatorSet `default/customized`；`ready/partial/unavailable` | P1 | detail | yes | AC-02, SD-05 |
| BUC-04 | 解读 MTS 多周期趋势信号 | 研究驱动用户 | 用趋势状态、分数带、信号类型、提醒等级、原因和失效条件理解技术提醒 | 数据刷新完成或用户打开标的 | BO-003, BO-004, BO-005, BO-007 | MtsSignal `data_insufficient/interpretable`；`watch/confirm/strong_signal/risk` | P0 | detail | yes | AC-03, AC-04, SD-06 |
| BUC-05 | 管理本地提醒规则与触发历史 | 研究驱动用户、本地使用者 | 创建、启停、触发、确认价格型/变化型/技术指标型/MTS型/定时提醒，并保留原因 | 用户创建规则或系统刷新后命中条件 | BO-001, BO-003, BO-004, BO-005, BO-006 | AlertRule `enabled/disabled/suspended_by_archive` + `idle/triggered/acknowledged` | P0 | detail | yes | AC-04, AC-05, SD-07, SD-08 |
| BUC-06 | 查看来源健康并处理降级 | 所有看盘用户 | 识别 formal/demo_fallback/stale/unavailable，知道上次刷新、降级原因和重试状态 | 来源刷新成功、失败、过期或用户重试 | BO-003, BO-005, BO-006, BO-007 | MarketDataSource `formal/demo_fallback/stale/unavailable`；retry 状态变化 | P0 | detail | yes | AC-02, AC-03, AC-04, SD-09 |
| BUC-07 | 重开浏览器恢复本地工作台 | 本地使用者 | 无账号恢复自选、提醒状态、触发历史和基础布局偏好 | 用户在同一浏览器重新打开应用 | BO-001, BO-006, BO-008 | ChartLayout `restored`；AlertRule 恢复启停/确认状态 | P0 | detail | yes | AC-05, SD-10, SD-11 |
| BUC-08 | 切换工作台布局模式 | 高频扫描用户、移动端用户 | 在 dense/focus/mobile_tab 间切换，按设备获得可读工作台 | 用户切换布局或进入移动端 | BO-008 | ChartLayout `dense/focus/mobile_tab` | P1 | detail | yes | AC-02, AC-05, SD-11 |
| BUC-09 | 使用冻结样本验收关键路径 | 验证者、产品维护者 | 用四市场样本、歧义输入、来源降级、恢复样本证明 PRD 行为 | 验证阶段执行验收 | BO-001~BO-008 | 不改变业务状态；提供验收证据 | P0 | map_only | no | AC-01~AC-05, SD-12 |

## BUC Detail

### BUC-01 管理多市场自选与歧义预览

**业务目标**  
用户能把港股、A 股、美股、韩股标的放入同一本地自选工作台，并在写入前知道系统如何理解市场与代码。

**主成功场景**

1. 用户选择或输入市场与股票代码。
2. 系统展示“市场 + 原始代码 + 归一代码”的预览。
3. 用户确认添加后，系统创建或恢复对应 WatchSymbol 为 `active`。
4. 自选列表行显示名称、市场、归一代码、来源状态摘要、最近价和涨跌摘要。
5. 用户归档标的后，标的退出 active 列表；绑定提醒进入 `suspended_by_archive`。
6. 用户恢复标的后，标的重新 active，提醒按归档前用户意图恢复。

**异常与边界**

- 数字代码存在多市场歧义时，系统不得静默写入 active。
- 归一失败时，系统应停在可理解错误态，不创建 WatchSymbol。
- 重复添加同一市场同一归一代码时，应恢复或聚合既有对象，不制造重复标的。

**GWT**

**Scenario BUC-01-S01 新增标的前显示归一预览**

- **GIVEN** 用户正在添加一个来自支持市场的股票代码
- **WHEN** 用户输入代码并选择市场
- **THEN** 页面显示市场、原始代码和归一代码预览
- **AND** 用户确认后，标的进入对应市场分组的 active 自选列表

**Scenario BUC-01-S02 歧义代码不得静默写入**

- **GIVEN** 用户输入一个可能同时属于多个市场的数字代码
- **WHEN** 用户尚未确认市场或归一结果
- **THEN** 系统不得把该代码写入 active 自选
- **AND** 页面展示需要用户确认市场的状态

**Scenario BUC-01-S03 归档暂停提醒并可恢复**

- **GIVEN** 一个 active 标的已绑定 enabled 提醒
- **WHEN** 用户归档该标的
- **THEN** 标的状态变为 archived
- **AND** 绑定提醒进入 `suspended_by_archive` 且不再触发
- **WHEN** 用户恢复该标的
- **THEN** 标的回到 active，提醒按归档前启停意图恢复

**AC**

- AC-BUC-01-01：添加前必须可见市场、原始代码、归一代码。
- AC-BUC-01-02：歧义或不可识别输入不得进入 active 自选。
- AC-BUC-01-03：自选列表行必须展示市场、归一代码、来源状态和最近价/涨跌摘要。
- AC-BUC-01-04：归档标的暂停绑定提醒；恢复标的后提醒状态可恢复。

**验证证据类型**：页面状态、持久化状态、冻结输入样本、截图。

### BUC-02 打开默认看盘工作台

**业务目标**  
用户选中标的后不需要先配置布局，即可看到可扫描的本地看盘工作台。

**主成功场景**

1. 用户点击一个 active WatchSymbol。
2. 工作台进入 `dense/default` 桌面布局：左侧自选，中间主图/成交量/副图，右侧 MTS/提醒/来源摘要。
3. 主图展示 PriceSeries；成交量 pane 常驻；副图 pane 显示默认指标。
4. 来源健康状态以一级 UI 元素存在，不只是一句偶发 notice。

**异常与边界**

- 数据 stale 或 demo_fallback 时，图表仍可展示，但 MTS/提醒区必须同步表达可信度下降。
- 没有足够 PriceSeries 时，页面应显示不可解释状态，而不是空白或伪信号。

**GWT**

**Scenario BUC-02-S01 选中标的后进入默认三栏工作台**

- **GIVEN** 用户已有 active 自选标的
- **WHEN** 用户选中该标的
- **THEN** 页面展示自选区、图表区、信号与提醒区
- **AND** 图表区包含主图、成交量 pane 和一个副图 pane

**Scenario BUC-02-S02 来源降级时工作台不伪装正式行情**

- **GIVEN** 当前标的的行情来源为 `demo_fallback` 或 `stale`
- **WHEN** 用户打开工作台
- **THEN** 图表区显示来源状态
- **AND** MTS 与提醒区标明当前结论的可信度或可解释性限制

**AC**

- AC-BUC-02-01：首开 active 标的必须出现三栏工作台或移动端等价 tab。
- AC-BUC-02-02：图表区必须包含主图、成交量和副图。
- AC-BUC-02-03：来源状态必须在工作台内作为一级状态可见。

**验证证据类型**：页面截图、组件状态、来源降级样本。

### BUC-03 切换副图指标并读取 OHLC

**业务目标**  
用户能在同一标的上下文中切换分析维度，并读取 OHLC 与关键指标读数，不只依赖颜色和曲线。

**GWT**

**Scenario BUC-03-S01 切换副图不丢主图上下文**

- **GIVEN** 用户正在查看某 active 标的的默认看盘布局
- **WHEN** 用户从 MACD 切换到 RSI、KDJ 或 ATR/波动
- **THEN** 主图和成交量 pane 保持同一标的上下文
- **AND** 副图 pane 更新为所选指标

**Scenario BUC-03-S02 OHLC 与指标读数可读**

- **GIVEN** 图表有可用 PriceSeries
- **WHEN** 用户查看某个时间点或当前读数区域
- **THEN** 页面能展示 open、high、low、close、volume 和当前副图指标读数

**Scenario BUC-03-S03 数据不足时副图局部降级**

- **GIVEN** 当前 PriceSeries 不足以计算某个副图指标
- **WHEN** 用户选择该指标
- **THEN** 页面显示 `partial` 或 `unavailable` 状态
- **AND** 不展示伪造读数

**AC**

- AC-BUC-03-01：副图切换不应改变当前标的和主图上下文。
- AC-BUC-03-02：OHLC 与关键指标读数必须通过 tooltip、读数表或等价 UI 可见。
- AC-BUC-03-03：指标不可计算时必须可见地降级。

**验证证据类型**：页面状态、截图、冻结 PriceSeries 样本。

### BUC-04 解读 MTS 多周期趋势信号

**业务目标**  
MTS 将研究设计转成解释性信号卡，帮助用户区分观察、确认、强信号和风控，而不是给出交易指令。

**GWT**

**Scenario BUC-04-S01 数据充分时输出完整 MTS 卡**

- **GIVEN** PriceSeries 与 IndicatorSet 足够解释
- **WHEN** 系统完成 MTS 评估
- **THEN** 页面展示趋势状态、MTS 分数、分数带、信号类型、提醒等级、原因和 invalidators

**Scenario BUC-04-S02 MTS 不使用投资建议主语义**

- **GIVEN** MTS 进入高强度正向或风险状态
- **WHEN** 页面展示信号
- **THEN** 文案使用“强信号”“强风险”“技术提醒”等口径
- **AND** 不以“强买”“强卖”“保证收益”“胜率”作为产品主语义

**Scenario BUC-04-S03 风控优先于观察提醒**

- **GIVEN** 同一标的同时满足观察类条件和风控条件
- **WHEN** 系统展示 MTS 与提醒摘要
- **THEN** 风控级别优先呈现
- **AND** 页面显示触发风控的 reason_codes 或 invalidators

**Scenario BUC-04-S04 数据不足时不输出伪 MTS**

- **GIVEN** 当前来源为 unavailable 或 PriceSeries 不足
- **WHEN** 系统尝试评估 MTS
- **THEN** 页面显示 `data_insufficient` 或等价不可解释状态
- **AND** 不展示有效提醒等级

**AC**

- AC-BUC-04-01：MTS 卡必须包含 trend_state、score_band、signal_type、alert_level、reason_codes、invalidators。
- AC-BUC-04-02：MTS 不得输出收益承诺、胜率或确定性买卖建议。
- AC-BUC-04-03：风控状态视觉和信息优先级高于观察类状态。

**验证证据类型**：冻结 MTS 样本、文案审查、页面截图。

### BUC-05 管理本地提醒规则与触发历史

**业务目标**  
提醒从“价格到达时提示”扩展为本地规则系统：分类、启停、触发、确认、历史和归档联动都可解释。

**主成功场景**

1. 用户在 active 标的上创建提醒。
2. 用户选择提醒类型：价格型、变化型、技术指标型、MTS 型或定时提醒。
3. 系统保存规则、启停状态、条件和本地触发历史。
4. 条件命中时，规则进入 `triggered`，展示触发时间和触发理由。
5. 用户确认后，规则进入 `acknowledged`，并可回到等待下一次触发。

**GWT**

**Scenario BUC-05-S01 创建不同类型本地提醒**

- **GIVEN** 用户正在查看 active 标的
- **WHEN** 用户创建价格型、变化型、技术指标型、MTS 型或定时提醒
- **THEN** 系统保存提醒 taxonomy、条件、启停状态和目标标的

**Scenario BUC-05-S02 命中提醒后展示历史与确认状态**

- **GIVEN** 某 enabled 提醒条件命中
- **WHEN** 系统更新提醒状态
- **THEN** 该规则进入 `triggered`
- **AND** 页面展示触发时间、触发理由和确认动作
- **WHEN** 用户确认该提醒
- **THEN** 规则进入 `acknowledged`

**Scenario BUC-05-S03 归档标的暂停提醒**

- **GIVEN** 一个标的已归档
- **WHEN** 系统刷新提醒规则
- **THEN** 绑定该标的的规则保持 `suspended_by_archive`
- **AND** 规则不触发新的本地提醒

**AC**

- AC-BUC-05-01：提醒创建 UI 必须体现 taxonomy，而不是只有价格上穿/下破。
- AC-BUC-05-02：提醒列表必须区分启停状态和触发状态。
- AC-BUC-05-03：触发历史至少包含触发时间、触发理由、确认状态。
- AC-BUC-05-04：归档标的的提醒不得触发，恢复后按原意图恢复。

**验证证据类型**：本地状态、页面状态、冻结触发样本、浏览器重开恢复。

### BUC-06 查看来源健康并处理降级

**业务目标**  
用户在继续看盘的同时能理解数据来源可信度，避免把 demo、stale 或 unavailable 当成正式行情。

**GWT**

**Scenario BUC-06-S01 来源健康面板展示正式状态**

- **GIVEN** 当前来源可用且数据新鲜
- **WHEN** 用户查看工作台
- **THEN** 来源健康面板显示 `formal`、上次刷新时间和覆盖状态

**Scenario BUC-06-S02 demo fallback 穿透到图表、MTS 和提醒**

- **GIVEN** 正式来源不可用，系统使用 demo fallback
- **WHEN** 工作台刷新完成
- **THEN** 来源健康显示 `demo_fallback` 和降级原因
- **AND** PriceSeries、MTS、提醒区域同步显示降级语义

**Scenario BUC-06-S03 stale 状态不伪装实时成功**

- **GIVEN** 当前数据已经过期但仍可展示旧数据
- **WHEN** 用户查看工作台
- **THEN** 来源健康显示 `stale`
- **AND** 页面显示上次刷新时间或等价旧数据说明

**Scenario BUC-06-S04 重试失败不导致页面不可用**

- **GIVEN** 用户点击重试来源
- **WHEN** 重试失败
- **THEN** 页面保留上一次可解释状态
- **AND** 显示新的失败原因或仍处于降级状态

**AC**

- AC-BUC-06-01：来源健康必须区分 formal、demo_fallback、stale、unavailable。
- AC-BUC-06-02：来源降级必须同步影响图表、MTS、提醒解释。
- AC-BUC-06-03：重试失败不得导致页面 crash 或伪装刷新成功。

**验证证据类型**：来源降级 fixture、页面截图、状态断言。

### BUC-07 重开浏览器恢复本地工作台

**业务目标**  
用户不需要账号也能继续使用已配置的本地工作台。

**GWT**

**Scenario BUC-07-S01 恢复自选、提醒和布局**

- **GIVEN** 用户已有 active/archived 自选、提醒规则、触发历史和布局偏好
- **WHEN** 用户关闭并重新打开浏览器
- **THEN** 系统恢复自选状态、提醒启停/确认状态和基础 ChartLayout

**Scenario BUC-07-S02 恢复失败时回到默认布局**

- **GIVEN** 本地保存的布局状态部分损坏或版本不兼容
- **WHEN** 系统恢复工作台
- **THEN** 系统回到默认 dense 布局或等价可用布局
- **AND** 自选和提醒仍尽可能恢复

**AC**

- AC-BUC-07-01：同一浏览器配置下重开后，自选和提醒不丢失。
- AC-BUC-07-02：ChartLayout 应恢复上次模式；无法恢复时回到默认可用布局。
- AC-BUC-07-03：恢复过程不要求账号、云同步或服务端数据库。

**验证证据类型**：浏览器重开验证、本地存储状态、截图。

### BUC-08 切换工作台布局模式

**业务目标**  
不同设备和使用节奏下，用户能在信息密度和专注看图之间切换。

**GWT**

**Scenario BUC-08-S01 桌面 dense 与 focus 切换**

- **GIVEN** 用户在桌面端查看工作台
- **WHEN** 用户切换到 focus 模式
- **THEN** 页面隐藏或收起非关键侧栏
- **AND** 保留图表、副图切换、来源健康的可见或可访问入口
- **WHEN** 用户切回 dense 模式
- **THEN** 页面恢复自选、图表、信号/提醒的三栏结构

**Scenario BUC-08-S02 移动端使用 tab 工作台**

- **GIVEN** 用户在移动端宽度打开系统
- **WHEN** 页面进入 mobile_tab 模式
- **THEN** 自选、图表、提醒、来源以 tab 或等价导航组织
- **AND** 文本和控件不互相遮挡

**AC**

- AC-BUC-08-01：桌面端至少支持 dense 与 focus。
- AC-BUC-08-02：移动端必须提供 tab 化或等价单列导航，不强行压缩桌面三栏。
- AC-BUC-08-03：布局切换后仍能访问来源健康和提醒状态。

**验证证据类型**：桌面/移动截图、布局状态、恢复状态。

## 验证输入矩阵

| 验证输入 | 覆盖 BUC | 必须证明 |
|---|---|---|
| 四市场标的样本 | BUC-01, BUC-02 | 市场分组、归一代码、列表摘要、默认工作台 |
| 数字代码歧义样本 | BUC-01 | 添加前预览或阻断，不静默写入 |
| 指标充足与不足样本 | BUC-03, BUC-04 | 指标 ready/partial/unavailable，MTS 不伪信号 |
| MTS strong_signal/risk 样本 | BUC-04, BUC-05 | 解释卡完整，风控优先，不使用投资建议语义 |
| 提醒触发样本 | BUC-05 | taxonomy、triggered、acknowledged、trigger_reason |
| 来源 demo_fallback/stale/unavailable 样本 | BUC-02, BUC-06 | 来源健康穿透图表、MTS、提醒 |
| 浏览器重开样本 | BUC-01, BUC-05, BUC-07, BUC-08 | 自选、提醒、触发历史、布局恢复 |

## 下游提示

- interaction 必须覆盖 BUC-01 到 BUC-08 的用户可见路径，尤其是来源健康、MTS 解释卡和提醒 taxonomy。
- solution 必须重对齐：旧 solution 中“价格型/信号型提醒”不足以覆盖当前 taxonomy；旧 `PriceBar` 口径也需调整为 `PriceSeries`。
- technical_analysis 必须围绕 `PriceSeries`、`MarketDataSource`、`AlertRule` 双状态机和 `ChartLayout` 模式设计数据/状态流。
