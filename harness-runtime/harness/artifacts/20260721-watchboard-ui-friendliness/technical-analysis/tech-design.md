# 技术设计：多市场看盘终端（MyInvestment）界面友好化改造

> **来源**：technical_analysis 技能 → `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/technical-analysis/tech-design.md`
> **上游输入**：`solution/solution.md`（Route A 语义色 token 四档分层 + 只读呈现映射层；DEC-S01~S09；禁止路径 FB/§3.3；SR-01 + RISK-01~07；§8 交接 9 项 open item）| `discovery/dependency-impact.md`（blast radius 事实源）| `product/product-definition.md` | `product/use-case-model.md`（SUC-01~06 / 9 个 SUC-xx-OP-xx / UIC-01~07）| `product/acceptance-scenarios.md`（SCN-01~07 / SCN-xx-COND / NEG-01~07）| `product/product-domain-model.md`（BC-01↔BC-02 / INV-01~07 / POL-01~03 / STM-01~08 / VO-01~03）| `mission-contract.md` | `project-context.md` | 现状源码核对（见下「现状检索范围」）
> **阶段职责**：把 solution 已锁定的路线落成模块 / 接口 / 数据 / 状态 / 验证策略，供 breakdown、execute、code-review、verify 消费。不重选架构路线（§4 已锁定），不补造产品行为，不写实现代码，不拆原子任务队列。
> **Agent 段落声明**：本任务 `agent_engineering` 未启用、无 Agent 组件，**不含 `## Agent 实现` 段落**（solution §8、mission-contract 治理块「Agent 行动权 low」）。

**任务编号（mission-id）：** 20260721-watchboard-ui-friendliness
**状态：** `draft`

---

## 控制契约

Control Contract: `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/contracts/tech-design.contract.yaml`

- 控制契约（程序识别标记：Control Contract: `contracts/tech-design.contract.yaml`）
- 权威来源：外部 YAML 由主流程 CLI 写入，是程序化权威来源；本文件提供人类可读技术设计正文与结构化摘要，不内嵌控制契约 YAML。
- 原型承载：interaction 阶段经治理档 `可跳过阶段=[discovery, interaction]` 显式跳过，无 `behavior-graph.yaml` / `surface-model.md`，本设计**无 `SURF` / `PS-` 承载义务**，`prototype_coverage_exemptions=[]`；覆盖对象为 9 个 `SUC-xx-OP-xx` 系统操作 + UIC-01~07 界面承载要求 + INV-01~07 呈现不变量。

---

## 0. 总体说明（生产可用边界）

本次是 **brownfield 呈现层友好化改造**：在既有多市场看盘系统的呈现层（`src/styles.css` / `src/App.tsx` / `src/features/*`）建立**四档语义色 token 分层 + 只读呈现映射层**，把既有领域状态（来源健康 / MTS / 交易信号 / 回测 / 恢复态）忠实、无误导地翻译成界面语义，覆盖 7 类改造点（DEL-01~07）。

- **变更形态**：呈现层「扩展 + 隔离迁移 + 结构重排」，不是新增业务功能、不是替换算法、不是数据迁移。核心动作 = ① CSS 新增语义色 token（不改共享类颜色定义）；② 新增只读映射函数（复用既有人话源）；③ 把**范围内 4 处** `.data-notice` 用法迁移到新语义承载；④ 主视图裸枚举 / 裸理由码收进折叠详情并人话化；⑤ 去重复到唯一主源；⑥ 顶部 / 信号卡 / 侧栏层级重排。
- **生产可用边界（非演示范围）**：全部 9 个 `SUC-xx-OP-xx`、22 条验收条件、7 条负向路径（NEG-01~07）均须落地并可验证，覆盖所有 fan-out 结局态（来源五态、恢复四态、评分极性、交易信号非 ready 三态），不得只做「一条正常路径」。禁止把「先做正常态演示」当默认策略（solution §4 验证重点）。
- **不做**：不改 `src/domain/*`（算法 / 状态机 / 门控）、不改 `src/lib/signals.ts` 计算、不改后端 / 数据源、不触 alibaba 在途代码、不改 `styles.css:379` `.data-notice` 颜色定义、不改范围外 5 处 `.data-notice` 用法、不新建枚举→文案映射表、不写折叠态持久化、不改 STM-06 切换语义。

---

## 1. 输入合格判断

> 对每类输入判定 `fit` / `return_to_*` / `needs_decision`（枚举值）。`fit` 时至少推出一个技术承载落点。现状类结论均标注检索范围与命中文件，不脑补现状。

### 1.1 现状检索范围（取证记录）

| 检索目标 | 路径 glob / 关键词 | 命中文件:行（承载文件 + 符号 + 调用方三定位） | 取证结论 |
|----------|--------------------|-----------------------------------------------|----------|
| `.data-notice` 全量普查 | `grep -rn "data-notice" src/` | 定义 `styles.css:379`；用法 9 处：范围内 `App.tsx:640`(signal-degradation-note)/`645`(signal-error-note)、`features/restore/RestoreStatus.tsx:16`(restore-status)、`features/chart/ChartSurface.tsx:207`(chart-degradation-note)；范围外 `features/alerts/AlertRulePanel.tsx:136`、`features/layout/LayoutController.tsx:75/121`、`features/workbench/WorkbenchShell.tsx:78/135` | CONFIRMED（与 dependency-impact 3.1 完全一致，无未归类用法） |
| 共享类颜色定义 | `src/styles.css:379-389` | `.data-notice{color:#f0c75e;background:rgba(240,199,94,.1);border:1px solid rgba(240,199,94,.2)…}` | CONFIRMED（唯一定义点，9 处共享 → SR-01 红线：禁改此定义颜色） |
| 涨跌色物理独立性 | `src/styles.css:403-409` | `.up{color:#33c481}` / `.down{color:#f15f5f}`，与 `.data-notice` 无共享 | CONFIRMED（涨跌红绿 token 已物理独立，INV-05 后半可结构保证） |
| 既有 tone 承载类 | `src/styles.css:566-605` | `.signal-card.positive`(绿框)/`.signal-card.watch`(rgba(240,199,94) 琥珀框)/`.signal-card.risk`,`.signal-card.negative`(红框)；`.score-grid`(581/601) | CONFIRMED（负向评分现走 `.signal-card.risk` 红框，已与 `.data-notice` 琥珀 banner 物理分离、类名不复用） |
| 来源状态承载 + 人话源 | `App.tsx:79-92`(getSourceStatus/sourceStatusLabel)、`94-99`(mtsTone)、`101-106`(tradeSignalTone) | `mtsTone` 返回 `positive/risk/neutral`，`source_degraded`/`data_insufficient`→neutral，`scoreBand` 正负→positive/risk；`sourceStatusLabel` 五态中文；调用方 `signal-card className`(634)、侧栏(435) | CONFIRMED |
| MTS 卡裸枚举泄漏 | `App.tsx:634-660` | `score-grid`(650-656) 直呈 `trend_state {mts.trendState}`/`mts_score`/`score_band`/`signal_type`/`alert_level {mts.alertLevel}`；`displayLabel`(649)/`technicalReminder`(657) 人话已在用；降级 note(640) / 错误 note(645) 用 `.data-notice` | CONFIRMED（GAP-D1 靶点坐实） |
| ReasonRegistry 裸理由码 | `App.tsx:662-678` | `reasons.map` 直呈 `<code>{item.code}</code>`(667)；`invalidators.map` 亦直呈 `<code>{item.code}</code>`(673，`.warning` 类)——**两处双直呈**，未用 `item.label` | CONFIRMED（GAP-D1 补点：reasons + invalidators 双泄漏） |
| 交易信号卡非 ready 裸枚举 | `App.tsx:526-632` | signal-topline(532) 非 ready 直呈 `{tradeSignal.status}`（枚举串）；`stanceLabel`(534)/`nonAdvice`(628-630) 人话已在用；回测流水(608-627) 默认铺开、无折叠 | CONFIRMED |
| RestoreStatus 四态复用告警类 | `features/restore/RestoreStatus.tsx:1-22` | `statusLabel`(7-12) 四态中文映射；render(14-21) 对**全部四态**（含 restored/partial/default_fallback 正常态）复用 `.data-notice`；唯一调用方 `App.tsx:471` `<RestoreStatus metadata={restoreMetadata}/>` | CONFIRMED（SCN-01 直接根因坐实，隔离良好、单一调用方） |
| 人话源 + UNKNOWN_CODE 回落 | `types.ts:152-153,172-173,191`；`domain/mts-registry.ts:16-146,160-167`；`domain/trade-signals.ts:54,65,519-681` | `MtsReason.label/detail`、`displayLabel`/`technicalReminder`、`stanceLabel`/`nonAdvice` 均存在；`resolveMtsReason`(160) 带 `UNKNOWN_CODE` 回落(161) | CONFIRMED（DEC-S03 复用面成立） |
| domain 只读读取点 | `App.tsx:82,95,639`；`domain/trade-signals.ts:619-627` | 门控在 domain 层（`sourceHealth.status!=="formal"→status:"source_degraded"`），呈现层只读 `mts.*`/`tradeSignal.*`/`metadata.*`/`sourceHealth.*`，无写回 | CONFIRMED（DEC-S01/S06 只读边界与现状一致） |

