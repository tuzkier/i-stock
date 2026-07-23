# 业务对象分析：多市场看盘终端（MyInvestment）

> **来源**：prd 技能 → `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/product/business-object-analysis.md`
> **用途**：盘清「看盘终端界面友好化改造」当前界面所承载 / 暴露的既有领域对象、状态机、属性、引用关系与领域约束，供用例模型、验收场景、产品定义与领域模型消费。本文不定义数据库表、字段、接口、缓存、队列或服务模块，也不发明新业务规则。
> **任务性质约束**：本任务是**呈现层友好化**（状态色归位 / 枚举人话化 / 去重复 / 重排 / 层级 / 侧栏 / 信号卡密度），**不改业务算法、不改数据、不加功能**。因此本文的领域对象与状态机全部**据 `src/types.ts` 与 `src/domain/*` 真实代码抽取**，目的是让改造忠实呈现既有领域状态、不泄漏内部编码，而非引入新语义。

**任务编号（mission-id）：** 20260721-watchboard-ui-friendliness
**状态：** `draft`

---

## 输入合格性判断

| 输入 | 来源 | 是否足以建模 | 缺口 | 处理 |
|------|------|--------------|------|------|
| 任务契约 | `harness-runtime/harness/missions/20260721-watchboard-ui-friendliness/mission-contract.md` | 足够 | GAP-01：『友好』验收口径待 prd 逐条落地——属验收细化，不影响领域对象识别 | 领域对象来自源码，验收口径由 acceptance-scenario-designer 消费本文的状态分类结论 |
| intent-framing | `harness-runtime/harness/missions/20260721-watchboard-ui-friendliness/intent-framing.yaml` | 足够 | 无 | 直接消费其对 7 类界面状态的框定与非目标边界 |
| 探索简报 | 不适用：本任务治理档 `可跳过阶段=[discovery, interaction]`，未产出 discovery-brief | 界面现状事实由源码与会话内截图直接提供 | 无 discovery-brief | 以权威源码（`src/types.ts` / `src/domain/*` / `src/App.tsx`）为事实基线，逐条标注来源路径 |
| 项目知识 / 规格 | `project-knowledge/product/design-system/`（呈现语义参考，未逐一展开）；`src/types.ts`、`src/domain/*`、`src/App.tsx`、`src/features/restore/RestoreStatus.tsx` | 足够 | 无 | 领域对象与状态机以类型定义 + 领域逻辑为权威源 |
| 业务材料 | 会话内真实界面截图（现状证据）+ mockup 方向（讨论产物，设计输入而非交付形态） | 足够 | 截图为现状快照，非规则来源 | 只作现状印证；规则一律回溯到源码路径，不从截图臆造规则 |

**合格性结论**：足以建模。所有领域对象、状态机、业务规则均可追溯到源码路径；无需 NEEDS_DECISION。任务未授权新增业务语义，故本文对「呈现如何做」只给状态语义分类（下游消费提示），不设计具体样式。

---

## 候选对象清单

| 候选 ID | 候选名词 | 来源 | 成为业务对象的理由 | 排除 / 保留结论 |
|---------|----------|------|--------------------|----------------|
| CAND-01 | 自选标的 WatchSymbol | `src/types.ts:15-22`；`src/domain/watchlist-state.ts` | 被用户持续管理（增/归档/恢复）、有 active↔archived 生命周期、侧栏主看载体 | 保留为 OBJ-01 |
| CAND-02 | 行情来源健康 SourceHealth / SourceStatus | `src/types.ts:2-3,86-92`；`src/App.tsx:79-93` | 被界面持续追踪并渲染成状态色，正常/异常分类是「状态色归位」核心 | 保留为 OBJ-02 |
| CAND-03 | MTS 技术提醒 MtsExplanation | `src/types.ts:163-186`；`src/domain/mts-registry.ts` | 承载 trendState/scoreBand/alertLevel 等被暴露的内部枚举，是「人话化」对象 | 保留为 OBJ-03 |
| CAND-04 | 交易信号 TradeSignalState | `src/domain/trade-signals.ts:45-66` | status/stance/holding/levels/回测被信号卡呈现，是「信号卡密度」对象 | 保留为 OBJ-04 |
| CAND-05 | 提醒规则 AlertRule | `src/types.ts:188-223`；`src/domain/alert.ts` | 有 activation / trigger 双状态机、受归档联动，被用户管理 | 保留为 OBJ-05 |
| CAND-06 | 工作台布局 WorkspaceLayout / 恢复元数据 | `src/types.ts:38-65`；`src/domain/workspace.ts`；`src/features/restore/RestoreStatus.tsx` | 布局模式可切换；恢复态（restored/partial/default_fallback/failed）是顶部误导性黄条来源 | 保留为 OBJ-06 |
| CAND-07 | MTS 原因项 MtsReason（含 ReasonRegistry） | `src/types.ts:150-161`；`src/domain/mts-registry.ts` | 承载理由代码→人话 label/detail 的注册映射，是枚举人话化的现成翻译源 | 保留为 OBJ-07（依附 OBJ-03） |
| CAND-08 | 回测报告 TradeBacktestReport / 反T状态 FanTState | `src/domain/trade-signals.ts:77-92,411-427` | 胜率/累计收益/三段回合流水，是信号卡密度优化的折叠对象 | 保留为 OBJ-08（依附 OBJ-04） |
| CAND-09 | 归一化预览 NormalizationPreview | `src/domain/market-normalization.ts:9-31` | 承载添加标的时的 empty/ready/ambiguous/invalid/duplicate_active 校验态 | 保留为 OBJ-09（边缘：添加流程态，与 7 类改造弱相关） |
| CAND-10 | 价量序列 PriceSeries / 观测 MarketObservation | `src/types.ts:67-84`；`src/domain/observation.ts` | 价格/涨跌主看数字的数据载体 | 排除为 EXC-01（技术数据载体，价格/涨跌作为 OBJ 属性建模） |
| CAND-11 | 指标序列 IndicatorSeries（MACD/RSI/KDJ/ATR） | `src/domain/observation.ts:6-16` | 图表副图指标 | 排除为 EXC-02（图表技术呈现，非被追踪业务对象） |
| CAND-12 | MarketDataEnvelope / cacheState / retryState | `src/types.ts:94-119,5-13` | 数据管道包裹与缓存/重试技术态 | 排除为 EXC-03（技术实现对象，非业务概念；来源健康已由 OBJ-02 表达） |
| CAND-13 | 顶部黄条 / data-notice / 侧栏圆点 / 折叠区 | `src/App.tsx`；`src/styles.css` | UI 控件 | 排除为 EXC-04（UI 控件/呈现容器，不是业务对象；映射关系见下游消费提示） |

