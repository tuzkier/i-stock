# Product Domain Model: MyInvestment

> **来源**：prd 技能 → `harness-runtime/harness/stages/20260522-stock-watch-system/product/product-domain-model.md`
> **用途**：按 DDD 方法沉淀产品领域模型。本文定义业务语义、边界、规则、状态和行为契约，不定义数据库、接口、框架、缓存、队列或部署方案。

**mission-id:** `20260522-stock-watch-system`  
**Status:** `draft`

---

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件提供产品领域模型解释。

---

## Domain Intent

| Item | Content | Trace |
|------|---------|-------|
| Business Problem | 用户缺少一个可持续使用的跨市场观察工作台，无法在单一入口持续管理自选、看盘、解读 MTS 和接收提醒 | Mission Objective, US-01~US-04 |
| Product Capability | 多市场本地看盘、自选管理、默认图表上下文、MTS 解释性信号、四级提醒、本地恢复、来源降级透明化 | FR-01 ~ FR-06 |
| Non-Goals | 自动交易、收益承诺、云同步、完整基本面、完整回测平台、在 PRD 锁定供应商或开源库 | Scope SD-11 ~ SD-17 |
| Modeling Depth | complex | 涉及多对象协作、状态迁移、降级语义、权限边界、来源可信度和解释性提醒，简单名词清单不足以支撑验收与下游设计 |

如果某个 DDD 要素不适用，必须写明 `N/A because ...` 或 `不适用：原因...`，不得留空。

---

## Strategic DDD

### Domain / Subdomain

| Type | Name | Why It Exists | Core / Supporting / Generic | Trace |
|------|------|---------------|-----------------------------|-------|
| Domain | 本地多市场股票看盘与提醒 | 把跨市场观察、自选管理、图表上下文、解释性信号和提醒整合为单一持续使用入口 | Core | Mission Objective |
| Subdomain | 自选与观察对象管理 | 负责市场分组、代码归一、观察状态、归档/恢复 | Core | FR-01, BUC-01 |
| Subdomain | 看盘视图与指标解释 | 负责默认看盘布局、指标组合、副图切换、局部降级 | Core | FR-02, BUC-02, BUC-03 |
| Subdomain | MTS 趋势解释与提醒 | 负责趋势状态、分数带、买卖/风控类型、提醒等级与触发理由 | Core | FR-03, FR-04, BUC-04, BUC-05 |
| Subdomain | 来源状态与可解释性降级 | 负责正式 / 演示 / 降级语义和对下游对象的可信度影响 | Supporting | FR-06, BUC-07 |
| Subdomain | 本地连续使用体验 | 负责恢复自选、提醒和基础看盘上下文 | Supporting | FR-05, BUC-06 |

### Bounded Contexts

| Context-ID | Context Name | Responsibility | In Language | Out of Boundary |
|------------|--------------|----------------|-------------|-----------------|
| BC-01 | Watchlist Context | 管理 WatchSymbol、Market、归档/恢复和观察身份 | 自选、市场、原始代码、归一代码、active、archived | 不负责价格序列、信号计算、供应商实现 |
| BC-02 | Chart Observation Context | 组织 PriceBar、IndicatorSet、ChartLayout 的观察语义和降级状态 | 主图、副图、成交量、默认布局、数据不足、不可解释 | 不负责 MTS 评分策略、不负责来源接入实现 |
| BC-03 | Signal & Alert Context | 组织 MtsSignal、AlertRule 的解释、等级、触发和优先级 | 趋势状态、分数带、趋势回调买点、收敛突破买点、趋势破坏、动量衰竭、风控止损、观察/确认/强信号/风控 | 不负责自动交易或收益解释 |
| BC-04 | Source Transparency Context | 管理 MarketDataSource 及其对 PriceBar / IndicatorSet / MtsSignal / AlertRule 的可信度影响 | 正式、演示、降级、可用、不可用、数据不足 | 不负责具体上游供应商协议 |
| BC-05 | Local Continuity Context | 管理恢复范围、恢复策略和本地会话连续性 | 重开恢复、基础看盘上下文、恢复策略 | 不负责云同步或跨设备共享 |

### Context Map