### 1.2 输入合格判断结论

| 输入类 | 结论（枚举） | 依据 | fit 时推出的技术承载落点 |
|--------|-------------|------|--------------------------|
| 产品定义 / 用例（SUC-01~06、9 个 SUC-xx-OP-xx、UIC-01~07、SCN-01~07、INV-01~07、POL-01~03、STM-01~08、VO-01~03） | `fit` | 9 个 OP 全为读侧映射、每条含读取对象 / 规则 / 可观察结果；INV-01~07 为呈现不变量、可逐条对上；VO-01~03（呈现色档 / 人话 / 可读评分）给出值对象语义 | → M1 四档语义色 token（VO-01/INV-01~03）、M2 只读映射层（POL-01~03/VO-02/03）、M3~M8 承载各 SUC |
| solution（Route A、DEC-S01~S09、SR-01、禁止路径 §3.3、§8 交接 9 项） | `fit` | 路线已锁定为语义色 token 分层 + 只读映射层，边界 §4 明确、禁止路径可执行、9 项 open item 全部落到本设计 §2~§7 | → 本设计不重选架构，仅在锁定路线内细化 |
| 现状代码证据（§1.1 全部 CONFIRMED） | `fit` | 9 处 `.data-notice`、共享定义、涨跌独立、tone 承载类、裸枚举 / 裸理由码泄漏点、人话源、UNKNOWN_CODE 回落、domain 只读点均已源码坐实 | → 迁移清单锚定真实 file:line；SR-01 隔离可执行；INV-03 已部分结构保证（红框 vs 琥珀 banner） |
| 依赖影响（Blockers=0、破坏性=无、GAP-D1/D2/D3） | `fit` | 三层依赖取证完成、无阻断；GAP-D2（demo_fallback 定档）为 verify 前用户决策、不阻断本设计；GAP-D1/D3 由本设计承接 | → GAP-D1 裸枚举穷举纳入 §7 验证；GAP-D3 唯一主源选点纳入 §3 M6 |

**合格性结论：全部 `fit`，无 `return_to_*`、无 `needs_decision` 阻断项。** 唯一未定项 GAP-D2（demo_fallback 最终色档，产品 DEC-01）按 DEC-S07 设计为「档位可切换、不改承载结构」，属 verify 前用户决策，不阻断技术设计。**不返回 BLOCKED。**

---

## 2. 系统操作到技术设计映射（必产）

> 逐条承载 use-case-model 9 个 `SUC-xx-OP-xx`。每条：追溯 `SUC-xx-FLOW-xx` → 接口 / 命令 / 事件 / 模块 → 读取实现 → 写入 / 状态迁移实现（本任务全为只读，写明无写入）→ 条件 / 错误码 → 原子性 / 并发 / 幂等 → 验证证据。承载模块编号见 §3。

### SUC-01-OP-01 — 将 SourceHealth 档映射为呈现色语义（三档）
- **来源流步骤**：SUC-01-FLOW-02（fan-out：not_loaded/formal/demo_fallback/stale/unavailable）
- **承载接口 / 模块**：`resolveSourceTone(status: SourceStatus): Tone`（M2 只读映射层）；来源权威承载组件（M6 顶部区）+ 派生一致性指示（M8 ChartSurface、M3 MTS 卡降级子集）
- **读取实现**：读 `getSourceStatus(payload, hasError)`（App.tsx:79-84）产出的 `SourceStatus` 与 `payload.sourceHealth.{status,degradationReason,affectedObjects}`、`activePayload.notice`；`resolveSourceTone` 按 BR-02 映射：`formal`/`not_loaded`→`normal`、`demo_fallback`→`info`（DEC-S07 默认档，可切换）、`stale`/`unavailable`→`warning`
- **写入 / 状态迁移**：无（呈现层只读 STM-02，不驱动迁移、不写领域状态）
- **条件 / 错误码**：无 payload → `not_loaded` 中性占位；`hasError && !payload` → `unavailable`（既有 getSourceStatus 语义，不改）；无「错误码」概念（纯呈现）
- **原子性 / 并发 / 幂等**：呈现幂等（同 `status` 同 `Tone`，VO-01 呈现幂等）；无并发写、无副作用；每次 render 重算，React 单向渲染无竞态
- **验证证据**：SCN-01-COND-01（formal/not_loaded 无 `.notice--warning` DOM 断言）、COND-02（demo_fallback 信息级并置截图）、COND-03（stale/unavailable warning + 受影响范围 DOM 断言）；四档并置 preview 截图

### SUC-01-OP-02 — 价格 / 涨跌收敛唯一主源，涨跌色与警告色分离
- **来源流步骤**：SUC-01-FLOW-03
- **承载接口 / 模块**：价格 / 涨跌权威主源承载点（M6 顶部 quote-line，`data-testid="price-authority"`，计数=1）；涨跌色沿用既有 `.up`/`.down`（styles.css:403-409，不改、物理独立于 `.notice--*`）
- **读取实现**：读选中标的派生行情（`latest.close`、`changePercent`，EXC-01 呈现属性）；侧栏 per-item 价格（App.tsx:435）保留为**列表扫读角色**（SCN-06），与详情区权威主源角色分离——两者语义不同层（列表定位 vs 详情权威），不构成同级重复主源
- **写入 / 状态迁移**：无
- **条件 / 错误码**：无行情 → 占位「—」（既有 formatNumber 语义）；无错误码
- **原子性 / 并发 / 幂等**：呈现幂等；无写
- **验证证据**：SCN-03-COND-02（价格 / 涨跌权威承载 `data-testid="price-authority"` 计数=1 DOM 断言 + 涨跌红绿 vs 警告色并置截图）

