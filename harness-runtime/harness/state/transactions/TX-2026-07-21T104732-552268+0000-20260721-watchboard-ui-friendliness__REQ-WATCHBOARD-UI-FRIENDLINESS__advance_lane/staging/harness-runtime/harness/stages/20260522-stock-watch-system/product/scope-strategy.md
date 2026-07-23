# Scope Decision Table

> 本文件是对 `20260522-stock-watch-system` 的 PRD 范围策略回改：以 `docs/open-source-ui-reference.md` 为新增输入，重写产品范围边界；当前 Mission 已进入 solution 阶段，因此本文件同时作为后续 solution 重对齐的上游约束。仅更新本文件，不改 `mission-contract`、Work Graph、`solution` 或代码。

| ID | 范围判定 | 条目 | 本阶段策略 | 影响 BO / BUC / AC | 主要依据 |
|---|---|---|---|---|---|
| SD-01 | In | 本地网页入口 | 第一阶段交付形态固定为本地网页，在同一浏览器配置内持续使用。 | BO-001/003/006/008；BUC-02/06；AC-02/05 | Mission Objective, Success Definition |
| SD-02 | In | 四市场自选 | 港股、A股、美股、韩股进入同一工作台；支持市场分组、原始代码与归一代码并存、归档与恢复。 | BO-001/002；BUC-01；AC-01/05 | Mission Scope, BO-001/002 |
| SD-03 | In | 输入歧义预览 | 数字代码或歧义输入在加入前必须展示“市场 + 归一结果预览/错误态”，而不是写入后再纠错。 | BO-001/002；BUC-01；AC-01 | Open-source UI ref §自选列表, PIT-002 |
| SD-04 | In | 默认日常看盘工作台 | 桌面端默认采用“自选 / 图表 + MTS + 状态摘要”的日常看盘工作台，不要求用户先自定义布局才能进入核心路径；诊断 / 验收模式展开提醒、来源、恢复和布局细节。 | BO-008；BUC-02/04/05；AC-02 | 用户原型走查反馈 + Open-source UI ref §工作台布局 |
| SD-05 | In | 主图 / 成交量 / 副图指标切换 | 主图 pane、成交量 pane、一个可切换副图 pane 为首开默认结构；副图至少支持 MACD、RSI、KDJ、ATR/波动候选。 | BO-003/004/008；BUC-02/03；AC-02 | Mission AC-02, Open-source UI ref §图表与指标区 |
| SD-06 | In | MTS 解释卡 | MTS 以解释卡/解释区呈现趋势状态、分数带、提醒等级、触发理由、invalidators；不得退化成单一分数或箭头。 | BO-005；BUC-04；AC-03/04 | Mission AC-03/04, Open-source UI ref §MTS 信号卡 |
| SD-07 | In | 提醒规则 taxonomy | 第一阶段产品范围必须包含本地提醒规则的分类模型：价格型、变化型、技术指标型、MTS 型、定时提醒。 | BO-006；BUC-05；AC-04/05 | BO-006, Open-source UI ref §提醒规则 |
| SD-08 | In | 本地触发历史 | 提醒不只显示“已触发数量”；必须保留本地触发历史最小闭环，至少包含触发时间、触发理由、确认状态。 | BO-006；BUC-05；AC-04/05 | Open-source UI ref §提醒规则 |
| SD-09 | In | 来源健康面板 | 来源状态是一级 UI 元素；需明确 `formal / demo_fallback / stale / unavailable`，并显示上次刷新、来源名或等价状态、重试入口。 | BO-007；BUC-06；AC-02/03/04 | BO-007, Open-source UI ref §来源与健康状态 |
| SD-10 | In | 本地恢复 | 自选、提醒启停/确认状态、基础布局偏好在浏览器重开后恢复，不依赖账号、云端或数据库用户模型。 | BO-001/006/008；BUC-07；AC-05 | Mission AC-05, CODE-002 |
| SD-11 | In | dense / focus / mobile tab 模式 | 布局模式进入本阶段产品定义：桌面至少支持 dense 与 focus；移动端采用 tab 化工作台，而不是强行复刻桌面三栏。 | BO-008；BUC-08；AC-02/05 | BO-008, Open-source UI ref §工作台布局 |
| SD-12 | In | fixture-first 验证输入 | PRD 明确把“四市场冻结样本 + 歧义输入 + 来源降级 + 本地恢复”列为首批验证输入边界，供后续 solution / verification 使用。此项是验收输入要求，不是对具体测试框架选型。 | BO-001~008；BUC-01/02/04/05/06/07；AC-01~05 | Mission Verification Evidence, Open-source UI ref §建议修订 |
| SD-13 | Out | 账号 / 云同步 / 数据库多用户 | 不引入账号体系、云同步、服务端数据库用户模型或多用户权限。 | 影响 BO-001/006/008 边界收缩；不新增对应 BUC | Mission 非目标, Open-source UI ref §明确不采用 |
| SD-14 | Out | 自动交易 | 不做下单、broker 集成、策略执行或自动买卖。 | 不把 BO-005/006 扩展成执行对象；不新增交易 BUC | Mission 非目标 |
| SD-15 | Out | 收益承诺 | 不输出收益保证、胜率承诺、确定性买卖建议。 | 约束 BO-005/006 文案边界；AC-03/04 维持“提醒”口径 | Mission constraints, PIT-003 |
| SD-16 | Out | TradingView iframe 替代本地图表 | 不用 TradingView iframe 代替本地图表层；图表、MTS 叠加、来源降级和 fixture-first 验证必须仍在本地可控边界内。 | 约束 BO-003/004/008；BUC-02/03/07 | Open-source UI ref §明确不采用 |
| SD-17 | Out | 直接复制 AGPL 代码 | 只参考功能与交互模式，不直接复制 AGPL 项目代码。 | 约束全部下游实现边界 | Open-source UI ref §明确不采用 |
| SD-18 | Out | 完整基本面 | 不交付财报、估值、行业、板块、新闻等完整基本面模块。 | 不新增 BO/BUC 族群 | Mission 非目标 |
| SD-19 | Out | 组合管理 | 不做持仓、收益归因、再平衡、组合调仓或资产分配模型。 | 不把 WatchSymbol 扩成 Portfolio/Holding | Open-source reference 对 Ghostfolio/OpenStock 的排除 |
| SD-20 | Out | 完整回测平台（本阶段） | 本次 PRD 不把完整回测平台写入交付或验收闭环。 | 不新增 Backtest BO/BUC；避免改变验证系统 | Mission TL;DR, 非目标 |
| SD-21 | Out | 外部推送服务集成 | 不集成邮件、短信、Telegram、企业微信、飞书、Webhook 等外部通知服务。 | BO-006 保持本地提醒边界；BUC-05 不扩成外送流程 | User instruction, Open-source UI ref |
| SD-22 | Later | KLineChart 替换评估 | 后续可正式评估是否由当前图表路线切换/补充到 KLineChart，但不是本轮 PRD 交付承诺。 | 主要影响 BO-003/004/008 的实现映射 | Open-source UI ref §图表与指标区/建议修订 |
| SD-23 | Later | 高级画线 | 趋势线、斐波那契、手绘标注、多对象画线留到后续阶段。 | 后续可能扩 BO-008 与交互 BUC | Open-source UI ref 推导，当前未授权 |
| SD-24 | Later | 多源正式供应商 | 后续再评估正式供应商矩阵、覆盖市场、授权与成本模型，不在本轮锁定。 | 后续影响 BO-007 与 BUC-07 | Mission 非目标, discovery 风险 |
| SD-25 | Later | 外部通知 | 当本地提醒闭环稳定后，再评估外部通知渠道与发送策略。 | 后续扩 BO-006/提醒 BUC | 与 SD-21 区分：本轮不集成，后续可立项 |
| SD-26 | Later | 桌面封装 | 本地网页稳定后，再评估 Electron/Tauri 等桌面封装。 | 后续影响 BO-008 与恢复语义 | Mission objective |
| SD-27 | Later | 完整回测 | 完整回测能力可作为后续独立阶段立项，但不回流本轮 PRD 交付。 | 后续新增对象、验证链路与工作台 | 与 SD-20 区分：本轮 Out，后续路线 Later |
| SD-28 | Decision Needed | ChartLayout 恢复粒度 | 已确认“必须恢复”，但尚未决定是全局工作台级、按市场级、按标的级还是混合恢复。 | BO-008；BUC-06；AC-05 | BO-008, Open-source UI ref §工作台布局 |
| SD-29 | Decision Needed | 移动端默认 tab | 移动端采用 tab 已确定，但默认落点是“自选”“图表”“提醒”还是“来源”尚未定稿。 | BO-008；BUC-02/05/07 | Open-source UI ref §工作台布局 |
| SD-30 | Decision Needed | 来源健康信息密度 | 已确定需要来源健康面板；仍需决定展示到“来源名/刷新时间/延迟/覆盖差异/重试语义”的哪一层。 | BO-007；BUC-07；AC-02/03/04 | BO-007, Open-source UI ref §来源与健康状态 |
| SD-31 | Decision Needed | MTS reason / invalidator taxonomy | 已确定需要结构化原因与失效条件；但 code taxonomy、展示文案映射和首批枚举深度仍需定稿。 | BO-005；BUC-04；AC-03/04 | BO-005, Open-source UI ref §MTS 信号卡 |