---

## 业务对象详情

### OBJ-01：WatchSymbol（自选标的）

| 项 | 内容 |
|----|------|
| 业务定义 | 用户加入自选、在侧栏与主区被持续盯盘的一支市场标的（美/港/A/韩） |
| 存在原因 | 承载「用户关注哪些标的」这一核心管理意图；是侧栏扫读（SCN-06）与主区一切呈现的锚点 |
| 业务身份 | `symbol`（归一化大写代码，如 `HK.09988`）；`id` 为技术标识 |
| 生命周期 | active（在盯）↔ archived（归档，退出主动盯盘但**不物理删除**，`archivedAt` 记录归档时刻）；见 STM-01。默认不删除，历史引用（提醒、布局）仍保留 |
| 所有者 / 管理者 | 看盘用户 |
| 主要使用场景 | 侧栏列表条目呈现；添加/归档/恢复；主区选中标的的一切派生呈现的锚 |
| 来源 | `src/types.ts:15-22`；`src/domain/watchlist-state.ts:3-18`；`src/domain/workspace.ts:60-66,105-110`；`src/App.tsx:164,426` |

#### 属性

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-01 | id | 外部标识 | 技术主键，非业务身份 | 否 | 稳定不变 | `src/types.ts:16` |
| ATTR-02 | symbol | 一般属性 | 归一化市场代码，业务身份 | 否 | 归一化为大写、去空格、补零后缀（`market-normalization.ts:44-65`） | `src/types.ts:17` |
| ATTR-03 | name | 一般属性 | 显示名 | 否 | 恢复时可覆盖为新名 | `src/types.ts:18`；`watchlist-state.ts:12` |
| ATTR-04 | market | 一般属性 | 所属市场 US/HK/CN/KR | 否 | 决定归一化与校验规则 | `src/types.ts:19` |
| ATTR-05 | status | 状态属性 | active/archived | 是 | 见 STM-01；默认 active | `src/types.ts:20`；`workspace.ts:64` |
| ATTR-06 | archivedAt | 状态属性 | 归档时刻 | 是 | 归档时写入、恢复时清空 | `src/types.ts:21`；`watchlist-state.ts:4,13` |

#### 引用关系

| 引用 ID | 本对象 | 被引用对象 | 引用角色 | 数量关系 | 是否影响生命周期 | 规则 | 来源 |
|---------|--------|------------|----------|----------|------------------|------|------|
| REF-01 | OBJ-01 | OBJ-05 AlertRule | 该标的的提醒规则集合（按 `symbol` 关联） | 1:N | 是，原因：归档标的会联动暂停其全部提醒（BR-01） | `alert.ts:220-235` | `watchlist-state.ts:20-32`；`alert.ts` |
| REF-02 | OBJ-01 | OBJ-06 WorkspaceLayout | 每标的一份布局（`layoutBySymbol[symbol]`） | 1:1（可缺省回退全局） | 否 | 缺省时回退 `globalLayoutFallback` | `workspace.ts:261-278` |
| REF-03 | OBJ-01 | OBJ-04 / OBJ-03 / OBJ-02 | 选中标的派生出信号 / MTS / 来源健康 | 1:1（当前选中标的） | 否 | 派生呈现，不反向影响标的生命周期 | `src/App.tsx:281-285,112` |

---

### OBJ-02：SourceHealth / SourceStatus（行情来源健康）

| 项 | 内容 |
|----|------|
| 业务定义 | 当前标的行情数据来源的健康状态，回答「你现在看到的数据可信吗、是不是真实/最新的」 |
| 存在原因 | 界面据此决定是否给出警告色与降级提示；是「状态色语义归位」（SCN-01）的直接领域依据 |
| 业务身份 | 依附于选中标的与其数据包，无独立 id |
| 生命周期 | 每次数据加载/刷新重算：not_loaded（未加载）→ formal/demo_fallback/stale/unavailable；见 STM-02 |
| 所有者 / 管理者 | 系统（数据管道计算）；用户只读观察 |
| 主要使用场景 | 侧栏条目来源标签、主区降级横幅、信号卡是否输出的门控、MTS 是否降级 |
| 来源 | `src/types.ts:2-3,86-92`；`src/App.tsx:79-93,639-646`；`trade-signals.ts:619-627` |

#### 属性

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-07 | status | 状态属性 | formal/demo_fallback/stale/unavailable(+not_loaded) | 是 | 见 STM-02 与 BR-02 正常/异常分类 | `src/types.ts:2-3` |
| ATTR-08 | affectedObjects | 一般属性 | 受影响对象集合 chart/mts/alerts | 否 | 说明降级波及范围 | `src/types.ts:88` |
| ATTR-09 | degradationReason | 一般属性 | 降级原因文案 | 否 | 用于提示，非枚举 | `src/types.ts:91` |
| ATTR-10 | retryState | 一般属性（含技术态） | 重试尝试/可否重试/下次时刻 | 否 | 技术细节，主视图不宜直呈 | `src/types.ts:7-13,90` |
| ATTR-11 | lastRefreshedAt | 一般属性 | 上次刷新时刻 | 否 | 判定 stale 的依据之一 | `src/types.ts:89` |

> **BR-02 正常/异常分类（状态色归位的领域依据，务必下游消费）**：
> - **正常态（中性/成功色，不应触发警告色）**：`formal`（正式，真实健康数据）。
> - **加载中/占位态（中性，非异常）**：`not_loaded`（尚未加载，App 初始/未选中项）。
> - **降级但可用（需关注但非故障；应为信息/次级提示级，不用高危警告色）**：`demo_fallback`（演示/兜底数据）。当前 `App.tsx:639` 对任何 `status !== "formal"` 一律渲染 `.data-notice`，把 `demo_fallback` 也提到与真故障同级——下游需区分「降级可用」与「真异常」两档。
> - **真异常态（警告/错误色的合法归属）**：`stale`（数据过期）、`unavailable`（不可用）。
> 来源：`src/types.ts:2`；`src/App.tsx:79-93,639`；分类判定同 `trade-signals.ts:619`（`status !== "formal"` 即降级不输出信号）。