### SUC-02-OP-01 — 人话化 + 进度条 + 极性上色
- **来源流步骤**：SUC-02-FLOW-01、SUC-02-FLOW-02（fan-out：positive/negative）
- **承载接口 / 模块**：`resolveScoreTone(mts): Tone`（M2，复用 / 重构既有 `mtsTone` App.tsx:94-99）；`humanizeTrendState`（M2）；`<ScoreBar>` 进度条承载（M3）；人话文案复用 `mts.displayLabel`(649)/`mts.technicalReminder`(657)/中文 `alertLevel`/`resolveMtsReason(code).label`
- **读取实现**：读 `mts.{displayLabel,technicalReminder,scoreBand,alertLevel,mtsScore,trendState,reasons,invalidators}`；`resolveScoreTone` 按 BR-04：`strong_positive`/`positive`→`positive`（积极色）、`neutral`/`not_applicable`→`neutral`（无色）、`negative`/`strong_negative` 或 `alertLevel=风控`→`caution`（谨慎-风险色）；进度条据 `mtsScore` 数值渲染，`not_applicable`/null 按中性不填充（VO-03）
- **写入 / 状态迁移**：无（MtsExplanation 每次观测重算，无 STM，DMF-01）
- **条件 / 错误码**：`mtsScore` 为 null/`not_applicable` → 进度条中性态、不误导性满填；未注册理由码 → `resolveMtsReason` 回落 `UNKNOWN_CODE`（mts-registry.ts:161）不直呈原始 code
- **原子性 / 并发 / 幂等**：呈现幂等（同 scoreBand 同 Tone）；无写
- **关键约束（INV-03）**：`caution`（谨慎-风险 = 市场看空）承载 class 名**不复用**来源 `warning` 承载 class 名，且物理可辨（现状 `.signal-card.risk` 红框 vs `.data-notice` 琥珀 banner 已分离，本设计在 token 层形式化该分离）
- **验证证据**：SCN-02-COND-01（主视图无枚举 token DOM 断言 + Playwright 文本断言）、COND-02（进度条承载 DOM 断言）、SCN-01-COND-06（negative 评分承载 ≠ 来源警告类名 DOM 断言 + negative 与 stale 并置截图证物理区分）

### SUC-02-OP-02 — 原始字段折叠；非常态人话化
- **来源流步骤**：SUC-02-FLOW-03（fan-out：detail/data_insufficient/source_degraded）
- **承载接口 / 模块**：可折叠详情组件 + 本地 UI 折叠态（M3，`useState<boolean>`）；`humanizeTrendState`（M2）
- **读取实现**：折叠区读 `mts.{trendState,scoreBand,signalType,alertLevel}` 原始枚举 + `reasons[].code`/`invalidators[].code` + retry/cache 技术态（EXC-03）；非常态经 `humanizeTrendState` 映射 `data_insufficient`→「数据不足」、`source_degraded`→「数据来源降级」人话
- **写入 / 状态迁移**：无领域写；折叠态为**组件本地 UI 状态**（DEC-S04），不写 localStorage / workspace 快照
- **条件 / 错误码**：默认折叠（收起）；技术态（retryState/cacheState）仅在折叠区、不外溢主视图（修正 App.tsx:641 泄漏）
- **原子性 / 并发 / 幂等**：折叠 toggle 为本地 setState、幂等（同一态多次点击结果确定）；无领域副作用
- **验证证据**：SCN-02-COND-03（Playwright 默认无原始字段 → 展开 → 出现；收起 / 展开两态截图）、COND-04（非 ready 人话 DOM 断言无枚举串）、NEG-04（UNKNOWN_CODE 不直呈）

### SUC-03-OP-01 — 主卡关键数字突出、明细折叠、免责保持
- **来源流步骤**：SUC-03-FLOW-01、SUC-03-FLOW-02（fan-out：collapsed/expanded）
- **承载接口 / 模块**：交易信号卡主 / 次层级结构（M4）；明细折叠本地态（M4 `useState`）；`nonAdvice` 常驻承载（M4，复用 `tradeSignal.nonAdvice` App.tsx:628-630）
- **读取实现**：主卡读 `tradeSignal.{stanceLabel,holding,levels}` + `tradeBacktest.{winRate,strategyReturnPct}`（关键数字默认呈现）；三段回测 / 反T回合 / 事件（App.tsx:590-627）降为次级、默认折叠；`tradeSignal.nonAdvice` 常驻（DEC-S08，不进折叠区）
- **写入 / 状态迁移**：无领域写；折叠态本地 UI 态
- **条件 / 错误码**：`status!=="ready"` → 无回测块（BR-07，衔接 NEG-02，不呈空回测容器）；`levels` 分正式信号位 vs ATR 观察位两层级（SCN-07-COND-03）
- **原子性 / 并发 / 幂等**：折叠 toggle 本地幂等；无领域副作用
- **验证证据**：SCN-05-COND-01（主 / 次层级差截图 + 次级降级样式 DOM 断言）、COND-02（nonAdvice 可见 DOM 断言）、SCN-07-COND-01（默认关键数字、无流水 DOM 断言）、COND-02（Playwright 折叠 / 展开）、COND-03（非 ready 无回测块 DOM 断言）、NEG-05（折叠态 nonAdvice 可见 Playwright）

### SUC-03-OP-02 — 非 ready status 人话化
- **来源流步骤**：SUC-03-FLOW-03（fan-out：not_target/data_insufficient/source_degraded）
- **承载接口 / 模块**：`humanizeTradeStatus(status): string`（M2）；一致性只读绑定（M4 ← 来源门控结果）
- **读取实现**：读 `tradeSignal.status`（STM-05）+ `tradeSignal.stanceLabel`（domain 已产出人话，trade-signals.ts:614/624/634/654/681）；`humanizeTradeStatus` 优先复用 `stanceLabel`；signal-topline(532) 现状直呈 `{tradeSignal.status}` 枚举串 → 替换为人话（复用 stanceLabel / 状态人话）
- **写入 / 状态迁移**：无（呈现层只读 STM-05，门控在 domain trade-signals.ts:619-627，不重实现 BR-03，DEC-S01）
- **条件 / 错误码**：`source_degraded`（来源≠formal）→「数据来源降级，暂不给出买卖价位」+ 无回测块；`not_target_symbol`→「该标的无定制策略信号」；`data_insufficient`→「数据不足以给出信号」
- **原子性 / 并发 / 幂等**：呈现幂等（来源恢复 formal 后重回 ready 呈现，EXC-02）；无写
- **验证证据**：SCN-02-COND-04（非 ready 承载文本无枚举串 DOM 断言 + 逐态截图）、NEG-01（来源 stale → 信号卡 source_degraded、不显 ready、不给价位，跨呈现一致性 Playwright）

