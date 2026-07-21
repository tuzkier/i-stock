# 探索简报（Discovery Brief）：20260720-alibaba-trade-signals

> **来源**：探索（discovery）技能 → `harness-runtime/harness/artifacts/20260720-alibaba-trade-signals/discovery/discovery-brief.md`
> **参考方法论**：事件风暴（Event Storming）；影响地图（Impact Mapping）；待完成工作（Jobs-to-be-Done）
> **上游**：`harness-runtime/harness/missions/20260720-alibaba-trade-signals/mission-contract.md` | `project-context.md`

- Contract: `contracts/discovery-brief.contract.yaml`
- 结构定义：`.harness/common/schemas/control_contract.v1/discovery_brief_contract.yaml`

> 结构化字段（`affected_capabilities` / `roles` / `scenarios` / `existing_solutions` / `design_assumptions` / `agent_engineering_candidates` / `degradations`）由外部契约 YAML 承载；本文件只保留面向人的叙事段，不内嵌围栏 YAML 控制契约段。

**作者：** hanbin（执笔：discovery-analyst）
**日期：** 2026-07-20
**任务编号（mission-id）：** 20260720-alibaba-trade-signals
**状态：** `draft`

---

## 摘要

本任务要在既有看盘终端上为 HK.09988 增加「多指标组合买卖信号标注 + 可复现回测证据 + 非投资建议边界」。探索取证结论：三条待探索缺口（GAP-01 图表承载、GAP-02 MTS/alerts 现状、GAP-03 数据事实）中，前两条已用代码直接证据完全闭合；GAP-03 因取证时 FutuOpenD（127.0.0.1:11111）与本地服务（localhost:5173）均无进程监听，实时探测降级为「代码事实 + 契约内既有实测记录」，已记入降级记录并给出补救动作。

核心事实：(1) lightweight-charts 5.2.0 已安装且导出 `createSeriesMarkers` 标注插件 API，项目内尚无任何 marker 使用，图表信号标注是全新增量；(2) MTS 多指标信号体系（`buildSignal` + ReasonRegistry v2 + MTS 解释卡 UI + mts 型提醒）**已完整实现并有单测/E2E**，不是仅设计；且存在一个高度同构的相邻先例——腾讯 HK.00700 专属规则化买卖触发位模块 `tencent-trade-plan.ts`（卡片承载、非投资建议文案齐备、无图表标注、无回测）；(3) 数据链路代码确认：日 K 复权口径 QFQ（前复权）、UTC 秒级时间戳、`1y` 请求窗为 420 自然日 / max_count 520（理论约 245~260 根日 K），扣除信号预热期（现有 MTS 需 ≥60 根）后有效回测信号窗约 180~200 根——是否足以支撑「有意义回测」是 solution 阶段需用户确认的口径问题（契约升级规则已有对应阻断条款）；(4) 项目内**不存在任何回测代码**，回测器是全新构件。

---

## 问题空间

### 背景

用户（个人投资者本人）在本地看盘终端跟踪 HK.09988，目前只能靠肉眼与零散指标主观判断买卖时机（mission-contract.md US-01）。任务契约已确认交付形态为「图表标注 + 回测证据 + 非投资建议边界」，指标选型与参数留给 prd/solution（mission-contract.md 范围内表）。

### 当前现状（现有系统事实，全部 CONFIRMED，source=manual_code_search）