#### 引用关系

| 引用 ID | 本对象 | 被引用对象 | 引用角色 | 数量关系 | 是否影响生命周期 | 规则 | 来源 |
|---------|--------|------------|----------|----------|------------------|------|------|
| REF-04 | OBJ-02 | OBJ-04 TradeSignalState | 来源非 formal 时门控信号输出（source_degraded） | 1:1 | 否 | BR-03 | `trade-signals.ts:619-627` |
| REF-05 | OBJ-02 | OBJ-03 MtsExplanation | 降级时 MTS 挂 `sourceHealth` 子集并只保留解释性提醒 | 1:1 | 否 | `SOURCE_DEGRADED` reason | `src/types.ts:184`；`mts-registry.ts:134-143` |

---

### OBJ-03：MtsExplanation（MTS 技术提醒 / 多因子技术评分解释）

| 项 | 内容 |
|----|------|
| 业务定义 | 对选中标的的多因子技术状态给出的可解释评分与提醒（趋势/动量/波动/量能综合），含评分、评分带、信号类型、提醒级别与理由/失效项 |
| 存在原因 | 主视图呈现「技术面现在偏强还是偏弱、为什么」；其内部枚举当前直接暴露，是「人话化 + 评分可读」（SCN-02）核心对象 |
| 业务身份 | 依附选中标的，无独立 id；`registryVersion` 标注解释口径版本 |
| 生命周期 | 每次观测重算，无跨会话持久生命周期 |
| 所有者 / 管理者 | 系统计算；用户只读 |
| 主要使用场景 | 主视图技术提醒区、评分呈现、可展开理由/失效项、MTS 类提醒规则的触发比对 |
| 来源 | `src/types.ts:163-186`；`src/domain/mts-registry.ts`；`src/App.tsx:95-97,651-655` |

#### 属性

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-12 | trendState | 状态属性 | bullish/neutral/bearish/data_insufficient/source_degraded | 是 | 见 BR-04 分类；主视图当前裸呈 `trend_state`（`App.tsx:651`） | `src/types.ts:130,164` |
| ATTR-13 | mtsScore | 计算属性 | 数值或 null | 否 | 评分数值，宜进度条化呈现（SCN-02） | `src/types.ts:165` |
| ATTR-14 | scoreBand | 状态属性 | strong_positive/positive/neutral/negative/strong_negative/not_applicable | 是 | 见 BR-04 分类；当前裸呈 `score_band`（`App.tsx:653`） | `src/types.ts:131,166` |
| ATTR-15 | signalType | 状态属性 | technical_alert/risk_alert/watch/data_insufficient | 是 | 内部枚举，需人话化 | `src/types.ts:132,167` |
| ATTR-16 | alertLevel | 状态属性 | none/观察/确认/强信号/风控 | 是 | 已是中文档位；当前以 `alert_level` 前缀裸呈（`App.tsx:655`） | `src/types.ts:133,168` |
| ATTR-17 | reasonCodes | 引用（→OBJ-07） | 理由代码列表 | 否 | 非本对象固有属性，是对 MtsReason 的引用键，禁止把代码当人话直呈 | `src/types.ts:169` |
| ATTR-18 | reasons / invalidators | 引用（→OBJ-07） | 已解析理由项/失效项 | 否 | 含人话 label/detail，可折叠详情源 | `src/types.ts:170-171` |
| ATTR-19 | displayLabel / technicalReminder | 一般属性 | 已备好的人话展示串 | 否 | 现成可读文案，人话化应优先复用而非再暴露枚举 | `src/types.ts:172-173` |
| ATTR-20 | interpretability.technicalLevels | 计算属性 | upper/middle/risk 关注位 | 否 | 可读的位级参考 | `src/types.ts:174-183` |
| ATTR-21 | sourceHealth（子集） | 引用（→OBJ-02） | 降级来源健康快照 | 是 | 引用来源健康，不是 MTS 固有属性 | `src/types.ts:184` |
| ATTR-22 | registryVersion | 外部标识 | 解释口径版本号 | 否 | 追溯理由注册表版本 | `src/types.ts:185`；`mts-registry.ts:3` |

> **BR-04 trendState / scoreBand / alertLevel 正常 vs 需关注/异常 分类（评分可读 + 状态色的领域依据）**：
> - **scoreBand**：`strong_positive`/`positive` = 正向（成功/积极语义，非警告）；`neutral`/`not_applicable` = 中性（无色/中性）；`negative`/`strong_negative` = 偏弱/看空（可用谨慎/风险色）。**关键领域事实：负向评分是「技术面看空」的正常业务结论，不等于系统异常，绝不能与「数据来源故障」共用同一套告警色**（`App.tsx:96-97` 现将 negative→`risk` tone，需与来源异常色区分）。
> - **trendState**：`bullish`/`neutral`/`bearish` = 正常市场结论（偏多/中性/偏空，均非异常）；`data_insufficient` = 数据质量关注（非市场结论）；`source_degraded` = 来源异常（`App.tsx:95` 已把后两者归 neutral tone）。
> - **alertLevel**：`none` 无提醒；`观察`/`确认`/`强信号` 为递进的信号强度（业务语义，非系统异常）；`风控` 为风险级（可用警示色，语义是「风险信号」而非「界面/数据故障」）。
> 来源：`src/types.ts:130-133`；`src/App.tsx:95-97`；`mts-registry.ts` polarity/severityHint 映射。

#### 引用关系

| 引用 ID | 本对象 | 被引用对象 | 引用角色 | 数量关系 | 是否影响生命周期 | 规则 | 来源 |
|---------|--------|------------|----------|----------|------------------|------|------|
| REF-06 | OBJ-03 | OBJ-07 MtsReason | 理由项/失效项（经 ReasonRegistry 解析出人话） | 1:N | 否 | 代码→label/detail 由注册表解析（BR-05） | `mts-registry.ts:160-163` |
| REF-07 | OBJ-03 | OBJ-05 AlertRule | MTS 类提醒按 `alertLevel` 档位比对触发 | 1:N | 否 | 档位 rank 比较（BR-06） | `alert.ts:285-290,347-351` |

