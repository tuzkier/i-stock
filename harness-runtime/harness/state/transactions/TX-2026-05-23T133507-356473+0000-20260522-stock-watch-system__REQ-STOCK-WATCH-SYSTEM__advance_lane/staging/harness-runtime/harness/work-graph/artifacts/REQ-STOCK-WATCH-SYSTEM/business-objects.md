# BO Registry

**mission-id:** `20260522-stock-watch-system`  
**stage:** `PRD / Product Definition`  
**artifact:** `business-objects.md`  
**status:** `rewritten-for-open-source-reference`  

## Registry Summary

| BO-ID | 标准名称 | 别名 | 定义边界 | 关键属性 | 状态组 | 关系 | 业务规则 | Spec 来源关系 | 下游提示 |
|---|---|---|---|---|---|---|---|---|---|
| BO-001 | WatchSymbol / 自选标的 | 自选项、watchlist item | 用户主动维护并持续观察的单个标的；承载自选列表行语义，不承载历史行情计算。 | 市场、原始代码、归一代码、名称、active/archived、来源状态摘要、最近价/涨跌摘要、排序位次 | 生命周期、选中状态、来源摘要状态 | 属于 Market；引用 PriceSeries、MtsSignal、AlertRule | 必须保存原始代码与归一代码；归档不等于删除；来源状态与价格摘要需可追溯 | adjusted：来自 BO-CAND-001，并吸收开源参考中的列表状态要求 | 必须进入 BUC：新增、归档、恢复、切换、列表状态展示 |
| BO-002 | Market / 市场 | 市场分组、MarketCode | 负责市场分组与代码归一语义；不承担供应商实现。 | market_code、显示名、归一规则、默认币种/时区（如展示） | supported / temporarily_unavailable | 容纳多个 WatchSymbol；被 MarketDataSource 覆盖 | 数字代码必须结合市场解释；新增市场属于范围变化 | existing：来自 BO-CAND-002，范围由 mission 已确认 | 必须进入 BUC/AC：跨市场归一、歧义处理 |
| BO-003 | PriceSeries / 行情序列 | K 线序列、OHLCV 视图 | 某标的在某观察周期上的价格/成交量序列与最近价摘要；服务图表、tooltip 与列表摘要。 | timeframe、最新价、涨跌额/幅、最新 OHLC、成交量序列、freshness、source_mode | ready / stale / unavailable；formal / demo_fallback | 属于 WatchSymbol；由 MarketDataSource 提供；被 IndicatorSet、MtsSignal、AlertRule 引用 | 数据不足可展示，但不得伪造解释；OHLC 必须可读 | adjusted：由 BO-CAND-003 从单条 PriceBar 提升为序列级 BO | 必须进入原型/AC：主图、成交量、OHLC/tooltip 可读性 |
| BO-004 | IndicatorSet / 指标集 | 主图指标、副图指标 | 某标的当前观察上下文下的指标组合与读数；不包含图表库 API。 | 主图指标、成交量 pane、副图指标选择、参数组合、读数状态 | ready / partial / unavailable；default / customized | 依赖 PriceSeries；由 ChartLayout 呈现；为 MtsSignal 提供解释上下文 | 默认需支持主图+成交量+一个可切换副图 | adjusted：来自 BO-CAND-004，并吸收开源参考中的 pane/toggle 要求 | 必须进入 BUC/原型：副图切换、读数展示 |
| BO-005 | MtsSignal / MTS 多周期趋势信号 | MTS、趋势评分卡 | 面向观察与风控的解释性结果对象；不是交易指令。 | trend_state、mts_score、score_band、signal_type、alert_level、reason_codes、invalidators | interpretability、提醒等级、信号类型 | 依赖 PriceSeries 与 IndicatorSet；可被 AlertRule 引用 | 不得使用强买/强卖投资建议语义；必须显示原因和失效条件 | adjusted：来自 BO-CAND-005，并按研究文档与界面参考定型 | 必须进入 BUC/AC：趋势、分带、提醒等级、原因 |
| BO-006 | AlertRule / 提醒规则 | 本地提醒、提醒卡 | 用户在本地配置并持续管理的提醒规则；不包含外部通知渠道。 | taxonomy、条件、阈值、状态、最近触发时间、确认时间、原因、下一次定时点 | enabled / disabled / suspended_by_archive；idle / triggered / acknowledged | 绑定 WatchSymbol；可引用 PriceSeries、IndicatorSet、MtsSignal | taxonomy 至少含价格型、变化型、技术指标型、MTS 型、定时提醒 | adjusted：来自 BO-CAND-006，并补全 taxonomy 与状态机 | 必须进入 BUC/AC：创建、启停、触发、确认、归档联动 |
| BO-007 | MarketDataSource / 行情来源健康 | 来源状态、source health | 面向用户声明当前行情是否正式、降级、过期或不可用的对象；不讨论接口适配。 | health_status、上次刷新、降级原因、覆盖市场、重试语义、当前来源名 | formal / demo_fallback / stale / unavailable；retry_idle / retry_pending / retrying | 覆盖多个 Market；为 PriceSeries 提供状态；影响 WatchSymbol 摘要、MtsSignal、AlertRule 的可信度 | 降级必须显式；重试失败不能伪装成刷新成功 | reclassify：由 BO-CAND-007 的技术词 DataProvider 重分类为业务语义对象 | 必须进入 AC/原型：来源面板、降级提示、重试语义 |
| BO-008 | ChartLayout / 工作台布局 | 看盘布局、ChartLayout、工作台模式 | 用户可感知、可恢复的工作台布局偏好；不等于图表库 pane API。 | layout_mode、主图 pane、成交量 pane、副图 pane、mobile_tab、restore_state | dense / focus / mobile_tab；default / customized / restored | 呈现 WatchSymbol、PriceSeries、IndicatorSet、MtsSignal、AlertRule、MarketDataSource | 重开浏览器后应恢复上次布局；移动端与桌面端模式分离 | adjusted：来自 BO-CAND-008，并吸收开源参考中的 dense/focus/mobile tab | 必须进入原型/BUC：布局切换、恢复、专注看图 |