- **数据流路径**：`src/App.tsx:185` `fetch(/api/chart/${symbol}?range=${range})` → `server/index.js:14-29` Express 路由 → `src/domain/market-data-source.ts:317-360` `execFile("python3", server/futud-client.py)` → FutuOpenD。返回 `MarketDataEnvelope`（bars / priceSeries / sourceHealth / meta / cacheState），缓存 TTL 60s、stale 容忍 15min（market-data-source.ts:78-79）。
- **图表结构**：`src/features/chart/ChartSurface.tsx` 用三个独立 chart 实例（主图 260px 蜡烛+EMA20/EMA60、成交量 108px、副图 168px MACD/RSI/KDJ/ATR），每个由 `ChartPane`（:78-126）在 `useEffect` 内 `createChart` 并在 bars 变化时销毁重建（:120-123）。主图 series 挂载点在 :207-220。
- **标注能力**：项目内无任何 marker/primitive 使用（grep `createSeriesMarkers|setMarkers|Marker` 于 src/ 零命中）；已安装 lightweight-charts 5.2.0（node_modules/lightweight-charts/package.json:2）的 typings 导出 `createSeriesMarkers`（v5 插件式 markers API，替代 v4 的 series.setMarkers）与 `SeriesMarker` 类型。
- **MTS 已实现**：`src/lib/signals.ts:117-219` `buildSignal` 由趋势（EMA20/60）、动量（RSI14/MACD）、量能（成交量比/OBV）、波动（布林/ATR）四类指标合成 −100..100 评分，<60 根 bars 输出 `DATA_INSUFFICIENT` 不给伪信号（:121-124）；来源降级时压制评分并追加 `SOURCE_DEGRADED`（:194-209）。ReasonRegistry v2 在 `src/domain/mts-registry.ts`（13 个注册码 + UNKNOWN_CODE 降级）。UI 消费在 `src/App.tsx:273`（buildSignal）与 :518-547（MTS 解释卡，含 `data-testid="mts-non-advice"` 非投资建议文案 :544-546）。测试：`tests/unit/signals/mts.spec.ts`（node:test 直接 import .ts）、`tests/e2e/mts/card.spec.ts`。
- **alerts 已实现**：taxonomy 含 `price/change/technical_indicator/mts/scheduled` 五类（`src/domain/alert.ts:29`），`evaluateAlertRules` 在 `App.tsx:282` 每次行情/MTS 更新时求值。
- **sourceHealth.affectedObjects 的确切含义**：`market-data-source.ts:76-77` 定义常量——来源降级（stale/unavailable）时 `affectedObjects=["chart","mts","alerts"]`，formal 时为空数组。它表达「来源降级会波及哪些 UI 对象」，不是模块注册表；对应长期 spec Requirement「来源健康与降级穿透」（project-knowledge/specs/local-stock-watch-workbench/spec.md:102-121）。
- **相邻先例**：`src/domain/tencent-trade-plan.ts` 是 HK.00700 专属策略 `tencent-0700-trend-v1`——规则化买入/卖出触发位（buyZone/sellTrigger/stopLoss 等）、action 枚举（buy_watch/buy_triggered/sell_watch/risk_control…）、MIN_BARS=80 预热、每种状态附 nonAdvice 文案（:91,216,246,285,307）；由 `App.tsx:274-277` 按 `isTencent700Symbol` 条件渲染为卡片。**它证明项目已有「按标的条件启用的专属信号算法」模式，但只有当前状态卡，无历史信号点、无图表标注、无回测。**
- **回测**：grep `backtest|回测` 于 src/server/tests 零命中——项目无任何回测实现。
- **测试设施**：无 `npm test` script；unit 用 node:test 直跑 .ts（Node 23 环境，project-context.md 运行时表），e2e 用 Playwright（playwright.config.ts testDir=tests/e2e）。质量门为 `npm run build`（tsc --noEmit && vite build）。

### 关键约束

| 约束 | 来源 | 影响 |
|------|------|------|
| 非投资建议边界：不得出现荐股式/承诺收益式措辞 | mission-contract 约束表 + spec「MTS 不表达投资建议」+ PIT-003（project-context.md:99） | SCN-05 验收；文案与 MTS/tencent-plan 既有口径需一致 |
| 回测证据必须真实可复现，禁 mock 冒充 | mission-contract 约束表 + 升级规则「外部依赖失效」 | FutuOpenD 不可用时必须停下报告，不得伪造 |
| 回测窗口受数据上限约束：1y ≈ 260 根日 K | server/futud-client.py:30-50（420 自然日 / max_count 520）+ 契约约束表 | 超出上限的回测声明不可信；有效信号窗还要扣预热期 |
| 来源降级语义须穿透到信号展示 | spec「来源健康与降级穿透」+ signals.ts:194-196 SOURCE_DEGRADED 先例 | 新信号标注在 stale/unavailable/demo 下的行为必须显式设计 |
| K 线渲染只用 lightweight-charts，禁手写 canvas 核心 | project-context.md 技术选择表 | 标注方案必须落在 lightweight-charts 5 API 内 |
| 用户可见文案默认中文 | CODE-001 | 信号标签、回测报告文案 |
| 不新增外部依赖为治理前提 | mission-contract 治理风险表「外部依赖 low」 | 引入第三方指标/回测库需重新过治理判断 |