---

### OBJ-04：TradeSignalState（交易信号）

| 项 | 内容 |
|----|------|
| 业务定义 | 针对已注册定制策略标的（当前 5 支港股）计算出的买卖信号态：现在该观望/买/卖/持有、关键价位、信号事件与回测 |
| 存在原因 | 回答「现在该不该动」；是主卡与交易信号卡（SCN-05/SCN-07）的核心，信号卡密度优化对象 |
| 业务身份 | `strategyId` + `symbol` |
| 生命周期 | 每次观测重算：not_target_symbol / source_degraded / data_insufficient / ready；ready 内再派生 stance；见 STM-05 |
| 所有者 / 管理者 | 系统（固定规则策略引擎）；用户只读 |
| 主要使用场景 | 主卡建议、关键价位、回测胜率/累计收益、反T回合、非建议免责声明 |
| 来源 | `src/domain/trade-signals.ts:45-66,592-693` |

#### 属性

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-23 | status | 状态属性 | ready/not_target_symbol/data_insufficient/source_degraded | 是 | 见 STM-05；当前非 ready 时直接把枚举串呈现（`App.tsx:532`） | `trade-signals.ts:19,55` |
| ATTR-24 | stance / stanceLabel | 状态属性 | buy/sell/hold/watch + 人话标签 | 是 | stanceLabel 已是人话，应优先复用 | `trade-signals.ts:20,56-57` |
| ATTR-25 | holding | 状态属性 | 是否持仓中 | 是 | 决定呈现「持仓中/空仓」 | `trade-signals.ts:56`；`App.tsx:532` |
| ATTR-26 | levels | 计算属性 | 各买卖/观察价位 | 否 | 正式信号位 vs ATR 投影观察位需区分层级（SCN-05） | `trade-signals.ts:22-43,58` |
| ATTR-27 | holdBarsUsed / holdBarsMax | 计算属性 | 均值回归持仓超时口径 | 否 | 次级明细 | `trade-signals.ts:57-58` |
| ATTR-28 | events / lastEvent / barsSinceLastEvent | 计算属性 | 历史信号事件 | 否 | 明细，可折叠 | `trade-signals.ts:59-62` |
| ATTR-29 | reasons / warnings / nonAdvice | 一般属性 | 理由/数据警告/免责声明 | 否 | nonAdvice 为免责，必须保留可见 | `trade-signals.ts:63-65` |

#### 引用关系

| 引用 ID | 本对象 | 被引用对象 | 引用角色 | 数量关系 | 是否影响生命周期 | 规则 | 来源 |
|---------|--------|------------|----------|----------|------------------|------|------|
| REF-08 | OBJ-04 | OBJ-08 TradeBacktestReport / FanTState | 回测报告与反T状态（仅 status=ready 时计算） | 1:1 / 1:1 | 否 | ready 门控（BR-07） | `App.tsx:281-285`；`trade-signals.ts:699,433` |
| REF-09 | OBJ-04 | OBJ-02 SourceHealth | 来源非 formal 即降级为 source_degraded | 1:1 | 否 | BR-03 | `trade-signals.ts:619-627` |

---

### OBJ-05：AlertRule（提醒规则）

| 项 | 内容 |
|----|------|
| 业务定义 | 用户为某标的设定的提醒规则（价格/涨跌幅/技术指标/MTS/定时），到条件即触发 |
| 存在原因 | 承载用户「什么情况提醒我」的管理意图；有激活与触发双状态机，受标的归档联动 |
| 业务身份 | `id`（`alert-{taxonomy}-{symbol}-{now}`）；按 `symbol` 关联标的 |
| 生命周期 | 激活维度 enabled↔disabled↔suspended_by_archive（STM-03）；触发维度 idle→triggered→acknowledged（STM-04）。**不物理删除**，归档暂停而非删除，历史 `history` 保留 |
| 所有者 / 管理者 | 看盘用户 |
| 主要使用场景 | 提醒列表、触发提示、归档联动暂停/恢复、确认已读 |
| 来源 | `src/types.ts:188-223`；`src/domain/alert.ts` |

#### 属性

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-30 | id / symbol | 外部标识/引用键 | symbol 是对 OBJ-01 的引用键，非本对象固有属性 | 否 | 按 symbol 关联标的 | `src/types.ts:189-190` |
| ATTR-31 | taxonomy / level / condition | 一般属性 | 分类/级别/触发条件 | 否 | condition.kind 决定评估逻辑 | `src/types.ts:192-204` |
| ATTR-32 | enabled | 状态属性（派生） | 是否启用 | 是 | `enabled === (activationState==="enabled")`（`alert.ts:208`） | `src/types.ts:208` |
| ATTR-33 | activationState | 状态属性 | enabled/disabled/suspended_by_archive | 是 | 见 STM-03 | `src/types.ts:215` |
| ATTR-34 | suspendedReason / restoreIntent | 状态属性 | 暂停原因 / 恢复意图 | 是 | 归档暂停时记录归档前意图，供恢复还原（BR-01） | `src/types.ts:216-217`；`alert.ts:230,241` |
| ATTR-35 | triggerState | 状态属性 | idle/triggered/acknowledged | 是 | 见 STM-04；idle 守卫防重复触发（BR-08） | `src/types.ts:213`；`alert.ts:392` |
| ATTR-36 | lastTriggeredAt / lastScheduledTriggerKey / lastScheduledMissedKey | 状态属性 | 触发/定时去重键 | 是 | 定时提醒按 scheduledKey 去重（BR-09） | `src/types.ts:209-211`；`alert.ts:313-314` |
| ATTR-37 | history | 一般属性 | 生命周期事件流水 | 否 | created/triggered/acknowledged/suspended/restored/missed 追加不删 | `src/types.ts:218-222` |

#### 引用关系

