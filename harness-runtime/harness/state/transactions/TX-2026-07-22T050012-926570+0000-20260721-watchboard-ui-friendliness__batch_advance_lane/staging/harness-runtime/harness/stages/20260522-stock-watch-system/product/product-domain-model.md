# Product Domain Model: MyInvestment 本地多市场看盘工作台

> **来源**：prd 技能 → `harness-runtime/harness/stages/20260522-stock-watch-system/product/product-domain-model.md`  
> **用途**：按 DDD 方法沉淀产品领域模型。本文定义业务语义、边界、规则、状态和行为契约，不定义数据库、接口、框架、缓存、队列或部署方案。

**mission-id:** `20260522-stock-watch-system`  
**Status:** `rewritten-for-open-source-reference`

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/prd.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本文件提供产品领域模型解释。

## Domain Intent

| Item | Content | Trace |
|---|---|---|
| Business Problem | 用户缺少一个本地、可持续、可信度透明的跨市场看盘工作台 | Mission Objective, SCN-01~SCN-07 |
| Product Capability | 多市场自选、归一预览、PriceSeries 看盘、指标切换、MTS 解释、本地提醒、来源健康、本地恢复、布局模式 | FR-01~FR-09 |
| Non-Goals | 自动交易、收益承诺、账号/云同步、外部推送、完整基本面、组合管理、完整回测、直接复制 AGPL 代码 | SD-13~SD-21 |
| Modeling Depth | complex | 涉及多个业务对象、双状态机、降级传播、布局恢复、金融风险文案和 fixture-first 验证 |

## Strategic DDD

### Domain / Subdomain

| Type | Name | Why It Exists | Core / Supporting / Generic | Trace |
|---|---|---|---|---|
| Domain | 本地多市场看盘工作台 | 统一自选、图表、MTS、提醒、来源和恢复 | Core | Mission Objective |
| Subdomain | 自选身份与市场归一 | 维护 WatchSymbol 与 Market，处理歧义和归档恢复 | Core | FR-01, FR-02 |
| Subdomain | 看盘观察与指标解释 | 管理 PriceSeries、IndicatorSet、OHLC 读数和副图切换 | Core | FR-03 |
| Subdomain | MTS 与本地提醒 | 管理解释性 MTS、提醒 taxonomy、触发历史和风控优先级 | Core | FR-04, FR-05 |
| Subdomain | 来源健康与降级传播 | 管理 formal/demo/stale/unavailable，并影响下游解释 | Supporting | FR-06 |
| Subdomain | 本地连续使用与布局 | 管理 ChartLayout、dense/focus/mobile_tab 和恢复 | Supporting | FR-07, FR-08 |
| Subdomain | 验收样本与可验证性 | 为核心路径提供 fixture-first 输入 | Supporting | FR-09 |

### Bounded Contexts

| Context-ID | Context Name | Responsibility | In Language | Out of Boundary |
|---|---|---|---|---|
| BC-01 | Watchlist Context | 自选标的、市场归一、active/archived、列表摘要 | 自选、市场、原始代码、归一代码、归档、来源摘要 | 行情源协议、指标计算实现 |
| BC-02 | Observation Context | PriceSeries、主图/成交量/副图、OHLC/指标读数 | 行情序列、主图、成交量、副图、读数、数据不足 | MTS 策略、提醒规则 |
| BC-03 | Signal & Alert Context | MTS、AlertRule taxonomy、触发历史、确认与风控优先级 | 趋势状态、分数带、技术提醒、触发理由、确认 | 自动交易、收益承诺、外部推送 |
| BC-04 | Source Health Context | 来源健康、刷新、降级、stale、重试语义 | formal、demo_fallback、stale、unavailable、降级原因 | 具体供应商接入和保存细节 |
| BC-05 | Workspace Layout Context | ChartLayout、dense/focus/mobile_tab、恢复策略 | 工作台、布局模式、移动 tab、恢复 | 图表库内部面板能力、拖拽算法 |
| BC-06 | Verification Context | 冻结样本和可回放验收输入 | 四市场样本、歧义样本、降级样本、恢复样本 | 具体测试框架实现 |

### Context Map

