# BO Registry

**mission-id:** `20260522-stock-watch-system`  
**stage:** PRD / Product Definition  
**artifact:** 业务对象注册表（BO Registry）  
**status:** draft  

## 输入与输入缺口

- 已消费输入：
  - `harness-runtime/harness/missions/20260522-stock-watch-system/mission-contract.md`
  - `harness-runtime/harness/work-graph/artifacts/REQ-STOCK-WATCH-SYSTEM/discovery-brief.md`
  - `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/discovery-brief.contract.yaml`
  - `docs/technical-signal-research-design.md`
  - `project-knowledge/_index.md`
  - `project-knowledge/context/overview.md`（draft）
  - `project-knowledge/context/constraints.md`（draft）
  - `project-knowledge/context/risks.md`（draft）
  - `project-knowledge/product/scope-boundaries.md`（draft）
- 输入缺口：
  - `harness-runtime/project-context.md` 缺失。已按 discovery contract 的补偿路径，仅把 `project-knowledge/context/*` 视为弱证据，不将其中 `init/draft` 内容当作定稿业务事实。
  - `project-knowledge/*` 当前多数仍为 `init/draft`，因此本文件以 mission contract、discovery brief、discovery contract 和技术信号研究为主证据。

## Registry Summary

| BO-ID | 标准名称 | 候选来源 | 处理结果 | 定义边界 | Spec 来源关系 | 下游提示 |
|---|---|---|---|---|---|---|
| BO-001 | WatchSymbol / 自选标的 | BO-CAND-001 | promote | 用户在本地看盘系统中主动维护、被持续观察的单个股票标的，不包含行情序列本身。 | adjusted：来自现有草稿对象，补足状态、关系与持久化语义。 | 必须进入 BUC：添加、删除、恢复、切换、关联提醒。 |
| BO-002 | Market / 市场 | BO-CAND-002 | promote | 承载市场分组、代码归一规则与交易语境的业务对象，不等同于数据源。 | existing：mission 与 discovery 均已定稿为 US/HK/CN/KR。 | 必须进入 BUC：跨市场分组、代码识别、归一失败处理。 |
| BO-003 | PriceBar / 价格条 | BO-CAND-003 | promote | 某标的在某周期上的单条 OHLCV 行情记录，是图表、指标、MTS 和提醒解释的共同输入。 | adjusted：已有实现与研究文档一致，但补足“数据充分性/来源状态”业务语义。 | 必须进入 AC：数据不足降级、demo 数据提示。 |
| BO-004 | IndicatorSet / 指标集 | BO-CAND-004 | promote | 针对某标的、某周期计算并展示的一组技术指标及其当前读数，不含供应商实现细节。 | adjusted：研究文档定义了类别与默认组合，需补足状态与解释边界。 | 必须进入原型：主图/副图切换、默认组合。 |
| BO-005 | MtsSignal / 多周期趋势信号 | BO-CAND-005 | promote | 对某标的当前趋势、买卖/风控语义和提醒强度的解释性结果对象，不是交易指令，也不是单一箭头。 | new：研究文档给出明确产品语义，现有代码尚未达到该语义。 | 必须进入 BUC/AC：趋势状态、买点类型、卖点类型、提醒等级。 |
| BO-006 | AlertRule / 提醒规则 | BO-CAND-006 | promote | 用户配置的本地提醒规则对象，绑定标的并依据价格或 MTS 条件触发观察、确认、强信号或风控提醒。 | adjusted：现有草稿已有价格/信号提醒，PRD 补足等级语义和停用规则。 | 必须进入 BUC：创建、启停、触发、恢复。 |
| BO-007 | MarketDataSource / 行情来源 | BO-CAND-007 | merge_and_promote | 面向产品语义的“当前行情来源声明”对象，承载来源身份、覆盖市场、数据状态、演示/正式模式与可用性，不讨论接口和适配器代码。 | new：由“DataProvider”去技术化重命名而来。 | 必须进入 AC：上游不可用时 demo 模式提示、来源状态展示。 |
| BO-008 | ChartLayout / 看盘布局 | BO-CAND-008 | promote | 用户可感知、可切换的看盘视图配置对象，承载主图/成交量/副图指标的布局与展示偏好，不等于图表库 pane API。 | new：研究文档与 discovery 已确认布局需求，现有粒度未定。 | 必须进入原型：默认布局、切换、是否恢复。 |