| 引用 ID | 本对象 | 被引用对象 | 引用角色 | 数量关系 | 是否影响生命周期 | 规则 | 来源 |
|---------|--------|------------|----------|----------|------------------|------|------|
| REF-10 | OBJ-05 | OBJ-01 WatchSymbol | 该提醒所属标的（按 symbol） | N:1 | 是，原因：标的归档→提醒 suspended，恢复→按 restoreIntent 还原 | `alert.ts:220-252` |
| REF-11 | OBJ-05 | OBJ-03 MtsExplanation | MTS 类提醒读取 alertLevel 比对触发 | N:1 | 否 | BR-06 | `alert.ts:347-351` |

---

### OBJ-06：WorkspaceLayout / WorkspaceRestoreMetadata（工作台布局与恢复态）

| 项 | 内容 |
|----|------|
| 业务定义 | 工作台的呈现布局（dense/focus/mobile_tab + 移动页签）与快照恢复结果元数据 |
| 存在原因 | 布局是用户偏好；**恢复态（restored/partial/default_fallback/failed）是顶部误导性黄条的来源之一**（SCN-01） |
| 业务身份 | 布局 per-symbol（`layoutBySymbol[symbol]`）+ 全局回退；恢复元数据依附快照 |
| 生命周期 | 布局：用户在 dense/focus/mobile_tab 间切换（STM-06）；恢复态：读取快照时一次性判定为四态之一（STM-07） |
| 所有者 / 管理者 | 布局由用户切换；恢复态由系统在启动读取快照时判定，用户只读 |
| 主要使用场景 | 布局模式切换；顶部恢复状态提示（当前 `RestoreStatus.tsx` 对所有态复用 `.data-notice`） |
| 来源 | `src/types.ts:38-65`；`src/domain/workspace.ts`；`src/features/restore/RestoreStatus.tsx` |

#### 属性

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-38 | mode | 状态属性 | dense/focus/mobile_tab | 是 | 见 STM-06；默认 focus | `src/types.ts:39`；`workspace.ts:42-45` |
| ATTR-39 | selectedMobileTab | 状态属性 | chart/source | 是 | 移动布局下页签 | `src/types.ts:40` |
| ATTR-40 | restoreMetadata.status | 状态属性 | restored/partial/default_fallback/failed | 是 | 见 STM-07 与 BR-10 分类 | `src/types.ts:44,47-52` |
| ATTR-41 | restoreMetadata.reason | 一般属性 | 回退/迁移原因（如 snapshot_missing/legacy_keys_migrated） | 否 | 当前直接拼进黄条文案（`RestoreStatus.tsx:18`） | `src/types.ts:49`；`workspace.ts:234,187` |
| ATTR-42 | migratedFromLegacy / discardedLayoutKeys / snapshotBytes | 一般属性 | 迁移/丢弃/体积技术态 | 否 | snapshotBytes 有 2MB 上限门控（BR-11） | `src/types.ts:48,50-51`；`workspace.ts:17,244` |

> **BR-10 恢复态正常 vs 异常分类（顶部黄条归位的领域依据）**：
> - **正常态（成功/中性，不应渲染警告色黄条）**：`restored`（已恢复，快照完好）。**关键领域事实**：`RestoreStatus.tsx:8` 把 `restored`（已恢复）也用 `.data-notice`（与降级/错误同类）渲染，是 SCN-01 误导性黄条的直接根因。intent-framing 亦点名 `已恢复`、`snapshot_missing` 属正常态。
> - **信息态（非用户可干预的正常回退，宜信息级而非警告）**：`partial`（已从旧存储迁移）、`default_fallback`（回退默认布局，含首次无快照 `snapshot_missing`）。
> - **真异常态（警告/错误色合法归属）**：`failed`（恢复失败）；以及 `RestoreStatus.tsx:19` 的「已丢弃坏布局」明细属需关注提示。
> 来源：`src/types.ts:44`；`src/features/restore/RestoreStatus.tsx:7-21`；`workspace.ts:180-190,234`。

---

### OBJ-07：MtsReason（MTS 理由项，依附 OBJ-03；含 ReasonRegistry）

| 项 | 内容 |
|----|------|
| 业务定义 | 单条技术理由/失效项：代码 + 人话 label/detail + 极性 + 类别 + 严重度提示；由版本化注册表提供 |
| 存在原因 | **是枚举人话化（SCN-02）的现成翻译源**：每个 `MtsReasonCode`（如 TREND_ABOVE_EMA）在注册表都有 `label`（趋势结构偏强）与 `detail`，界面应呈现 label/detail 而非代码 |
| 业务身份 | `code`（MtsReasonCode） |
| 生命周期 | 注册表静态定义，版本化（`MTS_REASON_REGISTRY_VERSION=2`）；未知码回落 `UNKNOWN_CODE` |
| 所有者 / 管理者 | 系统（注册表） |
| 主要使用场景 | 主视图理由/失效项人话呈现、可折叠详情、极性上色依据 |
| 来源 | `src/types.ts:134-161`；`src/domain/mts-registry.ts:13-163` |

#### 属性（要点）

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-43 | code | 外部标识 | 理由代码（内部枚举） | 否 | 主视图不应直呈 code，应显示 label | `src/types.ts:151`；`mts-registry.ts` |
| ATTR-44 | label / detail | 一般属性 | 人话标题 / 说明 | 否 | 人话化直接复用源 | `mts-registry.ts:16-17` |
| ATTR-45 | polarity | 状态属性 | positive/neutral/negative | 是 | 上色依据（正/中/负），非「异常」语义 | `src/types.ts:154`；`mts-registry.ts` |
| ATTR-46 | kind | 状态属性 | reason/invalidator | 是 | 理由 vs 失效项分组 | `src/types.ts:155` |
| ATTR-47 | severityHint | 状态属性 | info/watch/confirm/strong_signal/risk | 是 | 严重度提示，映射呈现强调级 | `src/types.ts:157` |

> **BR-05**：理由代码→人话由 `resolveMtsReason` 经注册表解析，未注册码回落 `UNKNOWN_CODE`（不得作为有效解释直呈）。来源：`mts-registry.ts:160-163,144-153`。

---

### OBJ-08：TradeBacktestReport / FanTState（回测报告与反T状态，依附 OBJ-04）