---

## 影响面

| 领域 / 模块 | 影响类型 | 置信度 | 证据 |
|-------------|----------|--------|------|
| `local-stock-watch-workbench` 能力（长期 spec） | 扩展（新增行为落在其治理的图表区/信号区内） | CONFIRMED | spec Requirement「默认看盘工作台与指标切换」治理图表区（spec.md:45-64）；「MTS 解释性信号」治理信号区与非投资建议口径（spec.md:66-84）；「来源健康与降级穿透」要求降级同步到 chart（spec.md:102-121）；新功能渲染于 ChartSurface（受上述场景约束的同一 surface） |
| 买卖信号标注 + 回测（新行为本身） | 新增能力（现有 spec 无任何 Requirement 覆盖「历史买卖信号点标注」「回测证据」） | CONFIRMED（缺口确认） | 通读 spec.md 全部 9 个 Requirement，无一覆盖信号点标注/回测 → 建议新建能力规格（如 `hk-signal-annotation`），并以 delta spec 标注对 workbench 既有场景的触碰 |
| `src/features/chart/ChartSurface.tsx` | 修改（挂 markers/当前状态展示） | CONFIRMED | 主图 series 挂载点 :207-220；无现成 markers |
| `src/lib/indicators.ts` + `src/lib/signals.ts` | 复用/扩展（指标函数齐备：sma/ema/rsi/macd/bollinger/atr/obv + kdj in observation.ts） | CONFIRMED | indicators.ts:5-133；signals.ts 组合先例 |
| `src/App.tsx` | 修改（信号计算接入、状态卡/文案） | CONFIRMED | :273 buildSignal、:518-547 MTS 卡的接入模式 |
| 回测模块（新） | 新增 | CONFIRMED | 项目内零回测代码（grep 零命中） |
| `server/futud-client.py` + `market-data-source.ts` | 视回测窗口决策而定：若 1y 上限被判不足需扩 range 枚举 | UNCERTAIN | range 枚举硬编码于 futud-client.py:18 与 market-data-source.ts:75；是否扩窗待 solution 决策 |
| alerts 体系 | 不动（契约范围外），但存在被顺带触碰的诱惑 | CONFIRMED（边界） | mission-contract 范围外表「MTS/alerts 重构」 |

---

## 业务对象候选

> 仅记录候选线索；正式业务对象模型由 PRD 阶段 `business-domain-modeler` 完成。

| 候选对象 | 来源证据 | 状态 / 规则 / 关系线索 | 疑点或命名冲突 | PRD 建模提示 |
|----------|----------|------------------------|----------------|---------------|
| 买卖信号点（历史信号事件） | 契约 SCN-01（方向可区分、与 K 线时间对齐）；相邻先例 tencent-trade-plan 的 action 枚举 | 有方向（买/卖）、时间、对应价位；由信号规则在 K 线序列上产生；被图表标注与回测共同消费 | 与 MTS 的 alertLevel（强信号/确认/风控/观察）和 tencent-plan 的 buy_watch/sell_watch 语义相近但口径不同 | 三种信号语义（MTS 评分、trade-plan 触发位、新买卖信号点）是并列还是统一？信号点是否需持久化/可追溯 ID？ |
| 当前信号状态 | 契约 SCN-02（买入/卖出/观望，随数据可复算） | 由最新 K 线重算得出、口径须与历史信号一致；是信号点的「最新一期视图」还是独立对象待定 | tencent-plan 已有 status+action 双层状态 | 当前状态与历史信号点是否同一对象的两种投影 |
| 信号规则（多指标组合策略） | 契约 SCN-03（≥2 指标、选型/逻辑/参数可追溯）；signals.ts 四类分项评分先例；tencent-plan strategyId 版本化先例（`tencent-0700-trend-v1`） | 有版本/参数/可追溯性要求；须与回测所用规则同一实现 | 「策略」「算法」「规则」混用；是否需要 strategyId 式版本标识 | 规则参数集是否为一等对象（影响回测可复现声明） |
| 回测报告 / 回测统计 | 契约 SCN-04（胜率、相对买入持有收益、同数据同参数结果一致） | 有口径（胜率定义、收益基准）、输入指纹（数据窗口+参数）、可复现性规则 | 「胜率」的判定口径（持有期？下一信号平仓？）完全未定 | 胜率/收益的业务定义是 PRD 必须显式建模的规则 |
| 非投资建议边界文案 | technicalReminder（signals.ts:82）、nonAdvice（tencent-trade-plan.ts:91 等 5 处）、PIT-003 | 已在两处被具体化为对象属性；每种展示态各配一条 | 新功能是复用 MTS 口径还是自带文案 | 建议作为信号展示对象的必备属性建模，而非页面装饰 |
| K 线序列（PriceSeries） | types.ts / market-data-source.ts:490-519（已有对象） | 既有对象：range/interval/bars/latestOhlc；QFQ 复权口径由 futud-client 决定 | 复权口径未在前端对象上显式表达 | 回测证据须声明复权口径——是否把 adjustType 提升为 PriceSeries 属性 |
| MTS 解释卡 / 提醒规则 | 既有实现（本任务范围外） | 与新信号的关系仅为「相邻」；alerts 的 mts taxonomy 展示了「信号→提醒」的既有关系模式 | — | 只需建模关系边界，不重新建模其内部 |