# BO Detail

## BO-001 WatchSymbol / 自选标的

- **定义边界**
  - 表示用户加入工作台、准备持续跟踪的单个证券标的。
  - 包含自选列表中用户真正管理的业务语义：市场、代码、归档状态、来源状态摘要、最近价摘要。
  - 不包含历史 OHLCV 序列、指标公式、MTS 计算过程。
- **别名**：自选标的、自选项、watchlist item。
- **关键属性**
  - `market_ref`
  - `raw_symbol`
  - `normalized_symbol`
  - `display_name`
  - `watch_status`：`active | archived`
  - `row_source_status`：派生自 `MarketDataSource.health_status`
  - `latest_price_summary`：派生自默认观察周期的 `PriceSeries`
  - `sort_order`
  - `added_at`
- **引用关系**
  - 多个 WatchSymbol 属于一个 Market。
  - 一个 WatchSymbol 在任一时刻可关联一个当前 PriceSeries、一个当前 IndicatorSet、一个当前 MtsSignal。
  - 一个 WatchSymbol 可绑定零到多个 AlertRule。
- **状态属性 / 状态机**
  - 生命周期：`active -> archived -> active`。
  - 选中状态：`selected | unselected`。
  - 行情摘要状态：`formal | demo_fallback | stale | unavailable`（派生展示状态，不单独持久化为主状态）。
- **业务规则**
  - 保存时必须同时保留原始代码与归一代码。
  - `archived` 代表退出当前工作台主列表，不代表物理删除历史引用。
  - 列表行显示的来源状态和最近价摘要必须能追溯到当前 PriceSeries 与 MarketDataSource。
- **追溯来源**
  - `mission-contract.md`：AC-01、AC-05。
  - `discovery-brief.md`：BO-CAND-001，多市场自选与本地恢复。
  - `docs/open-source-ui-reference.md`：自选列表要求展示市场、归一代码、来源状态、最近价/涨跌幅、active/archived。
  - `project-context.md`：本地持久化边界、demo fallback 必须明示。