| 项 | 内容 |
|----|------|
| 业务定义 | 策略长仓回测结果（胜率/平均收益/策略收益/买入持有对比/交易明细）与反T（高卖低买降成本）回合状态 |
| 存在原因 | **信号卡密度优化（SCN-07）对象**：关键数字（胜率/累计收益）应默认呈现，三段回测/回合流水默认折叠 |
| 业务身份 | `strategyId` + `symbol` |
| 生命周期 | 仅 TradeSignalState.status=ready 时计算（BR-07），随观测重算 |
| 来源 | `src/domain/trade-signals.ts:68-92,400-508,699-760` |

#### 属性（要点）

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-48 | winRate / strategyReturnPct / buyHoldReturnPct | 计算属性 | 胜率/累计收益/对比 | 否 | 关键数字，默认呈现（SCN-07） | `trade-signals.ts:87-90,753-757` |
| ATTR-49 | trades / closedTrades | 计算属性 | 交易明细流水 | 否 | 明细，默认折叠 | `trade-signals.ts:84-85,751` |
| ATTR-50 | FanTState.phase / rounds / completedRounds / winRounds / totalSpreadPct | 状态属性/计算属性 | 反T满仓/减仓阶段与回合 | 部分是 | phase=full↔reduced；回合明细折叠 | `trade-signals.ts:400-427,491-499` |

---

### OBJ-09：NormalizationPreview（添加标的归一化预览，边缘对象）

| 项 | 内容 |
|----|------|
| 业务定义 | 用户输入代码添加标的时的实时校验预览态：empty/ready/ambiguous/invalid/duplicate_active |
| 存在原因 | 承载添加流程的输入校验反馈；与 7 类改造弱相关（不在主看盘扫读路径），仅为完整性登记 |
| 生命周期 | 输入过程中即时计算，无持久生命周期 |
| 来源 | `src/domain/market-normalization.ts:9-153`；`src/App.tsx:399-410` |

#### 属性（要点）

| 属性 ID | 属性 | 类型 | 归属判断 | 是否状态属性 | 规则 / 约束 | 来源 |
|---------|------|------|----------|--------------|-------------|------|
| ATTR-51 | status | 状态属性 | empty/ready/ambiguous/invalid/duplicate_active | 是 | ready 才可确认加入；archived 命中则为恢复（restoresArchived） | `market-normalization.ts:9-31,144-152` |

---

## 状态机总览

> 本节是业务领域模型草案的核心部分。若用例展开发现新状态/迁移/规则，须在 `use-case-model.md ## 领域模型反馈` 回流，由 senior-product-expert 统一裁剪进最终产品领域模型。

| 状态机 ID | 归属对象 / 聚合 | 状态组 | 状态集合 | 触发事件 / 命令 | 前置条件 / 守卫 | 合法迁移 | 非法迁移 / 失败行为 | 终态 | 影响的规则 / 用例 |
|-----------|----------------|--------|----------|----------------|----------------|----------|-------------------|------|-------------------|
| STM-01 | OBJ-01 WatchSymbol | 盯盘生命周期 | active, archived | 归档 / 恢复 | 恢复目标须存在于自选（含已归档） | `active ->[归档]-> archived`；`archived ->[恢复(可改名)]-> active` | 归档非物理删除；重复添加 active 标的被拒（走 duplicate_active，不迁移） | 无（archived 非终态，可恢复） | BR-01；SCN-06；US-06 |
| STM-02 | OBJ-02 SourceHealth | 来源健康 | not_loaded, formal, demo_fallback, stale, unavailable | 加载 / 刷新 / 重试 / 错误 | 有 payload 才可判定健康档 | `not_loaded ->[加载成功]-> formal`；`not_loaded ->[无 payload+错误]-> unavailable`；`formal ->[数据陈旧]-> stale`；`formal/stale ->[来源失败]-> unavailable`；`* ->[兜底数据]-> demo_fallback`；`stale/unavailable/demo_fallback ->[刷新恢复]-> formal` | 无 payload 且无错误时停在 not_loaded；不得把 not_loaded/formal 当异常上色（BR-02） | 无（随刷新循环） | BR-02；BR-03；SCN-01；US-01 |
| STM-03 | OBJ-05 AlertRule | 激活状态 | enabled, disabled, suspended_by_archive | 启用 / 停用 / 标的归档 / 标的恢复 | 归档暂停记录 restoreIntent；恢复按 restoreIntent 还原 | `enabled ->[停用]-> disabled`；`disabled ->[启用]-> enabled`；`enabled/disabled ->[标的归档]-> suspended_by_archive`；`suspended_by_archive ->[标的恢复 & restoreIntent=enabled]-> enabled`；`suspended_by_archive ->[标的恢复 & restoreIntent=disabled]-> disabled` | 已是 suspended_by_archive 的规则再归档不重复暂停（`alert.ts:223` 幂等）；suspended 态下 enabled 恒为 false | 无 | BR-01；US-06 |
| STM-04 | OBJ-05 AlertRule | 触发状态 | idle, triggered, acknowledged | 条件命中 / 用户确认 | 仅 activationState=enabled 且 triggerState=idle 才评估触发（`alert.ts:372,392`） | `idle ->[条件命中]-> triggered`；`triggered ->[用户确认]-> acknowledged` | idle 守卫防重复触发（非 idle 不再触发，BR-08）；定时提醒按 scheduledKey 去重、错过记 missed_while_closed（BR-09） | acknowledged（可随新周期定时再评估） | BR-08；BR-09 |
| STM-05 | OBJ-04 TradeSignalState | 信号可用性 + 立场 | status: not_target_symbol, source_degraded, data_insufficient, ready；stance(ready 内): buy, sell, hold, watch | 观测重算 | 门控顺序：非注册标的→not_target_symbol；来源≠formal→source_degraded；bars<80→data_insufficient；否则 ready | `观测 ->[无策略]-> not_target_symbol`；`->[来源降级]-> source_degraded`；`->[数据不足]-> data_insufficient`；`->[通过门控]-> ready`；ready 内 `holding&最新触发->buy`／`holding->hold`／`空仓&最新触发->sell`／`空仓->watch` | 门控优先级固定，先来源后数据；非 ready 时不计算回测/反T（BR-07） | 无（每次观测重判） | BR-03；BR-07；SCN-05；SCN-07；US-05；US-07 |
| STM-06 | OBJ-06 WorkspaceLayout | 布局模式 | dense, focus, mobile_tab | 用户切换布局 / 移动页签 | 仅 layoutModes 白名单值合法，非法值归一为默认 | `focus <-> dense <-> mobile_tab`（任意互切）；`mobile_tab` 下 `selectedMobileTab: chart <-> source` | 非法 mode 归一化丢弃并回退（`workspace.ts:76,92-93`）；默认 focus | 无 | SCN-04（顶部重排不改布局语义，仅呈现） |
| STM-07 | OBJ-06 WorkspaceRestoreMetadata | 快照恢复结果 | restored, partial, default_fallback, failed | 启动读取快照 | 读取时一次性判定 | `读取 ->[快照完好]-> restored`；`->[旧存储迁移]-> partial`；`->[缺失/损坏/坏布局/超限]-> default_fallback`；`->[版本无效等]-> failed(恢复失败)` | 超 2MB 存储门控→default_fallback（`workspace.ts:244-246`，BR-11）；**restored/partial/default_fallback 属正常/信息态，不应渲染警告色**（BR-10） | 是（本次会话内恢复结果固定） | BR-10；BR-11；SCN-01；US-01 |
| STM-08 | OBJ-08 FanTState | 反T仓位阶段 | full（满仓）, reduced（已减仓） | 高卖触发 / 买回触发 | 仅震荡回归型标的启用（`fanT` 配置存在） | `full ->[收盘创新高且高于SMA]-> reduced`；`reduced ->[买回/追高认错]-> full` | 未配置 fanT 或 bars<80 则 disabled，不进入状态机 | 无 | SCN-07 |