### SUC-04-OP-01 — 侧栏主看突出 + 来源弱化小圆点
- **来源流步骤**：SUC-04-FLOW-01、SUC-04-FLOW-02（fan-out：normal/attention）
- **承载接口 / 模块**：侧栏条目结构承载（M5，App.tsx:428-449）；来源小圆点承载（M5，弱化次级、非主源）；`resolveSourceTone`（M2 复用，弱化上色）
- **读取实现**：读 `item.{name,symbol,market,status}`、`summary.{latestPrice,changePercent,sourceStatus}`；名称+代码一行、价格+涨跌右对齐主看；来源档 → 小圆点（`resolveSourceTone` 弱化：formal 中性圆点 / 非 formal 需关注弱提示圆点）；`archived` 条目弱化（STM-01，复用既有 `.watch-item.archived` App.tsx:455）
- **写入 / 状态迁移**：无（归档 / 恢复写侧属范围外既有逻辑，本任务只呈现区分）
- **条件 / 错误码**：`archived` → 弱化呈现区分 active；侧栏来源**不作来源状态权威主源**（呼应 SCN-03-COND-01，权威主源在 M6 顶部）
- **原子性 / 并发 / 幂等**：呈现幂等；无写
- **验证证据**：SCN-06-COND-01（条目结构截图 + DOM 断言）、COND-02（正常 / 需关注小圆点截图 + 来源承载非主源横幅 DOM 断言）、COND-03（archived 弱化样式 DOM 断言）、SCN-03-COND-01（侧栏来源非第二主源）

### SUC-05-OP-01 — 标题主位 + 控件降级右对齐
- **来源流步骤**：SUC-05-FLOW-01、SUC-05-FLOW-02
- **承载接口 / 模块**：顶部视觉层级结构承载（M6，顶部区重排）；不改 STM-06 切换语义
- **读取实现**：读 `selected.name`（OBJ-01）、`selectedLayout.mode`/STM-06（OBJ-06）；标题以最高字号 / 权重呈现主位；周期 / 视图（布局模式）控件降级、右对齐
- **写入 / 状态迁移**：无（布局切换语义 STM-06 由既有逻辑处理，本任务不改白名单 / 切换逻辑，DEC-S09）
- **条件 / 错误码**：非法布局值 → 既有 workspace 归一化回退 focus（EXC-05，本设计不新增失败分支）
- **原子性 / 并发 / 幂等**：呈现重排幂等；无写
- **验证证据**：SCN-04-COND-01（标题字号 / 权重 > 控件 DOM 断言 + 截图）、COND-02（各布局模式截图 + Playwright 切换后标题仍主位且切换生效）、NEG-06（非法值归一化、标题主位不变）

### SUC-06-OP-01 — 恢复态四档映射呈现语义
- **来源流步骤**：SUC-06-FLOW-01、SUC-06-FLOW-02（fan-out：restored/partial/default_fallback/failed）
- **承载接口 / 模块**：`resolveRestoreTone(metadata): Tone`（M2）；`RestoreStatus.tsx` 四档归位（M7，隔离现状对全态复用 `.data-notice`）
- **读取实现**：读 `metadata.{status,reason,discardedLayoutKeys,migratedFromLegacy,snapshotBytes}`（STM-07）；`resolveRestoreTone` 按 BR-10：`restored`→`normal`（中性 / 成功）、`partial`/`default_fallback`→`info`（信息级）、`failed` 或 `discardedLayoutKeys` 非空→`warning`（需关注）；技术态（reason/migratedFromLegacy/snapshotBytes）收进详情、不拼进主提示
- **写入 / 状态迁移**：无（呈现层只读 STM-07 一次性判定结果，快照读写属范围外既有逻辑）
- **条件 / 错误码**：`failed` / 坏布局丢弃 → warning 承载（合法归属）；恢复态承载**独立于来源态黄条**（DEC-S06 / NEG-03，STM-07 vs STM-02 两套独立状态机）
- **原子性 / 并发 / 幂等**：呈现幂等（会话内恢复结果固定）；无写
- **验证证据**：SCN-01-COND-04（restored/partial/default_fallback 无 `.notice--warning` 逐态截图 + DOM 断言）、COND-05（failed / 坏布局需关注承载 DOM 断言）、NEG-03（恢复承载与来源承载独立元素 DOM 断言）

**覆盖结论：9 / 9 个 `SUC-xx-OP-xx` 全部落技术映射，无缺口、无 N/A 豁免。** 三条操作间依赖（来源→MTS / 信号降级、ready→回测块、恢复态↔来源态分离）由 DEC-S06 承载为只读一致性绑定，见 §5.3。

---

## 3. 模块责任

> 每个模块追溯到方案决策（DEC-Sxx）、系统操作、系统用例、验收场景或业务规则；说明复用 / 扩展 / 替换 / 隔离边界（用 dependency-impact 真实 file:line）。

### M1 — 四档语义色 token 层（`src/styles.css`）
- **职责**：建立四档语义色 token（正常 / 信息 / 谨慎-风险 / 警告-异常），承载类名互不复用；提供 notice variant 类替换范围内 `.data-notice` 用法；提供评分极性 tone 类。
- **禁止职责**：不改 `styles.css:379` `.data-notice` 颜色 / 背景 / 边框定义（SR-01 红线，9 处共享、范围外 5 处依赖）；不改 `.up`/`.down`（403-409）；不改范围外组件样式。
- **设计（token 结构与命名）**：
  - CSS 自定义属性（四档）：`--tone-normal`（中性 / 成功，可无色）、`--tone-info`（信息级 / 次级提示）、`--tone-caution`（谨慎-风险 = 市场看空业务结论）、`--tone-warning`（警告-异常 = 数据 / 恢复故障，可沿用既有琥珀 `#f0c75e` 族但为**新类**、非 `.data-notice`）。
  - notice variant 承载类（替换范围内用法，独立于 `.data-notice`）：`.notice--info`、`.notice--warning`。**类名与 `.data-notice` 不同**，故不波及范围外。
  - 评分 / 卡片极性 tone 类：`.tone-positive`、`.tone-caution`、`.tone-neutral`（或形式化既有 `.signal-card.positive/.risk/.watch`）。核心约束（INV-03）：`caution`（市场看空）承载类名 ≠ `warning`（来源 / 恢复故障）承载类名；两者色物理可辨。
  - 进度条承载类：`.score-bar`（新，VO-03 可读评分）。
- **DEC-01 / demo_fallback 可切换档（DEC-S07）**：`demo_fallback` 默认映射 `--tone-info`；承载结构设计为**改一处映射即可切换档**（`resolveSourceTone` 内 `demo_fallback` 分支从 `info` 改 `warning`，CSS 类不变），若用户改判「需关注」切换成本最小、不改承载元素结构。
- **追溯**：DEC-S02、SR-01；INV-01/02/03；VO-01/03；SCN-01-COND-01~06；SUC-01-OP-01、SUC-02-OP-01、SUC-06-OP-01。
- **边界**：扩展（新增 token + 类）+ 隔离（不动共享类定义）。