| Upstream Context | Relationship | Downstream Context | Contract / Translation Rule | Risk |
|------------------|--------------|--------------------|-----------------------------|------|
| BC-01 Watchlist Context | customer_supplier | BC-02 Chart Observation Context | 只有 `active` 且市场可识别的 WatchSymbol 才能进入看盘观察流程 | 若归档/恢复语义不清，会影响图表与提醒上下文 |
| BC-02 Chart Observation Context | customer_supplier | BC-03 Signal & Alert Context | MtsSignal 只能消费同一标的、同一观察上下文下可解释的 PriceBar 与 IndicatorSet | 若数据不足未正确传递，会产生伪信号 |
| BC-04 Source Transparency Context | upstream guardrail | BC-02 Chart Observation Context | 来源状态必须翻译为 `sufficient / insufficient / demo_fallback / unavailable` 等产品语义 | 若翻译失真，用户会误读可信度 |
| BC-04 Source Transparency Context | upstream guardrail | BC-03 Signal & Alert Context | demo 或降级状态必须改变 MTS 和提醒的可解释性，而不是只改页面角标 | 若降级只停留在视觉层，产品会产生错误确定感 |
| BC-05 Local Continuity Context | supporting | BC-01 / BC-02 / BC-03 | 恢复只恢复产品授权的本地语义对象，不恢复未定义的跨设备或后台行为 | 恢复粒度未定会影响交互和状态模型 |

### Ubiquitous Language

| Term | Definition in This Context | Forbidden Ambiguity | Source |
|------|----------------------------|---------------------|--------|
| WatchSymbol / 自选标的 | 用户主动维护的单个观察对象 | 不等于行情序列或提醒规则 | BO-001 |
| Market / 市场 | 承载分组和代码归一语义的业务对象 | 不等于数据供应商 | BO-002 |
| PriceBar / 价格条 | 某标的某周期上的单条 OHLCV 观察记录 | 不等于界面刷新频率或临时展示状态 | BO-003 |
| IndicatorSet / 指标集 | 当前看盘上下文中的指标组合及其解释状态 | 不等于某个库的公式实现 | BO-004 |
| MtsSignal | 多周期趋势解释对象 | 不等于自动买卖指令，也不等于单一箭头 | BO-005 |
| AlertRule / 提醒规则 | 用户配置的本地提醒规则 | 不等于外部推送通道 | BO-006 |
| MarketDataSource / 行情来源 | 面向用户表达来源身份与可信度的对象 | 不等于具体接入方式或程序适配对象 | BO-007 |
| ChartLayout / 看盘布局 | 用户可感知的主图/副图结构与恢复偏好 | 不等于具体图表能力或组件参数 | BO-008 |
| 风控提醒 | 对趋势破坏、动量衰竭或止损风险的高优先级提示 | 不等于自动卖出动作 | Research, BR-011, BR-013 |
| data_insufficient / 数据不足 | 当前数据不足以解释指标或 MTS 的状态 | 不等于系统故障或“无信号” | BO-003, BO-005 |

### Capability Boundary

| Capability-ID | Capability | Added / Changed / Removed / Reused | Boundary Rule | Trace |
|---------------|------------|------------------------------------|---------------|-------|
| CAP-01 | 多市场自选管理 | Added | 只覆盖 US/HK/CN/KR；新增市场需走范围决策 | FR-01 |
| CAP-02 | 默认看盘布局与副图切换 | Added | 只定义产品布局语义，不定义图表实现方案 | FR-02 |
| CAP-03 | MTS 解释性信号 | Added | 输出解释对象，不输出自动交易决策或收益承诺 | FR-03 |
| CAP-04 | 四级提醒 | Added | 只覆盖本地提醒与浏览器通知，不扩展外部推送编排 | FR-04 |
| CAP-05 | 本地恢复 | Added | 只承诺同一浏览器配置内的连续使用，不承诺云同步 | FR-05 |
| CAP-06 | 来源降级透明化 | Added | 只定义来源状态和可信度表达，不锁定供应商 | FR-06 |

---

## Tactical DDD

### Actors

| Actor-ID | Actor / Role | Goal | Allowed Contexts |
|----------|--------------|------|------------------|
| ACT-01 | 个人投资者 | 管理跨市场自选并持续看盘 | BC-01, BC-02, BC-05 |
| ACT-02 | 技术分析用户 | 观察主图、副图指标和图表上下文 | BC-02, BC-04 |
| ACT-03 | 研究驱动用户 | 解读 MTS、配置提醒、处理风险提示 | BC-03, BC-04, BC-05 |
| ACT-04 | 系统 | 根据当前观察上下文更新来源状态、指标解释、MTS 结果和提醒触发结果 | BC-02, BC-03, BC-04, BC-05 |

### Aggregates