---

## 业务规则

> 全部规则均从既有源码抽取，非本任务新增。任务为呈现层改造，不改这些规则本身，仅要求界面忠实呈现其状态。

| 规则 ID | 规则 | 承载对象 | 触发事件 | 前置条件 | 约束结果 | 失败 / 例外处理 | 来源 |
|---------|------|----------|----------|----------|----------|----------------|------|
| BR-01 | 标的归档联动暂停其全部提醒；恢复时按归档前意图（restoreIntent）还原启用/停用 | OBJ-01→OBJ-05 | 归档 / 恢复标的 | 提醒按 symbol 关联该标的 | archived→提醒 suspended_by_archive；恢复→enabled 或 disabled | 已 suspended 的规则再归档幂等不重复 | `watchlist-state.ts:20-45`；`alert.ts:220-252` |
| BR-02 | 来源状态正常/异常分类：formal/not_loaded=正常/占位，demo_fallback=降级可用（信息级），stale/unavailable=真异常 | OBJ-02 | 加载/刷新数据 | 有来源健康态 | 界面据此上色：仅真异常用警告色 | 当前 `App.tsx:639` 把所有非 formal 一律 data-notice（含 demo_fallback），需分档 | `src/types.ts:2-3`；`App.tsx:79-93,639` |
| BR-03 | 来源状态非 formal 时不输出该标的买卖信号（降级为 source_degraded） | OBJ-04←OBJ-02 | 观测重算 | sourceHealth.status≠formal | status=source_degraded，stance=watch，仅提示不给价位 | 来源恢复 formal 后重新输出 | `trade-signals.ts:619-627` |
| BR-04 | scoreBand/trendState/alertLevel 的负向/风控是市场业务结论，非系统异常，不得与来源故障共用告警色 | OBJ-03 | 观测重算 | 有 MTS 解释 | negative/strong_negative/风控 用谨慎/风险语义色，与来源异常色区分 | 中性态（neutral/not_applicable/data_insufficient）用中性色 | `src/types.ts:130-133`；`App.tsx:95-97` |
| BR-05 | 理由代码经版本化注册表解析为人话 label/detail；未注册码回落 UNKNOWN_CODE | OBJ-07 | 呈现理由项 | reasonCodes 存在 | 主视图显示 label/detail 而非 code | 未知码不作为有效解释直呈 | `mts-registry.ts:160-163,144-153` |
| BR-06 | MTS 类提醒按 alertLevel 档位 rank 比较触发；风控/强信号要求精确匹配，其余按 ≥ 触发 | OBJ-05←OBJ-03 | 评估提醒 | condition.kind=mts | 达标则 triggered | rank 表见 `alert.ts:31-37` | `alert.ts:285-290,347-351` |
| BR-07 | 回测报告与反T状态仅在 TradeSignalState.status=ready 时计算 | OBJ-08←OBJ-04 | 观测重算 | status=ready | 计算胜率/收益/回合 | 非 ready 时不计算（信号卡无回测块） | `App.tsx:281-285` |
| BR-08 | 提醒触发幂等：仅 triggerState=idle 且 activationState=enabled 的规则参与触发评估 | OBJ-05 | 条件命中 | idle & enabled | idle→triggered，一次性 | 非 idle 不重复触发，直至 acknowledged/新周期 | `alert.ts:372,392` |
| BR-09 | 定时提醒按当日 scheduledKey 去重；浏览器关闭期间错过记为 missed_while_closed 本地历史 | OBJ-05 | 到达定时点 / 打开应用 | condition.kind=daily_time | 同 key 不重复触发；错过记 missed | 周末/非交易日/skipIfMarketClosed 跳过 | `alert.ts:297-329,359-366` |
| BR-10 | 工作台恢复态 restored/partial/default_fallback 属正常/信息态，仅 failed 及坏布局丢弃属需关注；不应把正常恢复渲染成警告黄条 | OBJ-06 | 启动读取快照 | 有 restoreMetadata | 正常恢复用中性/成功呈现 | 当前 `RestoreStatus.tsx` 对所有态复用 `.data-notice` | `RestoreStatus.tsx:7-21`；`workspace.ts:180-190` |
| BR-11 | 工作台快照超 2MB 存储门控则回退默认布局；写入超限抛错 | OBJ-06 | 读/写快照 | snapshotBytes>2,000,000 | 读→default_fallback；写→抛错 | reason=snapshot_exceeds_storage_gate | `workspace.ts:17,244-246,253-254` |
| BR-12 | 添加标的：active 重复被拒（duplicate_active），命中 archived 则为恢复而非新增；纯数字代码跨市场歧义需先选市场 | OBJ-01←OBJ-09 | 输入代码 | 归一化后比对自选 | ready 才可确认；restoresArchived 走恢复 | ambiguous/invalid/duplicate_active 阻断确认 | `market-normalization.ts:111-152` |