# Rationale

## In

| ID | 业务价值 | 风险 / 边界 | 证据 | Mission 追溯 |
|---|---|---|---|---|
| SD-01 | 锁定本地网页入口，保证与“无需云账号即可持续使用”的核心价值一致。 | 若放宽为账号/云优先，会直接偏离 Mission 非目标。 | `mission-contract.md` Objective / Success Definition | US-01~US-04, AC-05 |
| SD-02 | 四市场自选是跨市场观察闭环的入口，没有它就不是用户要的多市场看盘系统。 | 若缩成单市场，会破坏 Mission 已授权范围。 | `mission-contract.md` 范围内；`business-objects.md` BO-001/002 | AC-01 |
| SD-03 | 歧义预览直接处理数字代码冲突，是四市场输入成功率的关键体验。 | 若缺失，用户会在错误加入后才发现市场判定错误，破坏 BO-002 归一规则可信度。 | `docs/open-source-ui-reference.md` §1；`project-context.md` PIT-002 | BUC-01, AC-01 |
| SD-04 | 默认日常看盘工作台把自选、图表、MTS 和状态摘要放进同一观察面，符合扫描效率优先；诊断 / 验收模式承载提醒、来源和恢复细节。 | 若要求先配置布局，或把诊断信息全部常驻，会破坏首开闭环。 | 用户原型走查反馈；`docs/open-source-ui-reference.md` §6 | BUC-02/04/05 |
| SD-05 | 主图+成交量+副图切换共同构成“看盘”而不是“价格列表”；也让 MTS 有传统指标上下文。 | 若只保留单图或 strip，会削弱解释性并偏离开源参考。 | `mission-contract.md` AC-02；`docs/open-source-ui-reference.md` §2 | BUC-02/03 |
| SD-06 | MTS 解释卡把研究设计转成用户可读语言，是 AC-03/04 的核心。 | 若只显示分数/箭头，会把解释层收缩成不可验证的黑盒。 | `mission-contract.md` AC-03/04；`business-objects.md` BO-005 | BUC-04 |
| SD-07 | taxonomy 先进入产品边界，提醒才不是单一“到价提醒”；可支撑研究驱动用户的多条件观察。 | 若 taxonomy 不入 PRD，下游会把提醒简化成零散规则，难以对齐 UI 与验证。 | `business-objects.md` BO-006；`docs/open-source-ui-reference.md` §4 | BUC-05 |
| SD-08 | 本地触发历史让提醒结果可追溯、可确认、可恢复，是提醒闭环的一部分。 | 若只有已触发计数，无法支持“为什么触发”和本地确认语义。 | `docs/open-source-ui-reference.md` §4 | BUC-05, AC-04/05 |
| SD-09 | 来源健康面板是金融场景的可信度护栏，决定用户如何理解 demo/fallback 与 stale。 | 若只剩 notice，会把关键可信度信息降级成偶发提示。 | `business-objects.md` BO-007；`docs/open-source-ui-reference.md` §5 | BUC-06 |
| SD-10 | 本地恢复是“持续使用”前提，不恢复则产品无法成为日常工具。 | 若依赖账号/数据库恢复，会直接越过非目标。 | `mission-contract.md` AC-05；`project-context.md` CODE-002 | BUC-07 |
| SD-11 | dense/focus/mobile tab 模式把开源参考中的信息密度与设备差异正式纳入产品定义。 | 若只定义桌面三栏，会让移动端退化为临时适配；若过度扩成拖拽布局，又超出授权。 | `business-objects.md` BO-008；`docs/open-source-ui-reference.md` §6 | BUC-08 |
| SD-12 | fixture-first 验证输入把“看起来能用”转成“有冻结样本可验证”，是本轮回改的关键下游输入。 | 这是验证边界，不是技术路线；若缺失，下游可能用不可重放的 live 数据掩盖问题。 | `mission-contract.md` Verification Evidence；`docs/open-source-ui-reference.md` §建议修订 | AC-01~05 |