| Aggregate-ID | Aggregate | Aggregate Root | Consistency Boundary | Invariants Owned |
|--------------|-----------|----------------|----------------------|------------------|
| AGG-01 | Watchlist Aggregate | WatchSymbol | 单个观察对象及其市场身份、观察状态、与提醒/布局引用的业务一致性 | INV-01, INV-02, INV-03 |
| AGG-02 | Observation Aggregate | ObservationSession（概念根，围绕某个 WatchSymbol 的当前观察上下文） | 同一标的的 PriceBar、IndicatorSet、ChartLayout、SourceStatus 是否形成可解释的观察上下文 | INV-04, INV-05, INV-06 |
| AGG-03 | Signal & Alert Aggregate | AlertRuleSet（概念根，围绕某个 WatchSymbol 的提醒集合） | 同一标的的 MtsSignal 解释、提醒等级、启停状态、归档暂停和优先级是否一致 | INV-07, INV-08, INV-09, INV-10 |

### Entities

| Entity-ID | Entity | Identity | Lifecycle | Aggregate |
|-----------|--------|----------|-----------|-----------|
| ENT-01 | WatchSymbol | `market + normalized_symbol` | `draft_added -> active -> archived` | AGG-01 |
| ENT-02 | AlertRule | `rule_id` | `enabled/disabled/suspended_by_archive` + `idle/triggered/acknowledged` | AGG-03 |
| ENT-03 | MarketDataSource | `source_name + source_mode` | `available/degraded/unavailable` | AGG-02 |
| ENT-04 | ChartLayout | `layout_name + scope` | `default/customized` + `session_only/restorable` | AGG-02 |
| ENT-05 | MtsSignal | `symbol + timeframe_bundle + evaluation_moment` | `data_insufficient/interpretable` + `watch/confirmed/strong/risk` | AGG-03 |

### Value Objects

| ValueObject-ID | Value Object | Attributes | Equality / Validation Rule | Used By |
|----------------|--------------|------------|----------------------------|---------|
| VO-01 | MarketIdentity | `market_code`, `display_label` | 必须属于已支持市场集合 | WatchSymbol |
| VO-02 | SymbolCode | `raw_symbol`, `normalized_symbol` | 原始代码与归一代码必须同时保留且可追溯 | WatchSymbol |
| VO-03 | PriceBar | `time`, `open`, `high`, `low`, `close`, `volume`, `timeframe`, `source_mode` | 同一时点同一周期不得冲突；数据不足时标记而不伪造 | ObservationSession |
| VO-04 | IndicatorReading | `indicator_name`, `parameters`, `value`, `status` | status 必须与数据充分性一致 | IndicatorSet |
| VO-05 | SignalScoreBand | `score`, `band_label` | `score` 范围必须在 -100 到 100 之间；不得解释为胜率 | MtsSignal |
| VO-06 | SignalReason | `reason_code`, `reason_text`, `invalidation_hint` | 必须可解释，不得为空泛地写“买入/卖出” | MtsSignal |
| VO-07 | AlertCondition | `rule_type`, `threshold_or_signal_condition`, `alert_level` | 规则类型只能是价格型或信号型；等级只能在四级语义内 | AlertRule |
| VO-08 | SourceStatus | `source_mode`, `availability_status`, `freshness_note`, `degradation_reason` | 必须能区分 formal、demo_fallback、degraded、unavailable 等产品状态 | MarketDataSource |

### Domain Commands

| Command-ID | Command | Actor / System | Target Aggregate | Preconditions | Result |
|------------|---------|----------------|------------------|---------------|--------|
| CMD-01 | AddWatchSymbol | 用户 | AGG-01 | 市场可识别且在支持范围内 | 创建或恢复 WatchSymbol 为 `active` |
| CMD-02 | ArchiveWatchSymbol | 用户 | AGG-01 | 目标 WatchSymbol 当前为 `active` | WatchSymbol 转为 `archived`，相关 AlertRule 进入 `suspended_by_archive` 且不再触发 |
| CMD-03 | RestoreWatchSymbol | 用户 | AGG-01 | 目标 WatchSymbol 当前为 `archived` | WatchSymbol 恢复为 `active`，相关 AlertRule 按用户原先启停意图恢复 |
| CMD-04 | SelectWatchSymbol | 用户 | AGG-02 | WatchSymbol 为 `active` | 打开对应 ObservationSession |
| CMD-05 | SwitchSecondaryIndicator | 用户 | AGG-02 | 当前存在可用观察上下文 | ChartLayout 从 `default` 或当前自定义状态切换到新副图选择 |
| CMD-06 | RefreshObservationContext | 系统 | AGG-02 | 当前 WatchSymbol 已选中 | 更新 SourceStatus、PriceBar、IndicatorSet 的解释状态 |
| CMD-07 | EvaluateMtsSignal | 系统 | AGG-03 | 观察上下文可解释或已知不可解释 | 产出新的 MtsSignal 或 `data_insufficient` 结果 |
| CMD-08 | CreateAlertRule | 用户 | AGG-03 | 目标 WatchSymbol 为 `active`；条件合法 | 新建 enabled 或 disabled 的 AlertRule |
| CMD-09 | UpdateAlertRuleState | 用户 | AGG-03 | AlertRule 存在 | 切换启停、确认触发或调整规则条件 |
| CMD-10 | ResolveAlertOutcome | 系统 | AGG-03 | 已有新 MtsSignal 或价格条件变化 | 根据优先级更新 AlertRule 的触发结果 |
| CMD-11 | RestoreLocalWorkspace | 系统 | BC-05 | 本地存在可恢复配置 | 恢复自选、提醒和基础看盘上下文 |