## BO-002 Market / 市场

- **定义边界**
  - 表示股票归属的市场语境，是代码归一、市场分组和多市场支持边界的承载体。
  - 不等于行情供应商，也不包含交易成本、账号或券商信息。
- **别名**：市场、MarketCode、市场分组。
- **关键属性**
  - `market_code`：`US | HK | CN | KR`
  - `display_name`
  - `normalization_rule`
  - `default_timezone`（如需展示交易时段）
  - `default_currency`（如需展示价格单位）
- **引用关系**
  - 一个 Market 容纳多个 WatchSymbol。
  - 一个 Market 可被多个 MarketDataSource 覆盖，但对用户展示为当前有效来源状态。
- **状态属性 / 状态机**
  - 支持状态：`supported | temporarily_unavailable`。
- **业务规则**
  - 数字代码必须结合市场解释，不能脱离 Market 单独归一。
  - 第一阶段新增或替换市场支持集属于范围变化。
- **追溯来源**
  - `mission-contract.md`：范围锁定为港股、A 股、美股、韩股。
  - `discovery-brief.md`：BO-CAND-002 与跨市场归一。
  - `docs/open-source-ui-reference.md`：输入前需预览市场+归一结果，避免数字代码歧义。

## BO-003 PriceSeries / 行情序列

- **定义边界**
  - 表示某标的在某观察周期上的价格/成交量序列，以及由该序列得出的最近价与涨跌摘要。
  - 这是图表主图、成交量 pane、OHLC/tooltip 读数和列表摘要的共同业务输入。
  - 不包含指标计算结果和 MTS 判断结果。
- **别名**：行情序列、K 线序列、OHLCV 视图。
- **关键属性**
  - `symbol_ref`
  - `timeframe`
  - `bars_window`
  - `latest_price`
  - `change_amount`
  - `change_percent`
  - `latest_ohlc`
  - `volume_available`
  - `freshness_status`：`ready | stale | unavailable`
  - `source_mode`：`formal | demo_fallback`
  - `last_refreshed_at`
- **引用关系**
  - 一个 PriceSeries 属于一个 WatchSymbol。
  - 一个 PriceSeries 由一个当前有效的 MarketDataSource 提供。
  - 一个 PriceSeries 被 IndicatorSet、MtsSignal、AlertRule 作为判断输入。
- **状态属性 / 状态机**
  - 可用性：`ready | stale | unavailable`。
  - 来源模式：`formal | demo_fallback`。
- **业务规则**
  - 数据不足时仍可展示图表，但不得伪造完整指标或 MTS 解释。
  - OHLC 与 tooltip 信息必须可读，不能只剩颜色和曲线。
  - `demo_fallback` 必须作为显式业务状态影响下游解释。
- **追溯来源**
  - `mission-contract.md`：AC-02、AC-03。
  - `discovery-brief.md`：BO-CAND-003、数据不足与 demo fallback 降级语义。
  - `docs/open-source-ui-reference.md`：主图、成交量 pane、OHLC/tooltip 可读性、最近价/涨跌摘要。
  - `project-context.md`：演示行情必须明确提示。

## BO-004 IndicatorSet / 指标集

- **定义边界**
  - 表示当前观察上下文下被计算并展示的一组技术指标及其读数、分层位置和切换状态。
  - 是产品解释层，不是图表库配置对象。
- **别名**：指标集、主图指标、副图指标。
- **关键属性**
  - `primary_overlays`：如 `EMA20`、`EMA60`、`MA120`、`BOLL`
  - `volume_pane_enabled`
  - `secondary_indicator`：`MACD | RSI | KDJ | ATR`
  - `parameter_profile`
  - `computation_status`：`ready | partial | unavailable`
  - `readability_mode`：是否提供 tooltip/table 读数
- **引用关系**
  - 一个 IndicatorSet 依赖一个 PriceSeries。
  - 一个 IndicatorSet 由一个 ChartLayout 决定其摆放与可见性。
  - 一个 IndicatorSet 为一个 MtsSignal 提供解释上下文。