---

## 业务用例与系统边界线索

### 业务活动线索

| 业务场景 / 活动 | 参与角色 | 业务目标 / 结果 | 来源证据 | PRD 建模问题 |
|-----------------|----------|-----------------|----------|--------------|
| 打开 HK.09988 图表查看历史与当前买卖信号 | 个人投资者 | 获得系统化、时间对齐、方向清晰的技术信号参考 | US-01；ChartSurface 现有浏览路径 | range 切换（1d/5d 为 5M/15M 分钟 K，futud-client.py:24-28）时日 K 信号如何表达——见待澄清 |
| 采信前查验回测证据 | 个人投资者（怀疑者帽子） | 用历史表现数据决定信任程度 | US-02 | 回测证据在哪被「查看」——UI 内还是产物文件？契约只说「可复现回测产物与统计输出」 |
| 复跑回测验证可复现性 | 个人投资者 | 同数据同参数结果一致 | EVD-02 | 复跑入口（命令）是否属于产品面还是仅验证面 |

### 系统边界与责任划分线索

| 业务场景 / 活动 | 人工责任 | 当前系统责任 | 目标系统责任线索 | 外部系统责任 | 证据等级 | 待澄清点 |
|-----------------|----------|--------------|------------------|--------------|----------|----------|
| 查看信号标注 | 最终买卖判断永远归人（非投资建议边界） | 渲染 K 线/指标/MTS 卡（ChartSurface + App.tsx） | 新增：在图表上渲染历史信号点 + 当前状态 + 边界文案 | FutuOpenD 提供 QFQ 日 K | CONFIRMED | 降级（stale/unavailable）时信号标注是隐藏、置灰还是照常渲染旧数据 |
| 信号计算 | 无 | MTS 评分已在前端纯函数计算（signals.ts） | 新信号规则计算落点（前端/共享模块）待 solution | 无 | CONFIRMED | 前端计算 vs 共享模块——见设计假设分支 A |
| 回测执行 | 触发回测命令、判读统计 | 无（零回测代码） | 新增回测运行器 + 统计输出 | FutuOpenD 是唯一历史数据源；其历史 K 线可得性约束回测窗 | CONFIRMED | 回测数据获取是否复用 market-data-source 缓存链路还是直连 futud-client |
| 数据窗口扩展（若 1y 不足） | 用户裁决「窗口是否够」 | range 枚举硬上限 1y | 可能改 futud-client.py + market-data-source.ts range 枚举 | futu SDK request_history_kline 有历史 K 线额度机制（quota） | INFERRED（迹象：futud-client.py:129 用 request_history_kline + futu SDK 公开文档口径「历史K线额度」为业内已知机制 + 契约治理表未评估过扩窗场景；推断链：扩窗 → 单次请求更多历史 → 可能触及额度/订阅约束；不确定点：额度具体数值与 HK.09988 是否受限未实测） | 扩窗触发 dependency-impact；额度事实需实测 |

### 原型承载线索