### Domain Events

| Event-ID | Event | Raised By | Meaning | Consumers / Follow-up |
|----------|-------|-----------|---------|-----------------------|
| EVT-01 | WatchSymbolAdded | CMD-01 | 用户已把标的纳入观察范围 | BC-05 可记录恢复集合；BC-03 可允许创建提醒 |
| EVT-02 | WatchSymbolArchived | CMD-02 | 用户停止观察该标的 | BC-03 将相关提醒转入 `suspended_by_archive`，保留历史记录但禁止触发 |
| EVT-03 | WatchSymbolRestored | CMD-03 | 已归档标的重新进入观察范围 | BC-03 按归档前的用户启停意图恢复提醒状态 |
| EVT-04 | ObservationContextRefreshed | CMD-06 | 当前标的的来源状态、价格上下文和指标解释已更新 | 触发 MTS 评估与提醒解析 |
| EVT-05 | SourceDegraded | CMD-06 | 当前观察上下文进入降级或演示来源 | BC-03 必须重新判断可解释性与提醒可信度 |
| EVT-06 | MtsSignalEvaluated | CMD-07 | 新的 MTS 解释结果已经形成 | BC-03 更新提醒状态与页面展示 |
| EVT-07 | AlertRuleTriggered | CMD-10 | 某条提醒规则已命中 | 页面展示最近触发时间、原因与等级 |
| EVT-08 | LocalWorkspaceRestored | CMD-11 | 本地观察工作台恢复完成 | 首屏回到可用状态 |

### Invariants

| Invariant-ID | Invariant | Aggregate / Context | Commands Protected | Failure Behavior | Trace |
|--------------|-----------|---------------------|--------------------|------------------|-------|
| INV-01 | WatchSymbol 必须属于已支持市场，并同时保留原始代码与归一代码 | AGG-01 | CMD-01, CMD-03 | reject | FR-01, BR-001 |
| INV-02 | 同一市场内同一归一代码在 active 集合中只能代表同一观察对象 | AGG-01 | CMD-01 | reject 或恢复既有对象 | BUC-01 |
| INV-03 | archived 是可恢复状态，不得被产品语义当作不可追溯删除 | AGG-01 | CMD-02, CMD-03 | reject 物理抹除式语义 | BR-002 |
| INV-04 | ObservationSession 只能围绕一个 active WatchSymbol 建立 | AGG-02 | CMD-04, CMD-06 | reject | FR-02 |
| INV-05 | 数据不足或来源降级时，IndicatorSet 与 MtsSignal 不能伪装为 fully ready | AGG-02 / AGG-03 | CMD-06, CMD-07 | downgrade | BR-004, BR-005 |
| INV-06 | 默认布局必须始终能回到“主图 + 成交量 + 一个可切换副图”的可用状态 | AGG-02 | CMD-05, CMD-11 | compensate to default | FR-02, FR-05 |
| INV-07 | MtsSignal 必须同时表达趋势状态、分数带、信号类型和提醒等级 | AGG-03 | CMD-07 | reject incomplete signal | BR-008 |
| INV-08 | SignalScoreBand 不得被当作胜率或收益概率 | AGG-03 | CMD-07, CMD-10 | reject misleading interpretation | BR-009 |
| INV-09 | 多提醒同时命中时，风控提醒优先于观察类提醒 | AGG-03 | CMD-10 | prioritize risk | BR-013 |
| INV-10 | 归档标的绑定的 AlertRule 必须暂停触发并保持可恢复；恢复标的后按用户原先启停意图恢复 | AGG-01 / AGG-03 | CMD-02, CMD-03, CMD-10 | suspend or restore, never trigger while archived | RULE-02, FR-04, FR-05 |