- **状态属性 / 状态机**
  - 计算状态：`ready | partial | unavailable`。
  - 视图状态：`default | customized`。
- **业务规则**
  - 默认布局必须包含主图指标、成交量 pane 和一个可切换副图指标。
  - 副图指标不应全部同时堆叠，至少保留明确切换语义。
  - 指标读数必须服务解释，不得包装为收益承诺。
- **追溯来源**
  - `mission-contract.md`：AC-02。
  - `discovery-brief.md`：BO-CAND-004，主图/副图指标展示能力。
  - `docs/open-source-ui-reference.md`：副图指标 tab/segmented control、常用指标切换、读数可读性。
  - `docs/technical-signal-research-design.md`：趋势、动量、波动、成交量四类指标组合原则。

## BO-005 MtsSignal / MTS 多周期趋势信号

- **定义边界**
  - 表示系统基于当前 PriceSeries 与 IndicatorSet 给出的解释性趋势结果。
  - 只服务观察、确认和风控，不代表下单指令，不承诺收益。
- **别名**：MTS、趋势评分卡、多周期趋势信号。
- **关键属性**
  - `trend_state`：`bullish | ranging | bearish | recovering`
  - `mts_score`
  - `score_band`：如 `strong_risk | risk_confirm | weak_negative | neutral | watch | confirm | strong_signal`
  - `signal_type`：`pullback_setup | breakout_setup | trend_break | momentum_exhaustion | risk_stop | none`
  - `alert_level`：`watch | confirm | strong_signal | risk`
  - `reason_codes`
  - `invalidators`
  - `evaluated_at`
- **引用关系**
  - 一个 MtsSignal 依赖一个 PriceSeries 与一个 IndicatorSet。
  - 一个 MtsSignal 可被多个 AlertRule 引用。
- **状态属性 / 状态机**
  - 可解释性：`interpretable | data_insufficient`。
  - 提醒等级：`watch | confirm | strong_signal | risk`。
- **业务规则**
  - 不得使用“强买”“强卖”作为产品主语义，应使用“强信号”“强风险”“技术提醒”等表述。
  - 必须同时显示 `trend_state`、`score_band`、`signal_type`、`alert_level`、`reason_codes`、`invalidators`，不能退化成单一箭头或单个总分。
  - `mts_score` 只用于排序和提醒强度，不得解释为胜率或收益概率。
- **追溯来源**
  - `mission-contract.md`：AC-03、AC-04。
  - `discovery-brief.md`：BO-CAND-005 与“不是单一买卖箭头”的 PRD 输入建议。
  - `docs/open-source-ui-reference.md`：MTS 卡片字段、避免投资建议语义、风险提醒高于观察提醒。
  - `docs/technical-signal-research-design.md`：MTS 四类输出、分数范围、提醒等级、失效条件。
  - `project-context.md`：技术信号只用于提醒，不构成投资建议。

## BO-006 AlertRule / 提醒规则

- **定义边界**
  - 表示用户在本地工作台中显式创建并持续管理的提醒规则。
  - 不包含外部通知渠道、账号订阅或云端消息服务。
- **别名**：提醒规则、本地提醒、提醒卡。
- **关键属性**
  - `symbol_ref`
  - `taxonomy`：`price | change | technical_indicator | mts | scheduled`
  - `condition_payload`
  - `activation_state`：`enabled | disabled | suspended_by_archive`
  - `trigger_state`：`idle | triggered | acknowledged`
  - `last_triggered_at`
  - `last_acknowledged_at`
  - `trigger_reason`
  - `next_due_at`（用于定时提醒）
- **引用关系**
  - 一个 AlertRule 绑定一个 WatchSymbol。
  - 一个 AlertRule 可引用 PriceSeries、IndicatorSet 或 MtsSignal 的判断结果。
- **状态属性 / 状态机**
  - 启停状态：`enabled -> disabled`，或在标的归档时进入 `suspended_by_archive`。
  - 触发状态：`idle -> triggered -> acknowledged -> idle`。