| 场景 / 任务 | 可能需要 UI 承载 | 需要展示的信息 | 需要输入 / 操作 | 状态 / 错误 / 权限 / 反馈线索 | 证据 / 疑点 |
|-------------|------------------|----------------|-----------------|--------------------------------|-------------|
| 历史信号标注 | 是 | 信号方向（买/卖可区分）、发生时间（与 K 线对齐）、（可能）触发理由 | 无新增输入；随图表浏览 | 数据不足（<预热期）不出伪信号（MTS 先例 :121-124）；来源降级穿透 | SCN-01；理由是否上图（拥挤度）待交互阶段 |
| 当前信号状态 | 是 | 状态（买入/卖出/观望）+ 非投资建议文案 | 数据刷新触发重算 | 与 MTS 卡/tencent-plan 卡并存时的信息层级 | SCN-02/SCN-05；承载位置（图上/卡片）不在探索阶段决定 |
| 回测证据查看 | 不清楚 | 胜率、相对买入持有收益、窗口与参数口径 | 复跑命令（可能仅命令行） | 口径说明必须可见以防误读 | 契约交付格式说「回测统计输出」，未指明 UI；PRD 需裁决 |

---

## 关键发现

| ID | 发现 | 证据 | 对后续工作的影响 |
|----|------|------|------------------|
| DIS-001 | lightweight-charts 5.2.0 已具备官方 markers 插件 API（`createSeriesMarkers`/`SeriesMarker`），项目内零使用——图表标注技术上可行且是纯增量 | node_modules/lightweight-charts/package.json:2 + typings.d.ts grep（createSeriesMarkers×3、SeriesMarker×30）；src/ grep 零命中 | GAP-01 闭合；technical_analysis 直接可用；无需引入新依赖 |
| DIS-002 | ChartPane 在 bars 变化时整图销毁重建（useEffect 返回 chart.remove），且主图/成交量/副图是三个独立 chart 实例 | ChartSurface.tsx:91-123 | 标注注入点须进 renderChart 回调或重构挂载方式；多 pane 时间轴不联动是既有事实，信号标注只落主图即可满足 SCN-01 |
| DIS-003 | MTS 体系已完整实现（评分、Registry v2、UI 卡、mts 型提醒、单测+E2E），非仅设计；T003 节点处于 finishing-branch/ready | signals.ts / mts-registry.ts / App.tsx:518-547 / tests/unit/signals/mts.spec.ts / tests/e2e/mts/card.spec.ts / nodes/tasks/TASK-STOCK-WATCH-T003.yaml（stage: finishing-branch, status: ready, implementation_refs 指向 src） | GAP-02 闭合；「复用 MTS 还是另立信号体系」是 solution 阶段真实决策，两个选项都有完整事实基础 |
| DIS-004 | 存在高度同构先例：HK.00700 专属 `tencent-0700-trend-v1` 规则化买卖触发位模块（按标的条件启用、非投资建议文案齐备、MIN_BARS=80 预热），但无历史信号点、无图表标注、无回测 | src/domain/tencent-trade-plan.ts:38-49、:91 等；App.tsx isTencent700Symbol 条件渲染 | 本任务=该模式的「加历史维度 + 上图 + 加回测」演进；命名/语义须与其 action 枚举对齐或显式区分 |
| DIS-005 | 数据口径代码事实：QFQ 前复权（futud-client.py:127,135）、UTC 秒时间戳（:68-78）、1mo~1y 均为日 K、1y=420 自然日/max_count 520、1d/5d 是 5M/15M 分钟 K（:24-28） | server/futud-client.py | 回测复权口径可声明为 QFQ；1d/5d range 上的信号表达是 PRD 待澄清项 |
| DIS-006 | 1y 理论上限约 245~260 根日 K；现有信号预热惯例 60~80 根（MTS≥60、tencent-plan≥80）→ 有效回测信号窗约 165~200 根；契约升级规则已预设「窗口过短→停下请求用户决策」 | futud-client.py:30-50 推算 + signals.ts:121 + tencent-trade-plan.ts:40 + mission-contract 升级规则 | solution_direction 检查点必须让用户确认「~200 根有效窗的回测是否算有意义」，或决策扩窗（连带 dependency-impact） |
| DIS-007 | 取证时刻 FutuOpenD(11111) 与本地服务(5173) 均无监听，GAP-03 的 HK.09988 逐 range 实测未能执行 | `lsof -iTCP -sTCP:LISTEN` 无匹配进程；TCP 连接 127.0.0.1:11111/5173 均 Connection refused（含非沙箱复测）；`python3 server/futud-client.py --symbol HK.09988 --range 1y` 挂起超时 | 已记降级；契约内既有实测（HK.00700 6mo→144 根、status=formal，mission-contract.md:43）作为链路健康的文档证据；补救动作见降级记录 |
| DIS-008 | 项目无回测代码、无 npm test script；unit 测试用 node:test 直接 import .ts（Node 23 可直跑 TS）——为「前端与回测共享同一 TS 信号模块」提供了可行性迹象 | grep backtest 零命中；package.json scripts；tests/unit/signals/mts.spec.ts:1-4 | 设计假设分支 A/B 的事实输入；回测器若走 Node+TS 可与前端规则同源，直接支撑 SCN-03「与回测所用规则一致」 |
| DIS-009 | 来源降级语义是长期 spec 级约束且 MTS 已示范（SOURCE_DEGRADED 压制评分）；新信号标注必须显式设计降级行为，否则违反「来源健康与降级穿透」Requirement | spec.md:102-121 + signals.ts:194-209 + market-data-source.ts:76-77 | PRD 验收场景需覆盖降级态；不是可选项 |