## BO Detail

### BO-001 WatchSymbol / 自选标的

- 定义：用户显式加入本地观察范围、可被分组、选择、排序和恢复的股票标的。
- 别名：自选标的、watchlist item。
- 核心边界：
  - 包含：市场归属、代码归一结果、显示名称、观察状态、排序/分组位置、与提醒和布局的引用关系。
  - 不包含：历史行情明细、指标数值、MTS 计算逻辑。
- 关键属性：
  - `market`
  - `raw_symbol`
  - `normalized_symbol`
  - `display_name`
  - `watch_status`
  - `sort_position`
  - `persistence_scope`（本地）
- 状态组：
  - 观察生命周期：`draft_added` -> `active` -> `archived`
  - 视图状态：`selected` / `unselected`
  - 数据状态：`data_ready` / `data_limited` / `data_unavailable`
- 关系：
  - 多个 WatchSymbol 属于一个 Market。
  - 一个 WatchSymbol 关联零到多个 AlertRule。
  - 一个 WatchSymbol 在查看时引用一组 PriceBar、一个 IndicatorSet、一个 MtsSignal。
  - 一个 WatchSymbol 可使用一个 ChartLayout；布局归属粒度待后续综合。
- 生命周期规则：
  - 默认不物理删除历史引用；移出自选应建模为 `archived`，以保证提醒记录和恢复语义可解释。
  - 持久化恢复后，`active` 标的必须保持原市场归属和归一代码。

### BO-002 Market / 市场

- 定义：对股票标的进行业务分组并决定代码归一语义的市场对象。
- 别名：MarketCode、市场。
- 核心边界：
  - 包含：市场标识、分组语义、代码格式规则、股票池归属。
  - 不包含：具体行情供应商或交易成本模型。
- 关键属性：
  - `market_code`（US/HK/CN/KR）
  - `display_label`
  - `ticker_normalization_rule`
  - `default_currency`（如后续产品需展示）
- 状态组：
  - 可用性：`supported` / `temporarily_unavailable`
- 关系：
  - 一个 Market 容纳多个 WatchSymbol。
  - 一个 Market 可被多个 MarketDataSource 覆盖。
- 生命周期规则：
  - 第一阶段支持集为 mission 已确认范围；新增市场属于范围变化，需走决策。

### BO-003 PriceBar / 价格条

- 定义：某一标的在某一观察周期上的单条 OHLCV 行情记录。
- 别名：OHLCV、K 线。
- 核心边界：
  - 包含：时间点、开高低收、成交量、所属周期、来源状态。
  - 不包含：指标结果、趋势判断、提醒等级。
- 关键属性：
  - `time`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
  - `timeframe`
  - `source_mode`（正式/演示）
- 状态组：
  - 数据充分性：`sufficient` / `insufficient`
  - 来源可信度：`live_or_formal` / `demo_fallback`
- 关系：
  - 多条 PriceBar 组成某个 WatchSymbol 某个周期的行情序列。
  - IndicatorSet 和 MtsSignal 都以 PriceBar 序列为输入。
- 生命周期规则：
  - 当历史长度不满足指标或 MTS 最小要求时，PriceBar 仍可展示，但下游对象必须进入降级状态，而不是伪造信号。

### BO-004 IndicatorSet / 指标集

- 定义：围绕某标的当前观察上下文计算出的技术指标集合及其展示组合。
- 别名：技术指标集、主图/副图指标。
- 核心边界：
  - 包含：指标名称、参数、当前读数、所属显示层（主图/副图）、默认组合与切换状态。
  - 不包含：图表库实现、公式代码细节、供应商数据接入细节。