## Out

| ID | 为什么明确排除 | 风险控制 / 证据 | Mission 追溯 |
|---|---|---|---|
| SD-13 | 账号、云同步、数据库多用户会把本地自用系统扩成服务型产品。 | `mission-contract.md` 非目标；开源参考已明确不采用 OpenStock / Ghostfolio 的此类模型。 | AC-05, CODE-002 |
| SD-14 | 自动交易会把提醒系统变成执行系统，改变风险等级与合规边界。 | `mission-contract.md` 非目标；升级规则要求自动交易请求必须暂停。 | Mission constraints |
| SD-15 | 收益承诺与确定性建议不属于本产品授权，也会误导用户。 | `project-context.md` PIT-003。 | Mission constraints |
| SD-16 | TradingView iframe 会削弱本地图表、MTS 叠加、来源降级与 fixture-first 验证可控性。 | 开源参考已明确反对。 | BUC-02/07 |
| SD-17 | 直接复制 AGPL 代码会制造许可与交付风险。 | 范围策略只允许“参考功能与交互模式”，不允许代码复用。 | 下游实现边界 |
| SD-18 | 完整基本面会把对象模型从技术看盘扩到全栈投研。 | `mission-contract.md` 非目标。 | Mission 非目标 |
| SD-19 | 组合管理会引入持仓、收益、再平衡与资产配置语义，超出自选看盘边界。 | 开源参考已明确本项目没有持仓概念。 | BO-001 边界 |
| SD-20 | 完整回测平台会改变验证系统、数据源、指标链路和交付目标。 | 本阶段只保留后续路线，不把它写入当前验收。 | Mission TL;DR |
| SD-21 | 外部推送服务集成会把本地提醒扩成外送平台，并引入新的依赖与运营边界。 | 开源参考已明确第一阶段只做本地提醒规则与触发历史。 | BUC-05 |