| Upstream Context | Relationship | Downstream Context | Contract / Translation Rule | Risk |
|---|---|---|---|---|
| BC-01 Watchlist | customer_supplier | BC-02 Observation | 只有 active 且市场明确的 WatchSymbol 才进入观察 | 歧义写入会污染后续所有判断 |
| BC-04 Source Health | upstream guardrail | BC-02 Observation | 来源健康翻译为 PriceSeries 的 formal/demo/stale/unavailable | 若只做视觉 notice，会误导图表解释 |
| BC-02 Observation | customer_supplier | BC-03 Signal & Alert | MTS 和提醒只能消费同一标的的 PriceSeries 与 IndicatorSet | 数据不足会产生伪信号 |
| BC-04 Source Health | upstream guardrail | BC-03 Signal & Alert | demo/stale/unavailable 必须降低 MTS/提醒可解释性 | 风险提醒可能被误读为正式数据结论 |
| BC-05 Workspace Layout | supporting | BC-01/BC-02/BC-03/BC-04 | 布局只组织已授权对象，不新增交易/组合对象 | 过度布局化可能偷渡复杂终端能力 |
| BC-06 Verification | supporting | All | 每个核心 BUC 都必须能由 fixture 或截图证明 | live 行情不稳定导致证据不可复现 |

### Ubiquitous Language

| Term | Definition in This Context | Forbidden Ambiguity | Source |
|---|---|---|---|
| WatchSymbol | 用户主动维护的本地观察标的 | 不等于持仓、订单或行情序列 | BO-001 |
| Market | 市场分组与代码归一语义 | 不等于数据供应商 | BO-002 |
| PriceSeries | 某标的某周期的 OHLCV 序列和最新价摘要 | 不再用单条 PriceBar 代表产品语义 | BO-003 |
| IndicatorSet | 主图/成交量/副图指标组合与读数状态 | 不等于图表库配置 | BO-004 |
| MtsSignal | 技术提醒解释对象 | 不等于买卖指令、胜率或收益预测 | BO-005 |
| AlertRule | 本地提醒规则与触发历史 | 不等于外部推送渠道 | BO-006 |
| MarketDataSource | 用户可见来源健康状态 | 不等于具体来源接入方式 | BO-007 |
| ChartLayout | 工作台布局模式与恢复状态 | 不等于图表库内部面板能力 | BO-008 |

### Capability Boundary

| Capability-ID | Capability | Added / Changed / Removed / Reused | Boundary Rule | Trace |
|---|---|---|---|---|
| CAP-01 | 多市场自选与歧义预览 | Added | 只覆盖 US/HK/CN/KR；新增市场需决策 | FR-01 |
| CAP-02 | 自选列表摘要 | Added | 摘要来自 PriceSeries/Source Health，不伪造 | FR-02 |
| CAP-03 | 默认看盘与指标切换 | Added | 定义产品视图，不锁图表实现 | FR-03 |
| CAP-04 | MTS 解释卡 | Added | 技术提醒，不是交易建议 | FR-04 |
| CAP-05 | 本地提醒 taxonomy | Added | 本地触发历史，不做外部推送 | FR-05 |
| CAP-06 | 来源健康与降级穿透 | Added | 来源状态必须影响解释可信度 | FR-06 |
| CAP-07 | 本地恢复与布局模式 | Added | 同一浏览器内恢复，不做云同步 | FR-07, FR-08 |
| CAP-08 | Fixture-first 验收输入 | Added | live 行情不作为门禁 | FR-09 |

## Tactical DDD

### Actors

| Actor-ID | Actor / Role | Goal | Allowed Contexts |
|---|---|---|---|
| ACT-01 | 个人投资者 | 管理四市场自选并持续看盘 | BC-01, BC-02, BC-05 |
| ACT-02 | 技术分析用户 | 读取图表、OHLC、指标和布局 | BC-02, BC-05 |
| ACT-03 | 研究驱动用户 | 解读 MTS、管理提醒和风险 | BC-03, BC-04 |
| ACT-04 | 本地使用者 | 重开浏览器继续使用 | BC-01, BC-03, BC-05 |
| ACT-05 | 系统 | 刷新来源、更新 PriceSeries、评估 MTS、解析提醒 | BC-02, BC-03, BC-04 |
| ACT-06 | 验证者 | 用冻结样本证明 AC | BC-06 |