---

## 建模取舍

| 排除 ID | 候选对象 / 规则 | 排除原因 | 风险 | 后续处理 |
|---------|----------------|----------|------|----------|
| EXC-01 | PriceSeries / MarketObservation | 技术数据载体；价格/涨跌作为呈现属性归入主看数字，不是被独立追踪的业务对象 | 低 | 价格/涨跌的「唯一主源」收敛（SCN-03）由用例/交互层处理，不新增对象 |
| EXC-02 | IndicatorSeries（MACD/RSI/KDJ/ATR）/ IndicatorState | 图表副图技术呈现，非用户管理/追踪的业务对象 | 低 | 属图表组件呈现，7 类改造未点名 |
| EXC-03 | MarketDataEnvelope / MarketDataCacheState / MarketDataRetryState | 数据管道与缓存/重试技术实现对象；来源健康已由 OBJ-02 表达 | 中：retryState 细节当前泄漏进 notice（`App.tsx:641`） | 下游枚举人话化时把 retry/cache 技术态收进可折叠详情，不进主视图 |
| EXC-04 | 顶部黄条 / data-notice / 侧栏圆点 / 折叠区 / 周期视图切换控件 | UI 控件与呈现容器，模板明确禁止作为业务对象 | 低 | 领域状态→呈现语义映射见下游消费提示 |
| EXC-05 | 「新增友好化业务规则」 | 任务为呈现层改造，明确不改算法/数据/加功能；不得发明新业务规则 | 中：若下游误把呈现口径当新规则会范围溢出 | 下游只消费既有 BR 的状态分类，验收口径细化属呈现判定非业务规则 |
| EXC-06 | OBJ-09 NormalizationPreview 深建模 | 添加流程校验态与 7 类主看盘扫读改造弱相关 | 低 | 仅登记，除非 prd 将添加流程纳入范围 |

**证据不足 / 待澄清**：
- 待澄清：`demo_fallback`（演示态）在「状态色归位」中应归「正常」还是「需关注」——源码将其与真异常同样触发 notice（`App.tsx:639`），但 intent-framing 的正常态样例只点名 formal/已恢复/snapshot_missing，未点名 demo_fallback。本文建模为「降级可用=信息级」（介于正常与真异常之间），最终呈现分档由 acceptance-scenario-designer 依 SCN-01 判定。不阻断建模。

---

## 下游消费提示

| 消费方 | 必须消费的对象 / 状态 / 规则 | 消费方式 | 不得假设的内容 |
|--------|------------------------------|----------|----------------|
| 用例模型（use-case-modeler） | OBJ-01~06 及 STM-01~07；BR-01/02/03/07/10 | 建立「用户扫读来源健康 / 技术提醒 / 交易信号 / 侧栏标的 / 顶部恢复态」的系统用例与界面承载要求；界面边界须覆盖各状态呈现分支 | 不得新增业务用例或改状态机语义；本任务仅呈现改造 |
| 验收场景（acceptance-scenario-designer） | BR-02（SourceStatus 正常/异常分类）、BR-04（scoreBand 负向≠异常）、BR-10（恢复态正常≠警告）；STM-02/07 状态集合 | 将「警告色仅现于真异常」落成可观察验收：formal/not_loaded/restored/partial/default_fallback → 0 警告色；stale/unavailable/failed → 可见警告色；negative scoreBand → 谨慎色而非来源告警色 | 不得从未确认规则生成验收；demo_fallback 分档以 SCN-01 为准（见待澄清） |
| 产品领域模型（senior-product-expert） | 全部 OBJ 与 STM，尤其状态枚举→人话映射源：OBJ-07 label/detail、ATTR-24 stanceLabel、ATTR-19 displayLabel、ATTR-16 中文 alertLevel、`sourceStatusLabel`(`App.tsx:86-93`) | 综合进 product-domain-model；强调「人话化优先复用既有 label/displayLabel，而非再暴露枚举」 | 不得机械把枚举值当展示文案；不得把技术态（cacheState/retryState）当领域状态 |
| 方案 / 技术分析 | STM-02/07 分档呈现语义、EXC-03（技术态折叠）、BR-02/04/10 上色分档 | 落成状态→呈现语义映射层（正常/信息/需关注/异常四档色语义），把内部枚举/理由代码收进可折叠详情区 | 不得改动 `src/domain/*` 算法/状态机；改造限于 `src/App.tsx`/`src/features/*`/`src/styles.css` 呈现层（含 `RestoreStatus.tsx` 的样式归位） |

### 领域状态 → 呈现语义映射（供交互/技术分析落地，非样式设计）

| 领域状态 | 建议呈现语义档 | 依据 |
|----------|----------------|------|
| SourceStatus: formal / not_loaded | 正常 / 中性占位（无警告色） | BR-02 |
| SourceStatus: demo_fallback | 信息 / 次级提示（非高危色） | BR-02（待澄清分档） |
| SourceStatus: stale / unavailable | 需关注 / 异常（警告或错误色） | BR-02 |
| scoreBand: strong_positive/positive | 积极 / 正色 | BR-04 |
| scoreBand: neutral/not_applicable | 中性（无色） | BR-04 |
| scoreBand: negative/strong_negative；alertLevel: 风控 | 谨慎 / 风险（业务弱势语义，须与来源异常色区分） | BR-04 |
| RestoreStatus: restored | 成功 / 中性（不显黄条或极弱化） | BR-10 |
| RestoreStatus: partial / default_fallback | 信息（非警告色） | BR-10 |
| RestoreStatus: failed / 坏布局丢弃 | 需关注 / 异常 | BR-10 |
| TradeSignalState.status: not_target_symbol/data_insufficient/source_degraded | 中性说明（人话化，非裸枚举） | STM-05 |
| MtsReasonCode（理由代码） | 显示 label/detail，代码收入可折叠详情/调试区 | BR-05 |
