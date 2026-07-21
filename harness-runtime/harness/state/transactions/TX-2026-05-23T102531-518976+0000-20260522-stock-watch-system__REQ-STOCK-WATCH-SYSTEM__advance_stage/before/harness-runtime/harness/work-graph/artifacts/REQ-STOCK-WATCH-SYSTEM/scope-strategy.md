# Scope Decision Table

| ID | 范围判定 | 条目 | 本阶段策略 | 主要依据 |
|---|---|---|---|---|
| SD-01 | In | 本地网页看盘入口 | 第一阶段交付形态固定为本地网页，在同一浏览器配置内可持续使用。 | Mission Objective, US-01~US-04 |
| SD-02 | In | 四市场自选管理 | 港股、A股、美股、韩股进入同一观察入口，支持市场分组、代码归一、归档与恢复。 | AC-01, BUC-01, BO-001/002 |
| SD-03 | In | 默认看盘布局 | 主图、成交量常驻、副图指标可切换，首次进入无需重新配置。 | AC-02, BUC-02/03, BO-008 |
| SD-04 | In | 技术指标展示 | 主图包含价格类指标，副图覆盖 MACD / RSI / KDJ / ATR 等候选切换，数据不足时允许局部降级。 | research 默认视图, BR-004, BR-006 |
| SD-05 | In | MTS 多周期趋势信号 | 页面必须展示趋势状态、分数带、买点/卖点类型、提醒等级，不退化成单一箭头。 | AC-03, AC-04, BUC-04, BO-005 |
| SD-06 | In | 四级提醒 | 支持观察、确认、强信号、风控四级提醒；价格型与信号型规则都在第一阶段范围内。 | AC-04, BUC-05, BR-012/013 |
| SD-07 | In | 本地恢复 | 自选、提醒、基础看盘上下文在浏览器重开后可恢复，不依赖账号。 | AC-05, BUC-06 |
| SD-08 | In | demo / fallback 状态提示 | 正式来源不可用时可继续看盘，但必须显式告知当前为演示或降级状态，避免把 demo 数据伪装成正式行情。 | BUC-07, BR-005, BO-007 |
| SD-09 | In | 本地内提醒与浏览器通知 | 第一阶段提醒形态限定为系统内提醒与浏览器通知，不扩展到外部推送。 | research 实现边界 |
| SD-10 | In | 开源库优先但不锁库 | PRD 明确要求后续 solution / technical design 优先评估成熟、维护活跃、许可合适的现成开源库；本阶段不锁定具体库名或供应商。 | mission constraints, discovery dependency notes |
| SD-11 | Out | 自动交易 | 不下单、不联券商、不做自动买卖动作。 | Mission 非目标 |
| SD-12 | Out | 收益承诺与确定性投资建议 | 不输出收益保证、胜率承诺或确定性买卖建议。 | Mission constraints, research |
| SD-13 | Out | 云账号与跨设备同步 | 不做账号体系、云存储、跨设备同步。 | Mission 非目标 |
| SD-14 | Out | 完整基本面模块 | 不做财报、估值、行业、板块、完整基本面分析。 | Mission 非目标, research |
| SD-15 | Out | 后台无人值守盯盘 | 不做浏览器关闭后仍持续运行的后台任务或守护进程。 | research 实现边界 |
| SD-16 | Out | 正式供应商锁定 | PRD 不预先锁定正式行情供应商、回测数据源或成本模型。 | Mission 非目标, discovery |
| SD-17 | Out | 完整回测平台 | 不在第一阶段交付完整回测、参数寻优、报告平台。 | Mission TL;DR, research 后续路线 |
| SD-18 | Out | 组合调仓与仓位建议 | 不输出组合层面的调仓建议、仓位优化或资金分配建议。 | research 实现边界 |
| SD-19 | Out | 高频 / 秒级 / 日内交易场景 | 第一阶段只服务波段和中长期观察，不扩到高频或秒级日内。 | research 已确认约束 |
| SD-20 | Later | 正式行情 API 接入 | 在后续阶段完成供应商评估、授权与成本模型后再接入正式来源。 | discovery risks, research 数据源要求 |
| SD-21 | Later | 小时线、复权、停牌、拆股、交易日历 | 属于第二阶段数据能力扩展。 | research 数据源要求 |
| SD-22 | Later | 基本面、指数、板块、估值历史 | 属于第三阶段扩展能力。 | research 数据源要求 |
| SD-23 | Later | 桌面封装与外部通知适配器 | 可在本地网页稳定后再扩展。 | mission objective, research |
| SD-24 | Later | 完整回测与稳健性验证工作台 | MTS 真正进入更强实盘提醒前，需要后续补回测与稳健性框架。 | research 回测验证标准 |
| SD-25 | Decision Needed | ChartLayout 恢复粒度 | 本阶段已确定“需要恢复基础看盘上下文”，但恢复粒度是全局、按市场还是按标的，需 interaction / solution 联合定稿。 | AC-05, BO-008, BUC-06 |
| SD-26 | Decision Needed | MarketDataSource 用户可见信息密度 | 已确定必须显示“正式 / 演示 / 降级”状态；是否展示具体供应商品牌、刷新时间精度和覆盖差异，需在 interaction / solution 定稿。 | BO-007, BUC-07 |
| SD-27 | Decision Needed | MTS reason code / invalidator 标准化深度 | 已确定必须有结构化触发理由与失效理由；具体 code taxonomy、命名枚举和展示层映射需在 solution / technical design 定稿。 | BO-005, BUC-04, research |