### Aggregates

| Aggregate-ID | Aggregate | Aggregate Root | Consistency Boundary | Invariants Owned |
|---|---|---|---|---|
| AGG-01 | Watchlist Aggregate | WatchSymbol | 标的市场身份、active/archived、列表摘要引用 | INV-01~INV-04 |
| AGG-02 | Observation Aggregate | ObservationSession（概念根） | 同一标的的 PriceSeries、IndicatorSet、SourceStatus 可解释性 | INV-05~INV-08 |
| AGG-03 | Signal & Alert Aggregate | AlertRuleSet（概念根） | MTS、AlertRule taxonomy、触发历史、风控优先级 | INV-09~INV-14 |
| AGG-04 | Workspace Aggregate | ChartLayout | dense/focus/mobile_tab 与恢复一致性 | INV-15~INV-17 |

### Entities

| Entity-ID | Entity | Identity | Lifecycle | Aggregate |
|---|---|---|---|---|
| ENT-01 | WatchSymbol | `market + normalized_symbol` | `active <-> archived` | AGG-01 |
| ENT-02 | MarketDataSource | `source_name + health_status` | `formal/demo_fallback/stale/unavailable` + retry | AGG-02 |
| ENT-03 | MtsSignal | `symbol + timeframe_bundle + evaluated_at` | `data_insufficient/interpretable` + alert level | AGG-03 |
| ENT-04 | AlertRule | `rule_id` | `enabled/disabled/suspended_by_archive` + `idle/triggered/acknowledged` | AGG-03 |
| ENT-05 | ChartLayout | `workspace + layout_scope` | `dense/focus/mobile_tab` + `default/customized/restored` | AGG-04 |

### Value Objects

| ValueObject-ID | Value Object | Attributes | Equality / Validation Rule | Used By |
|---|---|---|---|---|
| VO-01 | SymbolCode | raw_symbol, normalized_symbol, market | raw 与 normalized 必须同时保留 | WatchSymbol |
| VO-02 | PriceSeriesWindow | timeframe, bars_window, latest_ohlc, latest_price, change_percent | 同一 symbol/timeframe/source 下可比较 | ObservationSession |
| VO-03 | IndicatorReading | indicator_name, params, value, status | status 必须与数据充分性一致 | IndicatorSet |
| VO-04 | MtsExplanation | trend_state, score_band, signal_type, alert_level, reason_codes, invalidators | 不允许空原因的有效 MTS | MtsSignal |
| VO-05 | AlertCondition | taxonomy, threshold_or_signal, schedule, level | taxonomy 限定在 PRD 范围内 | AlertRule |
| VO-06 | SourceHealth | health_status, last_refreshed_at, degradation_reason, retry_state | 必须区分 formal/demo/stale/unavailable | MarketDataSource |
| VO-07 | LayoutMode | dense, focus, mobile_tab, active_tab | 移动端不能强制使用桌面三栏 | ChartLayout |

### Domain Commands

| Command-ID | Command | Actor / System | Target Aggregate | Preconditions | Result |
|---|---|---|---|---|---|
| CMD-01 | PreviewSymbolNormalization | 用户/系统 | AGG-01 | 用户输入代码和市场候选 | 返回市场 + 原始代码 + 归一代码或歧义状态 |
| CMD-02 | AddWatchSymbol | 用户 | AGG-01 | 归一结果明确 | WatchSymbol active |
| CMD-03 | ArchiveWatchSymbol | 用户 | AGG-01/AGG-03 | WatchSymbol active | WatchSymbol archived，提醒 suspended_by_archive |
| CMD-04 | RestoreWatchSymbol | 用户 | AGG-01/AGG-03 | WatchSymbol archived | WatchSymbol active，提醒恢复原启停意图 |
| CMD-05 | OpenWorkbench | 用户 | AGG-02/AGG-04 | WatchSymbol active | 打开默认或恢复后的 ChartLayout |
| CMD-06 | SwitchSecondaryIndicator | 用户 | AGG-02 | 当前 PriceSeries 可展示 | IndicatorSet customized |
| CMD-07 | RefreshSourceHealth | 系统 | AGG-02 | 已选中标的 | 更新 SourceHealth 与 PriceSeries 状态 |
| CMD-08 | EvaluateMtsSignal | 系统 | AGG-03 | Observation 可解释或已知不可解释 | 产生 MtsSignal 或 data_insufficient |
| CMD-09 | CreateAlertRule | 用户 | AGG-03 | WatchSymbol active；condition 合法 | 新建 AlertRule |
| CMD-10 | ResolveAlertTrigger | 系统 | AGG-03 | 新 PriceSeries/MtsSignal 或定时条件 | 更新 triggered/acknowledged 状态 |
| CMD-11 | AcknowledgeAlert | 用户 | AGG-03 | AlertRule triggered | AlertRule acknowledged |
| CMD-12 | SwitchLayoutMode | 用户/系统 | AGG-04 | 工作台可用 | ChartLayout dense/focus/mobile_tab |
| CMD-13 | RestoreLocalWorkbench | 系统 | AGG-01/AGG-03/AGG-04 | 本地存在可恢复快照 | 恢复工作台或回到默认布局 |