### Policies

| Policy-ID | Policy | Trigger | Decision Inputs | Outcome | Trace |
|-----------|--------|---------|-----------------|---------|-------|
| POL-01 | 市场识别与代码归一策略 | CMD-01 | 用户输入代码、市场选择、支持市场集合 | 识别成功则加入观察；失败则拒绝 active 化 | BUC-01 |
| POL-02 | 默认布局回退策略 | CMD-04, CMD-11 | 当前布局状态、恢复策略、数据充分性 | 若无可恢复布局，则回到默认布局 | BUC-02, BUC-06 |
| POL-03 | MTS 解释策略 | CMD-07 | PriceBar、IndicatorSet、Research 规则、SourceStatus | 产出趋势状态、分数带、信号类型、提醒等级、理由与失效条件 | BUC-04 |
| POL-04 | 提醒优先级策略 | CMD-10 | AlertRule 条件、MtsSignal 结果、价格条件 | 风控 > 强信号 > 确认 > 观察 | BUC-05 |
| POL-05 | 来源降级传播策略 | EVT-05 | SourceStatus、数据充分性、当前观察对象 | 传播到 IndicatorSet、MtsSignal、AlertRule 的可信度和可解释性状态 | BUC-07 |

### Domain Services

| Service-ID | Domain Service | Why Not Entity-Owned | Inputs | Output / Event |
|------------|----------------|----------------------|--------|----------------|
| DS-01 | WatchSymbolNormalizationService | 代码识别与归一需要跨 Market 规则协作，不属于单一实体内部属性判断 | 原始代码、市场集合、归一规则 | 归一结果或不可识别结果 |
| DS-02 | ObservationReadinessService | 数据充分性、来源状态和布局可用性共同决定是否可解释，跨多个对象 | SourceStatus、PriceBar 集合、IndicatorReadings、ChartLayout | 观察上下文状态 |
| DS-03 | MtsSignalInterpretationService | MTS 需要综合价格、指标、波动、成交量和研究规则，不是单一实体自含行为 | PriceBar、IndicatorSet、SourceStatus、研究规则 | MtsSignal |
| DS-04 | AlertResolutionService | 提醒优先级与触发结果需要综合多个规则对象和当前信号结果 | AlertRule 集合、MtsSignal、价格条件 | AlertRuleTriggered / 状态更新 |
| DS-05 | LocalWorkspaceRecoveryService | 恢复跨越自选、提醒和布局多个对象，需要会话级协调 | 本地恢复集合、恢复策略 | LocalWorkspaceRestored |

### State Machines

| StateMachine-ID | Entity / Aggregate | From State | To State | Trigger Command / Event | Actor | Preconditions | Invalid Transitions |
|-----------------|--------------------|------------|----------|-------------------------|-------|---------------|---------------------|
| STM-01 | WatchSymbol | `draft_added` | `active` | CMD-01 | 用户 | 市场可识别且支持 | `draft_added -> archived` |
| STM-02 | WatchSymbol | `active` | `archived` | CMD-02 | 用户 | 当前处于 active | `archived -> archived` |
| STM-03 | WatchSymbol | `archived` | `active` | CMD-03 | 用户 | 目标可恢复 | `archived -> draft_added` |
| STM-04 | MarketDataSource | `available` | `degraded` / `unavailable` | EVT-05 | 系统 | 来源失败或覆盖不足 | 无来源变化却直接宣称 degraded |
| STM-05 | IndicatorSet / ObservationSession | `ready` | `partial` / `unavailable` | CMD-06 | 系统 | 数据不足或来源降级 | 在 `insufficient` 下维持 `ready` |
| STM-06 | MtsSignal | `data_insufficient` | `interpretable/watch|confirmed|strong|risk` | CMD-07 | 系统 | 数据与来源达到可解释条件 | `data_insufficient -> strong` without readiness |
| STM-07 | AlertRule | `enabled:idle` | `enabled:triggered` | CMD-10 | 系统 | 命中条件 | `disabled -> triggered` |
| STM-08 | AlertRule | `enabled:triggered` | `enabled:acknowledged` | CMD-09 | 用户 | 用户确认已触发提醒 | `disabled -> acknowledged` |
| STM-09 | ChartLayout | `default` | `customized` | CMD-05 | 用户 | 当前有可切换副图 | 无副图却进入 customized |
| STM-10 | AlertRule | `enabled` | `suspended_by_archive` | EVT-02 | 系统 | 绑定 WatchSymbol 已归档 | `suspended_by_archive -> triggered` |
| STM-11 | AlertRule | `suspended_by_archive` | `enabled` / `disabled` | EVT-03 | 系统 | 绑定 WatchSymbol 已恢复 | 丢失用户归档前启停意图 |