- **业务规则**
  - taxonomy 至少覆盖价格型、变化型、技术指标型、MTS 型、定时提醒。
  - `triggered` 不等于自动失效；用户确认后回到等待下一次触发。
  - 标的归档时，绑定规则自动进入 `suspended_by_archive`；标的恢复时按归档前用户意图恢复 `enabled` 或 `disabled`。
  - 第一阶段只做本地提醒，不做外部通知渠道。
- **追溯来源**
  - `mission-contract.md`：AC-04、AC-05。
  - `discovery-brief.md`：BO-CAND-006，本地提醒与恢复。
  - `docs/open-source-ui-reference.md`：taxonomy、状态集合、归档联动。
  - `docs/technical-signal-research-design.md`：提醒等级与文案必须说明原因。
  - `project-context.md`：本地持久化边界。

## BO-007 MarketDataSource / 行情来源健康

- **定义边界**
  - 表示用户当前看到的行情来源健康状态与降级原因。
  - 这是工作台的一等业务信息，而不是后台接口实现细节。
- **别名**：来源状态、source health、行情来源健康。
- **关键属性**
  - `source_name`
  - `health_status`：`formal | demo_fallback | stale | unavailable`
  - `coverage_markets`
  - `last_refreshed_at`
  - `degradation_reason`
  - `retry_semantics`：如手动重试、自动重试、等待下一轮刷新
  - `current_notice`
- **引用关系**
  - 一个 MarketDataSource 可覆盖多个 Market。
  - 一个 MarketDataSource 为多个 PriceSeries 提供来源状态。
  - 其健康状态影响 WatchSymbol 行摘要、MtsSignal 可信度与 AlertRule 是否可继续评估。
- **状态属性 / 状态机**
  - 健康状态：`formal | demo_fallback | stale | unavailable`。
  - 重试状态：`retry_idle | retry_pending | retrying`。
- **业务规则**
  - `demo_fallback` 必须与 `formal` 明确区分，并同步影响图表、MTS、提醒解释。
  - `stale` 表示用户正在看旧数据，不得伪装成实时刷新成功。
  - 重试失败不能导致页面崩溃；应保留上一次可解释状态并说明原因。
- **追溯来源**
  - `discovery-brief.md`：BO-CAND-007、demo fallback、来源可插拔但不在 PRD 锁定供应商。
  - `docs/open-source-ui-reference.md`：formal/demo_fallback/unavailable/stale、上次刷新、降级原因、重试语义。
  - `project-context.md`：Yahoo fallback 必须有可见提示。

## BO-008 ChartLayout / 工作台布局

- **定义边界**
  - 表示用户在看盘工作台中对信息密度、专注模式和移动端切换方式的布局偏好。
  - 它描述的是产品级布局行为，不是图表库的技术 pane API。
- **别名**：工作台布局、看盘布局、ChartLayout、工作台模式。
- **关键属性**
  - `layout_mode`：`dense | focus | mobile_tab`
  - `main_chart_pane`
  - `volume_pane`
  - `secondary_pane`
  - `mobile_tab_state`：如 `watchlist | chart | alerts | source`
  - `restore_state`：`default | customized | restored`
  - `last_restored_at`
- **引用关系**
  - 一个 ChartLayout 决定 WatchSymbol、PriceSeries、IndicatorSet、MtsSignal、AlertRule、MarketDataSource 在工作台上的组织方式。
  - 一个本地工作台在任一时刻有一个当前生效的 ChartLayout。
- **状态属性 / 状态机**
  - 布局模式：`dense | focus | mobile_tab`。
  - 恢复状态：`default -> customized -> restored`。
- **业务规则**
  - 桌面端至少支持 `dense` 与 `focus` 两种模式。
  - 移动端使用 `mobile_tab` 组织自选、图表、提醒、来源，不要求桌面拖拽式工作台。
  - 重开浏览器后应恢复上次布局，避免用户重复配置 ChartLayout。
- **追溯来源**
  - `mission-contract.md`：AC-02、AC-05。
  - `discovery-brief.md`：BO-CAND-008，布局和恢复行为待 PRD 明确。
  - `docs/open-source-ui-reference.md`：dense/focus/mobile tab、专注图表模式、三栏工作台、ChartLayout 恢复。
  - `project-context.md`：本地持久化边界。