### Domain Events

| Event-ID | Event | Raised By | Meaning | Consumers / Follow-up |
|---|---|---|---|---|
| EVT-01 | SymbolNormalizationPreviewed | CMD-01 | 归一结果或歧义状态已形成 | UI 显示预览/错误 |
| EVT-02 | WatchSymbolAdded | CMD-02 | 标的进入 active | 工作台可打开，提醒可创建 |
| EVT-03 | WatchSymbolArchived | CMD-03 | 标的归档 | AlertRule suspended_by_archive |
| EVT-04 | WatchSymbolRestored | CMD-04 | 标的恢复 | AlertRule 恢复原意图 |
| EVT-05 | WorkbenchOpened | CMD-05 | 工作台进入当前标的上下文 | 刷新来源和观察上下文 |
| EVT-06 | SourceHealthChanged | CMD-07 | 来源变为 formal/demo/stale/unavailable | 降级传播给图表/MTS/提醒 |
| EVT-07 | IndicatorSelectionChanged | CMD-06 | 副图指标变化 | 更新布局与读数 |
| EVT-08 | MtsSignalEvaluated | CMD-08 | MTS 结果形成 | 提醒解析 |
| EVT-09 | AlertRuleTriggered | CMD-10 | 提醒命中 | 本地触发历史记录 |
| EVT-10 | AlertAcknowledged | CMD-11 | 用户确认提醒 | 更新触发状态 |
| EVT-11 | LayoutModeChanged | CMD-12 | 布局模式变化 | 本地恢复快照更新 |
| EVT-12 | LocalWorkbenchRestored | CMD-13 | 本地工作台恢复完成 | 首屏可用 |

### Invariants

| Invariant-ID | Invariant | Aggregate / Context | Commands Protected | Failure Behavior | Trace |
|---|---|---|---|---|---|
| INV-01 | WatchSymbol 必须有明确 Market、raw_symbol、normalized_symbol | AGG-01 | CMD-01, CMD-02 | reject | FR-01 |
| INV-02 | 歧义输入未确认前不得进入 active | AGG-01 | CMD-02 | reject | FR-01 |
| INV-03 | 同市场同归一代码不能形成重复 active 标的 | AGG-01 | CMD-02 | merge/restore | BUC-01 |
| INV-04 | archived 不等于物理删除 | AGG-01 | CMD-03, CMD-04 | preserve | FR-02, FR-07 |
| INV-05 | PriceSeries 的 source_mode 必须来自 MarketDataSource | AGG-02 | CMD-07 | reject/downgrade | FR-06 |
| INV-06 | 数据不足时 IndicatorSet 不得显示 ready | AGG-02 | CMD-06, CMD-07 | downgrade | FR-03 |
| INV-07 | OHLC/指标读数必须可读，不只依赖颜色 | AGG-02 | CMD-05, CMD-06 | hold UI | FR-03 |
| INV-08 | 默认工作台必须能回到主图 + 成交量 + 副图 | AGG-02/AGG-04 | CMD-05, CMD-13 | compensate to default | FR-03, FR-07 |
| INV-09 | MtsSignal 有效时必须包含 trend_state、score_band、signal_type、alert_level、reason_codes、invalidators | AGG-03 | CMD-08 | reject incomplete signal | FR-04 |
| INV-10 | MTS score 不得解释为胜率或收益概率 | AGG-03 | CMD-08 | reject wording | NFR-02 |
| INV-11 | AlertRule taxonomy 必须在 PRD 允许集合内 | AGG-03 | CMD-09 | reject | FR-05 |
| INV-12 | AlertRule 启停状态与触发状态必须分离 | AGG-03 | CMD-09, CMD-10, CMD-11 | reject inconsistent state | FR-05 |
| INV-13 | 风控提醒优先于观察类提醒 | AGG-03 | CMD-10 | prioritize risk | FR-04, FR-05 |
| INV-14 | suspended_by_archive 的提醒不得触发 | AGG-03 | CMD-10 | suppress trigger | FR-05, FR-07 |
| INV-15 | 桌面 dense/focus 与移动 mobile_tab 是不同布局模式 | AGG-04 | CMD-12 | reject invalid layout | FR-08 |
| INV-16 | 布局恢复失败时必须回到可用默认布局 | AGG-04 | CMD-13 | compensate | FR-07 |
| INV-17 | 本地恢复不得要求账号、云同步或多用户数据库 | BC-05 | CMD-13 | reject scope expansion | NFR-04 |