### M2 — 只读呈现映射层（新增 `src/features/presentation/`）
- **职责**：纯只读函数，领域状态 → 语义档 / 人话文案。承载 POL-01（四档色映射）、POL-02（人话翻译）、POL-03（一致性只读同步）。
- **落点与理由**：新建 `src/features/presentation/tone.ts` + `humanize.ts`（`src/features/*` 在范围内）。**不放 `src/lib/signals.ts`**（该处含 domain-adjacent 计算，改动风险触碰算法，越界 RISK-06）；**不放 `src/domain/*`**（FB-09 禁改）。复用 / 重构既有 `mtsTone`(App.tsx:94)、`tradeSignalTone`(App.tsx:101)、`sourceStatusLabel`(App.tsx:86) 迁入本模块，收敛 tone / 人话解析入口。
- **禁止职责**：不重实现 BR-03 降级门控（DEC-S01，门控在 trade-signals.ts:619-627 只读消费）；不新建枚举→文案映射表（FB-04，复用既有源）；不改 domain 计算。
- **函数清单**：`resolveSourceTone`、`resolveScoreTone`、`resolveRestoreTone`（tone.ts）；`humanizeTradeStatus`、`humanizeTrendState`、`humanizeReason`（humanize.ts，`humanizeReason` 复用 `resolveMtsReason(code).label` 含 UNKNOWN_CODE 回落）。
- **追溯**：DEC-S01、DEC-S03；POL-01/02/03；VO-02/03；SUC-01-OP-01、SUC-02-OP-01/02、SUC-03-OP-02、SUC-06-OP-01。
- **边界**：新建（隔离于 domain）+ 复用既有人话源。

### M3 — MTS 卡人话化 + 进度条 + 折叠详情（`src/App.tsx` mts-card 段 634-678）
- **职责**：主视图 0 裸枚举 / 0 裸理由码；`score-grid`(650-656) 的 `trend_state`/`mts_score`/`score_band`/`signal_type`/`alert_level` 裸枚举收进折叠详情；`displayLabel`/`technicalReminder` 保留人话；`mtsScore` 进度条化（`<ScoreBar>`）；ReasonRegistry 的 `reasons.map`(667) 与 `invalidators.map`(673) **双处**由 `<code>{item.code}</code>` 改为人话（`item.label` 若有则用，否则 `humanizeReason(item.code)` = `resolveMtsReason(code).label`，UNKNOWN_CODE 回落）；折叠态本地 `useState`。
- **迁移 `.data-notice`（范围内 2 / 4）**：`App.tsx:640`(signal-degradation-note)、`App.tsx:645`(signal-error-note) → `.notice--warning`（来源降级 / 错误合法归属 warning 档）；retry 技术态（641）收进折叠详情、不外溢。
- **追溯**：DEC-S02/S03/S04；SUC-02-OP-01/02；SCN-02-COND-01/02/03/04；INV-04；BR-04/05；GAP-D1。
- **边界**：扩展（App.tsx 内聚重排）+ 隔离迁移（范围内 data-notice）。

### M4 — 交易信号卡密度 + 层级 + nonAdvice 常驻 + 折叠（`src/App.tsx` trade-signal-card 段 528-632）
- **职责**：主卡突出 `stanceLabel`(534) + 关键数字（胜率 / 累计收益，tradeBacktest 620-627）；三段回测 / 反T回合 / 事件（590-627）降次级、默认折叠（本地 `useState`）；signal-topline(532) 非 ready 直呈 `{tradeSignal.status}` → `humanizeTradeStatus`；`nonAdvice`(628-630) 常驻（DEC-S08，不进折叠区）；`levels` 分正式信号位 vs ATR 观察位层级（SCN-07-COND-03）。
- **禁止职责**：`status!=="ready"` 不呈回测块（BR-07 / NEG-02）；折叠不隐藏 nonAdvice（INV-06 / NEG-05）。
- **追溯**：DEC-S04/S08；SUC-03-OP-01/02；SCN-05-COND-01/02、SCN-07-COND-01/02/03；INV-04/06；BR-07。
- **边界**：扩展（App.tsx 内聚重排）。

### M5 — 侧栏条目结构 + 来源小圆点 + archived 弱化（`src/App.tsx` watchlist 段 428-466）
- **职责**：名称+代码一行、价格+涨跌右对齐主看（435）；来源 `sourceStatusLabel` 文本 → 小圆点弱化（`resolveSourceTone` 弱化上色）；`archived` 条目弱化（复用 `.watch-item.archived` 455）；侧栏来源**非来源权威主源**。
- **追溯**：DEC-S05/S02；SUC-04-OP-01；SCN-06-COND-01/02/03、SCN-03-COND-01；STM-01；BR-02。
- **边界**：扩展（App.tsx 内聚）。

### M6 — 顶部层级重排 + 唯一主源承载点（`src/App.tsx` 顶部 / market-workspace 段）
- **职责**：标题主位 + 周期 / 视图控件降级右对齐（SUC-05-OP-01）；**指定唯一主源承载点**（GAP-D3）：
  - **来源状态权威主源** = 顶部区单一承载（`data-testid="source-authority"`，计数=1，读 `getSourceStatus`）。派生一致性指示（ChartSurface `chart-source-status`/`chart-degradation-note`、MTS 卡降级子集、信号卡 source_degraded）是**受影响面 / 一致性呈现**（语义 = 「本承载面受来源影响」），非重复来源主源，各自独立 testid、不计入来源权威计数。
  - **价格 / 涨跌权威主源** = 顶部 quote-line 单一承载（`data-testid="price-authority"`，计数=1）。侧栏 per-item 价格（M5）为列表扫读角色，不同层。
- **去重后被降级 / 移除的重复呈现点清单**：侧栏来源文本 → 小圆点（M5 降级）；顶部 / 图表 / 指标条多处来源同级呈现 → 收敛到 `source-authority` 单点（其余转派生一致性指示或移除）。
- **禁止职责**：不改 STM-06 切换语义（DEC-S09）。
- **追溯**：DEC-S05/S09；SUC-05-OP-01、SUC-01-OP-02；SCN-03-COND-01/02、SCN-04-COND-01/02；UIC-03/04；INV-05。
- **边界**：扩展（App.tsx 顶部结构重排）。

### M7 — RestoreStatus 四档归位（`src/features/restore/RestoreStatus.tsx`，唯一调用方 App.tsx:471）
- **职责**：现状对全部四态复用 `.data-notice`(16) → 按 `resolveRestoreTone` 四档分色（restored=normal、partial/default_fallback=info、failed / 坏布局=warning）；技术态（reason/discardedLayoutKeys/migratedFromLegacy/snapshotBytes）收进详情、正常态不染警告色。
- **迁移 `.data-notice`（范围内 1 / 4）**：`RestoreStatus.tsx:16` → 四档 `.notice--*`（restored 中性 / 成功、partial+default_fallback `.notice--info`、failed+坏布局 `.notice--warning`）。
- **禁止职责**：不改快照读写 / STM-07 判定逻辑（范围外既有）。
- **追溯**：DEC-S02/S06；SUC-06-OP-01；SCN-01-COND-04/05；INV-01/02；BR-10/11；NEG-03。
- **边界**：替换（该组件呈现承载）+ 隔离（单一调用方，无跨组件破坏）。