---

## Rules & Constraints

### Permission Matrix

| Actor | Command | Target Aggregate / Entity | State | Allowed | Reason / Rule | Audit Required |
|-------|---------|---------------------------|-------|---------|---------------|----------------|
| 用户 | CMD-01 AddWatchSymbol | AGG-01 / WatchSymbol | 市场可识别 | yes | 用户必须能主动管理观察对象 | no |
| 用户 | CMD-02 ArchiveWatchSymbol | AGG-01 / WatchSymbol | `active` | yes | 归档是产品授权的观察退出方式 | yes |
| 用户 | CMD-03 RestoreWatchSymbol | AGG-01 / WatchSymbol | `archived` | yes | 恢复是连续使用的重要语义 | yes |
| 用户 | CMD-05 SwitchSecondaryIndicator | AGG-02 / ChartLayout | 当前可观察 | yes | 允许切换分析维度，但不改变主图上下文 | no |
| 用户 | CMD-08 CreateAlertRule | AGG-03 / AlertRule | WatchSymbol `active` | yes | 用户必须能创建本地提醒 | yes |
| 用户 | CMD-09 UpdateAlertRuleState | AGG-03 / AlertRule | 规则存在 | yes | 用户必须能启停或确认提醒 | yes |
| 系统 | CMD-06 RefreshObservationContext | AGG-02 | WatchSymbol `selected` | yes | 系统维护观察上下文新鲜度与可解释性 | yes |
| 系统 | CMD-07 EvaluateMtsSignal | AGG-03 / MtsSignal | 上下文已刷新 | yes | 系统负责形成解释性信号对象 | yes |
| 系统 | CMD-10 ResolveAlertOutcome | AGG-03 / AlertRule | 规则 enabled | yes | 系统负责提醒触发与优先级排序 | yes |
| 系统 | CMD-11 RestoreLocalWorkspace | BC-05 | 存在本地恢复数据 | yes | 系统负责恢复连续使用体验 | yes |
| 系统 | CMD-10 ResolveAlertOutcome | AGG-03 / AlertRule | `suspended_by_archive` | no | 归档标的的提醒只保留记录，不允许触发 | yes |
| 用户 / 系统 | 任意交易执行动作 | 无交易目标对象，第一阶段仅允许观察和提醒 | 任意 | no | 自动交易不在产品授权范围内 | 不进入本次产品定义的审计能力 |

### Exception / Compensation / Idempotency

| Case-ID | Case | Trigger | Expected Handling | Idempotency / Conflict Rule | Trace |
|---------|------|---------|-------------------|-----------------------------|-------|
| EXC-01 | 市场不可识别 | 用户新增自选时代码无法归属到支持市场 | 拒绝进入 active 集合，并返回“无法识别或不在支持范围”语义 | 相同失败输入重复提交，结果应一致 | BUC-01-S02 |
| EXC-02 | 重复添加同一归一标的 | 用户再次添加同一市场内同一归一代码 | 恢复或聚合同一 WatchSymbol，而不是制造重复对象 | AddWatchSymbol 对同一 identity 幂等 | INV-02 |
| EXC-03 | 数据不足 | 历史长度不足以支撑全部指标或 MTS | 价格可展示，但 IndicatorSet / MtsSignal 必须降级 | 相同输入数据下，不得一会儿 ready 一会儿 insufficient | BUC-02-S02, BUC-04-S04 |
| EXC-04 | 来源降级 | 正式来源失败、覆盖不足或刷新失败 | 切换 SourceStatus，并传播给下游对象的可信度状态 | 相同来源状态下，降级语义应稳定一致 | BUC-07 |
| EXC-05 | archived 标的存在提醒 | 用户归档 WatchSymbol 或恢复其观察状态 | 相关 AlertRule 进入 `suspended_by_archive`，不再触发；恢复标的后按用户原先 enabled / disabled 意图恢复 | Archive/Restore 对提醒状态转换应可重复推导，且不得物理删除提醒记录 | RULE-02, INV-10 |
| EXC-06 | 本地恢复信息不完整 | 浏览器重开时只能恢复部分对象 | 至少回到默认布局和可识别自选 / 提醒状态，不允许进入不可用死状态 | RestoreLocalWorkspace 多次执行不应持续破坏现有有效状态 | FR-05 |