### Policies

| Policy-ID | Policy | Trigger | Decision Inputs | Outcome | Trace |
|---|---|---|---|---|---|
| POL-01 | MarketNormalizationPolicy | CMD-01 | raw_symbol, market候选, 支持市场集合 | 归一预览或歧义阻断 | FR-01 |
| POL-02 | SourceHealthPropagationPolicy | EVT-06 | SourceHealth, PriceSeries, current MTS/alerts | 下游解释降级 | FR-06 |
| POL-03 | IndicatorReadinessPolicy | CMD-06/CMD-07 | PriceSeries 长度、source_mode、指标参数 | ready/partial/unavailable | FR-03 |
| POL-04 | MtsInterpretationPolicy | CMD-08 | PriceSeries、IndicatorSet、SourceHealth | MtsSignal 或 data_insufficient | FR-04 |
| POL-05 | AlertPriorityPolicy | CMD-10 | AlertRule 集合、MTS、PriceSeries | 风控优先，记录触发历史 | FR-05 |
| POL-06 | ArchiveSuspensionPolicy | EVT-03/EVT-04 | WatchSymbol 状态、AlertRule 原意图 | suspended_by_archive / 恢复 | FR-02, FR-05 |
| POL-07 | LayoutRecoveryPolicy | CMD-13 | 本地快照、设备类型、布局状态 | restored 或 default | FR-07, FR-08 |

### Domain Services

| Service-ID | Domain Service | Why Not Entity-Owned | Inputs | Output / Event |
|---|---|---|---|---|
| DS-01 | SymbolNormalizationService | 跨 Market 规则，不属于单一 WatchSymbol | raw_symbol, Market | normalization preview |
| DS-02 | WorkbenchReadinessService | 需要 SourceHealth、PriceSeries、Layout 联合判断 | WatchSymbol, SourceHealth, ChartLayout | workbench state |
| DS-03 | MtsSignalInterpretationService | 需要 PriceSeries、IndicatorSet、研究规则和来源状态 | PriceSeries, IndicatorSet, SourceHealth | MtsSignal |
| DS-04 | AlertResolutionService | 需要多个 AlertRule 和当前 PriceSeries/MTS | AlertRules, PriceSeries, MtsSignal | AlertRuleTriggered |
| DS-05 | LocalWorkbenchRecoveryService | 跨自选、提醒、触发历史、布局 | local snapshot | LocalWorkbenchRestored |
| DS-06 | VerificationFixtureService（产品级） | 验收样本跨多个上下文 | frozen samples | evidence inputs |

### State Machines