### M8 — ChartSurface 范围内 data-notice 迁移（`src/features/chart/ChartSurface.tsx:207`）
- **职责**：`chart-degradation-note`(207) `.data-notice` → `.notice--warning`（来源降级合法 warning 档）；chart-source-status(203) 作派生一致性指示、非来源权威主源（M6 收敛）。
- **迁移 `.data-notice`（范围内 1 / 4）**：`ChartSurface.tsx:207` → `.notice--warning`。
- **追溯**：DEC-S02；SUC-01-OP-01；SCN-01-COND-03；INV-02。
- **边界**：隔离迁移（范围内用法）。

### 范围外零改动（硬约束，SR-01）
- **不改**：`AlertRulePanel.tsx:136`、`LayoutController.tsx:75/121`、`WorkbenchShell.tsx:78/135` 5 处 `.data-notice` 用法**零改动**；`styles.css:379` `.data-notice` 颜色定义**禁改**。这 5 处继续引用原 `.data-notice`，只要不改其定义即零可观察变化。

**范围内 `.data-notice` 迁移清单汇总（4 处，M3+M7+M8）**：`App.tsx:640`、`App.tsx:645`（M3）、`RestoreStatus.tsx:16`（M7）、`ChartSurface.tsx:207`（M8）→ 全部迁到 `.notice--info`/`.notice--warning` 新类，不动共享 `.data-notice` 定义。

---

## 4. 接口设计

> 呈现映射函数与组件 props 的变更前 / 变更后、调用方、输入、输出、错误语义、兼容影响。全部为呈现层内接口，无新增外部 API / 依赖（FB / DEC-S01 集成方向）。

| 接口 | 变更前 | 变更后 | 调用方 | 输入 | 输出 | 错误 / 回落语义 | 兼容影响 |
|------|--------|--------|--------|------|------|----------------|----------|
| `resolveSourceTone(status)` | 无（现 `sourceStatusLabel` 仅出文本 App.tsx:86-92） | 新增（M2） | M5 侧栏、M6 顶部、M8 图表 | `SourceStatus`（five 态） | `Tone`：normal/info/warning | 未知 status → normal 兜底（防御） | 新增，无破坏 |
| `resolveScoreTone(mts)` | `mtsTone`(App.tsx:94-99) 返回 positive/risk/neutral | 重构迁入 M2，语义档化（positive/caution/neutral） | M3 MTS 卡 | `MtsExplanation` | `Tone` | scoreBand 缺省 → neutral | 内聚重构，行为等价（现 risk 红框 → caution 谨慎档，类名不复用来源 warning） |
| `resolveRestoreTone(metadata)` | 无（RestoreStatus 无分档，全 `.data-notice`） | 新增（M2） | M7 RestoreStatus | `WorkspaceRestoreMetadata` | `Tone`：normal/info/warning | 未知 status → warning（保守，恢复态兜底见警告优于漏报） | 新增，无破坏 |
| `humanizeTradeStatus(status)` | 无（App.tsx:532 直呈 `{tradeSignal.status}`） | 新增（M2），优先复用 `stanceLabel` | M4 信号卡 | `TradeSignalStatus` | 人话 string | 缺省 → stanceLabel 兜底 | 新增，无破坏 |
| `humanizeTrendState(trendState)` | 无（App.tsx:651 直呈 `trend_state {mts.trendState}`） | 新增（M2） | M3 MTS 卡 | `trendState` | 人话 string | 缺省 → 「—」占位 | 新增，无破坏 |
| `humanizeReason(code, detail?)` | 无（App.tsx:667/673 直呈 `<code>{item.code}</code>`） | 新增（M2），= `resolveMtsReason(code).label` | M3 ReasonRegistry（reasons + invalidators 双处） | `MtsReasonCode` | 人话 label string | **未注册码 → `resolveMtsReason` 回落 UNKNOWN_CODE**（mts-registry.ts:161，既有），不直呈原始 code（NEG-04） | 新增，复用既有回落，无破坏 |
| `<ScoreBar score={mtsScore}>` | 无（现 `mts_score {mts.mtsScore ?? "--"}` 裸数字 App.tsx:652） | 新增进度条组件（M3） | M3 MTS 卡 | `mtsScore: number \| null` | 进度条 DOM | null/not_applicable → 中性不填充（VO-03，不误导性满条） | 新增，无破坏 |
| `RestoreStatus({metadata})` props | `{metadata}`（16 行全态 `.data-notice`） | props 不变，内部按 `resolveRestoreTone` 四档分色 + 技术态收详情 | App.tsx:471（唯一） | `WorkspaceRestoreMetadata` | 四档承载 DOM | failed 兜底 warning | props 签名不变，纯呈现变更，单一调用方无破坏 |
| 折叠组件本地态 | 无折叠（回测流水默认铺开、原始字段直呈） | `const [expanded,setExpanded]=useState(false)`（M3/M4） | M3 MTS 详情、M4 信号卡明细 | — | 展开 / 收起 | 默认收起；不持久化（DEC-S04 / FB-07） | 新增本地态，无跨组件影响 |

**`Tone` 类型**：`type Tone = "normal" | "info" | "caution" | "warning" | "positive" | "neutral"`（映射到 M1 CSS 类；来源 / 恢复用 normal/info/warning，评分极性用 positive/caution/neutral，二者类名不复用以保 INV-03）。类型可置于 M2 或 `src/types.ts`（若需共享类型，`src/types.ts` 在呈现引用面，仅加类型不改既有字段，兼容）。

---

## 5. 数据与状态设计

### 5.1 数据模型 / 领域写入
- **全为读侧**：`N/A: 本任务无领域写入、无数据模型变更、无 schema、无迁移、无持久化`（BC-01 只读消费 BC-02，Domain Commands / Events 均不适用，product-domain-model §Tactical DDD）。所有承载读 `mts.*`/`tradeSignal.*`/`tradeBacktest.*`/`metadata.*`/`sourceHealth.*`/`item.*` 既有字段，不新增字段、不写回。

### 5.2 状态设计（折叠 UI 态）
- **折叠 / 展开 = 组件本地 UI 状态**（DEC-S04）：`useState<boolean>`，承载于 M3（MTS 详情）、M4（信号卡明细）。
- **禁止**：不写 `localStorage`、不写 workspace 快照 / OBJ-06、不进 URL query（FB-07 / DEC-S04 越界 SCOPE-12）。刷新后回默认折叠态（use-case-model ST-02e/ST-03f 定性为纯 UI 态，无需持久化）。
- **展开 / 收起入口**：每个 fan-out 折叠区必须有可操作入口（按钮 / disclosure），不靠 URL 到达（RISK-02）。

### 5.3 不变量结构保证（INV-01~07 如何在结构上保证，非临场处理）