- 关键属性：
  - `primary_indicators`（默认含 EMA20、EMA60、MA120、BOLL）
  - `secondary_indicator`（MACD / RSI / KDJ / ATR）
  - `parameter_profile`
  - `computation_status`
  - `interpretation_notes`
- 状态组：
  - 计算状态：`ready` / `partial` / `unavailable`
  - 展示状态：`default` / `customized`
- 关系：
  - 一个 IndicatorSet 依赖一个 WatchSymbol 的 PriceBar 序列。
  - 一个 IndicatorSet 为一个 MtsSignal 提供解释上下文。
  - 一个 ChartLayout 决定 IndicatorSet 的呈现位置和可见性。
- 生命周期规则：
  - 指标参数有默认值，但默认值不是收益承诺，也不是优化结论。
  - 数据不足时，IndicatorSet 可以局部可用，但必须显式标明哪些指标不可解释。

### BO-005 MtsSignal / 多周期趋势信号

- 定义：把趋势结构、动量变化、波动结构和成交量确认整合成可解释结果的业务对象。
- 别名：MTS、多周期趋势信号。
- 核心边界：
  - 包含：趋势状态、总分带、买点类型、卖点类型、提醒等级、触发理由、失效理由。
  - 不包含：自动交易动作、收益预测、黑箱模型输出。
- 关键属性：
  - `trend_state`（多头 / 震荡 / 空头 / 趋势修复中）
  - `score_band`（-100 到 100 的区间结果）
  - `entry_signal_type`（趋势回调买点 / 收敛突破买点 / none）
  - `exit_signal_type`（趋势破坏 / 动量衰竭 / 风控止损 / none）
  - `alert_level`（观察 / 确认 / 强信号 / 风控）
  - `reason_codes`
  - `invalidators`
- 状态组：
  - 信号成熟度：`watch` / `confirmed` / `strong` / `risk`
  - 数据可解释性：`interpretable` / `data_insufficient`
- 关系：
  - 一个 MtsSignal 依赖一个 WatchSymbol 的 PriceBar 序列和一个 IndicatorSet。
  - 一个 MtsSignal 可被多个 AlertRule 引用为触发条件。
- 生命周期规则：
  - MTS 是解释对象，不得退化成“买入/卖出”二元词。
  - 旧 `LegacyCompositeSignal` 不得直接冒充 MtsSignal；只能作为历史样例或回归素材。

### BO-006 AlertRule / 提醒规则

- 定义：用户在本地配置、用于接收观察/确认/强信号/风控提醒的规则对象。
- 别名：提醒规则、风控提醒。
- 核心边界：
  - 包含：绑定标的、触发条件、提醒等级、启停状态、最近触发结果。
  - 不包含：外部通知通道实现、推送服务实现。
- 关键属性：
  - `target_symbol`
  - `rule_type`（价格型 / 信号型）
  - `trigger_conditions`
  - `alert_level`
  - `enabled_status`
  - `last_triggered_at`
  - `trigger_reason`
- 状态组：
  - 启停状态：`enabled` / `disabled` / `suspended_by_archive`
  - 触发状态：`idle` / `triggered` / `acknowledged`
- 关系：
  - 一个 AlertRule 绑定一个 WatchSymbol。
  - 一个 AlertRule 可引用某个 MtsSignal 的状态或某个价格阈值。
- 生命周期规则：
  - 规则默认不因单次触发而失效；用户停用时进入 `disabled`。
  - 目标标的被归档时，绑定提醒进入 `suspended_by_archive`，保留记录但不得触发；目标标的恢复为 active 后，提醒按用户归档前的 enabled / disabled 意图恢复。
  - 风控类提醒优先级高于观察类提醒。

### BO-007 MarketDataSource / 行情来源

- 定义：系统当前使用的行情来源声明对象，用于向用户说明“这份行情来自哪里、覆盖哪些市场、当前是否为演示模式、是否可信可用”。
- 别名：行情来源、Data Provider、data source。
- 核心边界：
  - 包含：来源身份、覆盖市场、更新时间语义、来源模式、可用状态、降级原因。
  - 不包含：HTTP 接口、SDK、缓存策略、适配器类设计。
