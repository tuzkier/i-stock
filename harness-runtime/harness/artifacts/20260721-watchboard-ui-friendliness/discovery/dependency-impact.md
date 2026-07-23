# 依赖与影响评估（Dependency & Impact）：看盘界面友好化改造

> **任务编号（mission-id）：** 20260721-watchboard-ui-friendliness
> **阶段：** discovery / dependency-impact（tech-design 前置）
> **来源：** integration-impact-expert
> **上游输入：** `mission-contract.md`、`solution/solution.md`（SR-01 / DEC-S01~S09 / 禁止路径）、`product/product-domain-model.md`（BC-01↔BC-02 / INV-01~07 / POL-01~03 / STM-07）、`project-context.md`
> **取证方式：** 对 `src/` 实际 Grep/Read（文件:行）；每条结论标注置信度与证据；无源码命中才标 `[ASSUMED]` + 验证动作。
> **反幻觉声明：** 本文不使用「可能 / 大概 / 应该」判断依赖存在性；所有 blast radius 结论均有 grep/read 命中或明确 N/A 排除依据。

---

## 0. 结论速览

- 本任务为**纯前端呈现层 brownfield 改造**（既有多市场看盘系统），无基础设施依赖、无外部系统 / 新 API 依赖。
- 真实依赖关切集中在**第三层自身代码 blast radius**：共享告警类 `.data-notice` 跨范围内外组件（SR-01 爆炸半径），以及呈现层对既有人话源与 domain 门控输出的只读复用面。
- **Blockers：0**（无阻断性依赖缺口）。核心迁移边界（范围内 4 处 vs 范围外 5 处 `.data-notice`）已用源码取证坐实，可支撑 tech-design 迁移清单。

---

## 第一层：基础设施依赖（DB / Queue / Job / Cache / 存储 / 配置）

**结论：N/A（无基础设施依赖）** — CONFIRMED。

| 基础设施类别 | 核查结论 | 证据 |
|--------------|----------|------|
| 数据库 / schema / 迁移 | 无 | mission-contract:69「非目标…不改数据源/后端/server」；contract 治理块「不涉及…数据迁移/删除」（mission-contract:178）；`src/` 无 ORM / migration / schema 文件（`find src` 仅 tsx/ts 呈现与 domain 逻辑，无 db/migrations 目录） |
| 消息队列 / 事件总线 | 无 | 产品领域模型 Domain Events「不适用：本任务无领域写入」（product-domain-model.md:159-165）；grep 无 queue/broker 引用 |
| 定时任务 / Job | 无 | 无 cron/scheduler；`package.json` scripts 仅 dev/build/test/backtest（package.json:6-17），无 job runner |
| 缓存 / 派生状态 | 无（本任务不改） | 折叠态为组件本地 UI state，不持久化（solution DEC-S04）；`localStorage` 快照恢复属既有 OBJ-06，本任务只读呈现恢复态（RestoreStatus.tsx），不写快照 |
| 存储 / 配置 | 无写入 | solution §4 数据/状态方向「禁止新增 localStorage 键 / workspace 快照写入」；折叠态不进快照 |

**排除依据：** 变更格式限 `src/styles.css` + `src/App.tsx` + `src/features/*` 的 JSX/CSS（mission-contract:67, 253），无任何持久化 / 中间件 / 部署配置改动。

---

## 第二层：外部业务系统 / 外部 API 依赖

**结论：N/A（无外部系统依赖、无新增 API）** — CONFIRMED。

| 外部维度 | 核查结论 | 证据 |
|----------|----------|------|
| 新外部 API / 协议 | 无 | mission-contract 治理块硬触发项=无「不涉及…新外部 API」（mission-contract:178）；solution DEC-S01 集成方向「无新增外部依赖 / API / secret；仅前端组件内消费既有 domain 输出」（solution.md:92, 254） |
| 第三方 SDK / 组件库 | 禁止新增 | solution §3.3 Route C 被排除「不得新增组件库依赖」（solution.md:80）；DEC-S03「不新建映射表、复用既有源」 |
| 数据源 / 后端 server | 只读不改 | mission-contract 非目标「不改数据源/后端/server」；行情来源健康档由 BC-02 既有计算，本任务只读消费其 `sourceHealth.status` 输出 |
| 跨团队 / 跨 mission 接口 | 边界隔离 | mission-contract 范围外「不触碰 alibaba mission（20260720）在途策略代码语义」（mission-contract:105, 246）；solution §4「不触 alibaba 在途代码」 |