## Later

| ID | 为什么延后 | 现在不做的原因 | 后续触发条件 |
|---|---|---|---|
| SD-22 | KLineChart 替换评估有潜在价值，但当前已有图表路线和范围闭环。 | 现在改写会把 PRD 变成图表库选型文档。 | 当 solution 证明当前路线无法满足 pane / indicator / overlay 需求时再评估。 |
| SD-23 | 高级画线属于增强分析能力。 | 对首批自选-图表-MTS-提醒闭环不是前提。 | 当基础工作台稳定且用户确有画线需求。 |
| SD-24 | 多源正式供应商是未来可信度升级路径。 | 当前供应商覆盖、授权、成本尚未定稿。 | 后续有正式授权与成本模型决策。 |
| SD-25 | 外部通知可放大提醒价值。 | 但本阶段先证明本地提醒与触发历史闭环。 | 本地提醒稳定、需要跨设备/离线通知时。 |
| SD-26 | 桌面封装能增强常驻性与系统级能力。 | 当前 Mission 先锁本地网页。 | 网页形态稳定且有系统托盘/桌面集成需求。 |
| SD-27 | 完整回测有明确业务价值。 | 但它需要独立的数据、验证和产品空间，不应挤进当前 PRD。 | MTS 规则稳定后再独立立项。 |