- 关键属性：
  - `source_name`
  - `coverage_markets`
  - `source_mode`（formal / demo）
  - `availability_status`
  - `freshness_note`
  - `degradation_reason`
- 状态组：
  - 模式状态：`formal` / `demo_fallback`
  - 可用状态：`available` / `degraded` / `unavailable`
- 关系：
  - 一个 MarketDataSource 可为多个 Market 和多个 WatchSymbol 提供 PriceBar。
  - MarketDataSource 的状态直接影响 PriceBar 的 `source_mode`，并间接影响 IndicatorSet、MtsSignal、AlertRule 的可信度解释。
- 生命周期规则：
  - discovery 阶段不得锁定唯一正式供应商；PRD 只定义“来源声明对象”，不预判最终供应商。
  - 当系统切到 demo_fallback 时，必须同步改变相关 PriceBar 和下游解释对象的展示语义。

### BO-008 ChartLayout / 看盘布局

- 定义：用户查看图表时的结构化展示偏好对象，描述主图、成交量和副图指标如何被组织与切换。
- 别名：Pane、图表布局、看盘布局。
- 核心边界：
  - 包含：默认视图、当前副图选择、面板组织、是否恢复上次布局等产品行为。
  - 不包含：图表库 pane 实现、拖拽算法、渲染性能方案。
- 关键属性：
  - `layout_name`
  - `primary_panel_config`
  - `volume_panel_presence`
  - `secondary_panel_selection`
  - `restore_policy`
- 状态组：
  - 布局状态：`default` / `customized`
  - 恢复状态：`session_only` / `restorable`
- 关系：
  - 一个 ChartLayout 影响一个 WatchSymbol 查看时的 IndicatorSet 呈现方式。
  - 一个用户会话至少有一个默认 ChartLayout。
- 生命周期规则：
  - 第一阶段至少存在一个默认布局：主图 + 成交量常驻 + 一个可切换副图。
  - 是否按“全局/市场/标的”粒度持久化属于后续综合决策，不阻塞本对象成立。

## 业务规则