---

## 风险与未知

| ID | 风险 / 未知 | 严重度 | 处理建议 |
|----|-------------|--------|----------|
| RISK-001 | HK.09988 实际逐 range 根数、停牌/缺口表现未实测（GAP-03 残留）；若实际 1y 显著少于理论 260 根，回测窗进一步收窄 | 高 | 环境恢复后立即复跑取证命令（见降级记录）；在 prd 前或 prd 中补齐；若 <180 根有效窗触发契约升级规则请用户决策 |
| RISK-002 | 「有意义回测」口径未定：~200 根有效信号窗上多指标策略的信号样本量可能只有个位数到十几个，胜率统计置信度低 | 高 | solution_direction 检查点显式呈现样本量事实让用户裁决；备选分支为扩 range（连带 dependency-impact + futu 历史 K 线额度验证） |
| RISK-003 | 信号语义冲突：MTS alertLevel、tencent-plan action、新买卖信号三套口径并存可能造成用户困惑与文案边界失守 | 中 | PRD 建模时显式定义三者关系与展示层级；文案统一走非投资建议口径 |
| RISK-004 | 前端规则与回测规则口径漂移（若两套实现） | 中 | 设计假设分支 A 已给出共享 TS 模块的可行性迹象；由 solution 决策 |
| RISK-005 | ChartPane 销毁重建机制下，markers 随 bars 更新的生命周期管理易出隐性 bug（标注残留/丢失） | 中 | technical_analysis 阶段明确 markers 注入与重建时序；E2E 覆盖 range 切换 |
| RISK-006 | futu request_history_kline 历史 K 线额度（quota）机制未实测（ASSUMED）；若扩窗决策落地可能撞额度 | 低（当前范围内 1y 不受影响）| 仅在扩窗分支被选中时实测验证；责任阶段 solution/dependency-impact |
| RISK-007 | 1d/5d 为分钟 K：日 K 信号算法在这两个 range 的展示行为未定义，可能出现「切到 1d 信号消失」的体验断裂 | 中 | PRD 显式定义 intraday range 下的信号表达（隐藏+说明 / 仍显示日 K 信号锚点），列入验收场景 |

**假设清单（ASSUMED，均不得作为下游决策依据）**：
1. futu 历史 K 线额度不会约束 1y 窗口请求——验证动作：环境恢复后跑 1y 实测；责任阶段：discovery 补测/prd；若错：回测窗口进一步受限，触发 RISK-001 路径。
2. HK.09988 上市（2019-11）以来数据在 FutuOpenD 中完整可得（对 1y 窗口内无长期停牌）——验证动作：1y 实测数根数与日期连续性检查；责任阶段：discovery 补测；若错：回测窗口/缺口处理策略需调整。

---

## PRD 输入建议