| StateMachine-ID | Entity / Aggregate | From State | To State | Trigger | Invalid Transitions |
|---|---|---|---|---|---|
| STM-01 | WatchSymbol | none/archived | active | CMD-02/CMD-04 | ambiguity -> active |
| STM-02 | WatchSymbol | active | archived | CMD-03 | archived -> archived without no-op |
| STM-03 | MarketDataSource | formal | demo_fallback/stale/unavailable | CMD-07 | failure -> formal |
| STM-04 | IndicatorSet | ready | partial/unavailable | CMD-07 | insufficient -> ready |
| STM-05 | MtsSignal | data_insufficient | watch/confirm/strong_signal/risk | CMD-08 | insufficient -> strong_signal |
| STM-06 | AlertRule activation | enabled/disabled | suspended_by_archive | EVT-03 | suspended -> triggered |
| STM-07 | AlertRule trigger | idle | triggered | CMD-10 | disabled -> triggered |
| STM-08 | AlertRule trigger | triggered | acknowledged | CMD-11 | idle -> acknowledged |
| STM-09 | ChartLayout | dense | focus | CMD-12 | mobile viewport forced dense |
| STM-10 | ChartLayout | any | mobile_tab | device/layout trigger | mobile_tab loses access to source/alerts |
| STM-11 | Workspace | default/customized | restored | CMD-13 | corrupt snapshot -> dead state |

## Rules & Constraints

### Permission Matrix

| Actor | Command | Target | State | Allowed | Reason / Rule | Audit Required |
|---|---|---|---|---|---|---|
| 用户 | CMD-01/CMD-02 | WatchSymbol | clear normalization | yes | 用户可管理自选 | yes |
| 用户 | CMD-03/CMD-04 | WatchSymbol + AlertRule | active/archived | yes | 归档/恢复是本地连续性一部分 | yes |
| 用户 | CMD-06 | IndicatorSet | workbench open | yes | 用户可切换副图指标 | no |
| 用户 | CMD-09/CMD-11 | AlertRule | active symbol / triggered alert | yes | 用户可创建和确认本地提醒 | yes |
| 用户 | CMD-12 | ChartLayout | workbench available | yes | 用户可切换布局模式 | no |
| 系统 | CMD-07/CMD-08/CMD-10/CMD-13 | Source/MTS/Alerts/Workspace | valid context | yes | 系统维护状态与解释 | yes |
| 用户/系统 | 自动交易动作 | 无交易执行对象 | 任意 | no | 不在 Mission 授权范围 | 不需要审计：本产品不创建交易执行对象 |
| 系统 | 外部通知发送 | AlertRule | 任意 | no | 第一阶段不集成外部推送 | 不需要审计：本产品只保留本地提醒 |

### Exception / Compensation / Idempotency

| Case-ID | Case | Trigger | Expected Handling | Idempotency / Conflict Rule | Trace |
|---|---|---|---|---|---|
| EXC-01 | 歧义代码 | CMD-01 | 停在预览/确认状态 | 重复输入结果一致 | BUC-01 |
| EXC-02 | 重复添加 | CMD-02 | 合并或恢复既有 WatchSymbol | 同 identity 幂等 | BUC-01 |
| EXC-03 | 数据不足 | CMD-07/CMD-08 | IndicatorSet partial，MTS data_insufficient | 同样本结果一致 | BUC-03/04 |
| EXC-04 | 来源 fallback | CMD-07 | SourceHealth demo_fallback 并传播 | 不伪装 formal | BUC-06 |
| EXC-05 | 来源 stale | CMD-07 | 保留旧数据并标明上次刷新 | 不伪装实时刷新成功 | BUC-06 |
| EXC-06 | 重试失败 | CMD-07 | 保留上次可解释状态并说明失败 | 页面不 crash | BUC-06 |
| EXC-07 | 归档标的有提醒 | CMD-03/CMD-04 | suspended_by_archive 并可恢复原意图 | 不丢规则 | BUC-01/05 |
| EXC-08 | 布局快照损坏 | CMD-13 | 回到默认 focus 日常看盘或设备等价默认 | 重复恢复不破坏状态 | BUC-07 |

### Compliance / Security / Audit