| Rule-ID | 规则 | 承载 BO | 触发事件 | 约束结果 | 来源 |
|---|---|---|---|---|---|
| BR-001 | 自选标的必须归属于已支持市场，且保存原始代码与归一代码。 | WatchSymbol, Market | 用户新增自选 | 若市场不可识别，则不得进入 active 自选集合。 | mission AC-01, discovery candidates |
| BR-002 | 自选标的关闭浏览器后必须可恢复，不依赖账号登录。 | WatchSymbol | 浏览器重开 | 恢复为此前的 active/archived 状态与市场分组。 | mission AC-05 |
| BR-003 | 市场对象只承载分组与归一语义，不承载供应商绑定。 | Market | PRD 建模 | 不得把单一行情源写死到市场对象。 | mission non-goal, discovery PRD inputs |
| BR-004 | 历史行情不足时，价格条可以展示，但不得驱动出伪造的指标或 MTS 结论。 | PriceBar | 加载行情 / 刷新 | 下游必须进入 `partial`、`data_insufficient` 或中性提示。 | discovery edge_case, research |
| BR-005 | 当行情切到演示来源时，相关对象必须显式表明当前不是正式实时行情。 | MarketDataSource, PriceBar | 上游不可用 / fallback | 用户可区分 demo 展示与正式来源。 | discovery exception scenario |
| BR-006 | 指标集默认必须支持主图价格类指标、成交量常驻和一个可切换副图指标。 | IndicatorSet, ChartLayout | 打开看盘页面 | 默认视图满足 mission AC-02。 | mission AC-02, research 默认视图 |
| BR-007 | 指标集的数据和参数只能用于解释，不得被包装成收益承诺。 | IndicatorSet | 指标展示 | 页面与规则语义保持分析工具边界。 | mission constraints, research |
| BR-008 | MTS 必须同时表达趋势状态、分数带、信号类型和提醒等级，而不是单一箭头。 | MtsSignal | 信号计算完成 | 页面可区分观察、确认、强信号、风控。 | mission AC-03, AC-04, research |
| BR-009 | MTS 总分只用于排序与提醒强度，不得解释为胜率或收益概率。 | MtsSignal | 信号展示 | 维持产品风险边界。 | research |
| BR-010 | 趋势回调买点与收敛突破买点必须分类型呈现，不能混成一个“买点”。 | MtsSignal | 触发买点 | 保留可解释性与后续验证边界。 | research |
| BR-011 | 卖点提醒必须区分趋势破坏、动量衰竭和风控止损。 | MtsSignal | 触发卖点/风控 | 页面语义不能只写“卖出”。 | research |
| BR-012 | 提醒规则必须支持观察、确认、强信号、风控四级语义。 | AlertRule | 创建 / 编辑提醒 | 规则等级与 MTS 保持一致。 | mission AC-04, discovery candidates |
| BR-013 | 风控提醒优先于观察类提醒。 | AlertRule | 多条件同时命中 | 呈现高风险优先级。 | research 风控模型 |
| BR-014 | 旧复合信号不得直接作为产品信号对外展示。 | MtsSignal | PRD 建模 / 下游设计 | 仅可作为 fixture、样例或回归素材。 | discovery key findings, BO-CAND-009 |
| BR-015 | 第一阶段至少存在一个默认看盘布局；是否恢复上次布局可作为本地化体验的一部分。 | ChartLayout | 首次打开 / 重开页面 | 用户无需每次重配主图/副图结构。 | mission AC-02, AC-05, research |
| BR-016 | 行情来源对象可以变化，但不得改变“本地使用、不做自动交易、不承诺收益”的产品边界。 | MarketDataSource | 来源切换 / 正式供应商替换 | 供应商替换属于来源层变化，不应改写核心产品语义。 | mission scope/constraints |

## 建模取舍

### 候选对象逐条处理

| 候选 ID | 候选对象 | 处理 | 对应 BO | 取舍说明 | Traceability |
|---|---|---|---|---|---|
| BO-CAND-001 | WatchSymbol | promote | BO-001 | 是用户直接创建、持久化、恢复和关联提醒的核心观察对象。 | AC-01, AC-05, discovery candidates |
| BO-CAND-002 | Market | promote | BO-002 | 是跨市场分组与代码归一的规则承载体。 | AC-01, mission scope |
| BO-CAND-003 | PriceBar | promote | BO-003 | 是图表、指标、MTS 和提醒的共同业务输入；需显式承载“数据不足/演示模式”语义。 | AC-02, AC-03, discovery edge_case |
| BO-CAND-004 | IndicatorSet | promote | BO-004 | 用户需要在一个看盘上下文中共看指标，故它不是纯公式，而是解释对象。 | AC-02, research 默认视图 |
| BO-CAND-005 | MtsSignal | promote | BO-005 | discovery 标成 needs_decision，是因为实现形态未定；但产品语义已由研究文档充分定义，足以进入正式 BO。 | AC-03, AC-04, research MTS |
| BO-CAND-006 | AlertRule | promote | BO-006 | 用户显式配置并恢复提醒，是稳定业务对象。 | AC-04, AC-05 |
| BO-CAND-007 | DataProvider | merge | BO-007 | `DataProvider` 作为“适配器”是技术词；本次改建模为面向用户与产品语义的 `MarketDataSource / 行情来源`。 | discovery exception scenario, PRD inputs |
| BO-CAND-008 | ChartLayout | promote | BO-008 | 虽然 pane API 是技术实现，但“默认布局、切换、副图选择、是否恢复”是产品行为，因此建模为业务对象。 | AC-02, AC-05, research 图表结构 |
| BO-CAND-009 | LegacyCompositeSignal | exclude | - | 这是过渡实现，不是产品语义对象；只保留为测试/fixture 素材。 | discovery key findings, BO-CAND-009 |