# 业务规则

| Rule-ID | 规则 | 承载 BO | 触发事件 | 约束结果 | 来源 |
|---|---|---|---|---|---|
| BR-001 | 新增自选时必须同时保存原始代码与归一代码，并绑定明确市场。 | WatchSymbol, Market | 用户添加自选 | 若市场或归一结果不明确，不得进入 active 自选集 | `mission-contract.md` AC-01；`open-source-ui-reference.md` 自选列表 |
| BR-002 | 自选标的默认以 `active` 进入工作台；退出主列表时转为 `archived`，不做物理删除。 | WatchSymbol | 用户归档标的 | 历史提醒与恢复语义继续有效 | `open-source-ui-reference.md` active/archived；`mission-contract.md` AC-05 |
| BR-003 | 自选列表行必须可展示市场、归一代码、来源状态、最近价与涨跌摘要。 | WatchSymbol, PriceSeries, MarketDataSource | 工作台渲染 / 行情刷新 | 列表摘要来源可追溯且不与图表状态冲突 | `open-source-ui-reference.md` 自选列表 |
| BR-004 | 数字代码或歧义代码必须在确认前给出“市场 + 归一结果预览”。 | Market, WatchSymbol | 用户输入代码 | 避免提交后才发现跨市场解析错误 | `open-source-ui-reference.md` 自选列表建议；`project-context.md` PIT-002 |
| BR-005 | 行情序列可展示主图与成交量，即使数据不完整；但数据不足时不得产出完整 MTS 或误导性指标解释。 | PriceSeries, IndicatorSet, MtsSignal | 数据刷新 / 初次加载 | 下游进入 `partial` 或 `data_insufficient` | `discovery-brief.md` 数据充分性；`technical-signal-research-design.md` |
| BR-006 | 图表默认视图必须包含主图、成交量 pane 和一个可切换副图指标。 | IndicatorSet, ChartLayout | 打开个股工作台 | 满足看盘工作台基本形态 | `mission-contract.md` AC-02；`open-source-ui-reference.md` 图表与指标区 |
| BR-007 | OHLC、最新价和关键指标读数必须可读，不能只依赖颜色、曲线或视觉位置。 | PriceSeries, IndicatorSet | hover / tooltip / 详情读数 | 用户可解释当前价格与指标状态 | `open-source-ui-reference.md` OHLC/tooltip 可读性 |
| BR-008 | 副图指标至少支持 `MACD`、`RSI`、`KDJ`、`ATR/波动` 中的一类切换。 | IndicatorSet | 用户切换副图 | 副图不是固定死图层 | `open-source-ui-reference.md` 副图指标切换 |
| BR-009 | MTS 必须输出趋势状态、分数、分带、信号类型、提醒等级、原因和失效条件。 | MtsSignal | MTS 计算完成 | 页面不能退化成单一买卖箭头或只有一个大分数 | `mission-contract.md` AC-03；`technical-signal-research-design.md`；`open-source-ui-reference.md` |
| BR-010 | MTS 的文案不得以“强买/强卖”作为产品主语义。 | MtsSignal | 信号展示 | 统一使用观察、确认、强信号、风控、强风险等技术提醒口径 | `open-source-ui-reference.md` MTS 信号卡；`project-context.md` PIT-003 |
| BR-011 | `mts_score` 仅用于排序和提醒强度，不得解释为胜率、收益概率或交易建议。 | MtsSignal | 分数展示 / 排序 | 保持金融风险边界 | `technical-signal-research-design.md` |
| BR-012 | 提醒规则 taxonomy 至少包含价格型、变化型、技术指标型、MTS 型、定时提醒。 | AlertRule | 创建或编辑提醒 | 第一阶段规则分类完整可见 | `open-source-ui-reference.md` 提醒规则 taxonomy |
| BR-013 | 提醒规则必须区分启停状态与触发状态：`enabled/disabled/suspended_by_archive` 与 `idle/triggered/acknowledged`。 | AlertRule | 启停、触发、确认 | 避免把“已触发”误当成“已停用” | `open-source-ui-reference.md` 提醒规则状态 |
| BR-014 | 标的归档时，关联提醒自动进入 `suspended_by_archive`；标的恢复时按原用户意图恢复规则启停。 | WatchSymbol, AlertRule | 标的归档 / 恢复 | 规则不丢失，也不会在归档期继续触发 | `open-source-ui-reference.md` 归档联动；`mission-contract.md` AC-05 |
| BR-015 | 第一阶段提醒只做本地提醒，不扩展到外部通知渠道。 | AlertRule | PRD 定义 / 规则创建 | 保持当前产品边界 | `mission-contract.md` 范围；`technical-signal-research-design.md` |
| BR-016 | 行情来源健康必须显式区分 `formal`、`demo_fallback`、`stale`、`unavailable`。 | MarketDataSource | 刷新完成 / 刷新失败 | 用户能区分正式、降级、过期和不可用状态 | `open-source-ui-reference.md` 行情来源健康 |
| BR-017 | 当来源进入 `demo_fallback` 或 `stale` 时，图表、MTS、提醒必须同步降级说明，不得继续假装是正式实时行情。 | MarketDataSource, PriceSeries, MtsSignal, AlertRule | 来源状态变化 | 下游解释可信度同步变化 | `open-source-ui-reference.md`；`project-context.md` CODE-003 |
| BR-018 | 重试来源属于业务事件；重试失败应保留上次可解释状态并展示降级原因，而不是页面 crash。 | MarketDataSource | 用户手动重试 / 自动重试 | 工作台可继续使用并保留说明 | `open-source-ui-reference.md` 重试语义 |
| BR-019 | 桌面端至少支持 `dense` 与 `focus`；移动端使用 `mobile_tab` 组织主要区域。 | ChartLayout | 用户切换布局 / 设备变化 | 保持扫描效率与移动端可用性 | `open-source-ui-reference.md` 工作台布局 |
| BR-020 | 重开浏览器后应恢复上次 ChartLayout，避免用户重复配置工作台。 | ChartLayout | 浏览器重开 | 本地工作台连续性成立 | `mission-contract.md` AC-05；`open-source-ui-reference.md` ChartLayout 恢复 |
| BR-021 | 旧 `LegacyCompositeSignal` 不得直接作为正式 MTS 对外展示。 | MtsSignal | 产品定义 / 下游实现 | 只能作为迁移样例或回归测试素材 | `discovery-brief.md` BO-CAND-009 |