# Rationale

## In

- `SD-01` 到 `SD-03` 是最小可闭环之外的必要产品边界，不是为了压缩实现，而是因为用户成功定义本身要求“本地网页 + 跨市场自选 + 默认可用看盘布局”同时成立；缺任一项都会破坏首个核心路径。
- `SD-04` 与 `SD-05` 共同定义了“看盘系统”而不是“行情列表”。技术指标和 MTS 必须并存，否则既无法支撑研究设计，也无法满足 AC-03 / AC-04 对解释性提醒的要求。
- `SD-06` 与 `SD-09` 把提醒能力限定在本地观察和浏览器通知层，既保证用户能持续使用，又避免越界到自动交易、外部推送编排或无人值守系统。
- `SD-07` 是第一阶段产品价值的保底项。若不能恢复自选、提醒和基础看盘上下文，产品就无法支撑连续使用场景。
- `SD-08` 是风险边界，不是附加优化。demo / fallback 不可隐藏，否则会把演示数据误解为正式行情，直接损害提醒可信度。
- `SD-10` 把“优先评估成熟开源库”提升为后续方案约束，目的是控制维护风险与验证成本；但 PRD 仍保持产品中立，不在本阶段锁定具体图表库、指标库或行情 SDK。

## Out

- `SD-11` 到 `SD-13` 直接来自 Mission 非目标与金融风险边界，不能以“后续也许需要”为理由混入第一阶段。
- `SD-14`、`SD-18`、`SD-19` 防止范围从“技术分析看盘”膨胀为“全栈投研或交易终端”。这些能力会显著改变对象模型、验证方式和合规边界。
- `SD-15` 排除后台无人值守，是为了与“本地网页 + 浏览器通知”的第一阶段形态保持一致，也避免下游误建守护进程、计划任务或长期运行代理。
- `SD-16` 与 `SD-17` 明确把供应商锁定和完整回测平台从 PRD 中剥离，避免产品定义被技术选型和研究验证工作提前绑死。

## Later

- `SD-20` 到 `SD-24` 都有明确业务价值，但它们不属于“第一阶段用户可见闭环”成立的前提条件。
- 正式行情 API、小时线与复权能力会反向影响供应商选择、成本和授权，不应在本阶段借产品定义提前承诺。
- 完整回测与稳健性工作台是 MTS 走向更强提醒可信度的必要后续，但不是本阶段看盘系统上线的先决条件。

## Decision Needed

- `SD-25` 之所以保留决策，是因为恢复粒度会影响信息架构与持久化键设计，但当前证据不足以说明用户更需要“全局统一布局”还是“按标的记忆布局”。PRD 只先锁定“必须恢复基础上下文”。
- `SD-26` 已经能定的部分已经定掉：必须有来源模式和降级状态提示。仍未定的是信息密度与文案层级，这更适合 interaction 与 solution 结合 UI 复杂度、来源差异做取舍。
- `SD-27` 已经能定的部分也先定掉：MTS 不能只有抽象颜色或一句话，必须能追溯原因和失效条件。仍需后续定稿的是标准化 code 体系与展示映射，因为它牵涉计算对象、测试夹具和 UI 标签体系。