## Decision Needed

| ID | 决策点 | 为什么还不能直接定 | 若不决策会影响什么 | 建议决策时机 |
|---|---|---|---|---|
| SD-28 | ChartLayout 恢复粒度 | 现有证据足以说明“要恢复”，不足以决定恢复到全局/市场/标的哪一级最符合用户心智。 | 影响 BO-008 持久化模型、恢复键设计、交互文案和验证夹具。 | interaction 原型后，solution 定稿前 |
| SD-29 | 移动端默认 tab | 已确定移动端用 tab，但默认落点涉及首屏目标：扫自选、看图还是看提醒。 | 影响移动端首屏路径、截图验收与恢复默认值。 | interaction 原型阶段 |
| SD-30 | 来源健康信息密度 | 已知必须展示状态，但“信息太少会不可信、太多会压垮信息密度”之间仍需平衡。 | 影响 BO-007 字段展示层级、工作台空间分配与用户认知负担。 | interaction + solution 联合决策 |
| SD-31 | MTS reason / invalidator taxonomy | 已知必须结构化；但具体 taxonomy 深度会直接决定计算对象、fixture、文案映射和测试矩阵规模。 | 影响 BO-005 字段枚举、解释卡结构与验证样本设计。 | solution / technical_analysis 前置决策 |

# Dependencies And Risks

| 类型 | 条目 | 状态 | 风险 / 影响 | 验证动作 / 处理策略 |
|---|---|---|---|---|
| confirmed dependency | 四市场代码归一与歧义预览能力 | confirmed | 没有预览，BUC-01 会在高歧义输入下失真。 | solution 需把“市场 + 归一结果 + 错误态”定义为显式输入契约；verification 覆盖数字代码样本。 |
| confirmed dependency | 本地持久化恢复 | confirmed | 无法恢复会直接破坏 AC-05。 | solution 明确 BO-001/006/008 的持久化边界；verification 提供浏览器重开证据。 |
| confirmed dependency | 可解释的 MTS 结果对象 | confirmed | 若 reason / invalidator 不能穿透到 UI，AC-03/04 会退化。 | technical_analysis 预留结构化字段；interaction 设计解释卡。 |
| confirmed dependency | 来源健康状态穿透 | confirmed | 若 `formal / demo_fallback / stale / unavailable` 不能同时影响图表、MTS、提醒，用户会误判可信度。 | solution 把 BO-007 与 BO-003/005/006 联动写成契约；verification 覆盖来源降级夹具。 |
| confirmed dependency | fixture-first 验证输入集 | confirmed | 没有冻结样本，回改后的范围无法稳定验收。 | 建立四市场样本、歧义输入样本、降级样本、恢复样本；截图与断言都基于同一批夹具。 |
| assumed dependency | 现有本地图表路线可满足三 pane + 副图切换 + MTS 叠加 | assumed | 若能力不足，下游可能被迫扩大改造或提前换库。 | solution 需做能力对照；无法满足时把 KLineChart 评估升级为正式决策。 |
| assumed dependency | 本地浏览器环境足以承载 dense / focus / mobile tab 三种模式 | assumed | 若状态复杂度超出当前前端结构，恢复与适配成本会上升。 | interaction 先做低保真 / 中保真验证；solution 再定状态边界。 |
| open risk | AGPL 参考污染风险 | open | 若实现阶段直接借用代码，会引入许可问题。 | 在 solution / technical design 明确“只参考功能与交互，不复制代码”；评审时单列检查。 |
| open risk | 来源健康信息密度未定 | open | 过少会误导，过多会压缩看盘主视图。 | 保留 SD-30；交互原型后定。 |
| open risk | MTS taxonomy 深度未定 | open | 会影响 BO-005、提醒规则和 fixture 规模。 | 保留 SD-31；先锁结构，后锁枚举。 |
| accepted risk | 本轮只回改 PRD 范围策略，solution 暂时滞后 | accepted | 下游若继续沿旧范围推进，会出现 BO/BUC/UI 定义错位。 | 本文件发布后，solution 必须显式重对齐再继续细化。 |
| accepted risk | 第一阶段仍可能依赖 demo/fallback | accepted | 用户在部分场景看到演示数据而非正式数据。 | 必须通过来源健康面板与降级联动显式说明，不得伪装成正式行情。 |