# 建模取舍

## discovery 候选对象到正式 BO 的映射

| 候选 ID | 候选对象 | 处理结果 | 正式 BO | 说明 |
|---|---|---|---|---|
| BO-CAND-001 | WatchSymbol / 自选标的 | promote | BO-001 | 直接保留为核心业务对象，并补充自选列表行状态摘要语义。 |
| BO-CAND-002 | Market / 市场 | promote | BO-002 | 直接保留，用于市场分组与归一规则。 |
| BO-CAND-003 | PriceBar / OHLCV | reclassify_and_promote | BO-003 | 从“单条 PriceBar”提升为“PriceSeries / 行情序列”，因为工作台业务语义围绕整段图表、最新价摘要和 OHLC 可读性展开。 |
| BO-CAND-004 | IndicatorSet / 指标集 | promote | BO-004 | 保留并补充主图/成交量/副图切换语义。 |
| BO-CAND-005 | MtsSignal / MTS 多周期趋势信号 | promote | BO-005 | 正式进入 BO Registry，并按研究文档与界面参考约束为解释对象。 |
| BO-CAND-006 | AlertRule / 提醒规则 | promote | BO-006 | 保留并扩展 taxonomy、状态机和归档联动。 |
| BO-CAND-007 | DataProvider / 行情适配器 | reclassify | BO-007 | 去技术化，重分类为用户可理解的 `MarketDataSource / 行情来源健康`。 |
| BO-CAND-008 | ChartLayout / Pane / 图表布局 | promote | BO-008 | 保留，并明确 dense/focus/mobile tab 与恢复语义。 |
| BO-CAND-009 | LegacyCompositeSignal / 旧复合信号 | exclude | - | 不是正式业务对象，只能留作历史样例、fixture 或回归素材。 |