### Compliance / Security / Audit

| Rule-ID | Rule | Applies To | Evidence / Audit Requirement | Trace |
|---------|------|------------|------------------------------|-------|
| AUD-01 | 不得输出收益承诺、确定性投资建议或自动交易动作 | MtsSignal、AlertRule、任何页面文案 | 页面审查、验收清单必须证明提醒仅服务观察与风控 | Mission Constraint, NFR-04 |
| AUD-02 | 来源降级必须可审计到“何时降级、为何降级、哪些对象被降级” | MarketDataSource、ObservationSession、MtsSignal、AlertRule | 降级场景需有状态变更证据 | BR-005, FR-06 |
| AUD-03 | 用户操作引起的归档、恢复、提醒启停和因归档暂停需要可追溯 | WatchSymbol、AlertRule | 验收需能证明状态变化前后可识别，且归档期间提醒不触发 | FR-01, FR-04, FR-05, INV-10 |
| AUD-04 | 分数带只用于排序和提醒强度，不得被重新解释为概率表达 | MtsSignal | 页面和说明不得出现收益概率、胜率等暗示 | BR-009 |

---

## Traceability

| Product Requirement / Scenario | Domain Element | Element Type | Why It Covers the Requirement |
|--------------------------------|----------------|--------------|-------------------------------|
| FR-01 / SCN-01 | AGG-01, CMD-01, CMD-02, CMD-03, INV-01, INV-02, INV-03 | Aggregate / Command / Invariant | 覆盖市场识别、代码归一、active/archived 语义和可恢复性 |
| FR-02 / SCN-02 | AGG-02, CMD-04, CMD-05, CMD-06, INV-04, INV-06, POL-02 | Aggregate / Command / Invariant / Policy | 覆盖默认看盘布局、副图切换和默认布局回退 |
| FR-03 / SCN-03 | AGG-03, CMD-07, VO-05, VO-06, INV-07, INV-08, POL-03 | Aggregate / Command / Value Object / Policy | 覆盖 MTS 分数带、信号类型、理由和解释边界 |
| FR-04 / BUC-05 | CMD-08, CMD-09, CMD-10, ENT-02, INV-09, INV-10, POL-04 | Command / Entity / Invariant / Policy | 覆盖提醒创建、启停、归档暂停、触发与风控优先级 |
| FR-05 / BUC-06 | BC-05, CMD-11, DS-05, POL-02, EXC-05, EXC-06 | Context / Command / Service / Exception / Policy | 覆盖本地恢复、归档提醒恢复与至少回到可用默认路径 |
| FR-06 / SCN-05 | ENT-03, VO-08, EVT-05, POL-05, EXC-04 | Entity / Value Object / Event / Policy | 覆盖来源降级语义及其对可解释性的传播 |
| AC-01 / BUC-01 | AGG-01, CMD-01, INV-01, INV-02 | Aggregate / Command / Invariant | 覆盖四市场自选、代码归一和 active 集合准入 |
| AC-02 / BUC-02 | AGG-02, CMD-04, CMD-05, INV-04, POL-02 | Aggregate / Command / Policy | 覆盖默认主图、成交量常驻和副图切换 |
| AC-03 / BUC-04 | AGG-03, CMD-07, VO-05, VO-06, INV-07 | Aggregate / Command / Value Object / Invariant | 覆盖趋势状态、分数带、信号类型和提醒等级 |
| AC-04 / BUC-04-S03 | VO-06, POL-03, INV-07 | Value Object / Policy / Invariant | 覆盖趋势破坏、动量衰竭、风控止损三类风险语义 |
| AC-05 / BUC-06-S01 | BC-05, CMD-11, EVT-08 | Context / Command / Event | 覆盖浏览器重开后的恢复闭环 |
| RULE-01 | INV-01, CMD-01 | Invariant / Command | 自选标的必须归属于已支持市场并保留原始代码与归一代码 |
| RULE-02 | INV-03, INV-10, CMD-02, CMD-03, CMD-11, EXC-05 | Invariant / Command / Exception | 自选、提醒和基础上下文必须能本地恢复；归档标的提醒暂停且恢复后按原启停意图恢复 |
| RULE-03 | INV-05, EXC-03 | Invariant / Exception | 历史数据不足时可以展示价格，但不得产出伪造指标或 MTS 结论 |
| RULE-04 | POL-05, EXC-04, AUD-02 | Policy / Exception / Audit | 来源降级必须显式显示正式 / 演示 / 降级语义 |
| RULE-05 | INV-06, POL-02 | Invariant / Policy | 默认布局必须包含主图、成交量常驻和一个可切换副图 |
| RULE-06 | AUD-01, AUD-04, INV-08 | Audit Rule / Invariant | 指标与 MTS 只能服务解释与提醒，不得被包装成收益承诺 |
| RULE-07 | VO-05, VO-06, INV-07 | Value Object / Invariant | MTS 必须同时表达趋势状态、分数带、信号类型和提醒等级 |
| RULE-08 | VO-06, POL-03, INV-07 | Value Object / Policy / Invariant | 买点和风险类型必须分类型呈现 |
| RULE-09 | POL-04, INV-09, VO-07 | Policy / Invariant / Value Object | 提醒必须保持四级语义，且风控优先级最高 |
| RULE-10 | INV-08, AUD-01 | Invariant / Audit Rule | Legacy composite signal 不得作为正式 MTS 产品语义 |
| NFR-01 | VO-05, VO-06, AUD-01 | Value Object / Audit Rule | 解释性由结构化信号语义、理由和风险边界覆盖 |
| NFR-02 | BC-05, CMD-11, EVT-08 | Context / Command / Event | 连续性由本地恢复上下文覆盖 |
| NFR-03 | ENT-03, POL-05, EXC-04, AUD-02 | Entity / Policy / Exception / Audit Rule | 降级透明性由来源状态和传播规则覆盖 |
| NFR-04 | AUD-01, AUD-04 | Audit Rule | 范围合规由禁止收益承诺、确定性建议和自动交易动作覆盖 |
| NFR-05 | Context Map, Downstream Guidance | Context Boundary / Guidance | 可替换性约束由来源层边界和下游选型约束覆盖 |
| NFR-06 | DS-03, DS-04, INV-07, INV-09 | Domain Service / Invariant | 确定性由 MTS 与提醒结果的同输入同输出边界覆盖 |