| 主题 | 建议写入 PRD 的内容 | 依据 |
|------|--------------------|------|
| 信号对象建模 | 定义买卖信号点（方向/时间/价位/理由）与当前信号状态的对象关系；明确与 MtsExplanation、TencentTradePlan 的语义边界 | DIS-003/004、业务对象候选表 |
| 回测口径 | 胜率判定规则（持有期/平仓口径）、相对收益基准（买入持有）、复权口径（QFQ）、窗口与参数指纹的可复现性声明 | SCN-04、DIS-005/006 |
| 降级行为 | 信号标注在 stale/unavailable 下的验收场景（沿用穿透 Requirement） | DIS-009 |
| intraday range 行为 | 1d/5d 分钟 K 下信号的展示定义 | RISK-007 |
| 数据不足行为 | 预热期内不出伪信号（沿用 MTS DATA_INSUFFICIENT 模式） | signals.ts:121-124 先例 |
| 能力规格落点 | 新建 `hk-signal-annotation`（名称待定）能力 spec 承载新行为；对 `local-stock-watch-workbench` 触碰的既有场景以 delta spec 表达 | 影响面表第 1/2 行 |
| 回测证据承载 | 裁决回测统计是否进 UI（US-02 的「查看」发生在哪） | 业务活动线索表第 2 行 |

**下游触发建议**：interaction（用户可见 UI 功能，契约已排定）；solution（≥2 条互斥路线，见下）；technical_analysis（markers 时序/共享模块落点）；dependency-impact——仅当扩窗分支被选中（触碰 futud-client range 枚举与 futu 额度）；无 Agent 能力设计需求（核心构件全部确定性计算，见 Agent 化评估）。

---

## 设计假设与路线影响分支（只记线索，不定路线）

| 分支 | 互斥选项 | 事实来源 | 影响的判断 | 风险 | 待确认点 |
|------|----------|----------|------------|------|----------|
| A. 信号计算落点 | 前端内联（同 MTS 模式）vs 前端+回测共享的独立 TS 模块 | MTS/tencent-plan 均为前端纯函数（signals.ts、tencent-trade-plan.ts）；node:test 可直跑 .ts（tests/unit/signals/mts.spec.ts:1-4） | SCN-03「回测与图表规则一致」的达成方式 | 两套实现→口径漂移（RISK-004） | solution 决策；共享模块是唯一天然满足一致性的形态但需验证 import 边界 |
| B. 回测运行器 | Node(+node:test/CLI, 直跑 TS) vs Python 脚本 | 项目 Python 仅承担 futud 数据获取（futud-client.py）；统计计算在 TS 无障碍；无 Python 测试设施 | EVD-02 复现命令形态、与分支 A 的耦合 | Python 路线必然造成规则双实现 | solution 决策 |
| C. 指标实现 | 复用 src/lib/indicators.ts 自有实现 vs 引第三方指标库 | indicators.ts 已有 sma/ema/rsi/macd/bollinger/atr/obv（+kdj）；治理前提「不新增外部依赖」 | 依赖治理评级、参数口径可追溯性 | 引库需重过治理 | 若 prd 选型超出现有指标集才需重开 |
| D. 图表标注承载 | `createSeriesMarkers` 官方插件 vs 自定义 series primitive | DIS-001/002 | 实现复杂度与 RISK-005 | primitive 路线复杂度高 | technical_analysis 细化 |
| E. 回测窗口 | 接受 1y 上限（~200 根有效窗）vs 扩 range 枚举（改 futud-client + market-data-source） | DIS-005/006；range 枚举硬编码两处 | 回测统计置信度、是否触发 dependency-impact、RISK-006 | 扩窗触及数据链路与 futu 额度未知 | **solution_direction 人工检查点必须裁决**（契约已预设） |

---

## Agent 化评估输入

| 核心组件 | autonomy | runtime-context | multi-step | uncertainty | 结论与理由 |
|----------|----------|-----------------|------------|-------------|------------|
| 信号计算引擎 | false | false | false | false | 确定性纯函数：固定 bars 输入→固定信号输出（MTS 同构先例即纯函数）；无自主决策、无运行时上下文依赖、单步计算、无不确定性容忍需求 |
| 回测器 | false | false | false | false | 确定性批量重放：EVD-02 明确要求同数据同参数结果一致——与 Agent 化的不确定性特征根本冲突 |
| 图表标注层 | false | false | false | false | 确定性渲染：信号点→marker 映射，无判断空间 |