| Rule-ID | Rule | Applies To | Evidence / Audit Requirement | Trace |
|---|---|---|---|---|
| AUD-01 | 不得输出收益承诺、胜率或确定性投资建议 | MtsSignal、AlertRule、页面文案 | 文案审查 | NFR-02 |
| AUD-02 | 来源降级必须可见且可追溯 | MarketDataSource、PriceSeries、MtsSignal、AlertRule | 降级截图与状态断言 | NFR-03 |
| AUD-03 | 归档/恢复/提醒确认需保留本地状态语义 | WatchSymbol、AlertRule | 本地恢复验证 | FR-07 |
| AUD-04 | AGPL 项目仅作功能参考，不复制代码 | solution/execute | 选型与代码审查 | NFR-06 |

## Traceability

| Product Requirement / Scenario | Domain Element | Element Type | Why It Covers the Requirement |
|---|---|---|---|
| FR-01 / BUC-01 | CMD-01, CMD-02, INV-01, INV-02, POL-01 | Command / Invariant / Policy | 覆盖归一预览和歧义阻断 |
| FR-02 / BUC-01 | AGG-01, VO-02, VO-06, INV-04 | Aggregate / Value Object / Invariant | 覆盖列表摘要、归档和恢复 |
| FR-03 / BUC-02/03 | AGG-02, CMD-05, CMD-06, INV-06~INV-08 | Aggregate / Command / Invariant | 覆盖默认工作台、指标切换和读数 |
| FR-04 / BUC-04 | ENT-03, VO-04, CMD-08, INV-09, INV-10 | Entity / Value Object / Command / Invariant | 覆盖 MTS 解释卡和非投资建议边界 |
| FR-05 / BUC-05 | ENT-04, VO-05, CMD-09~CMD-11, INV-11~INV-14 | Entity / Value Object / Command / Invariant | 覆盖 taxonomy、触发历史、归档暂停 |
| FR-06 / BUC-06 | ENT-02, VO-06, CMD-07, POL-02 | Entity / Value Object / Command / Policy | 覆盖来源健康与降级穿透 |
| FR-07 / BUC-07 | CMD-13, DS-05, INV-16, INV-17 | Command / Service / Invariant | 覆盖本地恢复和默认布局补偿 |
| FR-08 / BUC-08 | ENT-05, VO-07, CMD-12, STM-09/10 | Entity / Value Object / Command / State Machine | 覆盖 dense/focus/mobile_tab |
| FR-09 / BUC-09 | DS-06, BC-06 | Domain Service / Context | 覆盖 fixture-first 验收输入 |
| AC-01 | CMD-01, CMD-02, INV-01, INV-02, POL-01 | Command / Invariant / Policy | 覆盖四市场自选、归一预览和歧义阻断 |
| AC-02 | AGG-02, AGG-04, CMD-05, CMD-06, INV-07, INV-08 | Aggregate / Command / Invariant | 覆盖默认工作台、图表 pane、指标切换和布局模式 |
| AC-03 | ENT-03, VO-04, CMD-08, INV-09, POL-04 | Entity / Value Object / Policy | 覆盖 MTS 趋势状态、分带、信号类型和解释原因 |
| AC-04 | ENT-03, ENT-04, INV-10, INV-13, POL-05 | Entity / Invariant / Policy | 覆盖风险提醒、提醒等级和风控优先级 |
| AC-05 | ENT-01, ENT-04, ENT-05, CMD-13, DS-05, INV-14, INV-16, INV-17 | Entity / Command / Service / Invariant | 覆盖本地恢复、自选归档、提醒状态和布局恢复 |
| RULE-01 | CMD-01, INV-01, INV-02 | Command / Invariant | 自选写入前必须有明确市场与归一结果 |
| RULE-02 | AGG-01, VO-02, VO-06 | Aggregate / Value Object | 自选列表摘要来自 PriceSeries 与 SourceHealth |
| RULE-03 | AGG-02, AGG-04, INV-08 | Aggregate / Invariant | 默认工作台必须有主图、成交量和副图 |
| RULE-04 | VO-02, VO-03, INV-07 | Value Object / Invariant | OHLC 与指标读数必须可读 |
| RULE-05 | ENT-03, VO-04, INV-09 | Entity / Value Object / Invariant | MTS 必须包含完整解释字段 |
| RULE-06 | INV-10, AUD-01 | Invariant / Audit Rule | MTS 与提醒不得越过投资建议边界 |
| RULE-07 | VO-05, INV-11 | Value Object / Invariant | 提醒 taxonomy 必须在允许集合内 |
| RULE-08 | ENT-04, INV-12 | Entity / Invariant | 提醒启停状态与触发状态必须分离 |
| RULE-09 | CMD-03, CMD-04, INV-14, POL-06 | Command / Invariant / Policy | 归档暂停提醒并可恢复 |
| RULE-10 | ENT-02, VO-06, POL-02, AUD-02 | Entity / Value Object / Policy / Audit Rule | 来源健康必须区分并传播降级语义 |
| RULE-11 | ENT-05, VO-07, CMD-12, INV-15 | Entity / Value Object / Command / Invariant | dense/focus/mobile_tab 布局模式受控 |
| RULE-12 | CMD-13, DS-05, INV-16, INV-17 | Command / Service / Invariant | 本地恢复失败时回到可用默认布局 |
| RULE-13 | INV-10, AUD-01 | Invariant / Audit Rule | Legacy 或旧信号不能替代正式 MTS 产品语义 |
| NFR-01 | VO-04, INV-09, AUD-01 | Value Object / Invariant / Audit Rule | 可解释性由 MTS 结构化字段和审计边界保证 |
| NFR-02 | INV-10, AUD-01 | Invariant / Audit Rule | 金融风险边界由禁止胜率、收益承诺和交易动作保证 |
| NFR-03 | ENT-02, VO-06, POL-02, AUD-02 | Entity / Policy / Audit Rule | 降级透明由来源健康与降级传播保证 |
| NFR-04 | CMD-13, DS-05, INV-17 | Command / Service / Invariant | 本地连续性不依赖账号或云同步 |
| NFR-05 | BC-06, DS-06 | Context / Domain Service | fixture-first 验证由独立验证上下文承载 |
| NFR-06 | AUD-04 | Audit Rule | 许可边界由开源参考不复制规则约束 |
| NFR-07 | ENT-05, VO-07, STM-09, STM-10 | Entity / Value Object / State Machine | 响应式可用由布局状态机约束 |
| NFR-08 | DS-03, DS-04, INV-09, INV-13 | Domain Service / Invariant | MTS 与提醒确定性由同输入同输出服务和不变量约束 |

