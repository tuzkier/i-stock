# 技术设计：20260522-stock-watch-system

**mission-id:** `20260522-stock-watch-system`  
**stage:** `technical_analysis`  
**status:** `draft-for-breakdown`

## 控制契约

- Contract: `contracts/tech-design.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件只提供可执行的工程设计说明。

## 1. Overview

本次技术设计的目标，是把已确认的产品语义与 solution 决策落成可拆分、可验证、可回滚的工程合同，而不是继续抽象讨论“怎么做得更像一个看盘产品”。当前阶段必须承接的核心约束是：

1. 本地网页入口不变，React/Vite/Express 仍是运行栈边界（`ARCH-001`、`solution D-01`）。
2. 多市场代码归一必须显式预览，歧义输入不得静默写入 active 自选（`FR-01`、`solution D-02`）。
3. 行情源、短 TTL cache 与降级必须可见，`demo_fallback` 不能伪装为正式行情（`FR-06`、`solution D-03`）。
4. 指标、MTS 与提醒必须通过纯领域层与策略编排输出解释性结果，不能由 UI 临时拼装（`FR-03`~`FR-05`、`solution D-04/D-05`）。
5. 本地恢复必须以版本化 workspace snapshot 承载，并具备迁移与回退（`FR-07`、`solution D-06`）。
6. 验证必须以 fixture-first 和稳定 locator 为门禁，live Yahoo 只能做 smoke，不得作为唯一门禁（`FR-09`、`solution D-07`）。

### 工程必须承接的业务/交互义务

- `AC-01`：四市场自选、代码归一、恢复后不丢 identity。
- `AC-02`：个股默认工作台、主图/成交量/副图、来源健康可见。
- `AC-03`：MTS 多周期趋势信号要有趋势状态、分数带、信号类型、提醒等级、原因与失效条件。
- `AC-04`：提醒要区分观察、确认、强信号、风控，并保留触发理由。
- `AC-05`：重开浏览器能恢复自选、提醒、触发历史和基础布局。

### 本阶段的设计边界

- 允许重构现有单体 `src/App.tsx`，但不扩大到账号、云同步、自动交易、外部推送或数据库。
- 允许新增纯前端领域模块、测试目录、fixture 目录和本地状态迁移器。
- 不允许把 `Yahoo` 的字段、授权、限流策略直接写进领域模型。
- 不允许把旧四因子信号的名称继续对外冒充正式 `MTS`。

---

## 2. 模块划分

> 说明：每个模块都给出职责、禁止职责、涉及路径与 `traces_to`。模块边界以 solution 决策与 FR/AC 为准，便于后续 `breakdown` 切任务。

| MOD | 模块 | 职责 | 禁止职责 | 涉及路径 | traces_to |
|---|---|---|---|---|---|
| MOD-01 | `market-normalization` | 统一处理 raw symbol / market 候选、归一预览、歧义阻断、重复添加幂等；输出可确认的 symbol identity。 | 不直接写入持久化、不发起行情请求、不计算指标。 | `src/data/markets.ts`、`src/features/watchlist/NormalizationPreview.tsx`、`src/domain/market-normalization.ts`（新） | `solution D-02`、`FR-01`、`FR-02`、`AC-01`、`BUC-01`、`BO-001`、`BO-002`、`RULE-01`、`RULE-02` |
| MOD-02 | `market-data-source` | 封装 Yahoo proxy / fallback / source health；产出可解释的 `SourceHealth` 与原始价格系列载荷；管理短 TTL cache 的显式边界。 | 不承载 watchlist、alert、MTS、布局与恢复状态；不把 provider-specific 字段写入领域层。 | `server/index.js`、`src/domain/market-data-source.ts`（新）、`src/features/source/*`（新） | `solution D-03`、`FR-06`、`AC-02`、`AC-03`、`AC-04`、`BUC-06`、`BO-007`、`RULE-10` |
| MOD-03 | `observation-engine` | 将价格条、指标可用性与来源健康组合成 `PriceSeries` / `IndicatorState`；计算主图、副图、OHLC 读数的准备态。 | 不输出 MTS 结论、不管理提醒、不负责本地恢复。 | `src/lib/indicators.ts`、`src/features/chart/*`（新）、`src/domain/observation.ts`（新） | `solution D-04`、`FR-03`、`FR-06`、`AC-02`、`BUC-02`、`BUC-03`、`BUC-06`、`BO-003`、`BO-004` |
| MOD-04 | `mts-interpreter` | 用纯函数把 `PriceSeries + IndicatorSet + SourceHealth` 解释成 `MtsExplanation`，输出 trend_state / score_band / signal_type / alert_level / reason_codes / invalidators。 | 不把 score 解释为收益概率，不把“观望/确认/强信号/风控”写成自动交易指令。 | `src/lib/signals.ts`（重构/替换）、`src/features/mts/*`（新）、`src/domain/mts.ts`（新） | `solution D-04`、`solution D-05`、`FR-04`、`AC-03`、`AC-04`、`BUC-04`、`BUC-06`、`BO-005`、`RULE-05`、`RULE-06` |
| MOD-05 | `alert-resolution` | 管理提醒 taxonomy、启停、触发、确认、归档暂停、历史记录与风控优先级；将 MTS、价格型与技术指标提醒统一编排。 | 不外发通知、不自动下单、不把提醒状态塞进 UI 临时 state。 | `src/features/alerts/*`（新）、`src/lib/alerts.ts`（新）、`src/types.ts` | `solution D-05`、`FR-05`、`AC-04`、`BUC-05`、`BUC-06`、`BUC-07`、`BO-006`、`RULE-07`~`RULE-09` |
| MOD-06 | `workspace-recovery` | 以版本化 snapshot 管理 watchlist / alerts / selected symbol / layout / restore status；负责迁移、回退与默认布局补救。 | 不把 localStorage 当数据库，不引入账号或云同步。 | `src/lib/storage.ts`（重构）、`src/domain/workspace.ts`（新） | `solution D-06`、`FR-07`、`FR-08`、`AC-05`、`BUC-07`、`BUC-08`、`BO-008`、`RULE-12` |
| MOD-07 | `surface-composition` | 将 `App.tsx` 拆分为 Watchlist / Workbench / MTS / Alerts / Source / Layout / Restore surface，并保留稳定 locator 与可访问名称。 | 不改变业务语义，不把 layout 切换变成数据变更。 | `src/App.tsx`、`src/features/surfaces/*`（新）、`src/styles.css`、`interaction-spec/_shared/surface-registry.md` | `solution D-01`、`solution D-07`、`FR-02`~`FR-08`、`AC-01`~`AC-05`、`SURF-*` |
| MOD-08 | `verification-harness` | 提供 frozen fixture、replay、E2E 断言和 build/test 门禁；验证作为产品合同的一部分，而不是实现后补作文档。 | 不进入 runtime，不承载产品数据，不替代 domain 逻辑。 | `tests/unit/*`（新）、`tests/replay/*`（新）、`tests/e2e/*`（新）、`fixtures/*`（新） | `solution D-07`、`FR-09`、`NFR-05`、`AC-01`~`AC-05`、`VIZ-001` |

### 模块依赖顺序

1. `market-normalization` 先冻结 identity，避免后续自选、提醒和恢复全都建立在错误 symbol 上。
2. `market-data-source` 与 `observation-engine` 同步冻结，确保 `PriceSeries` 与 `SourceHealth` 能被统一消费。
3. `mts-interpreter` 与 `alert-resolution` 采用纯函数/策略层方式接入，便于 fixture 回放。
4. `workspace-recovery` 必须晚于数据合同冻结，避免 snapshot 把旧 schema 写死。
5. `surface-composition` 最后重排 UI，确保 locator 和 state contract 已稳定。
6. `verification-harness` 从第一轮重构开始就并行建立，但以 contract freeze 后的 fixture 为准。

---

## 3. 关键接口设计

> 说明：以下接口是工程合同，不是代码草稿。`before/after` 描述的是现状与目标状态；`兼容策略` 说明如何避免一次性破坏现有路径。

| INT | kind | 接口 / 合同 | before | after | 调用方影响 | 错误语义 | 兼容策略 |
|---|---|---|---|---|---|---|---|
| INT-01 | ADDED | `MarketDataSource.fetchSeries(symbol, range, options)` | 现状由 `server/index.js` 直接拼接 Yahoo fetch + fallback，没有显式边界。 | 返回 `MarketDataEnvelope`，其中包含 `priceSeries`、`sourceHealth`、`meta`、`servedAt`、`cacheState`。cache owner 固定为 server-side `MarketDataSource` 内存层；key 为 `normalizedSymbol + range + interval + provider`；TTL 为 60 秒；`options.forceRefresh=true` 必须绕过 cache。 | `Workbench`、`MTS`、`Alerts` 只消费标准化结果，不再直接依赖 Yahoo 细节。 | 上游失败时：若 60 秒 TTL 内有成功缓存，可返回 `stale`，但 `staleUntil - servedAt` 不得超过 15 分钟；无可用缓存则返回 `unavailable` 或 `demo_fallback`，不抛出未包装异常给 UI。 | 保留 `/api/chart/:symbol` 路径；旧字段 `bars` 可在过渡期并存，但 domain 层只读新 envelope；cache 不写入 `localStorage`，不跨进程或浏览器重启恢复。 |
| INT-02 | MODIFIED | `ChartPayload` → `MarketDataEnvelope` | 当前 payload 为 `{symbol, range, interval, meta, bars, dataSource?, notice?}`。 | 增加 `sourceHealth`、`priceSeries`（domain 视图）、`degradationReason`、`sourceName`、`lastRefreshedAt`、`retryState`、`cacheState`，并保留旧 `bars` 作为迁移期兼容字段。`cacheState` 只能是 `miss/hit/bypass/stale_fallback/disabled`。 | `src/App.tsx` 与图表 surface 不再猜测 fallback 语义；source banner 可直接读取状态。 | 如果新字段缺失，则 UI 必须降级为 `unavailable` 并显示恢复提示，而不是默默把 `notice` 当状态。 | 双读策略：先读新字段，读不到再回退旧字段；旧消费者至少可继续使用 `bars`。 |
| INT-03 | ADDED | `SourceHealth` | 当前仅有 `dataSource: "yahoo" | "demo"` 和 `notice`，没有状态机。 | `formal | demo_fallback | stale | unavailable`，附带 `lastRefreshedAt`、`degradationReason`、`retryState`、`affectedObjects`。 | `SourceHealthPanel`、`Workbench`、`MTS`、`Alerts` 都能一致展示降级，不再各写各的 notice。 | 未知状态统一折叠为 `unavailable`，并强制暴露降级原因；不得映射成 formal。 |
| INT-04 | REPLACED | `PriceBar[]` → `PriceSeries` | 当前 domain 与 UI 直接使用裸 `PriceBar[]`。 | `PriceSeries` 作为 canonical domain object，包含 `bars`、`timeframe`、`latestOhlc`、`latestPrice`、`changeSummary`、`sourceHealth`。 | 指标、MTS、提醒、读数和回放都改为消费 `PriceSeries`，避免重复计算和隐式前提。 | 若 bars 不足，返回 `partial` / `unavailable`，而不是伪造完整指标。 | 底层 wire 可以继续传 `bars`，但域层与新组件不直接依赖 `PriceBar[]`。 |
| INT-05 | REPLACED | `CompositeSignal` → `MtsExplanation` | 当前 `buildSignal()` 产出旧四因子 `CompositeSignal`，UI 文案仍是“四因子共振指标”。 | 新的 `MtsExplanation` 包含 `trendState`、`scoreBand`、`signalType`、`alertLevel`、`reasonCodes`、`invalidators`、`interpretability`、`sourceHealth`、`registryVersion`。`reasonCodes` 与 `invalidators` 必须引用 `MtsReasonRegistry`，不得使用自由文本。 | `MtsSignalCard` 直接绑定解释对象，旧信号名称不得再进入用户可见 surface；展示文案通过 registry 映射。 | 数据不足返回 `data_insufficient`，不输出假信号；`sourceHealth != formal` 时必须同步暴露降级；未知 code 按 `UNKNOWN_CODE` 降级展示并记录兼容告警。 | 过渡期允许内部复用旧四因子评分作为子分项，但对外只暴露 `MtsExplanation`；registry 通过 additive 方式演进，已发布 code 不删除，只可标记 deprecated。 |
| INT-06 | MODIFIED | `AlertRule` | 当前仅有 `above/below` 价格提醒或 `signal` 提醒，且只有 `enabled` / `lastTriggeredAt?`。 | 增加 `taxonomy`（price/change/technical_indicator/mts/scheduled）、`condition`、`activationState`、`triggerState`、`history[]`、`acknowledgedAt`、`suspendedReason`、`restoreIntent`。scheduled 条件使用 `condition.schedule = { mode: "daily_time", localTime: "HH:mm", timezone: "local", daysOfWeek?: number[], skipIfMarketClosed?: boolean }`。 | `AlertsPanel`、`RestoreStatus`、`Workbench` 需要渲染启停、触发、确认和归档恢复；scheduled alert 仅在 app 打开且本地时钟到达时评估。 | 条件无效返回校验错误；归档状态不得触发；风控类触发优先于观察类；app 关闭期间错过的 scheduled tick 不补发，只在恢复时记录 `missed_while_closed`。 | 先支持旧规则双读，迁移时补默认 taxonomy；旧规则在读取后升级为新结构；scheduled 只保存本地时钟语义，不引入后台 worker、系统通知或外部推送。 |
| INT-07 | ADDED | `WorkspaceSnapshotV2` | 当前 localStorage 只有两把 key：watchlist 与 alerts 的数组。 | 版本化快照包含 `version`、`watchlist`、`alerts`、`selectedSymbol`、`layoutBySymbol`、`globalLayoutFallback`、`selectedMobileTab`、`restoreMetadata`。`layoutBySymbol[normalizedSymbol]` 保存 `layout_scope=symbol` 的 `layoutMode`、副图偏好、最近 range 与折叠状态。 | `RestoreStatus`、`WatchlistPanel`、`LayoutController` 共享同一恢复结果；切换标的时优先恢复标的级布局，缺失时使用全局 fallback。 | 快照损坏时不得阻断看盘；回退到默认 focus 布局并记录 `restoreStatus=default_fallback` 或 `partial`。 | 读取时支持旧 key；写入时只写 V2，但保留迁移回退路径；旧全局 `layoutMode` 迁移为 `globalLayoutFallback`，不伪造每个标的的偏好。 |
| INT-08 | MODIFIED | `readWatchlist/readAlerts/writeWatchlist/writeAlerts` → `readWorkspace/writeWorkspace/migrateWorkspace` | 现状为简单 JSON 读写，缺版本号和迁移器。 | 新接口负责双读旧 key、生成 V2、校验 schema、写入回退信息。 | 所有本地恢复调用方只对 snapshot API 编程，不直接碰 localStorage key。 | 解析失败返回 `recoverable=false` 的结果，不能抛出阻断性异常。 | 过渡期保留 legacy key 读取，至少一个发布周期内不得删除旧 key 的读取逻辑。 |

---

## 4. 数据 / 状态设计

> 说明：`kind` 反映本次变化形态；`migration`、`rollback/recovery`、`invariants` 是本阶段必须冻结的状态合同。

| DATA | kind | 数据 / 状态对象 | migration | rollback / recovery | invariants | traces_to |
|---|---|---|---|---|---|---|
| DATA-01 | MODIFIED | `SourceHealth` 与 source transition state machine | 从 `dataSource + notice` 迁移到 `formal/demo_fallback/stale/unavailable`；`server/index.js` 的 fallback 结果必须携带显式状态。 | 任何未知状态统一回退为 `unavailable`；刷新失败保留上次可解释状态并给出 retry 提示。 | 1) 不得把 demo 当 formal；2) `stale` 必须保留上次刷新时间；3) `affectedObjects` 必须同步到图表/MTS/提醒。 | `FR-06`、`RULE-10`、`AC-02`、`AC-03`、`AC-04` |
| DATA-02 | REPLACED | `PriceSeries`（替代裸 `PriceBar[]` 作为领域对象） | 从 wire bars 生成 `PriceSeries`；保留原始 bars 仅用于适配层与回放。 | bars 不足、字段缺失或时间序列不连续时，降级为 `partial/unavailable`，不得伪造完整 OHLC 或指标。 | 1) 同一 symbol/range/source 下可复算；2) `latestOhlc` 与 `changeSummary` 必须可由 bars 推导；3) 不能把 provider 字段塞进 domain。 | `FR-03`、`FR-06`、`BUC-02`、`BUC-03`、`BO-003`、`BO-004` |
| DATA-03 | REPLACED | `MtsExplanation` + `MtsReasonRegistry`（替代旧 `CompositeSignal` 对外展示） | 旧四因子评分作为内部子分项可保留，但 UI、fixture 与 snapshot 只认 `MtsExplanation`；新增 registry 文件作为 reason/invalidator 唯一字典。 | 评分不足或来源降级时输出 `data_insufficient`；未知 code 降级为 `UNKNOWN_CODE`，不允许把旧 signal label 或自由文本当正式 MTS 显示。 | 1) `reasonCodes` 与 `invalidators` 必须引用 registry；2) `alertLevel` 只能落在 观察/确认/强信号/风控；3) registry code 形如 `TREND_UP/EMA_CROSS_UP/MOMENTUM_DIVERGENCE/RISK_BREAKDOWN/DATA_INSUFFICIENT/SOURCE_DEGRADED`，包含 `category`、`severityHint`、`displayKey`、`introducedIn`、`deprecated`；4) 禁止收益承诺措辞。 | `FR-04`、`RULE-05`、`RULE-06`、`AC-03`、`AC-04` |
| DATA-04 | ADDED | `WorkspaceSnapshotV2` + `ChartLayoutPreference` | 从 `myinvestment.watchlist` / `myinvestment.alerts` 双 key 迁移到版本化 snapshot；补入 selected symbol、`layoutBySymbol` 与 global fallback。 | 读取失败时回退默认 focus 布局并重建最小可用工作台；标的级布局损坏时只回退该标的布局，不丢 watchlist/alerts。 | 1) 版本号必填；2) archived 标的必须可恢复；3) snapshot 不能隐式丢失触发历史；4) `layout_scope=symbol` 时 key 必须是 normalized symbol；5) `restoreStatus` 只能是 `restored/partial/default_fallback/failed`。 | `FR-07`、`FR-08`、`AC-05`、`RULE-12` |
| DATA-05 | MODIFIED | Watchlist archive state | 从“删除即消失”迁移到 `active/archived`；归档不等于删除，且会暂停绑定提醒。 | 回退时必须保留 archived 条目，哪怕只恢复为只读状态；不得清空 alert 绑定历史。 | 1) 同 identity 的 active 不能重复；2) archived 标的可恢复；3) 归档期间绑定提醒状态为 `suspended_by_archive`。 | `FR-01`、`FR-02`、`FR-07`、`BUC-01`、`BUC-07`、`RULE-09` |
| DATA-06 | MODIFIED | Alert taxonomy / history / trigger state | 从 `above/below + signal + enabled/lastTriggeredAt` 迁移到 taxonomy、condition、activationState、triggerState、history、acknowledged、suspended_by_archive。scheduled 旧数据不存在时不自动生成，新增规则必须显式选择本地时间。 | 旧提醒按默认 taxonomy 和状态补全后保存；历史缺失时以“无历史但可继续使用”回退；app 关闭期间错过的 scheduled tick 不补触发，只记录 `missed_while_closed` 并等待下一次本地时钟命中。 | 1) 风控优先于观察；2) `suspended_by_archive` 不得触发；3) 触发历史必须可追踪，确认与触发分离；4) scheduled 仅使用本地浏览器时钟和 local timezone；5) 归档会暂停 scheduled，恢复后只从下一次 tick 继续。 | `FR-05`、`AC-04`、`BUC-05`、`BUC-06`、`BUC-07` |

### 状态流转摘要

- `WatchSymbol`: `active <-> archived`
- `SourceHealth`: `formal -> demo_fallback/stale/unavailable`，禁止反向“自动恢复为 formal”
- `IndicatorState`: `ready / partial / unavailable`
- `MtsInterpretability`: `interpretable / data_insufficient`
- `AlertActivationState`: `enabled / disabled / suspended_by_archive`
- `AlertTriggerState`: `idle / triggered / acknowledged`
- `ScheduledAlertState`: `waiting / due / missed_while_closed / suspended_by_archive / acknowledged`
- `LayoutMode`: `dense / focus / mobile_tab`
- `LayoutScope`: `symbol / global_fallback`
- `RestoreStatus`: `restored / partial / default_fallback / failed`

### Command / Event / State-flow 合同

下游实现不得把这些传播关系藏在 UI hook 的临时状态里。每个 flow 都必须由 domain 函数或明确的 orchestrator 产生事件，再由对应模块消费。

| Flow | 触发源 / Command | 生产者模块 | 事件 / State transition | 消费者模块 | 持久化影响 | 顺序保证 | 非法转移 / 补偿 |
|---|---|---|---|---|---|---|---|
| SF-01 | `OpenWorkbench(symbol)` 或 `RefreshSourceHealth(symbol, range, forceRefresh?)` | `MOD-02 market-data-source` | `SourceHealthChanged(formal/demo_fallback/stale/unavailable, retryState, cacheState)` | `MOD-03`、`MOD-04`、`MOD-05`、`MOD-07` | 不写 snapshot；只更新运行时 source state 与可观测日志。 | source health 必须先于 `MtsSignalEvaluated` 与 `AlertRuleTriggered`。 | 未知 source state 转 `unavailable`；provider 字段渗透触发 Provider Gate；cache 超界触发 Cache Gate。 |
| SF-02 | `ObservationContextRefreshed(symbol, priceSeries, sourceHealth)` | `MOD-03 observation-engine` | `IndicatorStateChanged(ready/partial/unavailable)` | `MOD-04`、`MOD-07` | 不写 snapshot。 | `PriceSeries` 校验通过后才允许计算 MTS。 | bars 不足时进入 `partial/unavailable`，禁止伪造 OHLC 或指标。 |
| SF-03 | `EvaluateMts(symbol, priceSeries, indicators, sourceHealth)` | `MOD-04 mts-interpreter` | `MtsSignalEvaluated(MtsExplanation, registryVersion)` | `MOD-05`、`MOD-07` | 不写 snapshot；可被 replay fixture 记录。 | MTS 必须在 `SourceHealthChanged` 与 `IndicatorStateChanged` 后执行。 | 未知 reason/invalidator code 降级 `UNKNOWN_CODE`；数据不足转 `data_insufficient`。 |
| SF-04 | `EvaluateAlertRules(symbol, latestObservation, mtsExplanation, clockTick?)` | `MOD-05 alert-resolution` | `AlertRuleTriggered` / `AlertRuleAcknowledged` / `ScheduledAlertMissed` | `MOD-05`、`MOD-07`、`MOD-06` | 写入 `AlertRule.history`、`lastTriggeredAt`、`acknowledgedAt`、`missedAt`。 | alert 评估在 MTS 后；风控类触发优先于观察类；scheduled 只在 app 打开时由本地时钟 tick 触发。 | `suspended_by_archive` 不得触发；app 关闭期间不补发 scheduled，只记录 missed；无效 condition 阻断写入。 |
| SF-05 | `ArchiveWatchSymbol(symbol)` / `RestoreWatchSymbol(symbol)` | `MOD-01` + `MOD-06` | `WatchSymbolArchived` / `WatchSymbolRestored` | `MOD-05`、`MOD-06`、`MOD-07` | 写入 `WorkspaceSnapshotV2.watchlist`；归档时将绑定 alert 置为 `suspended_by_archive`，恢复时保留原 `restoreIntent`。 | watchlist 状态先变更，再更新 alert activation。 | archived symbol 不得保持 active alert；恢复不能清空 alert history。 |
| SF-06 | `RestoreLocalWorkbench()` | `MOD-06 workspace-recovery` | `WorkspaceRestored(restored/partial/default_fallback/failed)` | `MOD-01`、`MOD-05`、`MOD-07` | 读取 legacy/V2 snapshot；必要时写入迁移后的 V2；不删除旧 key。 | restore 必须先于首个自动 refresh；损坏 layout 只影响对应 symbol。 | snapshot 损坏回退默认 focus；超过 Storage Gate 阈值则停下决策。 |

### MTS registry 合同

`MtsReasonRegistry` 是 `MtsExplanation.reasonCodes` 与 `MtsExplanation.invalidators` 的唯一来源，建议落在 `src/domain/mts-registry.ts` 或同等 domain 文件中。registry entry 至少包含：

| 字段 | 要求 |
|---|---|
| `id` | 稳定大写 snake case，例如 `TREND_UP`、`EMA_CROSS_UP`、`MOMENTUM_DIVERGENCE`、`RISK_BREAKDOWN`、`DATA_INSUFFICIENT`、`SOURCE_DEGRADED`。 |
| `kind` | `reason` 或 `invalidator`。 |
| `category` | `trend`、`momentum`、`volatility`、`volume`、`risk`、`source`、`data_quality`。 |
| `severityHint` | `info`、`watch`、`confirm`、`strong_signal`、`risk`。 |
| `displayKey` | UI 文案 key，展示层只通过 key 映射中文文案。 |
| `introducedIn` | registry 版本，例如 `mts-registry-v1`。 |
| `deprecated` | 布尔值；已发布 code 不删除，只能弃用。 |

新增 code 必须有 replay fixture 覆盖；删除或复用旧 code 必须触发技术设计回流或 Decision Gate。

### 迁移与回滚原则

1. 先读旧 key，再写新 snapshot；旧数据不能在首次迁移时被删除。
2. 迁移器必须可幂等，重复执行不得制造重复 watchlist 或重复提醒。
3. 任何损坏 snapshot 都不得阻断看盘；最差情况回退到默认 focus 工作台。
4. 迁移失败时记录 recovery metadata，供 `RestoreStatus` 显示“已回退/恢复失败”。

---

## 5. 实现策略

> 下面的顺序是为了把不确定面尽量前置到合同冻结阶段，避免后面才发现 identity、source health、snapshot 或 locator 已经漂移。

### 5.1 推荐实施顺序

1. **冻结领域类型与状态枚举**
   - 先落 `SourceHealth`、`PriceSeries`、`MtsExplanation`、`WorkspaceSnapshotV2`、`AlertRule` 新状态。
   - 同步更新 `src/types.ts` 与新 domain 文件。

2. **抽出 source adapter 与 fallback 合同**
   - 把 `server/index.js` 中的 Yahoo fetch / fallback / error handling 包成 `MarketDataSource` 边界。
   - 先保证 `formal/demo_fallback/stale/unavailable` 都有明确输出。

3. **抽出 observation / MTS / alert 纯函数**
   - 将 `src/lib/indicators.ts`、`src/lib/signals.ts` 的逻辑拆成可回放纯函数。
   - 旧四因子结果只作为内部中间量，不再对外叫 `CompositeSignal`。

4. **实现 workspace snapshot 迁移**
   - 先读 legacy watchlist/alerts，再写 `WorkspaceSnapshotV2`。
   - 迁移失败只降级默认布局，不阻断页面加载。

5. **拆分 UI surfaces**
   - 把 `App.tsx` 分解为 Watchlist / Workbench / MTS / Alerts / Source / Layout / Restore surface。
   - 保留 stable `data-testid` 与一致的可访问名称，确保 e2e 不随重构漂移。

6. **补齐 fixture-first 验证**
   - 先构建 frozen bars、歧义输入、降级 source、archive/restore、snapshot 损坏等样本。
   - 再补 unit / replay / e2e，最后才看 live smoke。

### 5.2 停止条件（Stop Conditions）

- **Provider Gate**：如果正式供应商的 auth / quota / response schema 必须进入领域对象或 snapshot，立即停下并发起决策，不得继续把 provider-specific 字段写进 `WatchSymbol`、`PriceSeries`、`AlertRule` 或 `WorkspaceSnapshot`。
- **Cache Gate**：本阶段采用 `MarketDataSource` 内存短 TTL cache，key 为 `normalizedSymbol + range + interval + provider`，TTL 为 60 秒，仅服务当前本地运行进程；不写入 `localStorage`，不跨浏览器重启恢复。显式刷新或 range/provider 变化必须绕过旧 key；上游失败时，60 秒内的缓存可标为 `stale` 辅助展示，但不得超过 15 分钟继续服务，且 `SourceHealth` 必须显示 `stale`。如果实现需要跨进程、跨重启、持久化或超过上述 TTL/stale 窗口，必须先决策 cache scope，不得用隐式状态代替。
- **Storage Gate**：本阶段默认使用 `localStorage + WorkspaceSnapshotV2`。验证阈值：旧 key 迁移必须保留 watchlist 与 alerts；损坏 snapshot 必须回退默认 focus 布局且不清空旧 key；大体量 fixture（500 个标的、2000 条 alert history）序列化后应小于 2 MB，读写/迁移单次应小于 500 ms。若任一阈值无法满足，或浏览器写入失败导致 active watchlist / alerts 无法恢复，必须先决策是否引入额外存储层，不得静默升级到 IndexedDB / 后端持久化。
- **Chart Gate**：如果 `lightweight-charts` 不能稳定满足主图、成交量、副图和 locator contract，要先做图表库替换决策，不得在组件层硬缝补丁。

### 5.3 Gate 合同

| Gate | owner_stage | failure_mode | blocking_threshold | required_evidence |
|---|---|---|---|---|
| Provider Gate | technical_analysis / execute / verify | provider-specific auth、quota、response schema 渗透进 `WatchSymbol`、`PriceSeries`、`AlertRule` 或 `WorkspaceSnapshot` | 任一 provider-specific 字段进入领域对象或持久化 schema；fake provider fixture 无法通过同一 domain contract | Yahoo fixture、demo fixture、fake provider fixture；schema scan；`AFF-01` |
| Cache Gate | technical_analysis / execute / verify | cache 被当成本地恢复存储，或 stale 语义无法解释 | cache 需要持久化、跨重启、跨 provider 复用，或 stale 服务超过 15 分钟；显式刷新无法绕过 cache | TTL 60 秒命中/失效测试；显式 refresh bypass；upstream failure stale fixture；`VS-08` |
| Storage Gate | technical_analysis / execute / verify | `WorkspaceSnapshotV2` 无法在 localStorage 内可靠迁移、保存或恢复 | 500 个标的 + 2000 条 alert history fixture 超过 2 MB；单次读写/迁移超过 500 ms；legacy/corrupt fixture 造成 watchlist/alerts 静默丢失 | legacy key fixture、corrupt snapshot fixture、large snapshot fixture、浏览器重开恢复证据；`VS-05` |
| Chart Gate | execute / verify | `lightweight-charts` 无法稳定承载主图、成交量、副图与 locator contract | 主图/成交量/副图任一 pane 无法在 fixture e2e 稳定渲染，或 locator 不能绑定用户可见状态 | chart fixture screenshot、Playwright locator assertion、fallback readout evidence；`VS-06` / `VS-08` |

### 5.4 禁止路径

- 不得把 `notice` 当作来源健康对象。
- 不得把旧四因子 `CompositeSignal` 直接当正式 MTS 展示。
- 不得把 `active/archived` 简化成删除/重建。
- 不得把 localStorage 当数据库或多设备同步层。
- 不得用 UI 本地状态去承担提醒历史与恢复意图。

---

## 6. 验证策略

> 每个验证项都必须指向一个明确风险或 FR/AC，而不是泛泛地说“补测试”。验证目标优先覆盖外部依赖、降级、恢复和可视化合同。

| VS | 验证目标 | 覆盖对象 | 方法 / 证据 | 风险说明 |
|---|---|---|---|---|
| VS-01 | provider adapter / fallback smoke | `MOD-02`、`INT-01`、`INT-02`、`DATA-01`、`FR-06`、`AC-02` | 运行 live Yahoo + mock failure + fallback fixture，确认 `sourceHealth`、`degradationReason`、`notice`/banner 同时可见，且不会抛 500。 | 防止 Yahoo 限流或 schema 变化把界面拖成空白。 |
| VS-02 | source health state propagation | `MOD-02`、`MOD-03`、`MOD-04`、`MOD-05`、`DATA-01`、`DATA-03`、`FR-06`、`AC-03`、`AC-04` | 用 `formal/demo_fallback/stale/unavailable` fixture 回放，断言图表、MTS、提醒都显示降级语义。 | 防止降级只显示在顶部 notice，用户误读正式行情。 |
| VS-03 | MTS replay determinism + registry | `MOD-04`、`INT-05`、`DATA-03`、`FR-04`、`AC-03` | 冻结 bars 回放，重复执行同一输入应得到同一 `MtsExplanation`；检验 `data_insufficient`、`watch/confirm/strong_signal/risk` 边界；断言所有 reason/invalidator code 均存在于 `MtsReasonRegistry`，未知 code 只能降级为 `UNKNOWN_CODE`。 | 防止旧四因子信号退化为 UI 状态抖动或自由文本解释。 |
| VS-04 | alert / archive / restore / scheduled flow | `MOD-05`、`INT-06`、`DATA-05`、`DATA-06`、`SF-04`、`SF-05`、`FR-05`、`FR-07`、`AC-04`、`AC-05` | 触发价格型、变化型、技术指标型、MTS 型、scheduled 型、归档暂停、恢复原意图、确认历史；验证 `suspended_by_archive` 不触发、app 打开时本地时钟 tick 触发 scheduled、app 关闭期间 missed tick 不补发且记录 `missed_while_closed`。 | 防止提醒历史丢失、归档后仍触发、恢复时意图丢失，或定时提醒被误实现成后台推送。 |
| VS-05 | localStorage migration & recovery | `MOD-06`、`INT-07`、`INT-08`、`DATA-04`、`DATA-05`、`DATA-06`、`FR-07`、`FR-08`、`AC-05` | 用旧版本 watchlist/alerts key、损坏 snapshot、超大 snapshot fixture 做双读迁移；验证标的级 `layoutBySymbol`、副图偏好、`restoreStatus`、默认 focus fallback，且不丢可用状态。 | 防止一次 schema 改动毁掉本地连续性或把标的级布局退化成全局状态。 |
| VS-06 | UI surface / e2e locator contract | `MOD-07`、`INT-02`、`INT-07`、`FR-02`~`FR-08`、`SURF-*` | 通过稳定 `data-testid` 与可访问名称跑浏览器 e2e：watchlist → workbench → MTS → alerts → source → restore → layout；切换两个标的后验证各自 layout/副图偏好可独立恢复。 | 防止 `App.tsx` 拆分后 locator 漂移，或布局恢复范围与用户观察对象错配。 |
| VS-07 | build / test gate | `MOD-08`、`FR-09`、`NFR-05` | 新增独立 unit / replay / e2e 脚本，保证不再只有 `npm run build`。 | 防止质量检查只剩编译，无法覆盖 contract 回归。 |
| VS-08 | cache / chart gate checks | `MOD-02`、`MOD-03`、`solution D-03`、`solution D-01` | 验证 server-side 内存 cache 的 60 秒 TTL、key 维度、`forceRefresh` bypass、range/provider 变化失效、上游失败后 15 分钟内 `stale` 可见且不写入 `localStorage`；同时验证图表 pane 与 secondary pane 在当前库下稳定可渲染。 | 防止 cache 语义越界、被误当恢复存储，或图表库不满足合同却被继续推进。 |

### 验证产物要求

- 冻结样本：四市场标的、歧义输入、来源降级、MTS 强/弱/不可解释、提醒触发、归档恢复、snapshot 损坏。
- 证据类型：命令输出、截图、回放日志、浏览器重开前后对比。
- 门禁顺序：先 unit / replay，再 e2e，最后 smoke live Yahoo。

---

## 7. 生产就绪要求

### 7.1 Error handling

- 行情失败必须以 `SourceHealth` 和降级文案呈现，不允许无提示空白。
- MTS 数据不足必须输出 `data_insufficient`，不能伪造强信号。
- 本地恢复失败必须回退默认 focus 布局，不能把页面锁死。
- 提醒校验失败必须阻断写入，并给出明确原因，而不是静默丢规则。

### 7.2 Compatibility

- `ChartPayload` 过渡期保留旧 `bars`，同时新增标准化 envelope 字段。
- legacy `watchlist` / `alerts` key 必须可读，直到 V2 snapshot 稳定。
- 旧四因子评分可以存在于内部计算中，但不能继续作为用户可见的正式 MTS 名称。

### 7.3 Observability

- 后端要记录 upstream 成功/失败、fallback 原因与缓存命中/失效状态。
- 前端要显式展示 `SourceHealth`、恢复结果、提醒触发理由和降级状态。
- 测试侧要能通过 fixture 名称直接定位某条 AC/FR 的回放输入。

### 7.4 Rollback / Degradation

- 若 snapshot 迁移失败：回退默认布局 + 保留可恢复数据，不清空旧 key。
- 若 provider 适配失败：切换到显式 `demo_fallback`，继续可看但不伪装正式行情。
- 若图表库/布局无法满足合同：先降级到可用读数与摘要，再走 Chart Gate 决策。
- 若 cache 行为影响恢复或 stale 语义：先停用 cache，再重审边界。

---

## 8. 对现有系统影响

### 8.1 Blast radius

- **React/Vite/Express**：现有运行栈不变，但 `src/App.tsx` 必须拆分，`server/index.js` 必须从“直接 fetch + fallback”提升为显式 source adapter。
- **Yahoo proxy**：上游 schema、限流、授权变化会直接影响 `MOD-02`；必须以 adapter 缓冲，不让其渗透到 domain。
- **localStorage**：从两把 legacy key 迁移到 `WorkspaceSnapshotV2`，这是最容易破坏重开恢复的地方。
- **App.tsx 单体**：当前单点聚合会拆成多 surface；这是本次重构的最大 UI blast radius。
- **旧四因子 signal**：`src/lib/signals.ts` 现有 `CompositeSignal` 将被替换为 `MtsExplanation` 对外合同；UI 文案也要同步改写。
- **build-only gate**：当前只有 `npm run build`，必须加上 unit/replay/e2e 门禁，否则无法证明本次设计的关键风险。

### 8.2 现有文件级影响

- `src/types.ts`：会增加 `SourceHealth`、`PriceSeries`、`MtsExplanation`、`WorkspaceSnapshotV2`、`AlertRule` 新状态。
- `src/lib/storage.ts`：会被迁移为 workspace migration adapter。
- `src/lib/signals.ts`：会从旧四因子公开接口迁移为内部解释器或被拆分。
- `src/lib/indicators.ts`：保持纯函数，但输出会被 observation/MTS 共享。
- `src/data/markets.ts`：保留市场归一规则，但补充归一预览与歧义提示契约。
- `src/App.tsx`：由聚合组件变为 surface composition 容器。
- `server/index.js`：增加 source adapter、source health、cache metadata 与更明确的 fallback semantics。

### 8.3 回归面

1. 自选 identity 与去重。
2. 来源降级的可见性。
3. 主图/成交量/副图渲染。
4. MTS 解释卡的字段与文案。
5. 提醒启停、触发、确认、归档暂停。
6. 浏览器重开恢复与默认回退。
7. 移动端 `mobile_tab` 导航与桌面 dense/focus 切换。

---

## 9. Agent 实现

**不适用（Not Applicable）**

本 mission 不引入产品运行时 Agent。`mission-contract`、`solution` 与现有技术设计已共同确认：当前能力由确定性领域规则、状态机、纯函数、fixture-first 验证与 E2E 门禁承载，不需要也不授权产品运行时 Agent。

### 9.1 明确不做的事

- 不新增 Agent 定义文件、角色编排或任何产品运行时 Agent 行为。
- 不新增 skill / tool / MCP / worker 作为本 mission 的 Agent 承载物。
- 不新增 policy / hook / runtime gating / agent eval。
- 不把 MTS、提醒、来源健康、本地恢复拆给 Agent 负责。

### 9.2 当前承载方式

- MTS：由确定性的领域规则与纯函数实现，输出可回放、可断言、可 fixture 覆盖的解释结果。
- 提醒：由状态机与领域规则编排，记录触发、确认、暂停与恢复意图。
- 来源健康：由显式状态模型承载，禁止由临时判断或 Agent 解释覆盖。
- 本地恢复：由版本化状态、迁移器与回退规则承载，不依赖 Agent 介入。
- 验证：由 fixture-first 单测、回放测试与 E2E 门禁承载，不由 Agent 自动补齐。

### 9.3 后续变更门槛

若后续需求要求 Agent 进入以下任一范围：

1. `MTS` 解释或决策路径；
2. `AlertRule` 生成、修改或确认路径；
3. 交易路径；
4. 外部数据操作或外部资源访问；

则必须先修改 `mission/PRD` 的授权边界，并触发 `Decision Gate`。在边界未变更之前，任何 Agent 化方案均不得通过本节落地，也不得通过 prompt、注释或隐式约定替代正式授权。

### 9.4 结论

本节结论为：**本 mission 的 Agent 实现为“无”。**
如需引入 Agent，必须先完成上游授权与边界重审，再重新进行能力设计。