### dep-impact trigger 误命中说明（逐条排除）

本任务被 dependency-impact 技能触发，其 `external_api` / `data_migration` 信号**均来自任务契约的非目标否定行**（误命中），已逐条核实为「否定式排除」而非真实依赖：

- `external_api` 信号源 = mission-contract:178「**不**涉及…新外部 API」→ 否定行，实为无外部 API 依赖。
- `data_migration` 信号源 = mission-contract:178「**不**涉及…数据迁移/删除」→ 否定行，实为无数据迁移。

二者均为契约声明的**范围排除**，不构成实际依赖面。

---

## 第三层：自身代码 blast radius（本任务核心）

### 3.1 `.data-notice` 用法全量普查（SR-01 爆炸半径事实清单）

**定义点（唯一）：** `src/styles.css:379` — 黄色告警样式（`color:#f0c75e; background:rgba(240,199,94,.1); border:…rgba(240,199,94,.2)`，styles.css:379-388）。此定义被下列**全部 9 处用法**共享。

**总计 9 处用法，跨 6 个文件。范围内 4 处 / 范围外 5 处。** —— CONFIRMED（grep 全量命中）。

| # | 文件:行 | data-testid | 语义 | 范围 | 判定依据 |
|---|---------|-------------|------|------|----------|
| 1 | `src/App.tsx:640` | `signal-degradation-note` | 来源降级提示（信号卡） | **范围内** | App.tsx 主视图呈现层；solution SR-01 明列 App.tsx:640；DRV-01 |
| 2 | `src/App.tsx:645` | `signal-error-note` | 来源重试失败（信号卡） | **范围内** | 同上；App.tsx 主视图来源错误提示 |
| 3 | `src/features/restore/RestoreStatus.tsx:16` | `restore-status` | 恢复态四态提示 | **范围内** | solution DRV-10 明列「含 `RestoreStatus.tsx`」；STM-07 恢复态归位（DEC-S02/S06）；现状对**全部**恢复态（含 restored/partial 正常态）复用 `.data-notice`（RestoreStatus.tsx:7-20）——SCN-01 缺陷根因 |
| 4 | `src/features/chart/ChartSurface.tsx:207` | `chart-degradation-note` | 图表来源降级提示 | **范围内** | solution SR-01 明列 ChartSurface.tsx:207；features/* 看盘主视图组件 |
| 5 | `src/features/alerts/AlertRulePanel.tsx:136` | （空态文案 div） | 「暂无本地提醒规则」空态 | **范围外** | solution DRV-01 / §3.3 明列 AlertRulePanel 空态为范围外；OBJ-05 提醒管理属 SCOPE-16 范围外对象 |
| 6 | `src/features/layout/LayoutController.tsx:75` | `workbench-selection-summary` | 工作台选择摘要 | **范围外** | solution DRV-01 明列 LayoutController 摘要为范围外 |
| 7 | `src/features/layout/LayoutController.tsx:121` | `workbench-error` | 工作台错误 | **范围外** | 同上；LayoutController 错误承载 |
| 8 | `src/features/workbench/WorkbenchShell.tsx:78` | `workbench-selection-summary` | 工作台选择摘要 | **范围外** | solution DRV-01 明列 WorkbenchShell 摘要与错误为范围外 |
| 9 | `src/features/workbench/WorkbenchShell.tsx:135` | `workbench-error` | 工作台错误 | **范围外** | 同上 |

**迁移边界结论（CONFIRMED）：** tech-design 只得把**范围内 4 处（#1~#4）**迁移到新语义色承载；**范围外 5 处（#5~#9）零改动**。

**破坏性红线（CONFIRMED，对应 SR-01 阻断处理）：** `styles.css:379` 的 `.data-notice` 颜色定义被范围内外**共享**（9 处全部引用同一类），因此**禁止修改该类的颜色/背景/边框定义**——任何对 `.data-notice` 定义的重着色都会波及范围外 AlertRulePanel/LayoutController/WorkbenchShell，属 SCOPE-15/16 越界，改变范围外用户可观察行为。正确路线是新增独立语义色承载类，仅迁移范围内用法（solution §3.3 第 3 行禁止路径、DEC-S02）。

### 3.2 人话源复用点（DEC-S03「复用不新建映射表」复用面核对）

**结论：6 类既有可读源全部真实存在且已被呈现层引用** —— CONFIRMED。DEC-S03 复用面成立，无需新建映射表。

| 人话源 | 定义 / 计算点 | 呈现引用点 | 覆盖枚举面 | 置信度 |
|--------|---------------|------------|------------|--------|
| `sourceStatusLabel` | `src/App.tsx:86-92`（formal→正式 / demo_fallback→演示 / stale→过期 / unavailable→不可用 / 未加载） | 侧栏 `src/App.tsx:435` | 来源五态（STM-02） | CONFIRMED |
| `displayLabel` | 类型 `src/types.ts:172`；计算 `src/lib/signals.ts:53,81`（`displayLabelFor`） | MTS 卡 `src/App.tsx:649` | MTS 主标签人话 | CONFIRMED |
| `technicalReminder` | 类型 `src/types.ts:173`；值 `src/lib/signals.ts:82` | MTS 卡 `src/App.tsx:658` | MTS 免责/技术提醒 | CONFIRMED |
| `stanceLabel` | 类型 `src/domain/trade-signals.ts:54`；值 :614/624/634/654/681 | 交易信号卡 `src/App.tsx:534` | 信号立场五态（not_target/source_degraded/data_insufficient/ready±） | CONFIRMED |
| `nonAdvice` | 类型 `trade-signals.ts:65,130` / `tencent-trade-plan.ts:35`；值 trade-signals.ts:519/531/558 等 | 交易信号卡 `src/App.tsx:629` | 免责文案（INV-06 常驻） | CONFIRMED |
| `MtsReason.label` + `detail`（含中文 alertLevel 语义） | 类型 `src/types.ts:150-152`（`label:string`）；注册表 `src/domain/mts-registry.ts`（label:16/26/…）；`resolveMtsReason` :160 带 `UNKNOWN_CODE` 回落 :161 | 理由列表 `src/App.tsx`（ReasonRegistry 段，现状直呈 `item.code`） | 理由代码→人话 + 未注册回落 | CONFIRMED |

**附带发现（供 tech-design，非依赖阻断）：** 现状主视图仍有**裸枚举/裸理由代码泄漏点**，是 SCN-02（INV-04）改造靶点，非本文依赖结论，仅登记坐标：
- `src/App.tsx:651-655` score-grid 直呈 `trend_state {mts.trendState}` / `mts_score` / `score_band` / `signal_type` / `alert_level {mts.alertLevel}`（裸枚举）。
- ReasonRegistry 段直呈 `<code>{item.code}</code>`（裸理由码，未用已存在的 `item.label`）。
这些是「已有人话源但呈现层未复用」——DEC-S03 复用即可覆盖，无缺口。

### 3.3 domain 门控只读读取点（DEC-S01 / DEC-S06 只读边界核对）

**结论：呈现层需只读消费的 domain 输出字段与读取点均真实存在，只读边界成立** —— CONFIRMED。

| 只读依赖 | domain 产出点（不改） | 呈现读取点（只读消费） | 置信度 |
|----------|----------------------|------------------------|--------|
| 来源降级门控 `source_degraded` | `src/domain/trade-signals.ts:619-627`（`if sourceHealth.status && !== "formal" → status:"source_degraded", stanceLabel:"来源不可用"`） | 信号卡读 `activePayload.sourceHealth.status`（App.tsx:639）；`mtsTone` 读 `trendState==="source_degraded"`（App.tsx:95）；`getSourceStatus`（App.tsx:80-83） | CONFIRMED |
| 评分极性 / MTS 计算分类 | `src/lib/signals.ts`（`trendStateFor`:29 / `signalTypeFor`:38 / `alertLevelFor`:45 / `displayLabelFor`:53） | MTS 卡读 `mts.trendState/mtsScore/scoreBand/signalType/alertLevel`（App.tsx:651-655） | CONFIRMED |
| 恢复态状态机 STM-07 | `src/features/restore/RestoreStatus.tsx:7-12`（statusLabel: restored/partial/default_fallback/failed 映射，读 `metadata.status`） | RestoreStatus 渲染 App.tsx:471（`<RestoreStatus metadata={restoreMetadata}/>`） | CONFIRMED |
| 交易信号门控顺序（非策略→来源→数据→ready） | `trade-signals.ts:609-690`（门控分支返回 status/stance） | 信号卡读 `tradeSignal.stanceLabel`（App.tsx:534）、`nonAdvice`（App.tsx:629）、回测块（App.tsx:620-627） | CONFIRMED |

**只读边界（CONFIRMED）：** 上述读取点全在 `src/App.tsx` / `src/features/*`，均为 `mts.*` / `tradeSignal.*` / `metadata.*` / `sourceHealth.*` 的字段读取，无任何写回 / 门控重算。DEC-S01/S06「呈现层只读消费既有门控结果、不重实现 BR-03 降级」边界与现状一致——改造只需在这些读取点后追加语义色/人话映射，不触 `src/domain/*` 计算逻辑。

### 3.4 下游影响 / 破坏性判断

| 变更动作 | 下游影响 | 破坏性结论 | 置信度 |
|----------|----------|------------|--------|
| 迁移范围内 4 处 `.data-notice`（#1~#4）到新语义承载类 | 范围外 5 处（#5~#9）仍引用原 `.data-notice`，只要**不改其颜色定义**即零影响 | **无破坏**（前提：新增类而非改共享类定义） | CONFIRMED |
| `styles.css:379` `.data-notice` 定义 | 若改颜色/背景 → 波及范围外 AlertRulePanel/LayoutController/WorkbenchShell | **禁止改定义**（改则破坏范围外，越界 SCOPE-15/16） | CONFIRMED |
| RestoreStatus.tsx 按 STM-07 四档分色重构 | 仅 App.tsx:471 单一渲染点消费，无其它引用（grep `RestoreStatus` 仅 import+render） | **无破坏**（隔离良好） | CONFIRMED |
| 顶部/侧栏/信号卡结构调整（DEC-S05/S09） | 侧栏 `sourceStatusLabel`（App.tsx:435）、顶部标题、信号卡（App.tsx:534/620-660）均在 App.tsx 内 | **无跨组件破坏**（改动内聚于 App.tsx 呈现结构） | CONFIRMED |
| 折叠态承载（DEC-S04，组件本地 useState） | 不写 localStorage / workspace 快照 | **无持久化副作用** | CONFIRMED |
| 涨跌色 `.up`/`.down`（styles.css:403-409，绿/红）与语义色 token 分离 | 涨跌红绿为独立类，与 `.data-notice` 无共享 | **无冲突**（涨跌色 token 已物理独立） | CONFIRMED |

**破坏性变更总判定：无破坏性变更**（CONFIRMED）——所有范围内改造均可在「新增语义承载 + 迁移范围内用法 + App.tsx 内聚重排」的前提下达成，不改共享类定义、不改 domain、不触范围外组件与 alibaba 在途代码。唯一硬约束是 SR-01 红线（禁改 `.data-notice` 颜色定义），已坐实。

---

## 汇总

### Blockers（必须先解决）

**0 项。** 无阻断性依赖缺口——三层依赖均已取证，核心 blast radius（共享类范围内外划分、人话源复用面、domain 只读读取点）全部 CONFIRMED。

### 已确认就绪（CONFIRMED）

1. 第一层基础设施 / 第二层外部系统均 N/A，排除依据充分（契约否定行 + 无 migration/schema/API 命中）。
2. `.data-notice` 迁移边界坐实：范围内 4 处（App.tsx:640/645、RestoreStatus.tsx:16、ChartSurface.tsx:207）vs 范围外 5 处（AlertRulePanel:136、LayoutController:75/121、WorkbenchShell:78/135）。
3. 人话源 6 类全部存在且已被引用，DEC-S03 复用面成立（含 `MtsReason.label` + `UNKNOWN_CODE` 回落）。
4. domain 只读读取点全部存在，DEC-S01/S06 只读边界与现状一致（`source_degraded` 门控 trade-signals.ts:619-627）。
5. 验证基础设施就绪：`npm run build`=`tsc --noEmit && vite build`（package.json:8）、`test:e2e`=Playwright（:9），`tests/e2e/` 目录存在（mts / restore-layout / watchlist / workbench / alerts / gate），RISK-07 前提满足。
6. 破坏性变更：无（前提=不改 `.data-notice` 颜色定义）。

### 证据缺口（UNCERTAIN / ASSUMED + 验证动作）

| ID | 项 | 置信度 | 验证动作 | owner stage | blocking threshold |
|----|----|--------|----------|-------------|--------------------|
| GAP-D1 | 是否存在**主视图裸枚举/裸理由码**的其它泄漏点（本文已列 App.tsx:651-655 score-grid + ReasonRegistry `item.code`，未穷举其它 features/*） | UNCERTAIN | tech-design 对全部主视图 JSX 做「原始枚举字段直呈」全量核对（grep `mts.trendState`/`.scoreBand`/`.signalType`/`.alertLevel`/`item.code`），逐点映射既有人话源 | technical_analysis | 若发现某枚举点**无**既有可读源且非注册码 → 回流产品定义确认文案来源（solution RISK-03） |
| GAP-D2 | `demo_fallback` 来源色档最终归类（信息级 vs 需关注） | ASSUMED（默认信息级软口径） | 承载设计为色档可切换（DEC-S07）；verify 前经用户确认定档 | verify / 用户决策 | 用户改判「需关注」→ 按 DEC-S07 切换承载色档（不回流路线） |
| GAP-D3 | 唯一主源承载具体选点（主卡头部 vs 顶部区，计数=1） | UNCERTAIN（准则已定，选点未定） | tech-design 在 DEC-S05 准则内指定唯一主源承载组件 + 被降级重复点清单，并给 DOM 计数=1 断言 | technical_analysis | 主源选点破坏既有可读性 → 回流方案（solution DEC-S05） |

### 需要 Decision Gate 的条件

- 无当前触发项。仅 GAP-D2（demo_fallback 定档）为既定用户决策点，属 verify 前正常确认，非阻断 tech-design。
- 若 tech-design/execute 发现任一呈现目标**无法在不改 `src/domain/*` / 后端 / 共享 `.data-notice` 颜色定义的前提下达成** → 触发 solution RISK-06 升级决策关口（mission-contract 升级规则）。

---

## execution_result（交主流程登记）

- **状态：** `DONE`
- **artifact：** `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/discovery/dependency-impact.md`
- **第一层：** N/A（无基础设施依赖）— CONFIRMED
- **第二层：** N/A（无外部系统 / 无新增 API，trigger 信号系契约否定行误命中）— CONFIRMED
- **第三层 blast radius：** 范围内 `.data-notice` 4 处 / 范围外 5 处（共享定义 styles.css:379，禁改）；人话源复用点 6 类；domain 只读读取点 4 组；破坏性变更 = 无
- **Blockers：** 0
- **证据缺口：** 3（GAP-D1 裸枚举穷举 / GAP-D2 demo_fallback 定档 / GAP-D3 主源选点）— 均配验证动作与 owner stage

---

## 依赖有效性审查摘要

- **结论**：PASS（无阻断性发现）。审查者：dependency-validity-reviewer（只读，subagent aaf46bc34af4c33dd，claude-opus-4-8）。
- **证据核对**：全仓 `grep data-notice` 精确命中 1 处定义（styles.css:379）+ 9 处 JSX 用法，与本文档「范围内 4 + 范围外 5」完全一致，无未归类用法；抽查约 22 处 file:line 全部与源码匹配。
- **判据结果**：三层依赖结论均 supported；无来源 claim = 0；假设依赖（GAP-D1 主视图裸枚举穷举→technical_analysis、GAP-D2 demo_fallback 定档→verify/用户、GAP-D3 唯一主源选点→technical_analysis）全部配验证动作与责任阶段；blast radius 置信度 high；破坏性变更=无（前提：不改共享类颜色定义、涨跌色 `.up/.down` 已物理独立，均经源码验证）。
- **就地修订**：审查指出的两处 citation 行号瑕疵（涨跌色 styles.css:403-409、source_degraded 门控 trade-signals.ts:619-627）已由编排者就地更正，不改变任何推理结论。
- **可被下游消费**：design/execute ready；SR-01 共享类爆炸半径作为 tech-design/execute 的阻断类硬约束携带。