| 不变量 | 结构保证方式 | 承载模块 |
|--------|-------------|----------|
| INV-01（正常态 0 警告色） | `resolveSourceTone`/`resolveRestoreTone`/`resolveScoreTone` 把 formal/not_loaded/restored/partial/default_fallback/positive/neutral 映射到 normal/info，**永不映射到 `.notice--warning`**；正常态承载类不含 warning | M1/M2/M3/M7 |
| INV-02（真异常见警告 + 受影响范围） | stale/unavailable/failed/坏布局 → `.notice--warning` + 读 `degradationReason`/`affectedObjects`/`discardedLayoutKeys` 拼受影响范围 | M2/M3/M7/M8 |
| INV-03（负向评分谨慎色 ≠ 来源故障色，类名不复用） | `caution` tone 类名与 `warning` notice 类名在 M1 **物理分离**；`resolveScoreTone` 负向 → caution（非 warning）；现状 `.signal-card.risk` 红框 vs `.data-notice` 琥珀 banner 已分离，token 层形式化 | M1/M2 |
| INV-04（主视图 0 裸枚举 / 裸理由码；技术态折叠；未注册码不直呈） | score-grid 裸枚举 + reasons/invalidators 的 `item.code`(667/673) 全部经 `humanize*` 转人话或收折叠区；`humanizeReason` 走 UNKNOWN_CODE 回落 | M2/M3 |
| INV-05（来源 / 价格各计数=1 主源；涨跌≠警告色） | `source-authority`/`price-authority` 单点承载 + DOM 计数断言；涨跌用独立 `.up`/`.down`（物理独立，§1.1 CONFIRMED） | M6/M1 |
| INV-06（nonAdvice 常驻，折叠不隐藏） | `nonAdvice`(628-630) 置于主卡常驻区、**结构上不进折叠容器**（DEC-S08） | M4 |
| INV-07（跨呈现一致性：来源 stale → 信号卡 source_degraded；恢复态 vs 来源态独立黄条） | 见 §5.4 只读一致性绑定 | M4/M6/M7 |

### 5.4 跨呈现一致性只读绑定（DEC-S06，三处读同一门控结果）
- **单一门控源**：来源降级门控在 domain `trade-signals.ts:619-627`（`sourceHealth.status!=="formal"→status:"source_degraded"`），呈现层**只读消费**，不重实现（DEC-S01）。
- **三处一致读取路径**：① 来源权威承载（M6，读 `getSourceStatus`/`sourceHealth.status`）；② MTS 卡降级子集（M3，读同一 `sourceHealth.status`）；③ 交易信号卡（M4，读 `tradeSignal.status`——该 status 已由 domain 门控产出 source_degraded）。三者读同一 domain 结果 → 结构上不可能出现「来源 stale 而信号卡仍 ready」（NEG-01）。
- **恢复态 vs 来源态独立**：M7（STM-07 恢复态，`resolveRestoreTone`）与 M6（STM-02 来源态，`resolveSourceTone`）用**独立 DOM 元素 + 独立 tone 承载**，不共用同一 banner（NEG-03，两套独立状态机）。

---

## 6. 生产就绪要求

| 要素 | 设计 | 验证方式 |
|------|------|----------|
| **错误处理** | 未注册理由码 → `resolveMtsReason` 回落 `UNKNOWN_CODE`（mts-registry.ts:161），不直呈原始 code（NEG-04）；缺失字段：`mtsScore` null → 进度条中性不填充、价格无值 → 「—」占位、未知 status → tone 保守兜底（来源 normal / 恢复 warning）。所有回落为呈现幂等、无异常抛出 | NEG-04 DOM 断言（无未解析 code）；缺失字段逐态截图 |
| **兼容性** | **范围外 5 处 `.data-notice` 零改动**（AlertRulePanel:136、LayoutController:75/121、WorkbenchShell:78/135）；**不改 `styles.css:379` 颜色定义**（SR-01）；新增均为 additive（新 CSS 类 / 新函数 / 新组件），既有 `.up`/`.down`/`.signal-card.*` 保留；`RestoreStatus` props 签名不变；`src/types.ts` 若加 `Tone` 类型为纯新增不改既有字段 | 范围外组件改造前后 preview 截图无变化 + DOM 断言其承载未被重着色（SR-01 通过判据：范围外零可观察变化）；NEG-07 E2E 既有用户路径不回归 |
| **可观测性** | `N/A: 纯前端呈现层 CSS/JSX 变更，无运行时副作用、无网络 / 存储 / 后端调用，无需新增日志 / 埋点 / 监控`；验证依赖既有 tests/e2e + axe + preview 截图 + build，已足够 | 不适用（说明理由） |
| **回滚 / 降级** | 纯前端呈现层，回滚 = git revert 对应 commit；新类 / 新函数 / 新组件均 additive，移除即恢复现状；无数据 / schema / 迁移、无持久化态，无需数据回滚；`demo_fallback` 色档可切换（DEC-S07，改一处映射不改结构） | `npm run build`(tsc --noEmit && vite build) exit 0 作前提；回滚后既有 E2E 通过 |

---

## 7. 风险验证策略

> 每个关键模块 / 接口 / 状态变更 / 风险绑定验证手段，说明证明什么行为 / 约束 / 风险。绑定 SR-01 + RISK-01~07；覆盖 dependency-impact GAP-D1 / GAP-D3。`npm run build` exit 0 为所有验证前提（EVD-01），不单独构成验收通过。

| 风险 / 目标 | 验证手段 | 证明什么 | 覆盖条件 |
|-------------|----------|----------|----------|
| **SR-01**（共享类爆炸半径） | 范围外组件（AlertRulePanel/LayoutController/WorkbenchShell）改造前后 preview 截图并置 + DOM 断言其承载仍引用原 `.data-notice`、未被重着色；grep 断言 `.data-notice` 定义未改 | 范围内迁移未波及范围外 5 处、共享类定义未动（阻断类硬约束） | 通过判据：范围外零可观察变化 |
| **RISK-01 / GAP-D2**（demo_fallback 定档） | formal / demo_fallback / stale 三档并置 preview 截图可辨识；verify 前经用户确认定档 | demo_fallback 默认信息级、可辨识兜底数据、非高危警告色；改判则切换承载色档不改结构 | SCN-01-COND-02 |
| **RISK-02**（折叠义务丢失） | E2E（Playwright）：默认态断言明细 / 原始字段不可见 → 点击展开 → 断言可见；收起 / 展开两态截图 | 折叠入口本地承载可操作、义务未因 interaction 跳过而丢失 | SCN-02-COND-03、SCN-07-COND-02 |
| **RISK-03 / GAP-D1**（人话源 / 裸枚举穷举） | DOM 断言主视图文本**不含** `trend_state`/`mts_score`/`score_band`/`signal_type`/`alert_level` 前缀（App.tsx:651-655）与理由码 `item.code`（**reasons 667 + invalidators 673 双处**）；Playwright 文本断言；映射清单核对既有人话源覆盖全部枚举点 | 主视图 0 裸枚举 / 0 裸理由码、复用既有源无缺口 | SCN-02-COND-01/04、NEG-04；GAP-D1 穷举（含 score-grid + ReasonRegistry reasons/invalidators） |
| **RISK-04 / INV-07**（一致性门控只读） | E2E：构造 stale 来源态 → 断言信号卡呈 source_degraded、不显 ready、不给价位（NEG-01）；DOM 断言恢复承载与来源承载为独立元素（NEG-03） | 呈现层只读同一 domain 门控结果、三处一致、未重实现门控；恢复态与来源态独立黄条 | NEG-01、NEG-03、SCN-02-COND-04 |
| **RISK-05**（层级 / 突出 / 弱化主观项） | 主观项（SCN-05-COND-01 层级差、SCN-04-COND-01 标题主位、SCN-06 侧栏）preview 截图 + 次级 / 权重样式 DOM 断言**双证据** | 主观项落成可观察判定（截图 + 样式断言） | SCN-04-COND-01、SCN-05-COND-01、SCN-06-COND-01 |
| **RISK-06**（升级关口） | 若发现呈现目标无法在 domain / 后端 / 共享类颜色不变前提下达成 → 停下升级决策关口，不擅自扩范围 | 未越界改算法 / 后端 / 数据 | 当前判定未触发（DMF 总体结论未发现需新增对象 / 规则） |
| **RISK-07 / NEG-07**（可访问性 + E2E 无回归） | axe 扫描无新增违规 + Playwright E2E 既有用户路径不回归；`npm run build` exit 0 前提 | 改造不引入 axe 回归、既有路径不破坏 | NEG-07 |
| **唯一主源 / GAP-D3** | DOM 断言 `data-testid="source-authority"` 计数=1、`data-testid="price-authority"` 计数=1；被降级 / 移除重复点清单核对（§3 M6）；涨跌色 vs 警告色并置截图 | 来源 / 价格各唯一权威主源、涨跌红绿 ≠ 警告色 | SCN-03-COND-01/02 |
| **逐档并置（INV-01~03 色分档）** | 来源五档 / 恢复四档 / 评分正负 各态 preview 截图逐档并置；negative 评分与 stale 来源同批并置证物理区分 | 四档色分档正确、正常态 0 警告、看空 ≠ 故障 | SCN-01-COND-01~06 |
| **折叠 + 布局切换 E2E** | Playwright：折叠展开、布局模式（dense/focus/mobile_tab）切换后断言标题仍主位且切换生效 | 折叠交互 + 顶部层级 + STM-06 语义不变 | SCN-04-COND-02、SCN-07-COND-02、NEG-06 |