# Downstream Boundaries

## 对 solution

- 这是一次 **上游 PRD 回改**。`solution.md` 后续必须重对齐以下新增边界：`输入歧义预览`、`默认日常看盘工作台`、`MTS 解释卡`、`提醒 taxonomy + 本地触发历史`、`来源健康面板`、`focus/dense/mobile tab`、`fixture-first 验证输入`。
- 不得继续沿用“提醒只是一条 notice”“来源状态只是顶部黄条”“移动端直接压缩桌面三栏”“图表只做单一副图表达”等旧假设。
- 不得把 `TradingView iframe`、账号/云同步、数据库多用户、自动交易、外部推送、完整基本面、组合管理、完整回测平台偷渡回方案。
- 若当前图表路线不能支撑 `主图 pane + 成交量 pane + 副图切换 + MTS 叠加 + fixture-first`，只能升级为正式方案决策，不能绕过到 iframe 替代。

## 对 interaction

- 原型必须优先覆盖：多市场歧义输入、自选列表状态、桌面三栏、dense/focus 切换、移动端 tab、MTS 解释卡、提醒规则与触发历史、来源健康面板。
- 交互上必须保持“本地提醒/技术提醒”边界，不出现收益承诺或交易执行暗示。
- `ChartLayout 恢复粒度`、`移动端默认 tab`、`来源健康信息密度` 是本阶段最关键的交互决策点，不能留给开发现场拍脑袋决定。

## 对 technical_analysis

- BO 边界按当前 PRD 收敛：`WatchSymbol`、`Market`、`PriceSeries`、`IndicatorSet`、`MtsSignal`、`AlertRule`、`MarketDataSource`、`ChartLayout` 不扩成账户、持仓、交易、组合、回测对象。
- `MtsSignal` 必须预留 `reason_codes`、`invalidators`；`AlertRule` 必须预留 taxonomy、状态、触发时间、触发理由；`MarketDataSource` 必须预留健康状态与降级语义。
- fixture-first 属于必备输入：分析链路必须能被冻结样本复算与截图验证，而不是只在 live 数据下“看起来正确”。

## 对 breakdown

- 任务拆解必须先围绕用户可见闭环：四市场自选与歧义预览、默认工作台、指标切换、MTS 解释、提醒 taxonomy 与本地触发历史、来源健康面板、本地恢复。
- `Later` 项不进入本轮执行任务；`Decision Needed` 项在补决策前不得拆成实现任务，只能拆原型、比较或决策准备任务。
- 由于本文件只回改范围策略，`contract`、Work Graph、`solution`、代码均保持不动；后续任何任务若引用旧 solution 假设，必须先标记“需重对齐”。