---

## Downstream Guidance

| Consumer | Must Preserve / Consume | Source Domain Element | Notes |
|----------|--------------------------|-----------------------|-------|
| interaction | 自选状态、默认布局、副图切换、MTS 信息层级、四级提醒、来源降级语义 | AGG-01, AGG-02, AGG-03, STM-01~STM-09, POL-02~POL-05 | 原型必须回答恢复粒度、来源状态信息密度和 MTS 理由分层 |
| solution | 限界上下文、上下游关系、来源降级传播、可替换来源层边界 | BC-01~BC-05, Context Map, POL-05, AUD-02 | 只可把“优先评估成熟开源库/供应商”作为选型约束，不得回写到产品模型里 |
| technical_analysis | 聚合边界、命令、事件、不变量、例外处理、幂等要求 | AGG-01~AGG-03, CMD-01~CMD-11, EVT-01~EVT-08, INV-01~INV-09, EXC-01~EXC-06 | 必须保证 deterministic 结果链路；不得把 LegacyCompositeSignal 冒充正式 MTS |
| breakdown / test | GWT 可映射的状态迁移、权限、降级、恢复与优先级 | STM-01~STM-09, Permission Matrix, EXC-01~EXC-06 | 测试任务应优先覆盖自选恢复、MTS 不伪信号、风控优先级、来源降级透明化 |

---

## Open Questions & Modeling Risks

| Risk-ID | Question / Risk | Impact | Decision Needed By | Owner |
|---------|------------------|--------|--------------------|-------|
| RISK-01 | ChartLayout 恢复粒度未定：全局 / 市场 / 标的 / 混合 | 影响 BC-05 与 AGG-02 的边界、恢复语义和交互复杂度 | interaction / solution | 产品主流程 |
| RISK-02 | MarketDataSource 用户可见状态的枚举深度未定 | 影响 SourceStatus 词汇、页面信息密度和降级判断 | interaction / solution | 产品主流程 |
| RISK-03 | MTS `reason_codes` 与 `invalidators` taxonomy 尚未标准化 | 影响 VO-06、POL-03、测试样本和文案一致性 | solution / technical_analysis | 产品主流程 |
| RISK-04 | archived 的 WatchSymbol 与 AlertRule 的联动语义尚未最终定稿 | 影响 AGG-01 与 AGG-03 的状态耦合和恢复规则 | product-definition refine / interaction | 产品主流程 |
| RISK-05 | `project-context.md` 缺失、GitNexus 不可用、knowledge 多为 draft | 影响对历史上下文、棕地影响面和长期约束的置信度 | 主流程补证据后复核 | 主流程 |