---

## 8. 对现有系统影响

| 维度 | 结论 |
|------|------|
| 影响范围 | 呈现层内聚：`src/styles.css`（M1 新增 token / 类）、`src/App.tsx`（M3/M4/M5/M6 段内重排）、`src/features/restore/RestoreStatus.tsx`（M7）、`src/features/chart/ChartSurface.tsx`（M8）、新增 `src/features/presentation/`（M2）；`src/types.ts` 可选加 `Tone` 类型 |
| 破坏性变更 | **无**（dependency-impact 3.4 CONFIRMED）。前提：不改 `.data-notice` 颜色定义、新增类而非改共享类、App.tsx 内聚重排、折叠本地态不持久化 |
| 回归面 | 范围外 5 处 `.data-notice` 组件（零改动，需截图 + DOM 断言证零变化）；既有 E2E 用户路径（NEG-07 回归）；`.up`/`.down` 涨跌色（不改）；`src/domain/*` / `src/lib/signals.ts`（不改，只读消费） |
| 不触碰 | `src/domain/*`（FB-09）、后端 / 数据源、alibaba 在途代码、`styles.css:379` 颜色定义（SR-01）、范围外 5 处用法、STM-06 切换语义 |

---

## 9. 技术分析 open items 处理摘要（对齐 solution §8 交接 9 项）

| solution §8 后续主题 | 本设计处理 | 落点 |
|----------------------|-----------|------|
| 语义色 token 与 CSS 结构 | 四档 token + notice variant + score tone 类命名、范围内 4 处迁移清单、不改共享定义 | M1、§3 迁移清单 |
| 呈现映射接口 | `resolve*Tone` / `humanize*` 函数签名、复用既有人话源、UNKNOWN_CODE 回落 | M2、§4 |
| 折叠交互状态 | 组件本地 `useState`、展开入口、默认折叠、nonAdvice 常驻不进折叠 | M3/M4、§5.2 |
| 去重复承载点 | `source-authority`/`price-authority` 计数=1 选点 + 被降级清单（GAP-D3） | M6 |
| 跨呈现一致性 | 三处只读同一门控结果、恢复 vs 来源独立承载 | §5.4 |
| 恢复态承载归位 | RestoreStatus 四档分色、技术态收详情 | M7 |
| 顶部与信号卡结构 | 标题主位 / 控件降级、信号卡主 / 次层级、ATR 观察位分层 | M4/M6 |
| demo_fallback 可切换档 | 默认 info、改一处映射即切换、不改结构（DEC-S07） | M1/M2 |
| 验证策略 | 逐档截图 + DOM 断言 + E2E + axe + build，覆盖 SR-01/RISK/GAP-D1/D3 | §7 |

**遗留 open items / needs_decision**：仅 GAP-D2（demo_fallback 最终色档，产品 DEC-01）为 verify 前用户决策，已按 DEC-S07 设计为可切换、不阻断技术设计；本设计无新增 needs_decision、无 BLOCKED。

---

## 10. 摘要（交主流程登记 execution_result）

- **状态**：`DONE`
- **input_sufficiency**：全部 `fit`（产品定义 / 用例、solution、现状代码证据均 fit，现状 §1.1 全 CONFIRMED）
- **系统操作覆盖**：9 / 9 `SUC-xx-OP-xx` 全落技术映射（§2），无缺口、无 N/A 豁免
- **核心模块**：M1 四档语义色 token（styles.css）、M2 只读呈现映射层（新增 src/features/presentation/）、M3 MTS 卡人话化+进度条+折叠、M4 信号卡密度+层级+nonAdvice+折叠、M5 侧栏结构+来源小圆点、M6 顶部层级+唯一主源计数=1、M7 RestoreStatus 四档归位、M8 ChartSurface data-notice 迁移
- **接口变更**：9 项（resolveSourceTone/resolveScoreTone/resolveRestoreTone/humanizeTradeStatus/humanizeTrendState/humanizeReason/`<ScoreBar>`/RestoreStatus 内部四档/折叠本地态）；无新增外部 API / 依赖
- **数据 / 状态结论**：全读侧，无领域写入 / 无数据模型变更 / 无迁移 / 无持久化；折叠为组件本地 UI 态；INV-01~07 结构保证；DEC-S06 三处只读一致性绑定
- **生产就绪四要素**：齐（错误处理=UNKNOWN_CODE + 缺失字段回落；兼容性=范围外 5 处零改动 + 不改共享定义；可观测性=N/A 附理由；回滚=git revert additive）
- **验证覆盖风险**：SR-01（爆炸半径隔离）、RISK-01（demo_fallback 档）、RISK-02（折叠义务）、RISK-03/GAP-D1（裸枚举穷举含 App.tsx:651-655 + ReasonRegistry reasons/invalidators 667/673）、RISK-04/INV-07（一致性只读 NEG-01/03）、RISK-05（主观项双证据）、RISK-06（升级关口）、RISK-07/NEG-07（axe + E2E）、GAP-D3（唯一主源计数=1）
- **禁用做法遵守**：不改 domain / 共享类颜色 / STM-06；不新建映射表；折叠不持久化；nonAdvice 不进折叠区；范围外零改动
- **遗留**：GAP-D2（demo_fallback 定档）verify 前用户决策，不阻断；无 BLOCKED、无新增 needs_decision
- **contract_update 建议**：`execution_result=DONE`；`prototype_coverage_exemptions=[]`（无 SURF / PS 承载义务，interaction 跳过）；`modules=8`；`interfaces=9`；`data_or_state_changes=0`（全读侧，折叠为本地 UI 态）；`verification_items=12`；`system_use_case_ops_covered=9/9`；`blocked_items=none`