# Dependencies And Risks

| 类型 | 条目 | 状态 | 风险 / 影响 | 验证动作 / 处理策略 |
|---|---|---|---|---|
| confirmed dependency | 跨市场日线 / 周线 OHLCV 与基础股票信息 | confirmed | 没有该数据，图表、指标、MTS、提醒都无法闭环。 | solution 阶段定义来源接口与 demo/fallback 契约；verification 阶段覆盖四市场 fixture。 |
| confirmed dependency | 本地持久化能力 | confirmed | 若恢复不稳定，会直接破坏连续使用价值。 | interaction/solution 明确持久化对象边界；verification 提供浏览器重开恢复证据。 |
| confirmed dependency | 可解释的 MTS 结果对象 | confirmed | 若只剩 legacy composite signal，会导致产品语义与研究设计脱节。 | solution 固化结果字段；technical design 约束 deterministic 计算链路。 |
| assumed dependency | 成熟开源库可满足图表 / 指标 / 本地化约束 | assumed | 若现成库无法覆盖关键能力，下游可能被迫自研并扩大成本。 | solution 需做比较矩阵：成熟度、维护活跃度、许可、跨市场能力、二次开发成本。 |
| open risk | 正式行情供应商覆盖、许可、成本未定 | open | 会影响未来实时性、覆盖市场和演示/正式切换策略。 | 作为后续方案决策项处理；PRD 不提前承诺具体供应商体验。 |
| open risk | MTS reason code / invalidator taxonomy 未定 | open | 若过早实现，后续可能重写对象、文案与测试基线。 | 保留为 Decision Needed；下游先按结构化接口设计，不锁举值全集。 |
| open risk | ChartLayout 恢复粒度未定 | open | 不同粒度会影响状态建模与恢复复杂度。 | interaction 先用原型验证认知负担，再由 solution 定稿持久化粒度。 |
| accepted risk | 第一阶段仍可能依赖 demo/fallback 运行 | accepted | 用户可能在部分场景看到演示数据而非正式行情。 | 必须强提示来源状态，并在验收中验证不会误导为正式实时数据。 |
| accepted risk | 不交付完整回测平台 | accepted | MTS 初期可信度更多依赖规则解释和样本验证，而非完整策略实验室。 | 在 PRD 保持边界清晰；后续路线单列回测平台。 |

# Downstream Boundaries

## 对 solution

- 必须把“优先评估成熟、维护活跃、许可合适的现成开源库”作为显式选型约束，至少覆盖图表、指标计算、通知与数据接入关键位。
- 不得因为现有草稿代码已存在，就默认锁定某个图表库、指标库或供应商。
- 必须保留 `demo / fallback` 运行模式，并让来源状态能穿透到用户可见层。
- 不得把自动交易、收益承诺、云同步、完整基本面、完整回测平台偷渡回第一阶段方案。

## 对 interaction

- 必须覆盖多市场自选、默认看盘布局、MTS 解释、四级提醒、来源降级提示、本地恢复反馈这几条核心路径。
- `ChartLayout` 恢复粒度、来源状态信息密度、MTS 理由展示层级是重点原型决策点。
- 交互文案必须维持“观察 / 确认 / 强信号 / 风控”和“正式 / 演示 / 降级”这两组口径，不得退化成模糊颜色提示。

## 对 technical_analysis

- 必须把 `WatchSymbol`、`Market`、`PriceBar`、`IndicatorSet`、`MtsSignal`、`AlertRule`、`MarketDataSource`、`ChartLayout` 作为核心对象边界。
- `MtsSignal` 必须预留 `reason_codes` 与 `invalidators` 的结构化字段，即使枚举全集尚未最终定稿。
- `MarketDataSource` 必须是可替换来源层，不能把供应商实现直接绑定进指标或 MTS 模块。
- `ChartLayout` 的技术方案不得超出 PRD 已授权范围，例如扩展到复杂画线系统、交易终端或桌面常驻。

## 对 breakdown

- Atomic task 必须先保证用户可见闭环：自选管理、默认看盘、指标、MTS、提醒、本地恢复、demo/fallback 提示。
- 供应商锁定、完整回测平台、基本面模块、云同步、自动交易不得混入第一阶段任务拆解。
- Decision Needed 项必须在相应阶段补决策后再拆执行任务，不能让执行层自行补产品定义。