## Downstream Guidance

| Consumer | Must Preserve / Consume | Source Domain Element | Notes |
|---|---|---|---|
| interaction | 归一预览、自选摘要、日常看盘工作台、MTS 卡、提醒 taxonomy、来源健康、focus/dense/mobile_tab | BUC-01~BUC-08, BO-001~BO-008 | 需要重新对齐旧 interaction 产物 |
| solution | PriceSeries、MarketDataSource、AlertRule 双状态机、ChartLayout 模式、fixture-first | BC-02~BC-06, INV-05~INV-17 | 旧 solution 必须重写或补丁对齐 |
| technical_analysis | 聚合、命令、事件、不变量、异常处理、状态机 | AGG-01~04, CMD-01~13, EVT-01~12 | 不得把 BO 降回旧 PriceBar / 简单提醒 |
| breakdown / test | GWT、状态迁移、source 降级、恢复和 fixture-first | BUC-01~BUC-09, EXC-01~08 | Decision Needed 未定前不得拆实现任务 |

## Open Questions & Modeling Risks

| Risk-ID | Question / Risk | Impact | Decision Needed By | Owner |
|---|---|---|---|---|
| RISK-01 | ChartLayout 恢复粒度未定 | 影响恢复键、验收样本和用户心智 | interaction / solution | 产品主流程 |
| RISK-02 | 移动端默认 tab 未定 | 影响移动端首屏与恢复默认值 | interaction | 产品主流程 |
| RISK-03 | 来源健康信息密度未定 | 影响 UI 密度与可信度表达 | interaction / solution | 产品主流程 |
| RISK-04 | MTS reason / invalidator taxonomy 未定 | 影响字段、文案和 fixture | solution / technical_analysis | 产品主流程 |
| RISK-05 | 提醒配置表单分组与默认排序未定 | 不影响五类提醒进入范围，但影响配置效率、移动端信息密度和验收截图组织 | interaction / solution | 产品主流程 |
| RISK-06 | PRD 回改晚于 solution | 若继续沿旧 solution 推进，会出现产品/方案错位 | solution 重对齐前 | 主流程 |