结论：全部 deterministic，与任务信封预期一致；无需触发 agent-capability 设计。

---

## 降级记录

| 降级项 | 原因 | 影响 | 补救动作 |
|--------|------|------|----------|
| graphify_unavailable | 未建图（本机建图因缺 LLM API key 失败，主流程告知） | 现有实现取证改用手动检索（Read/Grep/Glob），已逐文件标注路径:行号；GAP-01/02 结论不受影响 | 主流程按约定记入 contract.degradations[]；后续建图后可交叉验证调用链 |
| futud_live_probe_unavailable | 取证时刻 127.0.0.1:11111（FutuOpenD）与 localhost:5173（本地服务）均无进程监听：lsof 零匹配、TCP 直连 Connection refused（含关闭沙箱复测）、`python3 server/futud-client.py --symbol HK.09988 --range 1y` 挂起至 120s 超时。与任务信封所述「FutuOpenD 运行中、5173 已启动」不符，属环境状态变化 | GAP-03 的 HK.09988 逐 range 实测根数、停牌/缺口表现、1y 实际深度未取得直接证据；复权/时间戳/窗口上限等口径已由代码直接证据（futud-client.py）覆盖；链路曾健康有契约内实测记录（HK.00700 6mo→144 根，mission-contract.md:43） | 用户启动 FutuOpenD 后复跑：`python3 server/futud-client.py --symbol HK.09988 --range 1y`（及 6mo/3mo/1mo），统计根数、首末日期、日期连续性；结果补入本 brief 或 prd 输入；若 1y 有效窗过短走契约升级规则 |

---

## 证据索引

| 证据 | 类型 | 路径 / 命令 / 来源 |
|------|------|-------------------|
| EV-01 | 代码 | src/features/chart/ChartSurface.tsx:78-126,207-220（图表初始化/series 挂载/销毁重建） |
| EV-02 | 代码 | node_modules/lightweight-charts/package.json:2（v5.2.0）+ dist/typings.d.ts grep createSeriesMarkers/SeriesMarker |
| EV-03 | 代码 | src/lib/signals.ts:117-219（buildSignal）；src/domain/mts-registry.ts（Registry v2）；src/App.tsx:273,518-547 |
| EV-04 | 代码 | src/domain/alert.ts:29（taxonomy 含 mts）；src/App.tsx:282（evaluateAlertRules） |
| EV-05 | 代码 | src/domain/market-data-source.ts:76-77（affectedObjects 语义）、:317-360（execFile 链路）、:75（range 枚举） |
| EV-06 | 代码 | server/futud-client.py:18,24-50（range→请求映射）、:68-78（UTC 时间戳）、:127,135（AuType.QFQ） |
| EV-07 | 代码 | src/domain/tencent-trade-plan.ts:38-49,91,216,246,285,307（相邻先例与 nonAdvice 文案） |
| EV-08 | 代码 | tests/unit/signals/mts.spec.ts:1-4（node:test 直跑 .ts）；tests/e2e/mts/card.spec.ts；playwright.config.ts:4 |
| EV-09 | 文档 | project-knowledge/specs/local-stock-watch-workbench/spec.md:45-121（工作台/MTS/降级穿透 Requirements） |
| EV-10 | 文档 | REQ-STOCK-WATCH-SYSTEM/tech-design.md:76,91,124,211（INT-05/DATA-03/VS-03：MTS 替换 CompositeSignal 的设计与实现对应） |
| EV-11 | 文档 | harness-runtime/harness/work-graph/nodes/tasks/TASK-STOCK-WATCH-T003.yaml（stage: finishing-branch, status: ready） |
| EV-12 | 命令 | `lsof -nP -iTCP -sTCP:LISTEN | grep -iE "11111|5173|futu|node"` → 空；TCP connect 127.0.0.1:{11111,5173} → Connection refused（沙箱内外一致）；`python3 server/futud-client.py --symbol HK.09988 --range 1y` → 120s 超时 |
| EV-13 | 文档 | mission-contract.md:43（HK.00700 6mo→144 根实测、status=formal 记录）；grep backtest/回测 于 src+server+tests → 零命中 |