## 被排除对象与原因

| 对象 | 结论 | 原因 |
|---|---|---|
| LegacyCompositeSignal | 排除 | 与正式 MTS 语义冲突，且 discovery 已明确不能直接升级为产品信号。 |
| 图表库 pane API | 排除 | 属于技术实现；只有用户可感知的布局偏好进入 BO-008。 |
| 行情供应商 SDK / HTTP 接口 | 排除 | 属于技术实现；业务上只保留 BO-007 的来源健康语义。 |
| 外部通知渠道 | 排除 | 第一阶段范围不包含外部通知和账号体系。 |

## 证据不足但暂不阻塞的假设

- `ChartLayout` 的恢复粒度是“全局工作台”还是“按标的”恢复，现有材料未定；本次仅锁定“必须可恢复”。
- `MarketDataSource` 的 `stale` 阈值未给出统一分钟数；本次只定义为业务状态，不锁定具体阈值。
- `scheduled` 提醒的具体时间表达式未定；本次只锁定其为可持久化、本地生效的提醒类型。
- `score_band` 的最终显示文案可在综合阶段微调，但不得改变“排序/提醒强度，不是胜率”的边界。

# Traceability

## 必须进入 BUC 的对象 / 能力

| 下游项 | 必须覆盖内容 | 关联 BO / 规则 |
|---|---|---|
| BUC-自选管理 | 添加、归档、恢复、排序、市场归一与歧义预览 | BO-001, BO-002；BR-001~BR-004 |
| BUC-看盘查看 | 主图、成交量、副图切换、OHLC/tooltip 读数 | BO-003, BO-004, BO-008；BR-005~BR-008 |
| BUC-MTS 解释 | 趋势状态、分带、信号类型、提醒等级、原因、失效条件 | BO-005；BR-009~BR-011 |
| BUC-提醒管理 | taxonomy、启停、触发、确认、归档联动、定时提醒 | BO-006；BR-012~BR-015 |
| BUC-来源降级 | formal/demo_fallback/stale/unavailable、上次刷新、重试语义 | BO-007；BR-016~BR-018 |
| BUC-布局恢复 | dense/focus/mobile tab 与重开恢复 | BO-008；BR-019~BR-020 |

## 必须进入 AC / 验证的状态与规则

| 验证主题 | 必须验证 | 关联 BO / 规则 |
|---|---|---|
| 自选恢复 | 浏览器重开后 active/archived、自选顺序与归一代码恢复正确 | BO-001；BR-001、BR-002 |
| 行情降级 | `demo_fallback`、`stale`、`unavailable` 状态可见且不伪装成正式数据 | BO-003, BO-007；BR-016、BR-017 |
| 图表可读性 | 主图、成交量 pane、副图切换与 OHLC/tooltip 读数成立 | BO-003, BO-004, BO-008；BR-006、BR-007、BR-008 |
| MTS 边界 | 不出现强买/强卖语义；必须展示原因与 invalidators | BO-005；BR-009、BR-010、BR-011 |
| 提醒状态机 | enabled/disabled/suspended_by_archive 与 triggered/acknowledged 行为正确 | BO-006；BR-013、BR-014 |
| 布局恢复 | dense/focus/mobile tab 的切换与 ChartLayout 恢复正确 | BO-008；BR-019、BR-020 |

## 必须进入原型或后续综合设计的问题

- WatchSymbol 行摘要中“最近价/涨跌摘要”默认取哪个观察周期，需要在原型中固定。
- `score_band` 的用户可见文案与颜色层级，需要在产品综合与原型中统一。
- `stale` 的业务阈值、定时提醒的时间文案、移动端 tab 默认落点，需要在后续综合设计中对齐。
- 现有 solution 若仍以旧 BO 边界为前提，后续必须按本文件重新对齐，尤其是 `PriceSeries`、`MarketDataSource`、`ChartLayout` 与 `AlertRule.taxonomy`。