### 被排除或降级的对象

| 名称 | 结论 | 原因 |
|---|---|---|
| LegacyCompositeSignal | exclude | 仅代表当前过渡代码输出，与正式 MTS 产品语义冲突。 |
| DataProvider（适配器语义） | reclassify | 若按“接口/适配器”理解则属于技术实现，不属于 BO；已重分类为 `MarketDataSource`。 |
| Pane API / 图表库能力 | exclude | 属于 UI/技术实现，不是业务对象；仅其用户可感知的布局偏好进入 `ChartLayout`。 |

### 证据不足但不阻塞建模的假设

- `ChartLayout` 是否按全局、市场或标的粒度恢复，现有材料不足；本文件仅定义其为“可恢复的看盘布局对象”，粒度留给综合阶段决定。
- `MtsSignal` 是否在内部拆成状态、评分、理由、提醒四个子对象，现有材料不足；本文件维持单一 BO，并以属性表达。
- `MarketDataSource` 未来是否对用户展示“延迟/正式/演示”更细分标签，现有材料未定；本文件只固定“formal / demo_fallback / availability”级别。

## Traceability

### 必须进入 BUC 的对象与能力

| 下游项 | 必须覆盖内容 | 来源 |
|---|---|---|
| BUC-自选管理 | WatchSymbol 的新增、归档、恢复、市场分组、代码归一失败处理。 | AC-01, AC-05 |
| BUC-看盘查看 | WatchSymbol 选中后，PriceBar、IndicatorSet、ChartLayout 的默认呈现与切换。 | AC-02 |
| BUC-MTS 解释 | MtsSignal 的趋势状态、买点类型、卖点类型、提醒等级和原因展示。 | AC-03, AC-04 |
| BUC-提醒管理 | AlertRule 的创建、启停、触发、恢复和优先级。 | AC-04, AC-05 |
| BUC-来源降级 | MarketDataSource fallback 到 demo 时的提示与降级语义。 | discovery exception scenario |

### 必须进入 AC / 验证的状态与规则

| 类型 | 必须验证 | 关联规则 |
|---|---|---|
| 状态验证 | WatchSymbol 的 `active` / `archived` 恢复语义。 | BR-001, BR-002 |
| 降级验证 | PriceBar `insufficient` 时，IndicatorSet / MtsSignal 不产出伪信号。 | BR-004 |
| 提示验证 | demo_fallback 时，页面必须区分演示数据与正式来源。 | BR-005 |
| 解释验证 | MTS 不能只显示买卖箭头，必须带状态、等级和理由。 | BR-008, BR-009, BR-010, BR-011 |
| 提醒验证 | AlertRule 的四级提醒与风控优先级。 | BR-012, BR-013 |
| 视图验证 | 默认布局满足主图 + 成交量 + 一个可切换副图。 | BR-006, BR-015 |

### 必须进入原型或后续设计综合的问题

- `ChartLayout` 的持久化粒度：全局、市场、标的三者取其一或组合。
- `MarketDataSource` 的用户可见状态口径：是否需要“延迟数据”“演示数据”“正式数据”三类以上标签。
- `MtsSignal` 的界面表达粒度：单卡片汇总还是分区展示趋势/评分/理由/风险。
- `project-context.md` 缺失后的长期约束补齐路径，避免后续阶段继续依赖弱证据。

## needs_synthesis_attention

- `project-context.md` 缺失，当前 PRD 仅能把 `project-knowledge/context/*` 当弱证据；综合阶段需补齐正式项目上下文。
- `MtsSignal` 已可作为正式 BO 建模，但其内部拆分粒度仍应由 `senior-product-expert` 在综合产物中统一。
- `ChartLayout` 已成立为 BO，但其本地恢复粒度尚未定稿，需在产品综合与原型阶段明确。
- `MarketDataSource` 已去技术化建模；后续不得把适配器/API 设计重新混回 BO 语义。
