# 执行简报: 20260721-watchboard-ui-friendliness

> **来源**：拆解技能 → `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/breakdown/execution-brief.md`
> **参考方法论**：OpenSpec 纵向切片（每个父任务是可独立交付的呈现层价值纵切片）；TDD 红灯 / 绿灯 / 重构
> **TDD 计划契约**：`.harness/docs/tdd-planning-contract.md`
> **上游**：`product/product-definition.md` | `product/use-case-model.md`（SUC-01~06 / 9 个 SUC-xx-OP-xx / UIC-01~07） | `product/acceptance-scenarios.md`（SCN-01~07 / 22 COND / NEG-01~07） | `product/product-domain-model.md`（INV-01~07 / POL-01~03 / STM-01~08 / VO-01~03） | `product/specs/watchboard-presentation/spec.md`（8 Requirement / 25 ADDED Scenario） | `solution/solution.md`（Route A / DEC-S01~S09 / SR-01） | `technical-analysis/tech-design.md`（M1~M8 / 9 接口 / §2 SUC 映射 / §7 验证策略） | `discovery/dependency-impact.md`（GAP-D1/D2/D3） | `mission-contract.md`

**作者:** Wang Hanbin
**日期:** 2026-07-21
**任务 ID:** 20260721-watchboard-ui-friendliness

---

## 控制契约

- Contract: `contracts/execution-brief.contract.yaml`
- Authority: 外部 YAML 是控制契约权威来源；本文的原子任务队列（`atomic_task_queue`）是执行队列权威来源。Markdown 不承载 `execution_result`、`role_verdicts` 或门禁结果。
- 原型承载：interaction 阶段经治理档显式跳过，无 `behavior-graph.yaml` / `SURF` / `PS-` 承载义务，`prototype_coverage_exemptions=[]`；本简报不生成 PS-/SURF- 追溯。
- Agent：本任务 `agent_implementation: []`，无 Agent 组件，不生成 Agent 任务。

---

## TL;DR

> 把看盘终端呈现层做友好化改造：先建「四档语义色 token + 只读呈现映射层」地基（PT-01），再按 MTS 卡（PT-02）/ 交易信号卡（PT-03）/ 侧栏（PT-04）/ 顶部与唯一主源（PT-05）/ 恢复态与范围内 data-notice 收尾迁移（PT-06）逐个纵切上色·人话化·去重复·折叠，最后做跨呈现一致性 + 范围外零改动回归验证（PT-07）。全读侧、无领域写入、无数据模型/迁移。**执行者最需注意**：① 禁改 `styles.css:379` `.data-notice` 定义与 `.up`/`.down`（403-409）；② 范围外 5 处 `.data-notice`（AlertRulePanel:136、LayoutController:75/121、WorkbenchShell:78/135）零改动；③ `LayoutController.tsx` 整文件不在授权改动集，SCN-04 标题主位/控件降级只能靠 `styles.css` 对既有 DOM 类做 CSS 重排、不改其 JSX。

---

## 任务目标

> 完成后看盘终端呈现层：状态色四档归位（正常态 0 警告色、真异常见警告色、看空色 ≠ 故障色）、主视图 0 裸枚举/0 裸理由码 + 进度条评分、来源/价格各收敛唯一主源（计数=1）、顶部标题主位控件降级、交易信号卡默认关键数字明细可折叠、侧栏可扫读、恢复态四档分色、跨呈现一致且范围外零改动。全读侧、忠实翻译既有领域状态，不重实现门控、不改算法/数据/STM-06。

**对应验收场景 / 条件：**

| 验收场景 / 条件 | 下游追溯锚点 | 摘要 |
|----------------|--------------|------|
| SCN-01（COND-01~06） | SCN-01 | 状态色四档归位：来源三档 + 恢复四态 + 评分极性，正常态无警告色、看空 ≠ 故障 |
| SCN-02（COND-01~04） | SCN-02 | 主视图人话化 + 进度条评分 + 原始字段折叠 + 非 ready 人话化 |
| SCN-03（COND-01~02） | SCN-03 | 来源 / 价格各收敛唯一主源计数=1；涨跌色 ≠ 警告色 |
| SCN-04（COND-01~02） | SCN-04 | 标题主位 + 控件降级右对齐、切换语义不变 |
| SCN-05（COND-01~02） | SCN-05 | 主卡突出、次级降灰、nonAdvice 常驻可见 |
| SCN-06（COND-01~03） | SCN-06 | 侧栏名称+代码一行、价格右对齐、来源小圆点、archived 弱化 |
| SCN-07（COND-01~03） | SCN-07 | 信号卡默认关键数字、明细折叠、仅 ready 呈回测块 |
| NEG-01~07 | NEG | 跨呈现一致性 / 独立承载 / UNKNOWN_CODE / 免责折叠 / 布局归一化 / axe+E2E 无回归 |

---

## 输入合格性判断

| 输入判断 | 结论 | 证据 / 缺口 | 处理 |
|---------|------|-------------|------|
| 产品定义包的系统用例、系统操作、验收场景/条件和质量约束足以判断执行义务 | `fit` | use-case-model 9 个 SUC-xx-OP-xx 全读侧、每条含读取对象/规则/可观察结果；acceptance-scenarios 22 COND + NEG-01~07 均含 Given/When/Then + 证据类型；domain-model INV-01~07 呈现不变量可逐条对上 | 推出 PT-01~07 父任务边界、每个 SUC-OP 的验证义务与停止条件 |
| 方案路线、禁止路线和风险处理方式已明确 | `fit` | solution §4 边界锁定（Route A 语义色 token + 只读映射层）、§3.3 禁止路径（保留 .data-notice 语义重载 / 全局重着色 / 复用来源警告类名 / 重实现门控）、SR-01 + RISK-01~07 处理方式 | 落成 PT-01 地基前置 + 各父任务 prohibited_paths + stop_if |
| 模块责任、接口契约、数据/状态变化和验证策略可执行 | `fit` | tech-design §3 M1~M8 带真实 file:line、§4 9 接口签名 + 错误语义、§5 全读侧 + INV 结构保证、§7 验证策略绑定 SR-01/RISK/GAP | 每父任务映射到 M 模块 + 接口 + §7 验证义务；见下「系统操作覆盖检查」 |
| 交互/前端能力边界已满足本轮需要 | `fit` | interaction 经治理档显式跳过，无 SURF/PS 义务；UIC-01~07 承载义务经 acceptance COND + tech-design §2 落地；折叠义务由 DEC-S04 补偿承载（组件本地 useState） | 折叠交互作为 E2E 义务承载（PT-02/PT-03）；无原型 trace 义务 |

**输入义务登记表：**

| 来源 | 可推出的执行义务 | 是否足够 | 处理动作 |
|------|------------------|----------|----------|
| tech-design M1+M2 | 四档 token + notice variant + score tone 类；resolve*Tone/humanize*/ScoreBar 只读映射 | 足够 | PT-01 地基（risk-front） |
| tech-design M3/M4/M5/M6/M7/M8 + acceptance COND | 各呈现面上色/人话化/去重复/折叠/迁移 | 足够 | PT-02~PT-06 |
| tech-design §5.4 + NEG-01/03 + §7 SR-01/RISK-07 | 跨呈现一致性只读绑定 + 范围外零改动 + axe/E2E 无回归 | 足够 | PT-07 一致性 + 回归验证 |
| mission 授权路径边界 | LayoutController.tsx 整文件不可改；范围外 5 处 .data-notice 零改动；styles.css:379/.up/.down 禁改 | 足够 | 各父任务 prohibited_paths + PT-05 stop_if（SCN-04 只能 CSS-only） |

**合格性结论：全部 `fit`，无 `return_to_*`、无 `needs_decision` 阻断。** 唯一未定项 GAP-D2（demo_fallback 最终色档，产品 DEC-01）已由 tech-design DEC-S07 设计为「可切换档、不改承载结构」，属 verify 前用户决策，不阻断拆解。**不返回 BLOCKED。**

> **执行注意（非阻断，供 PT-05 / 审查员知悉）**：tech-design M6 把「顶部层级重排 + 唯一主源承载点」标注落点为「App.tsx 顶部 / market-workspace 段」，但现状核对显示：标的标题 `<h2>` 与周期/视图控件实际在 `LayoutController.tsx:73-118`（该文件整体不在授权改动集，且 :75/:121 `.data-notice` 属范围外禁改）；价格 quote-line 在 `ChartSurface.tsx:344`。因此 PT-05 的执行落点为：SCN-04 标题主位/控件降级 = `styles.css` 对 LayoutController 既有 DOM 类（`.workspace-header h2` / `.range-controls` / `.layout-control-strip`）做 CSS-only 重排（不改其 JSX，故 STM-06 切换语义天然不变）；`source-authority`/`price-authority` 唯一主源承载 = 在授权面（App.tsx market-workspace 段新增 source-authority 元素、ChartSurface quote-line 挂 price-authority testid）落地。此为 tech-design DEC-S05 承载决策的可执行落法，非新增设计。若执行时发现源计数=1 或标题主位**必须**改 `LayoutController.tsx` JSX 或移除其 :75 来源文本才能达成 → 触发 PT-05 stop_if，停下回 technical_analysis / 决策门禁，不擅自改范围外文件。

---

## 迭代授权摘要

**本轮增量目标：** 完成看盘终端呈现层 7 类友好化改造（DEL-01~07）的用户可观察结果，验证 SR-01 共享类爆炸半径隔离 / RISK-03 裸枚举穷举 / RISK-02 折叠义务 / RISK-04 跨呈现一致性只读，授权变更集限 `src/styles.css` + `src/App.tsx`（M3/M4/M5/M6 段内重排）+ `src/features/restore/RestoreStatus.tsx` + `src/features/chart/ChartSurface.tsx` + 新增 `src/features/presentation/` + `src/types.ts`（仅加 Tone）+ `tests/e2e/**` + `tests/unit/presentation/**`。

**本轮风险焦点：**
- SR-01（solution §7）：共享 `.data-notice` 跨范围内外 9 处，改动易波及范围外 5 处 → PT-01 建独立 notice variant 新类、不改 :379 定义；PT-07 范围外零改动回归。
- RISK-03 / GAP-D1（tech-design §7）：主视图裸枚举（score-grid 5 字段）+ 裸理由码（reasons 667 + invalidators 673 双处）穷举人话化。
- RISK-02（solution §7）：interaction 跳过，折叠义务经组件本地 useState 承载、E2E 证展开/收起。
- RISK-04 / INV-07（tech-design §5.4）：来源 stale → 信号卡 source_degraded 三处只读同一 domain 门控结果，不重实现门控。
- LayoutController 越界风险：SCN-04 只能 CSS-only 重排，不得改范围外文件。

**授权变更集边界：**
- 纳入（Include）：`src/styles.css`（新增 token/类）、`src/App.tsx`（mts-card 634-678 / trade-signal-card 528-632 / watchlist 424-466 / market-workspace 470 段）、`src/features/restore/RestoreStatus.tsx`、`src/features/chart/ChartSurface.tsx`、`src/features/presentation/*`（新建）、`src/types.ts`（仅加 `Tone`）、`tests/e2e/**`、`tests/unit/presentation/**`（新建）。
- 排除（Exclude）：`src/domain/*`、`src/lib/signals.ts` 计算、后端/数据源、`src/features/layout/LayoutController.tsx`（整文件）、`src/features/alerts/AlertRulePanel.tsx`、`src/features/workbench/WorkbenchShell.tsx`、`styles.css:379` `.data-notice` 定义、`styles.css:403-409` `.up`/`.down`、范围外 5 处 `.data-notice` 用法、STM-06 切换白名单/逻辑。
- 延后（Deferred）：折叠态持久化（DEC-S04 明确不做）；新建枚举→文案映射表（DEC-S03 复用既有源）；demo_fallback 最终色档定档（GAP-D2 verify 前用户决策）。

**停止 / 回流条件：**
- 若某状态色归位无法在不改 `styles.css:379` 共享定义前提下达成 → 回 solution 重评承载策略（SR-01 回流条件）。
- 若源/价格计数=1 或标题主位必须改 `LayoutController.tsx` JSX / 范围外文件才能达成 → 回 technical_analysis / 决策门禁（不越界）。
- 若某主视图枚举点无既有人话源且非注册码 → 回 prd 确认文案来源（DEC-S03 回流）。
- 若发现呈现目标必须改 `src/domain/*` / 后端 / 数据才能达成 → 触发 `scope_change` 升级关口（RISK-06）。

---

## 硬性约束

| 约束 | 来源 | 说明 |
|-----|------|------|
| 不改 `styles.css:379` `.data-notice` 颜色/背景/边框定义 | solution SR-01 / tech-design M1 禁止职责 | 9 处共享、范围外 5 处依赖，改定义即波及范围外（阻断类红线） |
| 范围外 5 处 `.data-notice` 用法零改动 | tech-design §3「范围外零改动」 | AlertRulePanel:136、LayoutController:75/121、WorkbenchShell:78/135 零可观察变化 |
| `LayoutController.tsx` 整文件不改 JSX | mission 授权路径边界 | SCN-04 标题主位/控件降级只能 `styles.css` CSS-only 重排既有 DOM 类 |
| 不改 `.up`/`.down`（styles.css:403-409） | tech-design §1.1 CONFIRMED（涨跌色物理独立） | 涨跌红绿 token 保持独立于警告色（INV-05 后半） |
| 评分/卡片极性承载类名不复用来源 warning 类名 | INV-03 / DEC-S02 | `caution`（市场看空）≠ `warning`（数据/恢复故障），物理可辨 |
| 呈现层只读，不重实现降级门控 | DEC-S01 / tech-design §5.4 | 门控在 `domain/trade-signals.ts:619-627`，三处只读消费 |
| 折叠态不持久化 | DEC-S04 | 组件本地 `useState`，不写 localStorage / workspace 快照 / URL |
| nonAdvice 免责不进折叠区 | DEC-S08 / INV-06 | 免责在默认态与折叠态均常驻可见（合规红线） |
| 不改 STM-06 布局切换白名单/语义 | DEC-S09 | 非法值由既有归一化处理，不新增失败分支 |

**编码规范要点：** React 函数组件 + TS 严格模式（`tsc --noEmit`）；`data-testid` 命名沿用既有 kebab-case 约定（如 `mts-card`/`trade-signal-card`/`restore-status`）；新增语义色用 CSS 自定义属性 + 新类，不改共享类。
**技术选择限制：** 不引入组件库 / 新外部依赖（solution §4 集成方向）；复用既有人话源（`displayLabel`/`technicalReminder`/`stanceLabel`/`nonAdvice`/`resolveMtsReason`）。
**已知的坑：** ① `.data-notice` 是跨范围内外共享类，只能迁移范围内用法到新类、绝不改共享定义；② 标题/控件在 LayoutController（范围外），只能 CSS 重排；③ `resolveMtsReason` 已带 `UNKNOWN_CODE` 回落（mts-registry.ts:161），humanizeReason 直接复用、不重造。

---

## 接口与数据变更速查

### 新增/修改接口（全部呈现层内，无新增外部 API/依赖）

| 接口 | 变更类型 | 签名摘要 |
|-----|---------|---------|
| `resolveSourceTone(status: SourceStatus): Tone` | 新增（M2） | formal/not_loaded→normal、demo_fallback→info（DEC-S07 默认档）、stale/unavailable→warning；未知→normal 兜底 |
| `resolveScoreTone(mts: MtsExplanation): Tone` | 重构迁入（M2，原 `mtsTone`） | strong_positive/positive→positive、neutral/not_applicable→neutral、negative/strong_negative 或 alertLevel=风控→caution |
| `resolveRestoreTone(metadata): Tone` | 新增（M2） | restored→normal、partial/default_fallback→info、failed/坏布局→warning；未知→warning 保守兜底 |
| `humanizeTradeStatus(status): string` | 新增（M2） | 优先复用 `stanceLabel`；缺省 stanceLabel 兜底 |
| `humanizeTrendState(trendState): string` | 新增（M2） | data_insufficient→「数据不足」、source_degraded→「数据来源降级」；缺省「—」 |
| `humanizeReason(code, detail?): string` | 新增（M2） | = `resolveMtsReason(code).label`，未注册→UNKNOWN_CODE 回落不直呈 |
| `<ScoreBar score={mtsScore}>` | 新增组件（M3） | number\|null → 进度条 DOM；null/not_applicable→中性不填充 |
| `RestoreStatus({metadata})` | 内部改（M7，props 不变） | 内部按 resolveRestoreTone 四档分色 + 技术态收详情 |
| 折叠本地态 | 新增（M3/M4） | `const [expanded,setExpanded]=useState(false)`，不持久化 |

**`Tone` 类型：** `type Tone = "normal" | "info" | "caution" | "warning" | "positive" | "neutral"`（置于 `src/types.ts`，仅新增不改既有字段）。

### 数据模型变更

| 模型/表 | 变更类型 | 字段摘要 |
|-------|---------|---------|
| N/A | — | 全读侧：无领域写入、无数据模型/schema/迁移/持久化（tech-design §5.1）。折叠为组件本地 UI 态 |

---

## 风险优先级与任务顺序

> 依赖拓扑 + 风险前置 + 写入范围（write_scope）串行化共同决定顺序。`src/styles.css` 与 `src/App.tsx` 被多父任务写入 → 同文件写入冲突，必须串行化（非并行掩盖冲突）。

| 顺序 | 父任务 | 优先原因 | 处理的风险 / 不确定性 | 下游依赖 |
|-----|-------------|----------|-----------------------|----------|
| 1 | PT-01 四档 token + 只读映射层地基 | 所有上色/人话任务的地基；SR-01 隔离在此建立 | SR-01 爆炸半径隔离、映射层只读边界（DEC-S01） | PT-02~PT-07 全部 |
| 2 | PT-02 MTS 卡人话化+进度条+折叠 | 消费地基；GAP-D1 裸枚举穷举最密集面 | RISK-03/GAP-D1、RISK-02 折叠 | PT-07（一致性/回归） |
| 3 | PT-03 交易信号卡密度+层级+免责+折叠 | App.tsx 同文件串行（避免与 PT-02 冲突） | DEC-S08 免责红线、BR-07 非 ready 无回测块 | PT-07 |
| 4 | PT-04 侧栏结构+来源小圆点+archived | App.tsx 串行；为 PT-05 源计数=1 提供侧栏来源降级 | 侧栏来源非第二主源 | PT-05、PT-07 |
| 5 | PT-05 顶部层级+唯一主源计数=1 | App.tsx/styles.css/ChartSurface 串行；GAP-D3 去重复 | GAP-D3 唯一主源、SCN-04 主观项、LayoutController 越界 | PT-07 |
| 6 | PT-06 恢复态四档归位+范围内 data-notice 收尾迁移 | RestoreStatus/ChartSurface 串行（ChartSurface 与 PT-05 共享） | SR-01 隔离、NEG-03 恢复态vs来源态独立 | PT-07 |
| 7 | PT-07 跨呈现一致性 + 范围外零改动回归验证 | 需全部实现落地后做集成/回归 | RISK-04 一致性、SR-01 范围外零改动、RISK-07 axe/E2E 无回归 | 无（终局验证切片） |

---

## 系统操作覆盖检查

| 系统操作 ID | 技术设计落点 | 父任务 | 原子任务 | 验证义务 | 覆盖结论 |
|-------------|--------------|--------|----------|----------|----------|
| SUC-01-OP-01 来源档→呈现色 | M1/M2/M6/M8/M3 | PT-01,PT-05,PT-06,PT-02 | AT-0101/0102, AT-0501, AT-0601/0602, AT-0201 | 四档并置截图 + `.notice--warning` DOM 断言 | covered |
| SUC-01-OP-02 价格/涨跌唯一主源 | M6 | PT-05 | AT-0501 | `price-authority` 计数=1 + 涨跌色 vs 警告色并置截图 | covered |
| SUC-02-OP-01 人话化+进度条+极性 | M2/M3 | PT-01,PT-02 | AT-0103, AT-0201 | 主视图无枚举 DOM 断言 + 进度条 DOM 断言 | covered |
| SUC-02-OP-02 原始字段折叠+非常态人话 | M2/M3 | PT-02 | AT-0201/0202 | E2E 折叠展开 + UNKNOWN_CODE 不直呈 | covered |
| SUC-03-OP-01 主卡突出+明细折叠+免责 | M4 | PT-03 | AT-0301/0302 | 层级差 DOM 断言 + nonAdvice 可见 + E2E 折叠 | covered |
| SUC-03-OP-02 非 ready status 人话化 | M2/M4 | PT-01,PT-03 | AT-0103, AT-0302 | 非 ready 承载文本无枚举串 DOM 断言 | covered |
| SUC-04-OP-01 侧栏主看+来源小圆点 | M5 | PT-04 | AT-0401/0402 | 条目结构 + 小圆点非主源 DOM 断言 | covered |
| SUC-05-OP-01 标题主位+控件降级 | M6 | PT-05 | AT-0502 | 标题字号/权重 > 控件 DOM 断言 + E2E 切换后仍主位 | covered |
| SUC-06-OP-01 恢复态四档映射 | M2/M7 | PT-01,PT-06 | AT-0102, AT-0601 | restored/partial/default_fallback 无警告类名逐态 DOM 断言 | covered |

**覆盖结论：9/9 `SUC-xx-OP-xx` 全落父任务 + 原子任务 + 验证义务，无缺口、无 N/A 豁免。**

---

## 差量规格 Scenario 覆盖映射（spec.enabled=true，全 25 ADDED Scenario）

> 引用格式 `watchboard-presentation/spec.md#<Scenario 名>`；每条 Scenario 至少被一个父任务覆盖。

| # | Scenario 名 | Requirement | 覆盖父任务 |
|---|-------------|-------------|-----------|
| 1 | 来源正常态不出现警告色 | 状态色语义分档 | PT-05（+PT-06/PT-02 派生） |
| 2 | 来源真异常态出现警告色并标注受影响范围 | 状态色语义分档 | PT-05（+PT-06/PT-02） |
| 3 | 工作台正常恢复态不出现警告色黄条 | 状态色语义分档 | PT-06 |
| 4 | 工作台恢复失败态出现需关注提示 | 状态色语义分档 | PT-06 |
| 5 | 负向评分与来源故障色物理区分 | 状态色语义分档 | PT-02（+PT-01 token 分离） |
| 6 | demo_fallback 呈信息级不用高危警告色 | 状态色语义分档 | PT-05（+PT-01 映射） |
| 7 | 主视图不暴露原始枚举/理由代码 | 内部枚举人话化 | PT-02 |
| 8 | 评分以进度条式可读呈现 | 内部枚举人话化 | PT-02 |
| 9 | 原始枚举/理由代码仅在展开详情可见 | 内部枚举人话化 | PT-02 |
| 10 | 未注册理由码兜底不直呈 | 内部枚举人话化 | PT-02（+PT-01 humanizeReason） |
| 11 | 非 ready 技术/交易状态人话化 | 内部枚举人话化 | PT-02（MTS）+ PT-03（trade） |
| 12 | 来源状态收敛到唯一权威主源 | 重复信息收敛 | PT-05（+PT-04 侧栏降级） |
| 13 | 价格/涨跌收敛唯一主源且涨跌色与警告色分离 | 重复信息收敛 | PT-05 |
| 14 | 标题为顶部视觉主位、控件降级 | 顶部信息层级重排 | PT-05 |
| 15 | 切换周期/布局后标题仍主位、切换语义不变 | 顶部信息层级重排 | PT-05 |
| 16 | 主卡突出、次级降灰形成层级差 | 主看信息层级建立 | PT-03 |
| 17 | 免责声明保持可见 | 主看信息层级建立 | PT-03 |
| 18 | 侧栏条目主看信息突出 | 侧栏扫读优化 | PT-04 |
| 19 | 侧栏来源弱化为小圆点非主源 | 侧栏扫读优化 | PT-04 |
| 20 | 归档标的弱化区分 | 侧栏扫读优化 | PT-04 |
| 21 | 默认呈现关键数字 | 交易信号卡密度优化 | PT-03 |
| 22 | 三段回测明细默认折叠、展开后呈现 | 交易信号卡密度优化 | PT-03 |
| 23 | 仅 ready 呈现回测块、价位分层级 | 交易信号卡密度优化 | PT-03 |
| 24 | 来源降级时信号卡同步降级 | 跨呈现状态一致性 | PT-03（实现）+ PT-07（E2E 验证 NEG-01） |
| 25 | 恢复态与来源态各自独立承载 | 跨呈现状态一致性 | PT-06（独立 DOM）+ PT-07（验证 NEG-03） |

**覆盖结论：25/25 ADDED Scenario 全部至少被一个父任务覆盖，无遗漏。**

---

## 原子任务队列规则

**原子任务队列（Atomic task queue）:** 每个父任务下都有 `atomic_task_queue:`，状态 `ready`；每个 `execution_units[]` 有同 ID 原子任务详情块。

| 检查项 | 状态 | 说明 |
|-------|------|------|
| single_action | ready | 每个原子任务单一工程/验证行动 |
| explicit_inputs_outputs | ready | 每原子任务写明输入/输出/读写范围 |
| parent_task_coverage | ready | 7 父任务全含 atomic_task_queue |
| acceptance_scenario_coverage | ready | 9/9 SUC-OP + 25/25 Scenario + 22 COND + NEG 覆盖 |
| code_pattern_references | ready | 每涉码原子任务在 `src/` 真实检索样板；ScoreBar 无同类写 no_match |
| interface_or_data_contracts | ready | 9 呈现接口签名 + 无数据变更 |
| test_fixtures_and_seed_data | ready | E2E 复用 `tests/e2e/mts/card.spec.ts` envelope fixture；单测复用 `tests/unit/signals` 模式 |
| validation_commands | ready | build / test:e2e / node --test / axe |
| transaction_or_state_boundaries | ready | 全读侧无事务；折叠为本地 UI 态 |
| evidence_requirements | ready | 每原子任务声明证据路径 |
| stop_conditions | ready | 每原子任务/父任务含 stop_if |
| migration_or_route_boundaries | ready | 无数据迁移；范围内 data-notice 迁移清单 4 处 |

**队列完整性：** complete（7 父任务 / 共 15 原子任务，详见 Execution Units）。
**缺口处理：** 无阻断缺口；GAP-D2（demo_fallback 定档）为 verify 前用户决策，不阻断执行。

---

## 已知风险与注意事项

| 风险 | 可能性 | 缓解措施 |
|-----|--------|---------|
| SR-01 改动波及范围外 5 处 `.data-notice` | 中 | 只建新 notice variant 类、不改 :379 定义；PT-07 范围外零改动回归（grep + 截图 + DOM 断言） |
| GAP-D1 裸枚举/裸理由码遗漏某处 | 中 | PT-02 穷举 score-grid 5 字段 + reasons/invalidators 双处；DOM 断言主视图文本不含枚举 token |
| SCN-04 越界改 LayoutController | 中 | 硬约束 + PT-05 stop_if；CSS-only 重排既有 DOM 类 |
| RISK-04 呈现层误重实现门控 | 低 | DEC-S01 只读消费 `trade-signals.ts:619-627`；PT-07 E2E 证 NEG-01 一致性 |
| 主观层级差不可判定（RISK-05） | 中 | 截图 + 次级样式 DOM 断言双证据 |
| demo_fallback 定档（GAP-D2/RISK-01） | 低 | DEC-S07 可切换档，改一处映射不改结构；verify 前用户定档 |

---

## Execution Units

### PT-01: 四档语义色 token 层 + 只读呈现映射层地基 / 隔离共享 .data-notice 爆炸半径（SR-01）/ styles.css token + features/presentation/ + types.ts

```yaml
parent_task:
  id: "PT-01"
  title: "四档语义色 token 层 + 只读呈现映射层地基 / 隔离 SR-01 爆炸半径 / styles.css + features/presentation/ + types.ts"
  depends_on: []
  authorized_path_summary:
    - "src/styles.css（新增 token/notice variant/score tone/score-bar 类，不改 :379/:403-409）"
    - "src/types.ts（仅新增 Tone 类型）"
    - "src/features/presentation/tone.ts（新建）"
    - "src/features/presentation/humanize.ts（新建）"
    - "tests/unit/presentation/tone.spec.ts、humanize.spec.ts（新建）"
  required_evidence:
    - "node --test tests/unit/presentation/*.spec.ts 全绿（resolve*Tone/humanize* 映射断言）"
    - "npm run build exit 0（tsc --noEmit + vite build）"
    - "styles.css:379 .data-notice 定义与 :403-409 .up/.down 未改（git diff 断言）"
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "AT-0101"
        title: "styles.css 新增四档语义色 token + notice variant + score tone + score-bar 类"
        execution_order: 1
        depends_on: []
        write_scope: ["src/styles.css"]
        read_scope: ["src/styles.css", "harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/technical-analysis/tech-design.md"]
        detail_ref: "AT-0101"
        reviewer_verdict: "pending"
        evidence_required: [green_report, regression_report]
      - id: "AT-0102"
        title: "types.ts 加 Tone + features/presentation/tone.ts（resolveSourceTone/resolveScoreTone/resolveRestoreTone）+ 单测"
        execution_order: 2
        depends_on: ["AT-0101"]
        write_scope: ["src/types.ts", "src/features/presentation/tone.ts", "tests/unit/presentation/tone.spec.ts"]
        read_scope: ["src/App.tsx", "src/types.ts", "src/domain/mts-registry.ts"]
        detail_ref: "AT-0102"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
      - id: "AT-0103"
        title: "features/presentation/humanize.ts（humanizeTradeStatus/humanizeTrendState/humanizeReason）+ 单测"
        execution_order: 3
        depends_on: ["AT-0102"]
        write_scope: ["src/features/presentation/humanize.ts", "tests/unit/presentation/humanize.spec.ts"]
        read_scope: ["src/App.tsx", "src/domain/mts-registry.ts", "src/domain/trade-signals.ts", "src/types.ts"]
        detail_ref: "AT-0103"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
```

**依赖（Depends on）：** none

**本轮增量价值：** 建立四档语义色 token（正常/信息/谨慎-风险/警告-异常）与只读呈现映射层，使后续所有上色/人话化任务有一致、可复用、与共享 `.data-notice` 物理隔离的承载；映射函数纯只读、可单测。

**风险处理目标：** 隔离 SR-01（新建独立 notice variant 类、不改 :379 共享定义，从结构上杜绝波及范围外 5 处）；形式化 INV-03（caution 类名 ≠ warning 类名）；确立 DEC-S01 只读边界（映射层不重实现门控）。证据来源：solution SR-01、tech-design M1/M2、INV-03。

**授权变更集边界：**
- 纳入（Include）：styles.css 新增 CSS 自定义属性 `--tone-normal/--tone-info/--tone-caution/--tone-warning` + `.notice--info`/`.notice--warning` + `.tone-positive`/`.tone-caution`/`.tone-neutral` + `.score-bar`；types.ts 加 `Tone`；presentation/tone.ts + humanize.ts + 对应单测。
- 排除（Exclude）：不改 styles.css:379 `.data-notice` / :403-409 `.up`/`.down`；不改 domain；不消费这些函数进 App.tsx（消费在 PT-02~06）。
- 延后（Deferred）：ScoreBar 组件本体（在 PT-02/M3 落，因其属 MTS 卡 surface）。

**目标：** 完成后 styles.css 有四档语义 token 与新承载类、`src/features/presentation/` 有纯只读映射函数且单测全绿，`Tone` 类型可被呈现层引用，共享 `.data-notice` 定义与涨跌色零改动。

**完成边界：** 单测全绿 + build exit 0 + git diff 证 :379/:403-409 未改；映射函数被 PT-02~06 引用即视为地基就位。

**父任务级实现边界：**
- 只建 token/类/函数/类型与单测，不接入任何渲染组件（消费属下游父任务）。
- `resolveScoreTone` 由既有 `mtsTone`（App.tsx:94-99）重构迁入并语义档化（risk→caution），行为等价（负向仍走非 warning 的 caution 类）。

**测试要求：**
- **Given** SourceStatus / MtsExplanation / WorkspaceRestoreMetadata 各态输入
- **When** 调用 resolve*Tone / humanize*
- **Then** 返回符合 BR-02/04/10 与 INV-01~03 的 Tone / 人话串；未注册理由码走 UNKNOWN_CODE 回落

**测试驱动开发范围契约：**

| 项 | 内容 |
|----|------|
| Behavior under test | 领域状态 → 语义档 / 人话文案的纯只读映射 |
| Red scope | tone.spec.ts / humanize.spec.ts 先断言各态映射（未实现前失败） |
| Green scope | tone.ts + humanize.ts 实现使断言通过 |
| Refactor scope | 从 App.tsx 迁出 mtsTone/tradeSignalTone/sourceStatusLabel 到 presentation（PT-02~05 接入时完成迁移） |
| Out of scope | 不接入渲染组件、不改 domain、不测 CSS 视觉 |
| Required assertions | formal/not_loaded→normal、demo_fallback→info、stale/unavailable→warning；negative→caution（非 warning）；restored→normal、failed→warning；UNKNOWN_CODE 回落不直呈 code |
| Test data boundary | 纯枚举/对象字面量输入，不依赖网络/DOM |
| Allowed test doubles | 无需（纯函数） |
| Forbidden shortcuts | 不得在测试里硬编码返回值绕过实现；不得复制 domain 计算 |
| Fault / mutation signal | 若把 negative 误映射 warning、或 demo_fallback 误映射 warning，断言必须失败 |
| Command source | parent_local_atomic_task_queue |
| Red command / queue refs | AT-0102 / AT-0103 red |
| Green command / queue refs | AT-0102 / AT-0103 green |
| Regression command / queue refs | AT-0101 regression（build）+ AT-0102/0103 regression |

**测试义务（Test Obligation）：**
```yaml
risk_level: "medium"
surfaces:
  - "presentation_mapping_layer"
  - "css_token_layer"
required_capabilities:
  - "unit_test(node:test)"
  - "build_typecheck"
evidence_required:
  - "node --test 全绿报告"
  - "npm run build exit 0"
  - "git diff 证 styles.css:379/:403-409 未改"
accepted_alternatives:
  "unit_test(node:test)":
    - "若 presentation 纯函数无法独立单测，退化为 PT-02~06 E2E DOM 断言其渲染效果（需说明）"
```

**端到端义务（E2E Obligation）：**
```yaml
risk_level: "none"
user_surfaces: []
required_capabilities: []
evidence_required:
  - "N/A：地基层无用户可观察面，E2E 义务在消费父任务（PT-02~07）承载"
accepted_alternatives: {}
```

**授权路径摘要：**
| 文件 | 变更类型 |
|-----|---------|
| src/styles.css | 修改（新增类，不改 :379/:403-409） |
| src/types.ts | 修改（仅加 Tone） |
| src/features/presentation/tone.ts | 新增 |
| src/features/presentation/humanize.ts | 新增 |
| tests/unit/presentation/tone.spec.ts | 新增 |
| tests/unit/presentation/humanize.spec.ts | 新增 |

**父任务完成清单：**
- [ ] AT-0101/0102/0103 全部完成 Red→Green→Refactor→Regression
- [ ] 单测全绿 + build exit 0 + :379/:403-409 未改
- [ ] resolve*Tone/humanize* 覆盖来源五态/恢复四态/评分极性/UNKNOWN_CODE
- [ ] test_obligation required capabilities 均有证据

**原子任务详情（Atomic Task details）：**

#### AT-0101

**标题：** styles.css 新增四档语义色 token + notice variant + score tone + score-bar 类

**父任务：** PT-01

**队列元数据：** 见 `atomic_task_queue.execution_units[]` detail_ref: "AT-0101"。

**目标**

在 styles.css 新增四档语义色 CSS 自定义属性、notice variant 承载类（独立于 `.data-notice`）、评分极性 tone 类与进度条类，为下游消费提供承载；不改任何共享类定义。

**执行边界**
- 纳入（Include）：`--tone-normal/--tone-info/--tone-caution/--tone-warning` 变量；`.notice--info`/`.notice--warning`（新类，色可沿用琥珀 `#f0c75e` 族但为新类）；`.tone-positive`/`.tone-caution`/`.tone-neutral`；`.score-bar`（进度条）。
- 排除（Exclude）：不改 `.data-notice`(:379-389)、`.up`/`.down`(:403-409)、`.signal-card.positive/.watch/.risk/.negative`(:582-605) 的既有定义（可新增不覆写）。
- 停止前置点（Stop before）：不把这些类接入任何组件 JSX（接入在 PT-02~06）。

**文件行动**
```yaml
files:
  - path: "src/styles.css"
    action: "modify"
    purpose: "新增四档 token + notice variant + score tone + score-bar 类，不改共享定义"
```

**输入**
- tech-design M1 token 结构与命名约束（INV-03 类名不复用）

**输出**
- styles.css 新增类可被 DOM 引用；`.notice--warning` 与 `.data-notice` 类名不同

**代码模式参考**
```yaml
references:
  - path: "src/styles.css"
    pattern_type: "same_surface"
    symbol: ".data-notice (:379-389)"
    observed_convention: "notice 类用 color+background(rgba .1)+border(rgba .2)+radius 6px+padding+font-size 12px 的琥珀族样式结构"
    apply_to_this_task: "新 .notice--warning/.notice--info 沿用同结构但为独立类名，色档区分 info(次级)/warning(琥珀)"
    do_not_copy: "不得改 .data-notice 本体定义；不得让新类复用 .data-notice 类名"
  - path: "src/styles.css"
    pattern_type: "same_surface"
    symbol: ".signal-card.positive/.watch/.risk/.negative (:582-605)"
    observed_convention: "极性用 border-color rgba 表达：positive 绿(.6)、watch 琥珀(.55)、risk/negative 红(.55)"
    apply_to_this_task: "score tone 类 .tone-positive/.tone-caution/.tone-neutral 形式化该极性分离；caution=红族(市场看空)、与 warning 琥珀族物理可辨"
    do_not_copy: "不改既有 .signal-card.* 定义"
```

**接口 / 数据契约**

无接口/数据变更；纯 CSS 承载类。

**TDD 范围**
- Behavior under test: CSS 类存在性与色档物理区分（视觉/DOM 层，非单测）
- Red scope: 无独立 red（CSS 无 red 单测），以 PT-02~06 DOM 断言 + 逐档截图为回归
- Green scope: 类定义就位，build 通过
- Refactor scope: 无
- Out of scope: 不测视觉像素值（属 verify 截图）
- Required assertions: `.notice--warning` ≠ `.data-notice` 类名（PT-07 grep/DOM 证）
- Test data boundary: N/A
- Test doubles boundary: N/A
- Fault / mutation signal: 若误改 :379 定义 → PT-07 范围外零改动回归失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "N/A：CSS 类新增无独立 red 单测（accepted alternative：由 AT-0102 起下游 DOM/截图证）"
    expected_signal: "N/A"
  green:
    cwd: "."
    command: "npm run build"
    expected_signal: "exit 0（tsc --noEmit + vite build 成功，CSS 编译进产物）"
  regression:
    cwd: "."
    command: "git diff --unified=0 src/styles.css | grep -nE '^[-+].*(\\.data-notice|\\.up|\\.down)' || echo NO_SHARED_CHANGE"
    expected_signal: "输出 NO_SHARED_CHANGE（:379 .data-notice 与 :403-409 .up/.down 定义行未被删改）"
```

**证据**
- green_report: build exit 0 日志
- regression_report: git diff 证共享定义未改

**停止条件**
- 若某状态色档无法在不改 `.data-notice` 共享定义前提下表达 → 停下回 PT-01 父任务边界 / solution（SR-01 回流）。

---

#### AT-0102

**标题：** types.ts 加 Tone + presentation/tone.ts（resolveSourceTone/resolveScoreTone/resolveRestoreTone）+ 单测

**父任务：** PT-01

**队列元数据：** detail_ref: "AT-0102"。

**目标**

新增 `Tone` 类型与三个只读 tone 映射函数，先写单测断言各态映射（Red），再实现使其通过（Green）；`resolveScoreTone` 由既有 `mtsTone` 重构迁入并语义档化。

**执行边界**
- 纳入（Include）：types.ts 加 `Tone`；tone.ts 三函数；tone.spec.ts 覆盖来源五态/恢复四态/评分极性 + 兜底。
- 排除（Exclude）：不接入 App.tsx（接入在 PT-02/05/06）；不改 domain；humanize* 在 AT-0103。
- 停止前置点（Stop before）：不删除 App.tsx 原 mtsTone（消费迁移在 PT-02 完成前保留，避免断链）。

**文件行动**
```yaml
files:
  - path: "src/types.ts"
    action: "modify"
    purpose: "新增 export type Tone（仅加类型，不改既有字段）"
  - path: "src/features/presentation/tone.ts"
    action: "create"
    purpose: "resolveSourceTone/resolveScoreTone/resolveRestoreTone 纯只读映射"
  - path: "tests/unit/presentation/tone.spec.ts"
    action: "create"
    purpose: "node:test 断言各态映射（含 INV-01~03 关键约束）"
```

**输入**
- tech-design §4 接口签名 + 错误/回落语义；BR-02/04/10；既有 mtsTone(App.tsx:94-99)

**输出**
- tone.ts 三函数；Tone 类型；tone.spec.ts 全绿

**代码模式参考**
```yaml
references:
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "mtsTone (94-99) / tradeSignalTone (101-106) / sourceStatusLabel (86-92)"
    observed_convention: "既有 tone 解析用纯 if 链读 mts.trendState/scoreBand，返回字符串档（positive/risk/neutral）"
    apply_to_this_task: "resolveScoreTone 重构迁入该逻辑并档化（risk→caution）；resolveSourceTone 复用 sourceStatusLabel 的五态判定结构改产 Tone"
    do_not_copy: "不复制到 App.tsx 留双份；迁入后由 PT-02/05 改 App.tsx 引用"
  - path: "tests/unit/signals/trade-signals.spec.ts"
    pattern_type: "test_pattern"
    symbol: "import test from node:test + assert from node:assert/strict + 相对 import ../../../src/*"
    observed_convention: "node:test 单测：test('...', () => { assert.equal(fn(input), expected) })，从 ../../../src 相对导入"
    apply_to_this_task: "tone.spec.ts 沿用同结构，import ../../../src/features/presentation/tone.ts"
    do_not_copy: "不复制 domain 计算 fixture；用简单枚举/对象字面量输入"
```

**接口 / 数据契约**

`resolveSourceTone(status: SourceStatus): Tone`；`resolveScoreTone(mts: MtsExplanation): Tone`；`resolveRestoreTone(metadata: WorkspaceRestoreMetadata): Tone`。见「接口速查」。

**TDD 范围**
- Behavior under test: 领域状态 → Tone 只读映射
- Red scope: tone.spec.ts 断言（未实现前失败）
- Green scope: tone.ts 实现
- Refactor scope: 收敛 tone 解析入口（App.tsx 引用迁移留 PT-02/05）
- Out of scope: 不测渲染、不改 domain
- Required assertions: formal/not_loaded→normal、demo_fallback→info、stale/unavailable→warning；strong_positive/positive→positive、negative/strong_negative 或 alertLevel=风控→caution、neutral/not_applicable→neutral；restored→normal、partial/default_fallback→info、failed 或 discardedLayoutKeys 非空→warning；未知 source→normal 兜底、未知 restore→warning 兜底
- Test data boundary: 枚举/对象字面量
- Test doubles boundary: 无
- Fault / mutation signal: negative 误→warning，或 demo_fallback 误→warning，断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "node --test tests/unit/presentation/tone.spec.ts"
    expected_signal: "失败（tone.ts 未实现，import/断言报错）"
  green:
    cwd: "."
    command: "node --test tests/unit/presentation/tone.spec.ts"
    expected_signal: "全绿（各态映射断言通过）"
  regression:
    cwd: "."
    command: "npm run build"
    expected_signal: "exit 0（Tone 类型与 tone.ts 通过 tsc）"
```

**证据**
- red_report: tone.spec.ts 失败日志
- green_report: tone.spec.ts 全绿日志
- regression_report: build exit 0

**停止条件**
- 若某来源/恢复态无对应领域字段可读 → 停下回 tech-design §4（缺读取字段）。

---

#### AT-0103

**标题：** presentation/humanize.ts（humanizeTradeStatus/humanizeTrendState/humanizeReason）+ 单测

**父任务：** PT-01

**队列元数据：** detail_ref: "AT-0103"。

**目标**

新增三个人话映射函数，复用既有人话源与 UNKNOWN_CODE 回落；先写单测（Red）再实现（Green）。

**执行边界**
- 纳入（Include）：humanize.ts 三函数；humanize.spec.ts 覆盖非 ready 态 + 未注册码回落。
- 排除（Exclude）：不新建枚举→文案映射表（DEC-S03，复用 resolveMtsReason/stanceLabel）；不接入组件。
- 停止前置点（Stop before）：不改 domain/mts-registry。

**文件行动**
```yaml
files:
  - path: "src/features/presentation/humanize.ts"
    action: "create"
    purpose: "humanizeTradeStatus/humanizeTrendState/humanizeReason 复用既有人话源"
  - path: "tests/unit/presentation/humanize.spec.ts"
    action: "create"
    purpose: "node:test 断言非 ready 人话 + UNKNOWN_CODE 回落不直呈"
```

**输入**
- 既有源：`stanceLabel`(trade-signals.ts)、`resolveMtsReason`(mts-registry.ts:160-167 带 UNKNOWN_CODE 回落)

**输出**
- humanize.ts 三函数；humanize.spec.ts 全绿

**代码模式参考**
```yaml
references:
  - path: "src/domain/mts-registry.ts"
    pattern_type: "same_surface"
    symbol: "resolveMtsReason (160-167) + UNKNOWN_CODE 回落 (161)"
    observed_convention: "resolveMtsReason(code) 返回 {label,detail}，未注册回落 UNKNOWN_CODE 而非抛错/直呈 code"
    apply_to_this_task: "humanizeReason(code) = resolveMtsReason(code).label，直接复用回落，不重造映射表"
    do_not_copy: "不复制注册表内容；不在 presentation 层重建 code→label 表"
  - path: "tests/unit/signals/trade-signals.spec.ts"
    pattern_type: "test_pattern"
    symbol: "node:test + assert.equal"
    observed_convention: "同 AT-0102"
    apply_to_this_task: "humanize.spec.ts 沿用；断言未注册 code 不出现在返回串"
    do_not_copy: "不复制 domain fixture"
```

**接口 / 数据契约**

`humanizeTradeStatus(status): string`；`humanizeTrendState(trendState): string`；`humanizeReason(code, detail?): string`。见「接口速查」。

**TDD 范围**
- Behavior under test: 枚举/理由码 → 人话串（复用既有源 + UNKNOWN_CODE 回落）
- Red scope: humanize.spec.ts 断言
- Green scope: humanize.ts 实现
- Refactor scope: 无
- Out of scope: 不测渲染、不改 domain
- Required assertions: trendState=data_insufficient→「数据不足」、source_degraded→「数据来源降级」；status not_target_symbol/data_insufficient/source_degraded → 对应人话；未注册 code → 不含原始 code 串（NEG-04）
- Test data boundary: 枚举/字符串输入
- Test doubles boundary: 无
- Fault / mutation signal: 未注册 code 若直呈原始 code，断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "node --test tests/unit/presentation/humanize.spec.ts"
    expected_signal: "失败（humanize.ts 未实现）"
  green:
    cwd: "."
    command: "node --test tests/unit/presentation/humanize.spec.ts"
    expected_signal: "全绿"
  regression:
    cwd: "."
    command: "node --test tests/unit/presentation/tone.spec.ts tests/unit/presentation/humanize.spec.ts && npm run build"
    expected_signal: "全绿 + build exit 0"
```

**证据**
- red_report: humanize.spec.ts 失败日志
- green_report: humanize.spec.ts 全绿日志
- regression_report: presentation 单测全绿 + build exit 0

**停止条件**
- 若某主视图枚举点无既有人话源且非注册码 → 停下回 prd 确认文案来源（DEC-S03 回流）。

---

### PT-02: MTS 卡人话化 + 进度条 + 折叠详情 / 消除主视图裸枚举·裸理由码泄漏（GAP-D1）/ App.tsx mts-card 段 634-678 + ScoreBar

```yaml
parent_task:
  id: "PT-02"
  title: "MTS 卡人话化+进度条+折叠详情 / 消除 GAP-D1 裸枚举·裸理由码泄漏 / App.tsx mts-card 段 + ScoreBar"
  depends_on: ["PT-01"]
  authorized_path_summary:
    - "src/App.tsx（mts-card 段 634-678：score-grid/reason-list 人话化、折叠、data-notice 迁移）"
    - "src/features/presentation/ScoreBar.tsx（新建进度条组件）"
    - "src/styles.css（仅用 PT-01 已建 .score-bar/.tone-*/.notice--* 类，如需微调新增不改共享定义）"
    - "tests/e2e/mts/*.spec.ts（折叠展开 + 无裸枚举 DOM 断言）"
  required_evidence:
    - "E2E：主视图 mts-card 文本不含 trend_state/mts_score/score_band/signal_type/alert_level + reasons/invalidators 无裸 code"
    - "E2E：默认折叠→展开→原始字段可见"
    - "进度条承载 DOM 断言存在；npm run build exit 0"
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "AT-0201"
        title: "ScoreBar 组件 + score-grid 裸枚举收进折叠 + 人话化 + degradation/error note 迁 .notice--warning"
        execution_order: 1
        depends_on: ["PT-01"]
        write_scope: ["src/features/presentation/ScoreBar.tsx", "src/App.tsx"]
        read_scope: ["src/App.tsx", "src/features/presentation/tone.ts", "src/features/presentation/humanize.ts", "src/types.ts"]
        detail_ref: "AT-0201"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
      - id: "AT-0202"
        title: "ReasonRegistry reasons+invalidators 双处裸理由码人话化 + 折叠详情本地态"
        execution_order: 2
        depends_on: ["AT-0201"]
        write_scope: ["src/App.tsx"]
        read_scope: ["src/App.tsx", "src/features/presentation/humanize.ts"]
        detail_ref: "AT-0202"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
```

**依赖（Depends on）：** PT-01

**本轮增量价值：** MTS 卡主视图 0 裸枚举 / 0 裸理由码、评分以进度条呈现、原始字段收进可展开详情、来源降级/错误提示迁到独立 warning 承载；用户不再被内部枚举干扰、评分可视觉估读。

**风险处理目标：** RISK-03/GAP-D1（裸枚举穷举：score-grid 5 字段 App.tsx:651-655 + ReasonRegistry reasons 667 + invalidators 673 双处）；RISK-02（折叠义务经本地 useState 承载、E2E 证）；SR-01（App.tsx:640/645 两处 `.data-notice` 迁 `.notice--warning`，范围内 2/4）。证据来源：tech-design M3 / §7 RISK-03。

**授权变更集边界：**
- 纳入（Include）：ScoreBar 组件；App.tsx mts-card 段 score-grid 人话化+折叠、reason-list 双处人话化、640/645 note 迁 `.notice--warning`、retry 技术态(641)收进折叠。
- 排除（Exclude）：不改 trade-signal-card（PT-03）、不改 domain、不改 :379 定义、不动 mtsScore 计算。
- 延后（Deferred）：折叠态持久化（不做）。

**目标：** 完成后 mts-card 默认呈现 displayLabel/technicalReminder/进度条评分/人话理由，原始枚举与理由码仅在展开详情可见，非正常态经 humanizeTrendState 人话化。

**完成边界：** E2E 断言主视图无枚举 token + 折叠展开生效 + 进度条 DOM 存在 + build exit 0。

**父任务级实现边界：**
- 只重排 mts-card 段与新增 ScoreBar；接入 PT-01 的 resolveScoreTone/humanize*/ScoreBar。
- score-grid 5 字段 + reasons/invalidators code 全部经 humanize* 转人话或移入折叠区。

**测试要求：**
- **Given** 某标的有 trendState/mtsScore/scoreBand/signalType/alertLevel + reasonCodes（含未注册码）
- **When** 用户默认查看主视图，随后展开详情
- **Then** 默认态 0 裸枚举/0 裸理由码 + 进度条评分；展开后原始字段可见；未注册码不直呈

**测试驱动开发范围契约：**

| 项 | 内容 |
|----|------|
| Behavior under test | MTS 卡人话化 + 进度条 + 折叠 + 来源降级 warning 迁移 |
| Red scope | mts E2E 先断言「主视图不含 trend_state 等 token」「进度条存在」「默认无原始字段」（改前失败） |
| Green scope | mts-card 重排使断言通过 |
| Refactor scope | 完成 App.tsx 对 mtsTone→resolveScoreTone 的引用迁移 |
| Out of scope | 不改 trade card / domain / 侧栏 |
| Required assertions | mts-card 文本不含 trend_state/mts_score/score_band/signal_type/alert_level；reason-list 不含裸 code；进度条承载存在；展开后原始字段出现；640/645 用 `.notice--warning` 非 `.data-notice` |
| Test data boundary | 复用 tests/e2e/mts/card.spec.ts envelope fixture（formal + degraded 态） |
| Allowed test doubles | Playwright route mock（既有 fixture） |
| Forbidden shortcuts | 不得把枚举藏进 aria/hidden 蒙混 DOM 断言；不得删 reason-list 内容 |
| Fault / mutation signal | 若某枚举/裸 code 仍留主视图，DOM 断言失败 |
| Command source | parent_local_atomic_task_queue |
| Red command / queue refs | AT-0201 / AT-0202 red |
| Green command / queue refs | AT-0201 / AT-0202 green |
| Regression command / queue refs | npm run test:e2e + npm run build |

**测试义务（Test Obligation）：**
```yaml
risk_level: "high"
surfaces:
  - "mts_card_presentation"
required_capabilities:
  - "e2e(playwright)"
  - "dom_assertion"
  - "build_typecheck"
evidence_required:
  - "E2E 主视图无枚举 token 断言通过"
  - "进度条承载 DOM 断言"
  - "npm run build exit 0"
accepted_alternatives:
  "e2e(playwright)":
    - "无"
```

**端到端义务（E2E Obligation）：**
```yaml
risk_level: "high"
user_surfaces:
  - "MTS 解释卡主视图 + 折叠详情"
required_capabilities:
  - "e2e_collapse_expand"
  - "e2e_text_assertion(no_enum)"
evidence_required:
  - "折叠默认→展开→原始字段可见 Playwright"
  - "主视图文本无裸枚举/裸理由码 Playwright"
accepted_alternatives:
  "e2e_collapse_expand":
    - "无（interaction 跳过，折叠义务须 E2E 兜底）"
```

**授权路径摘要：**
| 文件 | 变更类型 |
|-----|---------|
| src/App.tsx | 修改（mts-card 段 634-678） |
| src/features/presentation/ScoreBar.tsx | 新增 |
| tests/e2e/mts/*.spec.ts | 新增/修改 |

**父任务完成清单：**
- [ ] AT-0201/0202 完成 Red→Green→Refactor→Regression
- [ ] 主视图无裸枚举/裸理由码（GAP-D1 穷举）+ 进度条 + 折叠 E2E 通过
- [ ] 640/645 迁 `.notice--warning`，:379 未改
- [ ] e2e_obligation required capabilities 有证据

**原子任务详情（Atomic Task details）：**

#### AT-0201

**标题：** ScoreBar 组件 + score-grid 裸枚举收进折叠 + 人话化 + degradation/error note 迁 .notice--warning

**父任务：** PT-02

**队列元数据：** detail_ref: "AT-0201"。

**目标**

新增 ScoreBar 进度条组件；把 score-grid(650-656) 5 个裸枚举字段收进可展开详情并保留 displayLabel/technicalReminder 人话；mtsScore 改进度条；640/645 两处 `.data-notice` 迁 `.notice--warning`，retry 技术态(641)收进折叠。

**执行边界**
- 纳入（Include）：ScoreBar.tsx；App.tsx score-grid 折叠+进度条+humanizeTrendState；640/645 迁 `.notice--warning`。
- 排除（Exclude）：不改 reason-list（AT-0202）、不改 trade card、不改 domain。
- 停止前置点（Stop before）：不删除既有 data-testid（mts-card/mts-state-grid/mts-display-label/mts-non-advice 保留，供既有 E2E）。

**文件行动**
```yaml
files:
  - path: "src/features/presentation/ScoreBar.tsx"
    action: "create"
    purpose: "进度条组件：score number|null → 可视化条，null/not_applicable 中性不填充"
  - path: "src/App.tsx"
    action: "modify"
    purpose: "score-grid 裸枚举收折叠+进度条+humanizeTrendState；640/645 迁 .notice--warning"
```

**输入**
- mts.{displayLabel,technicalReminder,trendState,mtsScore,scoreBand,signalType,alertLevel}；PT-01 resolveScoreTone/humanizeTrendState/ScoreBar

**输出**
- mts-card 主视图人话化 + 进度条；原始枚举移入折叠区

**代码模式参考**
```yaml
references:
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "mts-card section (634-660) score-grid (650-656)"
    observed_convention: "signal-card 用 className={`signal-card ${mtsTone(mts)}`}+data-testid；score-grid 现直呈 <span>trend_state {mts.trendState}</span> 等 5 字段"
    apply_to_this_task: "className 改用 resolveScoreTone 产 tone 类；score-grid 5 字段移入折叠详情，主视图留 displayLabel+ScoreBar+technicalReminder"
    do_not_copy: "不复制裸枚举呈现到别处；不改 mtsScore 数值来源"
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "signal-degradation-note (639-642) / signal-error-note (644-647)"
    observed_convention: "<div className='data-notice' data-testid='...'>...</div> 呈来源降级/错误"
    apply_to_this_task: "className data-notice → notice--warning；retry 技术态(641)移入折叠"
    do_not_copy: "不改 .data-notice 定义；testid 保留"
  - path: "src/features/chart/ChartSurface.tsx"
    pattern_type: "same_surface"
    symbol: "PanelShell / 函数组件导出 (344 quote-line 附近)"
    observed_convention: "features 下 React 函数组件 export function + props 类型 + className+data-testid"
    apply_to_this_task: "ScoreBar 沿用同函数组件约定，props {score:number|null}"
    do_not_copy: "不复制 chart 计算逻辑"
```

**接口 / 数据契约**

`<ScoreBar score={mtsScore}>`：number|null → 进度条 DOM；null/not_applicable → 中性不填充（VO-03）。

**TDD 范围**
- Behavior under test: 主视图人话化 + 进度条 + warning 迁移
- Red scope: E2E 断言主视图无 trend_state 等 token + 进度条存在（改前失败）
- Green scope: 重排使通过
- Refactor scope: mtsTone→resolveScoreTone 引用迁移
- Out of scope: reason-list（AT-0202）
- Required assertions: mts-card 文本不含 5 枚举前缀；ScoreBar DOM 存在；640/645 类为 notice--warning
- Test data boundary: mts fixture（formal + degraded）
- Test doubles boundary: Playwright route
- Fault / mutation signal: 枚举残留 → DOM 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- mts"
    expected_signal: "失败（主视图仍含 trend_state / 无进度条）"
  green:
    cwd: "."
    command: "npm run test:e2e -- mts"
    expected_signal: "通过（无枚举 token + 进度条存在）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e -- mts"
    expected_signal: "build exit 0 + mts E2E 全绿"
```

**证据**
- red_report: mts E2E 失败日志
- green_report: mts E2E 通过日志
- regression_report: build + mts E2E

**停止条件**
- 若 mtsScore 无有效数值来源无法渲染进度条 → 按中性不填充处理，不停；若某枚举无既有人话源 → 停下回 prd（DEC-S03）。

---

#### AT-0202

**标题：** ReasonRegistry reasons+invalidators 双处裸理由码人话化 + 折叠详情本地态

**父任务：** PT-02

**队列元数据：** detail_ref: "AT-0202"。

**目标**

把 reason-list 中 reasons.map(667) 与 invalidators.map(673) 两处 `<code>{item.code}</code>` 改为人话（item.label 优先，否则 humanizeReason(item.code)）；原始 code 收进可展开详情；折叠用本地 useState。

**执行边界**
- 纳入（Include）：App.tsx reason-list 双处人话化 + 折叠详情 useState + 展开入口。
- 排除（Exclude）：不改 score-grid（AT-0201）、不改 domain 注册表。
- 停止前置点（Stop before）：不新建 code→label 映射表（复用 humanizeReason）。

**文件行动**
```yaml
files:
  - path: "src/App.tsx"
    action: "modify"
    purpose: "reason-list reasons+invalidators 双处裸 code 人话化 + 折叠详情"
```

**输入**
- mts.reasons[].{code,detail,label?}、mts.invalidators[].{code,detail}；PT-01 humanizeReason

**输出**
- reason-list 主视图人话；原始 code 移入折叠详情；未注册码 UNKNOWN_CODE 回落

**代码模式参考**
```yaml
references:
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "reason-card reason-list (662-677) reasons.map(665)/invalidators.map(671)"
    observed_convention: "两处 <li><code>{item.code}</code><span>{item.detail}</span></li>，invalidators 带 className='warning'"
    apply_to_this_task: "<code>{item.code}</code> → 人话 label（item.label ?? humanizeReason(item.code)）；原始 code 移折叠"
    do_not_copy: "不删 detail 文本；不改 invalidators 的 warning class 语义为来源 warning"
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "useState hooks（组件顶部既有 setSelected/setDetailTab 等）"
    observed_convention: "React useState 本地态，事件 onClick 切换"
    apply_to_this_task: "折叠 const [expanded,setExpanded]=useState(false) + disclosure 按钮"
    do_not_copy: "不写 localStorage/快照持久化（DEC-S04）"
```

**接口 / 数据契约**

`humanizeReason(code)` = resolveMtsReason(code).label；折叠本地 useState 不持久化。

**TDD 范围**
- Behavior under test: 理由码人话化 + 折叠 + UNKNOWN_CODE 不直呈
- Red scope: E2E 断言 reason-list 无裸 code + 默认折叠原始码不可见（改前失败）
- Green scope: 双处人话化 + 折叠
- Refactor scope: 无
- Out of scope: score-grid（AT-0201）
- Required assertions: reason-list 主视图不含裸 code；展开后原始 code 可见；未注册码不呈原始串（NEG-04）
- Test data boundary: mts fixture 含已注册 + 未注册 code
- Test doubles boundary: Playwright route
- Fault / mutation signal: 裸 code 残留主视图 → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- mts"
    expected_signal: "失败（reason-list 仍含裸 code）"
  green:
    cwd: "."
    command: "npm run test:e2e -- mts"
    expected_signal: "通过（无裸 code + 折叠展开生效）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e -- mts"
    expected_signal: "build exit 0 + mts E2E 全绿"
```

**证据**
- red_report: mts E2E 失败日志
- green_report: mts E2E 通过日志
- regression_report: build + mts E2E

**停止条件**
- 若某理由码无 label 且非注册码回落不生效 → 停下回 prd/tech-design（DEC-S03）。

---

### PT-03: 交易信号卡密度 + 层级 + nonAdvice 常驻 + 折叠 / 主看信号突出·免责合规红线 / App.tsx trade-signal-card 段 528-632

```yaml
parent_task:
  id: "PT-03"
  title: "交易信号卡密度+层级+nonAdvice常驻+折叠 / 主卡突出·免责红线·非 ready 人话化 / App.tsx trade-signal-card 段"
  depends_on: ["PT-01", "PT-02"]
  authorized_path_summary:
    - "src/App.tsx（trade-signal-card 段 528-632：主/次层级、明细折叠、signal-topline 非 ready 人话化、nonAdvice 常驻）"
    - "src/styles.css（复用 PT-01 tone/次级灰字类，如需新增不改共享定义）"
    - "tests/e2e/*（信号卡默认关键数字/折叠展开/非 ready 人话/nonAdvice 可见）"
  required_evidence:
    - "E2E：默认呈关键数字、三段回测明细默认折叠→展开可见"
    - "E2E：非 ready status 人话化（无枚举串）、来源降级无回测块"
    - "DOM：主/次层级差样式断言 + nonAdvice 折叠态仍可见；build exit 0"
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "AT-0301"
        title: "主/次层级重排 + 三段回测明细折叠本地态 + nonAdvice 常驻不进折叠 + 关键数字默认呈现"
        execution_order: 1
        depends_on: ["PT-01", "PT-02"]
        write_scope: ["src/App.tsx"]
        read_scope: ["src/App.tsx", "src/features/presentation/humanize.ts", "src/features/presentation/tone.ts"]
        detail_ref: "AT-0301"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
      - id: "AT-0302"
        title: "signal-topline 非 ready status 人话化（humanizeTradeStatus）+ 非 ready 无回测块 + 价位分层级"
        execution_order: 2
        depends_on: ["AT-0301"]
        write_scope: ["src/App.tsx"]
        read_scope: ["src/App.tsx", "src/features/presentation/humanize.ts", "src/domain/trade-signals.ts"]
        detail_ref: "AT-0302"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
```

**依赖（Depends on）：** PT-01, PT-02（App.tsx 同文件串行，避免与 mts-card 段编辑冲突）

**本轮增量价值：** 交易信号卡默认只呈关键数字（stanceLabel/持仓/胜率/累计收益），三段回测/反T/事件明细默认折叠可展开；主卡突出、回测降次级灰字形成层级差；signal-topline 非 ready 人话化；nonAdvice 免责默认与折叠态均常驻可见。

**风险处理目标：** DEC-S08/INV-06（免责合规红线：折叠不隐藏 nonAdvice）；BR-07/NEG-02（非 ready 不呈空回测块）；SUC-03-OP-02 非 ready status 人话化（消除 App.tsx:532 直呈枚举）；RISK-05 主观层级差双证据。证据来源：tech-design M4 / §7 RISK-05。

**授权变更集边界：**
- 纳入（Include）：App.tsx trade-signal-card 段主/次层级、明细折叠、signal-topline 人话化、levels 正式信号位 vs ATR 观察位分层、nonAdvice 常驻。
- 排除（Exclude）：不改 mts-card（PT-02）、不改 domain 门控/回测计算、不改 :379。
- 延后（Deferred）：折叠态持久化（不做）。

**目标：** 完成后信号卡默认关键数字、明细折叠、非 ready 人话、免责常驻、主次层级差可辨。

**完成边界：** E2E 默认关键数字+折叠展开+非 ready 人话+nonAdvice 可见 + 层级差 DOM 断言 + build exit 0。

**父任务级实现边界：**
- 只重排 trade-signal-card 段；接入 PT-01 humanizeTradeStatus/tone。
- nonAdvice(628-630) 结构上置于主卡常驻区、不进折叠容器。

**测试要求：**
- **Given** 标的 status=ready（有回测）或非 ready（not_target/data_insufficient/source_degraded）
- **When** 用户默认查看信号卡，随后展开明细
- **Then** 默认关键数字+明细折叠；展开呈三段回测；非 ready 人话化无回测块；nonAdvice 始终可见

**测试驱动开发范围契约：**

| 项 | 内容 |
|----|------|
| Behavior under test | 信号卡密度/层级/折叠/免责/非 ready 人话 |
| Red scope | E2E 断言默认无回测流水+折叠展开+非 ready 无枚举串+nonAdvice 折叠态可见（改前失败） |
| Green scope | trade-signal-card 重排使通过 |
| Refactor scope | signal-topline 直呈 status → humanizeTradeStatus |
| Out of scope | 不改 mts-card/domain/侧栏 |
| Required assertions | 默认态无三段回测流水；展开后可见；signal-topline 非 ready 无枚举串；非 ready 无回测块 DOM；nonAdvice 折叠态可见；主/次层级差样式 |
| Test data boundary | E2E fixture ready + 非 ready（复用/扩展 card.spec envelope） |
| Allowed test doubles | Playwright route |
| Forbidden shortcuts | 不得把 nonAdvice 放进折叠区蒙混；不得用空回测容器占位 |
| Fault / mutation signal | 折叠隐藏 nonAdvice 或非 ready 呈回测块 → 断言失败 |
| Command source | parent_local_atomic_task_queue |
| Red command / queue refs | AT-0301 / AT-0302 red |
| Green command / queue refs | AT-0301 / AT-0302 green |
| Regression command / queue refs | npm run test:e2e + npm run build |

**测试义务（Test Obligation）：**
```yaml
risk_level: "high"
surfaces:
  - "trade_signal_card_presentation"
required_capabilities:
  - "e2e(playwright)"
  - "dom_assertion(hierarchy_style)"
  - "build_typecheck"
evidence_required:
  - "主/次层级差 DOM 断言 + 截图"
  - "非 ready 无回测块 DOM 断言"
  - "npm run build exit 0"
accepted_alternatives: {}
```

**端到端义务（E2E Obligation）：**
```yaml
risk_level: "high"
user_surfaces:
  - "交易信号卡默认态 + 折叠明细"
required_capabilities:
  - "e2e_collapse_expand"
  - "e2e_non_advice_visible_when_collapsed"
  - "e2e_non_ready_humanized"
evidence_required:
  - "折叠默认→展开→明细可见 Playwright"
  - "折叠态 nonAdvice 可见 Playwright（NEG-05）"
  - "非 ready 人话 + 无回测块 Playwright（NEG-02）"
accepted_alternatives:
  "e2e_collapse_expand":
    - "无"
```

**授权路径摘要：**
| 文件 | 变更类型 |
|-----|---------|
| src/App.tsx | 修改（trade-signal-card 段 528-632） |
| tests/e2e/* | 新增/修改 |

**父任务完成清单：**
- [ ] AT-0301/0302 完成 Red→Green→Refactor→Regression
- [ ] 默认关键数字+折叠+非 ready 人话+nonAdvice 常驻 E2E 通过
- [ ] 非 ready 无回测块（BR-07）+ 主次层级差双证据
- [ ] e2e_obligation required capabilities 有证据

**原子任务详情（Atomic Task details）：**

#### AT-0301

**标题：** 主/次层级重排 + 三段回测明细折叠本地态 + nonAdvice 常驻不进折叠 + 关键数字默认呈现

**父任务：** PT-03

**队列元数据：** detail_ref: "AT-0301"。

**目标**

把三段回测/反T/事件明细(590-627)降为次级灰字并默认折叠（本地 useState），主卡默认呈 stanceLabel + 关键数字（胜率/累计收益 620-627）；nonAdvice(628-630)常驻主卡区不进折叠。

**执行边界**
- 纳入（Include）：明细折叠 useState + 展开入口；主/次层级样式（复用 PT-01 tone + 次级灰字）；关键数字默认呈现；nonAdvice 常驻。
- 排除（Exclude）：不改 signal-topline 非 ready（AT-0302）、不改 domain。
- 停止前置点（Stop before）：不删 data-testid（trade-signal-card/trade-signal-stance/trade-backtest-summary/trade-signal-non-advice 保留）。

**文件行动**
```yaml
files:
  - path: "src/App.tsx"
    action: "modify"
    purpose: "trade-signal-card 主/次层级 + 明细折叠 + nonAdvice 常驻 + 关键数字默认"
```

**输入**
- tradeSignal.{stanceLabel,holding,levels,nonAdvice}、tradeBacktest.{winRate,strategyReturnPct}、fanT

**输出**
- 信号卡默认关键数字 + 折叠明细 + nonAdvice 常驻

**代码模式参考**
```yaml
references:
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "trade-signal-card (529-631)：级 grid(535-619)/backtest-line(614-626)/non-advice(628-630)"
    observed_convention: "signal-card 内 plan-group-title + level-grid 铺开三段回测；nonAdvice 用 <p className='technical-reminder' data-testid='trade-signal-non-advice'>"
    apply_to_this_task: "三段回测/反T(590-627)移入折叠容器；主卡留 stanceLabel+backtest 关键数字；nonAdvice 置折叠外常驻"
    do_not_copy: "不改 levels 数值来源；不把 nonAdvice 放折叠内"
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "useState 折叠（同 AT-0202）"
    observed_convention: "本地 useState + onClick 切换"
    apply_to_this_task: "明细折叠本地态，默认收起"
    do_not_copy: "不持久化"
```

**接口 / 数据契约**

折叠本地 useState 不持久化；nonAdvice 常驻（DEC-S08）；关键数字复用既有 tradeBacktest 字段。

**TDD 范围**
- Behavior under test: 密度/层级/折叠/免责常驻
- Red scope: E2E 断言默认无三段回测流水 + 折叠展开 + nonAdvice 折叠态可见（改前失败）
- Green scope: 重排使通过
- Refactor scope: 层级样式接入 PT-01 tone
- Out of scope: 非 ready 人话（AT-0302）
- Required assertions: 默认无三段流水；展开可见；nonAdvice 折叠态可见；主/次层级差样式 DOM
- Test data boundary: ready fixture
- Test doubles boundary: Playwright route
- Fault / mutation signal: 折叠隐藏 nonAdvice → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- gate"
    expected_signal: "失败（默认铺开三段回测 / nonAdvice 折叠隐藏）"
  green:
    cwd: "."
    command: "npm run test:e2e -- gate"
    expected_signal: "通过（默认关键数字+折叠+nonAdvice 常驻）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e"
    expected_signal: "build exit 0 + E2E 全绿"
```

**证据**
- red_report: E2E 失败日志
- green_report: E2E 通过日志
- regression_report: build + 全量 E2E

**停止条件**
- 若 nonAdvice 无法在折叠态常驻（结构冲突）→ 停下回 tech-design M4（DEC-S08）。

---

#### AT-0302

**标题：** signal-topline 非 ready status 人话化 + 非 ready 无回测块 + 价位分层级

**父任务：** PT-03

**队列元数据：** detail_ref: "AT-0302"。

**目标**

signal-topline(532) 非 ready 直呈 `{tradeSignal.status}` 枚举串 → humanizeTradeStatus；status!==ready 不呈回测块（BR-07）；levels 分正式信号位 vs ATR 观察位两层级。

**执行边界**
- 纳入（Include）：signal-topline 人话化；非 ready 无回测块；价位分层。
- 排除（Exclude）：不改 domain 门控（只读消费 tradeSignal.status）、不改主卡折叠（AT-0301）。
- 停止前置点（Stop before）：不重实现来源→信号降级门控（DEC-S01）。

**文件行动**
```yaml
files:
  - path: "src/App.tsx"
    action: "modify"
    purpose: "signal-topline 非 ready 人话化 + 非 ready 无回测块 + 价位层级"
```

**输入**
- tradeSignal.status/stanceLabel（domain 门控已产出 source_degraded）；PT-01 humanizeTradeStatus

**输出**
- 非 ready 呈人话说明、无回测块；ready 价位分层级

**代码模式参考**
```yaml
references:
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "signal-topline (530-533)：<strong>{status==='ready'?(holding?'持仓中':'空仓'):tradeSignal.status}</strong>"
    observed_convention: "非 ready 分支直呈 tradeSignal.status 原始枚举串"
    apply_to_this_task: "非 ready 分支改 humanizeTradeStatus(status)；回测块已在 status==='ready' 守卫(536/620)内，确认非 ready 不进"
    do_not_copy: "不改 domain 门控；不重算 status"
  - path: "src/domain/trade-signals.ts"
    pattern_type: "same_surface"
    symbol: "buildTradeSignalState source_degraded 门控 (619-627)"
    observed_convention: "门控在 domain 层产出 status=source_degraded，呈现层只读"
    apply_to_this_task: "只读 tradeSignal.status，不复制门控判断到 App.tsx"
    do_not_copy: "不在呈现层重实现 sourceHealth!==formal→source_degraded"
```

**接口 / 数据契约**

`humanizeTradeStatus(status)`（优先复用 stanceLabel）；非 ready 无回测块（BR-07）；只读 domain 门控结果（DEC-S01）。

**TDD 范围**
- Behavior under test: 非 ready 人话 + 无回测块 + 价位层级
- Red scope: E2E 断言非 ready 无枚举串 + 无回测块（改前失败）
- Green scope: 人话化 + 守卫
- Refactor scope: 无
- Out of scope: 主卡折叠（AT-0301）
- Required assertions: signal-topline 非 ready 无 `not_target_symbol`/`source_degraded` 枚举串；非 ready 无回测块 DOM；ready 价位正式位 vs ATR 观察位可辨
- Test data boundary: 非 ready fixture（not_target/data_insufficient/source_degraded）
- Test doubles boundary: Playwright route
- Fault / mutation signal: 非 ready 呈枚举串或空回测块 → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- gate"
    expected_signal: "失败（signal-topline 呈原始 status 枚举串）"
  green:
    cwd: "."
    command: "npm run test:e2e -- gate"
    expected_signal: "通过（非 ready 人话 + 无回测块）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e"
    expected_signal: "build exit 0 + E2E 全绿"
```

**证据**
- red_report: E2E 失败日志
- green_report: E2E 通过日志
- regression_report: build + 全量 E2E

**停止条件**
- 若非 ready 人话需在呈现层重算门控 → 停下回 tech-design §5.4（DEC-S01 越界，禁）。

---

### PT-04: 侧栏条目结构 + 来源小圆点 + archived 弱化 / 侧栏扫读·来源非第二主源 / App.tsx watchlist 段 424-466

```yaml
parent_task:
  id: "PT-04"
  title: "侧栏条目结构+来源小圆点+archived弱化 / 侧栏可扫读·来源非第二主源 / App.tsx watchlist 段"
  depends_on: ["PT-01", "PT-03"]
  authorized_path_summary:
    - "src/App.tsx（watchlist 段 424-466：条目名称+代码一行、价格右对齐、来源文本→小圆点、archived 弱化）"
    - "src/styles.css（复用 PT-01 tone 类做小圆点弱化，如需新增不改共享定义）"
    - "tests/e2e/watchlist/*（条目结构 + 小圆点非主源 + archived 弱化 DOM 断言）"
  required_evidence:
    - "DOM：条目含名称+代码行 + 右对齐价格；来源为小圆点非横幅主源"
    - "DOM：archived 弱化样式；npm run build exit 0"
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "AT-0401"
        title: "侧栏条目重排：名称+代码一行、价格+涨跌右对齐主看、来源文本改小圆点弱化"
        execution_order: 1
        depends_on: ["PT-01", "PT-03"]
        write_scope: ["src/App.tsx", "src/styles.css"]
        read_scope: ["src/App.tsx", "src/features/presentation/tone.ts", "src/styles.css"]
        detail_ref: "AT-0401"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
      - id: "AT-0402"
        title: "archived 条目弱化区分 active（复用 .watch-item.archived）+ DOM 断言"
        execution_order: 2
        depends_on: ["AT-0401"]
        write_scope: ["src/App.tsx", "src/styles.css"]
        read_scope: ["src/App.tsx", "src/styles.css"]
        detail_ref: "AT-0402"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
```

**依赖（Depends on）：** PT-01, PT-03（App.tsx 同文件串行）

**本轮增量价值：** 侧栏每条名称+代码一行、价格+涨跌右对齐为主看数字，来源状态从文本弱化为小圆点（formal 中性/非 formal 需关注弱提示），archived 弱化区分 active；侧栏来源不作第二来源主源，可快速扫读定位标的。

**风险处理目标：** GAP-D3 去重复（侧栏来源降级为非主源，配合 PT-05 源计数=1）；SCN-06 侧栏扫读；STM-01 archived 呈现区分（不改归档业务逻辑）。证据来源：tech-design M5。

**授权变更集边界：**
- 纳入（Include）：App.tsx watchlist 段条目结构、来源小圆点、archived 弱化；styles.css 小圆点/弱化样式（复用 PT-01 tone）。
- 排除（Exclude）：不改归档/恢复业务逻辑（archiveSymbol/restoreSymbol）、不改 domain、不作来源权威主源（在 PT-05）。
- 延后（Deferred）：无。

**目标：** 完成后侧栏条目结构清晰、来源小圆点弱化、archived 可辨。

**完成边界：** DOM 断言条目结构 + 小圆点非主源 + archived 弱化 + build exit 0。

**父任务级实现边界：**
- 只重排 watchlist 段呈现；来源用 resolveSourceTone 弱化上色为小圆点。
- 侧栏来源不带来源权威横幅语义（呼应 SCN-03-COND-01）。

**测试要求：**
- **Given** 侧栏含多条 active（formal/非 formal 来源）+ archived 标的
- **When** 用户扫读侧栏
- **Then** 名称+代码一行、价格右对齐主看、来源小圆点非主源、archived 弱化

**测试驱动开发范围契约：**

| 项 | 内容 |
|----|------|
| Behavior under test | 侧栏条目结构 + 来源小圆点 + archived 弱化 |
| Red scope | E2E/DOM 断言条目结构 + 小圆点非横幅 + archived 弱化（改前失败） |
| Green scope | watchlist 段重排使通过 |
| Refactor scope | sourceStatusLabel 文本 → resolveSourceTone 小圆点 |
| Out of scope | 不改归档逻辑/domain/顶部主源 |
| Required assertions | 条目含名称+代码行 + 右对齐价格；来源为小圆点承载（非 data-notice/横幅）；archived 弱化样式 |
| Test data boundary | watchlist fixture（active formal/非 formal + archived） |
| Allowed test doubles | Playwright route |
| Forbidden shortcuts | 不得把来源做成第二横幅主源；不改归档业务逻辑 |
| Fault / mutation signal | 来源仍为横幅主源 → 断言失败 |
| Command source | parent_local_atomic_task_queue |
| Red command / queue refs | AT-0401 / AT-0402 red |
| Green command / queue refs | AT-0401 / AT-0402 green |
| Regression command / queue refs | npm run test:e2e -- watchlist + npm run build |

**测试义务（Test Obligation）：**
```yaml
risk_level: "medium"
surfaces:
  - "watchlist_sidebar_presentation"
required_capabilities:
  - "dom_assertion"
  - "e2e(playwright)"
  - "build_typecheck"
evidence_required:
  - "条目结构 + 小圆点非主源 DOM 断言"
  - "archived 弱化 DOM 断言 + 截图"
  - "npm run build exit 0"
accepted_alternatives: {}
```

**端到端义务（E2E Obligation）：**
```yaml
risk_level: "low"
user_surfaces:
  - "侧栏自选列表"
required_capabilities:
  - "e2e_dom_structure"
evidence_required:
  - "侧栏条目结构 + archived 区分 Playwright/DOM"
accepted_alternatives:
  "e2e_dom_structure":
    - "verify 阶段 preview 截图 + DOM 断言（既有 watchlist E2E 回归）"
```

**授权路径摘要：**
| 文件 | 变更类型 |
|-----|---------|
| src/App.tsx | 修改（watchlist 段 424-466） |
| src/styles.css | 修改（小圆点/弱化，不改共享定义） |
| tests/e2e/watchlist/* | 新增/修改 |

**父任务完成清单：**
- [ ] AT-0401/0402 完成 Red→Green→Refactor→Regression
- [ ] 条目结构 + 小圆点非主源 + archived 弱化 DOM 断言
- [ ] 归档业务逻辑未改（回归通过）
- [ ] test_obligation required capabilities 有证据

**原子任务详情（Atomic Task details）：**

#### AT-0401

**标题：** 侧栏条目重排：名称+代码一行、价格+涨跌右对齐主看、来源文本改小圆点弱化

**父任务：** PT-04

**队列元数据：** detail_ref: "AT-0401"。

**目标**

把 watch-item-main(430-438) 内 `sourceStatusLabel · price · change%` 一行拆为：名称+代码一行、价格+涨跌右对齐主看数字、来源改小圆点弱化（resolveSourceTone 弱化上色，formal 中性/非 formal 需关注）。

**执行边界**
- 纳入（Include）：条目结构重排 + 来源小圆点；styles.css 小圆点样式。
- 排除（Exclude）：不改 archived（AT-0402）、不改归档按钮逻辑、不改 domain。
- 停止前置点（Stop before）：不删 watch-item/watch-item-main 结构 testid 相关（既有 selected 逻辑保留）。

**文件行动**
```yaml
files:
  - path: "src/App.tsx"
    action: "modify"
    purpose: "watch-item 名称+代码一行、价格右对齐、来源小圆点"
  - path: "src/styles.css"
    action: "modify"
    purpose: "来源小圆点弱化样式（复用 PT-01 tone），不改共享定义"
```

**输入**
- item.{name,symbol,market}、summary.{latestPrice,changePercent,sourceStatus}；PT-01 resolveSourceTone

**输出**
- 侧栏条目结构化 + 来源小圆点非主源

**代码模式参考**
```yaml
references:
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "watch-item-main (430-438)：<strong>{name}</strong><small>{symbol}·{market}</small><small>{sourceStatusLabel}·{price}·{change}%</small>"
    observed_convention: "条目用 strong+small 堆叠；来源/价格/涨跌挤在同一 small 行"
    apply_to_this_task: "拆为名称+代码一行 + 价格+涨跌右对齐 + 来源小圆点（resolveSourceTone 上色）"
    do_not_copy: "不改 onClick setSelected / 归档按钮；不把来源做横幅"
  - path: "src/styles.css"
    pattern_type: "same_surface"
    symbol: ".watch-item / .up / .down 附近"
    observed_convention: "既有 watch-item 布局 + .up/.down 涨跌色（不改）"
    apply_to_this_task: "小圆点用 PT-01 tone 类；价格右对齐用 flex 布局"
    do_not_copy: "不改 .up/.down(:403-409)"
```

**接口 / 数据契约**

resolveSourceTone 弱化上色为小圆点；涨跌复用 `.up`/`.down`（不改）。

**TDD 范围**
- Behavior under test: 侧栏条目结构 + 来源小圆点
- Red scope: DOM 断言名称+代码行 + 右对齐价格 + 小圆点非横幅（改前失败）
- Green scope: 重排
- Refactor scope: sourceStatusLabel 文本 → 小圆点
- Out of scope: archived（AT-0402）
- Required assertions: 条目含名称+代码结构；价格右对齐；来源承载为小圆点（非 data-notice 横幅）
- Test data boundary: watchlist fixture
- Test doubles boundary: Playwright route
- Fault / mutation signal: 来源仍为文本横幅 → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- watchlist"
    expected_signal: "失败（条目结构未重排/来源仍文本）"
  green:
    cwd: "."
    command: "npm run test:e2e -- watchlist"
    expected_signal: "通过（结构化 + 小圆点）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e -- watchlist"
    expected_signal: "build exit 0 + watchlist E2E 全绿"
```

**证据**
- red_report: watchlist E2E 失败日志
- green_report: watchlist E2E 通过日志
- regression_report: build + watchlist E2E

**停止条件**
- 若来源小圆点弱化需改归档业务逻辑才能达成 → 停下回 tech-design M5（范围外）。

---

#### AT-0402

**标题：** archived 条目弱化区分 active（复用 .watch-item.archived）+ DOM 断言

**父任务：** PT-04

**队列元数据：** detail_ref: "AT-0402"。

**目标**

archived 条目(454-464)弱化呈现、与 active 视觉区分（复用/加强既有 `.watch-item.archived`），不作主看强调，不改归档/恢复业务逻辑。

**执行边界**
- 纳入（Include）：archived 弱化样式 + DOM 断言。
- 排除（Exclude）：不改 restoreSymbol/archiveSymbol 逻辑、不改 active 条目（AT-0401）。
- 停止前置点（Stop before）：不改 STM-01 归档状态迁移。

**文件行动**
```yaml
files:
  - path: "src/App.tsx"
    action: "modify"
    purpose: "archived 条目弱化呈现（如需 className 调整）"
  - path: "src/styles.css"
    action: "modify"
    purpose: ".watch-item.archived 弱化样式加强，不改共享定义"
```

**输入**
- archivedWatchlist item.{name,symbol,market}；既有 `.watch-item.archived`

**输出**
- archived 弱化区分 active

**代码模式参考**
```yaml
references:
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "archive-block archived items (451-465)：<div className='watch-item archived'>"
    observed_convention: "archived 已用 .watch-item.archived 类 + 独立 archive-block 区"
    apply_to_this_task: "加强 .watch-item.archived 弱化样式（灰度/透明度），保持结构"
    do_not_copy: "不改 restoreSymbol onClick 逻辑"
  - path: "src/styles.css"
    pattern_type: "same_surface"
    symbol: ".watch-item.archived（既有）"
    observed_convention: "既有 archived 弱化类"
    apply_to_this_task: "弱化样式在此加强，不改共享 .data-notice/.up/.down"
    do_not_copy: "不改共享类"
```

**接口 / 数据契约**

无接口变更；纯呈现弱化，STM-01 逻辑不改。

**TDD 范围**
- Behavior under test: archived 弱化区分
- Red scope: DOM 断言 archived 弱化样式（改前若无区分则失败）
- Green scope: 弱化样式
- Refactor scope: 无
- Out of scope: 归档逻辑
- Required assertions: archived 条目弱化样式类存在且与 active 区分
- Test data boundary: watchlist fixture 含 archived
- Test doubles boundary: Playwright route
- Fault / mutation signal: archived 与 active 同权重 → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- watchlist"
    expected_signal: "失败（archived 未弱化区分）"
  green:
    cwd: "."
    command: "npm run test:e2e -- watchlist"
    expected_signal: "通过（archived 弱化）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e -- watchlist"
    expected_signal: "build exit 0 + watchlist E2E 全绿（归档/恢复回归通过）"
```

**证据**
- red_report: watchlist E2E 失败日志
- green_report: watchlist E2E 通过日志
- regression_report: build + watchlist E2E（含既有 archive-restore 回归）

**停止条件**
- 若弱化区分需改 STM-01 归档逻辑 → 停下（范围外，不改）。

---

### PT-05: 顶部层级重排 + 唯一主源承载计数=1（GAP-D3）/ 去重复·顶部动线 / styles.css CSS-only 重排 + App.tsx market-workspace 段 + ChartSurface quote-line testid

```yaml
parent_task:
  id: "PT-05"
  title: "顶部层级重排+唯一主源计数=1 / 去重复·标题主位·涨跌色≠警告色 / styles.css CSS-only + App.tsx market-workspace + ChartSurface quote-line"
  depends_on: ["PT-01", "PT-04"]
  authorized_path_summary:
    - "src/styles.css（CSS-only 重排 LayoutController 既有 DOM 类：.workspace-header h2 / .range-controls / .layout-control-strip / .workspace-actions）"
    - "src/App.tsx（market-workspace 段 470：新增 source-authority 唯一来源承载元素，读 getSourceStatus）"
    - "src/features/chart/ChartSurface.tsx（quote-line :344 挂 data-testid=price-authority；不改 :207 由 PT-06 负责）"
    - "tests/e2e/workbench/*、tests/e2e/restore-layout/*（source-authority/price-authority 计数=1 + 标题主位 + 布局切换后仍主位）"
  required_evidence:
    - "DOM：getByTestId('source-authority') 计数=1、getByTestId('price-authority') 计数=1"
    - "DOM：.workspace-header h2 字号/权重 > .range-controls/.layout-control-strip；控件右对齐"
    - "E2E：切换周期/布局后标题仍主位且切换生效（STM-06 语义不变）；涨跌色 vs 警告色并置截图；build exit 0"
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "AT-0501"
        title: "App.tsx market-workspace 新增 source-authority 唯一来源承载 + ChartSurface quote-line 挂 price-authority（计数=1）"
        execution_order: 1
        depends_on: ["PT-01", "PT-04"]
        write_scope: ["src/App.tsx", "src/features/chart/ChartSurface.tsx"]
        read_scope: ["src/App.tsx", "src/features/chart/ChartSurface.tsx", "src/features/presentation/tone.ts", "src/features/layout/LayoutController.tsx"]
        detail_ref: "AT-0501"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
      - id: "AT-0502"
        title: "styles.css CSS-only 顶部层级重排：标题主位 + 周期/视图控件降级右对齐（不改 LayoutController JSX）"
        execution_order: 2
        depends_on: ["AT-0501"]
        write_scope: ["src/styles.css"]
        read_scope: ["src/styles.css", "src/features/layout/LayoutController.tsx"]
        detail_ref: "AT-0502"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
```

**依赖（Depends on）：** PT-01, PT-04（PT-04 已把侧栏来源降级为非主源，是源计数=1 的前置；App.tsx/ChartSurface/styles.css 同文件串行）

**本轮增量价值：** 来源状态收敛到 1 处权威承载（`data-testid="source-authority"` 计数=1），价格/涨跌收敛到 1 处权威承载（`data-testid="price-authority"` 计数=1），其余来源呈现降级为派生一致性指示或小圆点；顶部标题以最高字号/权重呈现主位，周期/视图控件降级右对齐；涨跌红绿色与来源/布局警告色语义分离、视觉可辨。

**风险处理目标：** GAP-D3 唯一主源（DOM 计数=1 断言）；SCN-04 主观项（标题主位/控件降级 CSS + DOM 双证据）；**LayoutController 越界风险**（标题/控件在范围外文件，只能 CSS-only 重排既有 DOM 类，不改其 JSX → STM-06 切换语义天然不变）。证据来源：tech-design M6 / DEC-S05 / DEC-S09 / §7 GAP-D3。

**授权变更集边界：**
- 纳入（Include）：App.tsx market-workspace 段新增 source-authority 元素；ChartSurface quote-line 挂 price-authority testid；styles.css CSS-only 重排 `.workspace-header h2`/`.range-controls`/`.layout-control-strip`/`.workspace-actions`。
- 排除（Exclude）：**不改 `src/features/layout/LayoutController.tsx` 任何 JSX**（含 :74 `<h2>`、:80 range-controls、:90 layout-control-strip）；不改 LayoutController:75/121 `.data-notice`（范围外禁改）；不改 STM-06 切换白名单/逻辑；不改 `.up`/`.down`(:403-409)；不改 ChartSurface:207（PT-06）。
- 延后（Deferred）：demo_fallback 最终色档定档（GAP-D2 verify 前用户决策，source-authority 承载设计为可切换档）。

**目标：** 完成后来源/价格各计数=1 权威主源，标题主位、控件降级右对齐、切换语义不变、涨跌色 ≠ 警告色。

**完成边界：** source-authority/price-authority 计数=1 DOM 断言 + 标题主位/控件降级 DOM 断言 + 切换后仍主位 E2E + 涨跌 vs 警告色并置截图 + build exit 0。

**父任务级实现边界（Parent-level implementation boundary）：**
- source-authority 唯一来源承载新增在授权面（App.tsx market-workspace），读 getSourceStatus + resolveSourceTone；派生一致性指示（ChartSurface chart-source-status、MTS 卡降级子集、信号卡 source_degraded）保留独立 testid、不计入 source-authority 计数。
- 顶部标题主位/控件降级只允许 CSS-only 重排 LayoutController 既有 DOM 类，禁止改其 JSX。

**测试要求：**
- **Given** 某标的界面（formal/demo_fallback/stale 来源，默认 focus 布局，dense/mobile_tab 可切换）
- **When** 用户观察顶部并切换周期/布局
- **Then** source-authority/price-authority 各计数=1；标题字号/权重 > 控件且控件右对齐；切换后标题仍主位、切换生效、STM-06 语义不变；涨跌色 ≠ 警告色

**测试驱动开发范围契约（TDD Scope Contract）：**

| 项 | 内容 |
|----|------|
| Behavior under test | 唯一主源计数=1 + 顶部层级重排 + 切换语义不变 |
| Red scope | E2E 断言 source-authority/price-authority 计数=1 + 标题字号 > 控件（改前失败，无 testid/无层级差） |
| Green scope | 新增承载 + CSS 重排使断言通过 |
| Refactor scope | 来源多处同级呈现收敛为派生一致性指示 |
| Out of scope | 不改 LayoutController JSX / STM-06 / domain / ChartSurface:207 |
| Required assertions | getByTestId('source-authority').count()==1；getByTestId('price-authority').count()==1；h2 computed font-size/weight > 控件；切换后仍主位；涨跌 .up/.down ≠ 警告类 |
| Test data boundary | workbench fixture（复用 gate/workbench envelope，含 formal/stale + 布局切换） |
| Allowed test doubles | Playwright route + 布局 snapshot fixture |
| Forbidden shortcuts | 不得改 LayoutController JSX；不得给多个元素同 source-authority testid 蒙混计数；不得移除 LayoutController:75 来源文本 |
| Fault / mutation signal | 若源承载计数≠1 或标题主位丢失或改了 LayoutController → 断言/回归失败 |
| Command source | parent_local_atomic_task_queue |
| Red command / queue refs | AT-0501 / AT-0502 red |
| Green command / queue refs | AT-0501 / AT-0502 green |
| Regression command / queue refs | npm run test:e2e + npm run build + git diff 证 LayoutController.tsx 未改 |

**测试义务（Test Obligation）：**
```yaml
risk_level: "high"
surfaces:
  - "top_region_hierarchy"
  - "source_authority_dedup"
  - "price_authority_dedup"
required_capabilities:
  - "dom_count_assertion"
  - "dom_computed_style_assertion"
  - "e2e(playwright)"
  - "build_typecheck"
evidence_required:
  - "source-authority/price-authority 计数=1 DOM 断言"
  - "标题主位/控件降级 DOM + 截图双证据"
  - "git diff 证 LayoutController.tsx 未改"
accepted_alternatives:
  "dom_computed_style_assertion":
    - "verify preview 截图 + 样式类断言双证据（RISK-05 主观项）"
```

**端到端义务（E2E Obligation）：**
```yaml
risk_level: "high"
user_surfaces:
  - "顶部区（标题 + 周期/视图控件） + 来源/价格权威承载"
required_capabilities:
  - "e2e_layout_switch_title_stable"
  - "e2e_dom_count"
evidence_required:
  - "切换周期/布局后标题仍主位且切换生效 Playwright（NEG-06 非法值归一化）"
  - "source-authority/price-authority 计数=1 Playwright"
accepted_alternatives:
  "e2e_layout_switch_title_stable":
    - "无（SCN-04-COND-02 + NEG-06 须 E2E）"
```

**授权路径摘要（Authorized path summary）：**
| 文件 | 变更类型 |
|-----|---------|
| src/App.tsx | 修改（market-workspace 段 470，新增 source-authority） |
| src/features/chart/ChartSurface.tsx | 修改（quote-line :344 挂 price-authority testid） |
| src/styles.css | 修改（CSS-only 顶部层级重排，不改共享定义） |
| tests/e2e/workbench/*、tests/e2e/restore-layout/* | 新增/修改 |

**Prohibited paths：** `src/features/layout/LayoutController.tsx`（整文件禁改）；`styles.css:379`/`:403-409`；STM-06 切换逻辑。

**父任务完成清单（Parent completion checklist）：**
- [ ] AT-0501/0502 完成 Red→Green→Refactor→Regression
- [ ] source-authority/price-authority 计数=1 + 标题主位/控件降级双证据
- [ ] 切换后标题仍主位 + STM-06 语义不变 E2E；git diff 证 LayoutController.tsx 零改动
- [ ] e2e_obligation required capabilities 有证据

**原子任务详情（Atomic Task details）：**

#### AT-0501

**标题：** App.tsx market-workspace 新增 source-authority 唯一来源承载 + ChartSurface quote-line 挂 price-authority（计数=1）

**父任务（Parent task）：** PT-05 - 顶部层级重排 + 唯一主源承载计数=1

**队列元数据：** 见 `atomic_task_queue.execution_units[]` detail_ref: "AT-0501"。

**目标**

在 App.tsx market-workspace 段（470，RestoreStatus 上方或 LayoutController 上方的授权顶部区）新增唯一来源权威承载元素（`data-testid="source-authority"`，读 getSourceStatus + resolveSourceTone 四档），并把 ChartSurface quote-line(:344 chart-ohlc) 指定为价格权威承载挂 `data-testid="price-authority"`；使来源/价格各计数=1，其余来源呈现降级为派生一致性指示。

**执行边界**
- 纳入（Include）：App.tsx 新增 source-authority 元素；ChartSurface quote-line 挂 price-authority testid。
- 排除（Exclude）：不改 LayoutController JSX（其 :75 workbench-selection-summary 保留原样为派生上下文，非 source-authority testid，不计入计数）；不改 ChartSurface:207（PT-06）；不改 domain。
- 停止前置点（Stop before）：若发现必须移除 LayoutController:75 来源文本或改其 JSX 才能让来源"仅一处呈现"→ 停下（见停止条件）。

**文件行动**
```yaml
files:
  - path: "src/App.tsx"
    action: "modify"
    purpose: "market-workspace 段新增 source-authority 唯一来源权威承载（读 getSourceStatus + resolveSourceTone）"
  - path: "src/features/chart/ChartSurface.tsx"
    action: "modify"
    purpose: "quote-line(:344) 挂 data-testid=price-authority，指定价格权威承载"
```

**输入**
- getSourceStatus(activePayload, error)（App.tsx:79-84）；activePayload.sourceHealth.{status,degradationReason,affectedObjects}；PT-01 resolveSourceTone；ChartSurface quote-line 既有价格渲染

**输出**
- source-authority 计数=1、price-authority 计数=1 的顶部权威承载

**代码模式参考**
```yaml
references:
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "market-workspace section (470-490)：<section className='market-workspace'><RestoreStatus/><LayoutController/></section>"
    observed_convention: "顶部工作区段直接组合子组件；来源状态目前由子组件（LayoutController:75/ChartSurface:203）分散呈现"
    apply_to_this_task: "在此授权段新增单一 source-authority 承载元素，读 getSourceStatus + resolveSourceTone；不改子组件 JSX"
    do_not_copy: "不复制 LayoutController:75 的来源文本承载；不改 LayoutController"
  - path: "src/features/chart/ChartSurface.tsx"
    pattern_type: "same_surface"
    symbol: "quote-line (344)：<div className='quote-line' data-testid='chart-ohlc'>"
    observed_convention: "quote-line 为价格/OHLC 呈现容器，已有 chart-ohlc testid"
    apply_to_this_task: "追加 data-testid=price-authority 指定其为价格权威承载（计数=1）；涨跌沿用 .up/.down"
    do_not_copy: "不改 quote-line 价格计算/数据来源；不改 :207 data-notice"
  - path: "tests/e2e/gate/acceptance-matrix.spec.ts"
    pattern_type: "test_pattern"
    symbol: "getByTestId(...).toHaveCount / toContainText (58-93)"
    observed_convention: "Playwright getByTestId + toHaveClass/toContainText；envelope route fixture 驱动来源态"
    apply_to_this_task: "新增 expect(getByTestId('source-authority')).toHaveCount(1) / price-authority toHaveCount(1)"
    do_not_copy: "不复制 alert 部分断言"
```

**接口 / 数据契约**

source-authority 读 getSourceStatus + resolveSourceTone（DEC-S05/GAP-D3，计数=1）；price-authority 为 quote-line 单点（IF-价格主源）；派生一致性指示各自独立 testid、不计入来源权威计数（DEC-S06）。

**TDD 范围**
- Behavior under test: 唯一主源计数=1
- Red scope: E2E 断言 source-authority/price-authority 计数=1（改前失败，testid 不存在）
- Green scope: 新增承载 + testid
- Refactor scope: 来源多处同级呈现降级派生指示
- Out of scope: 顶部 CSS 层级（AT-0502）、LayoutController、domain
- Required assertions: source-authority count==1；price-authority count==1；派生指示 testid 不等于 source-authority
- Test data boundary: workbench/gate envelope fixture（formal/demo_fallback/stale）
- Test doubles boundary: Playwright route
- Fault / mutation signal: 计数≠1（漏加或重复 testid）→ 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- workbench"
    expected_signal: "失败（source-authority/price-authority testid 不存在，计数=0）"
  green:
    cwd: "."
    command: "npm run test:e2e -- workbench"
    expected_signal: "通过（source-authority/price-authority 各计数=1）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e && git diff --exit-code src/features/layout/LayoutController.tsx && echo LAYOUTCTRL_UNCHANGED"
    expected_signal: "build exit 0 + E2E 全绿 + 输出 LAYOUTCTRL_UNCHANGED"
```

**证据**
- red_report: workbench E2E 失败日志
- green_report: workbench E2E 通过日志
- regression_report: build + 全量 E2E + LayoutController 未改
- source_dedup_report: source-authority/price-authority 计数=1 断言输出

**停止条件**
- 若来源"仅一处呈现"或计数=1 必须改 LayoutController.tsx JSX / 移除其 :75 来源文本才能达成 → 停下回 technical_analysis / 决策门禁（tech-design M6 承载决策边界，不越界改范围外文件）。

---

#### AT-0502

**标题：** styles.css CSS-only 顶部层级重排：标题主位 + 周期/视图控件降级右对齐（不改 LayoutController JSX）

**父任务（Parent task）：** PT-05 - 顶部层级重排 + 唯一主源承载计数=1

**队列元数据：** detail_ref: "AT-0502"。

**目标**

仅用 styles.css 对 LayoutController 既有 DOM 类做层级重排：`.workspace-header h2`（标题）以最高字号/权重呈主位，`.range-controls`/`.layout-control-strip`（周期/视图控件）降级并右对齐（`.workspace-actions` flex 布局），不改 LayoutController JSX、不改 STM-06 切换语义。

**执行边界**
- 纳入（Include）：styles.css 对 `.workspace-header h2`/`.range-controls`/`.layout-control-strip`/`.workspace-actions`/`.eyebrow` 的层级/对齐样式。
- 排除（Exclude）：不改 LayoutController.tsx；不改 `.data-notice`(:379)/`.up`/`.down`(:403-409)；不改 STM-06。
- 停止前置点（Stop before）：若纯 CSS 无法达成标题主位（如 DOM 结构不支持）→ 停下（见停止条件）。

**文件行动**
```yaml
files:
  - path: "src/styles.css"
    action: "modify"
    purpose: "CSS-only 顶部层级重排（标题主位 + 控件降级右对齐），目标 LayoutController 既有 DOM 类"
```

**输入**
- LayoutController 既有 DOM：`.workspace-header`（含 `.eyebrow`/`<h2>`/workbench-selection-summary）、`.workspace-actions`（含 `.range-controls`/`.layout-control-strip`）

**输出**
- 标题主位（字号/权重 > 控件）+ 控件右对齐降级

**代码模式参考**
```yaml
references:
  - path: "src/features/layout/LayoutController.tsx"
    pattern_type: "same_surface"
    symbol: "workspace-header (73-118)：<header className='workspace-header'><div>...<h2>...</div><div className='workspace-actions'><div className='range-controls'/><div className='layout-control-strip'/></div></header>"
    observed_convention: "顶部 header 为 header+两 div 结构，标题 h2 与 workspace-actions（控件）并列；此文件范围外禁改 JSX"
    apply_to_this_task: "仅在 styles.css 针对这些既有类写层级样式：h2 加大字号/权重、workspace-actions 右对齐、控件降字号；READ-ONLY 参考其类名，不改此文件"
    do_not_copy: "禁止编辑 LayoutController.tsx；禁止改其 :75/:121 data-notice"
  - path: "src/styles.css"
    pattern_type: "same_surface"
    symbol: ".quote-line strong (391) / .signal-topline (582)"
    observed_convention: "既有字号/权重表达用 font-size + font-weight + flex justify-content"
    apply_to_this_task: "标题主位/控件降级沿用同 CSS 手法（font-size/weight/flex right-align）"
    do_not_copy: "不改 .up/.down/.data-notice"
```

**接口 / 数据契约**

无接口/JSX 变更；纯 CSS 层级重排（DEC-S09：切换语义不改，因不动 JSX）。

**TDD 范围**
- Behavior under test: 标题主位 + 控件降级右对齐 + 切换后仍主位
- Red scope: DOM computed-style 断言 h2 字号/权重 > 控件（改前失败）+ E2E 切换后标题仍主位
- Green scope: CSS 重排
- Refactor scope: 无
- Out of scope: LayoutController JSX / source-authority（AT-0501）/ STM-06 逻辑
- Required assertions: h2 computed font-size/weight > .range-controls/.layout-control-strip；控件右对齐；切换 dense/focus/mobile_tab 后标题仍主位、切换生效；非法值归一化不破坏（NEG-06）
- Test data boundary: workbench/restore-layout fixture（各布局模式）
- Test doubles boundary: Playwright route + layout snapshot
- Fault / mutation signal: 标题非主位或切换后丢失主位或 STM-06 语义变 → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- restore-layout"
    expected_signal: "失败（标题未主位/控件未降级）"
  green:
    cwd: "."
    command: "npm run test:e2e -- restore-layout"
    expected_signal: "通过（标题主位 + 控件降级 + 切换后仍主位）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e && git diff --exit-code src/features/layout/LayoutController.tsx && echo LAYOUTCTRL_UNCHANGED"
    expected_signal: "build exit 0 + E2E 全绿 + LAYOUTCTRL_UNCHANGED"
```

**证据**
- red_report: restore-layout E2E 失败日志
- green_report: restore-layout E2E 通过日志
- regression_report: build + 全量 E2E + LayoutController 未改
- hierarchy_report: 标题主位/控件降级 DOM + preview 截图双证据

**停止条件**
- 若纯 CSS 无法达成标题主位/控件降级（必须改 LayoutController JSX 结构）→ 停下回 technical_analysis / 决策门禁（不越界改范围外文件）。

---

### PT-06: 恢复态四档归位 + 范围内 data-notice 收尾迁移 / 恢复正常态不染警告色·爆炸半径隔离（SR-01）/ RestoreStatus.tsx + ChartSurface.tsx:207

```yaml
parent_task:
  id: "PT-06"
  title: "恢复态四档归位+范围内 data-notice 收尾迁移 / 恢复正常态不染警告色·恢复态vs来源态独立 / RestoreStatus.tsx + ChartSurface.tsx:207"
  depends_on: ["PT-01", "PT-05"]
  authorized_path_summary:
    - "src/features/restore/RestoreStatus.tsx（:16 全态 .data-notice → resolveRestoreTone 四档分色 + 技术态收详情）"
    - "src/features/chart/ChartSurface.tsx（:207 chart-degradation-note .data-notice → .notice--warning）"
    - "tests/e2e/restore-layout/*（恢复四态分色 + 恢复态vs来源态独立 DOM 断言）"
  required_evidence:
    - "DOM：restored/partial/default_fallback 逐态无 .notice--warning；failed/坏布局有需关注承载"
    - "DOM：恢复承载与来源承载为独立元素（NEG-03）；ChartSurface:207 用 .notice--warning 非 .data-notice"
    - "npm run build exit 0"
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "AT-0601"
        title: "RestoreStatus.tsx 四档分色（restored=normal/partial+default_fallback=info/failed+坏布局=warning）+ 技术态收详情"
        execution_order: 1
        depends_on: ["PT-01", "PT-05"]
        write_scope: ["src/features/restore/RestoreStatus.tsx"]
        read_scope: ["src/features/restore/RestoreStatus.tsx", "src/features/presentation/tone.ts", "src/types.ts"]
        detail_ref: "AT-0601"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
      - id: "AT-0602"
        title: "ChartSurface.tsx:207 chart-degradation-note 迁 .notice--warning（范围内 data-notice 收尾 1/4）"
        execution_order: 2
        depends_on: ["AT-0601"]
        write_scope: ["src/features/chart/ChartSurface.tsx"]
        read_scope: ["src/features/chart/ChartSurface.tsx", "src/styles.css"]
        detail_ref: "AT-0602"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
```

**依赖（Depends on）：** PT-01, PT-05（ChartSurface 与 PT-05 共享，同文件串行）

**本轮增量价值：** 工作台恢复状态从"全态复用黄条 `.data-notice`"改为四档分色（restored 中性/成功、partial+default_fallback 信息级、failed+坏布局丢弃需关注），技术态（reason/migratedFromLegacy/snapshotBytes）收进详情不拼主提示；恢复态与来源态用独立 DOM 元素承载；ChartSurface 图表降级提示迁到独立 warning 承载。

**风险处理目标：** SCN-01 直接根因（RestoreStatus.tsx:16 对全态复用 `.data-notice` 致正常恢复被染黄）；SR-01（范围内 data-notice 收尾迁移 RestoreStatus:16 + ChartSurface:207，不改 :379 定义）；NEG-03（恢复态 STM-07 vs 来源态 STM-02 两套独立状态机、独立承载）。证据来源：tech-design M7/M8 / DEC-S06 / §7 SR-01。

**授权变更集边界：**
- 纳入（Include）：RestoreStatus.tsx 四档分色 + 技术态收详情；ChartSurface.tsx:207 迁 `.notice--warning`。
- 排除（Exclude）：不改快照读写/STM-07 判定逻辑（范围外既有）；不改 :379 定义；不改 ChartSurface quote-line/chart-source-status（PT-05 派生指示）；不碰范围外 5 处 data-notice。
- 延后（Deferred）：无。

**目标：** 完成后恢复态四档分色、正常态无警告色、failed 见需关注、恢复态与来源态独立、ChartSurface 降级用独立 warning 承载。

**完成边界：** 恢复四态逐态 DOM 断言 + NEG-03 独立承载 DOM + ChartSurface:207 `.notice--warning` DOM + build exit 0。

**父任务级实现边界（Parent-level implementation boundary）：**
- RestoreStatus 用 resolveRestoreTone 四档，props 签名不变（单一调用方 App.tsx:471）；技术态收进详情不拼主提示。
- 范围内 data-notice 迁移收尾：RestoreStatus:16 + ChartSurface:207（M3 已迁 App.tsx:640/645，此处补齐 4/4）。

**测试要求：**
- **Given** restoreMetadata.status = restored/partial/default_fallback/failed（或 discardedLayoutKeys 非空）；某标的来源 stale（ChartSurface 降级）
- **When** 应用启动用户观察顶部恢复区 + 图表降级提示
- **Then** restored/partial/default_fallback 无黄条警告色；failed/坏布局见需关注；恢复承载与来源承载独立元素；ChartSurface:207 用 `.notice--warning`

**测试驱动开发范围契约（TDD Scope Contract）：**

| 项 | 内容 |
|----|------|
| Behavior under test | 恢复态四档分色 + 独立承载 + ChartSurface data-notice 迁移 |
| Red scope | E2E 断言 restored 无警告色 + 恢复/来源独立元素 + ChartSurface:207 用 .notice--warning（改前失败） |
| Green scope | RestoreStatus 四档 + ChartSurface:207 迁移 |
| Refactor scope | RestoreStatus 技术态收详情结构 |
| Out of scope | 不改快照读写/STM-07 逻辑/domain/范围外 data-notice |
| Required assertions | restored/partial/default_fallback 无 .notice--warning；failed/坏布局有需关注承载；恢复承载 testid ≠ 来源承载 testid（独立元素 NEG-03）；ChartSurface:207 class 为 .notice--warning 非 .data-notice |
| Test data boundary | restore-layout fixture（四态快照）+ stale 来源 fixture |
| Allowed test doubles | Playwright route + 快照 fixture |
| Forbidden shortcuts | 不得让恢复态与来源态共用同一 banner；不改 :379 定义 |
| Fault / mutation signal | restored 被染警告色 或 恢复/来源共用承载 → 断言失败 |
| Command source | parent_local_atomic_task_queue |
| Red command / queue refs | AT-0601 / AT-0602 red |
| Green command / queue refs | AT-0601 / AT-0602 green |
| Regression command / queue refs | npm run test:e2e -- restore-layout + npm run build |

**测试义务（Test Obligation）：**
```yaml
risk_level: "high"
surfaces:
  - "restore_status_presentation"
  - "chart_degradation_notice"
required_capabilities:
  - "dom_assertion"
  - "e2e(playwright)"
  - "build_typecheck"
evidence_required:
  - "恢复四态逐态无/有警告色 DOM 断言 + 逐态截图"
  - "恢复态vs来源态独立元素 DOM 断言（NEG-03）"
  - "npm run build exit 0"
accepted_alternatives: {}
```

**端到端义务（E2E Obligation）：**
```yaml
risk_level: "medium"
user_surfaces:
  - "工作台恢复状态区 + 图表降级提示"
required_capabilities:
  - "e2e_restore_four_states"
  - "dom_independent_carrier"
evidence_required:
  - "restored/partial/default_fallback/failed 逐态 Playwright/DOM"
  - "恢复承载与来源承载独立元素 DOM 断言"
accepted_alternatives:
  "e2e_restore_four_states":
    - "构造四态快照 fixture 分别驱动 + preview 截图"
```

**授权路径摘要（Authorized path summary）：**
| 文件 | 变更类型 |
|-----|---------|
| src/features/restore/RestoreStatus.tsx | 修改（:16 四档分色） |
| src/features/chart/ChartSurface.tsx | 修改（:207 迁 .notice--warning） |
| tests/e2e/restore-layout/* | 新增/修改 |

**Prohibited paths：** `styles.css:379`；范围外 5 处 data-notice；快照读写/STM-07 逻辑；ChartSurface quote-line/chart-source-status（PT-05）。

**父任务完成清单（Parent completion checklist）：**
- [ ] AT-0601/0602 完成 Red→Green→Refactor→Regression
- [ ] 恢复四态分色 + failed 需关注 + 恢复/来源独立承载（NEG-03）
- [ ] ChartSurface:207 迁 .notice--warning；范围内 data-notice 迁移 4/4 完成；:379 未改
- [ ] e2e_obligation required capabilities 有证据

**原子任务详情（Atomic Task details）：**

#### AT-0601

**标题：** RestoreStatus.tsx 四档分色 + 技术态收详情

**父任务（Parent task）：** PT-06 - 恢复态四档归位 + 范围内 data-notice 收尾迁移

**队列元数据：** detail_ref: "AT-0601"。

**目标**

把 RestoreStatus.tsx:16 对全部四态复用 `.data-notice` 改为按 resolveRestoreTone 四档分色（restored→normal 中性/成功、partial+default_fallback→`.notice--info`、failed+坏布局丢弃→`.notice--warning`），reason/discardedLayoutKeys/migratedFromLegacy/snapshotBytes 等技术态收进详情、不拼进主提示，恢复承载与来源承载用独立元素。

**执行边界**
- 纳入（Include）：RestoreStatus.tsx 四档分色 + 技术态收详情 + 独立承载。
- 排除（Exclude）：不改快照读写/STM-07 判定逻辑；不改 props 签名；不改 :379。
- 停止前置点（Stop before）：不改唯一调用方 App.tsx:471 的 props 传参。

**文件行动**
```yaml
files:
  - path: "src/features/restore/RestoreStatus.tsx"
    action: "modify"
    purpose: "全态 .data-notice → resolveRestoreTone 四档分色 + 技术态收详情，props 不变"
```

**输入**
- metadata.{status,reason,discardedLayoutKeys,migratedFromLegacy,snapshotBytes}（STM-07）；PT-01 resolveRestoreTone

**输出**
- 恢复四态分色承载（restored 无警告色、failed 需关注）；技术态收详情

**代码模式参考**
```yaml
references:
  - path: "src/features/restore/RestoreStatus.tsx"
    pattern_type: "same_surface"
    symbol: "RestoreStatus (14-22)：<div className='data-notice' data-testid='restore-status'>{statusLabel}{reason}{discarded}</div>"
    observed_convention: "现状全四态复用 .data-notice 单元素 + statusLabel 四态中文映射（7-12）"
    apply_to_this_task: "className 改用 resolveRestoreTone(metadata) 映射的四档类（normal/.notice--info/.notice--warning）；技术态（reason/discarded/migrated/snapshotBytes）收进详情子元素；保留 restore-status testid"
    do_not_copy: "不改 statusLabel 四态文案；不改 :379 data-notice 定义"
  - path: "src/features/presentation/tone.ts"
    pattern_type: "same_surface"
    symbol: "resolveRestoreTone（PT-01/AT-0102 产出）"
    observed_convention: "restored→normal、partial/default_fallback→info、failed/坏布局→warning、未知→warning 兜底"
    apply_to_this_task: "RestoreStatus 消费该函数产 tone → className"
    do_not_copy: "不在组件内重实现档位判断（复用 resolveRestoreTone）"
  - path: "tests/e2e/gate/acceptance-matrix.spec.ts"
    pattern_type: "test_pattern"
    symbol: "getByTestId('restore-status').toContainText('已恢复'/'已回退默认布局') (91-102)"
    observed_convention: "既有 E2E 已断言 restore-status 文案；沿用 getByTestId 断言类名/警告色"
    apply_to_this_task: "扩展为逐态断言无/有 .notice--warning + 独立元素"
    do_not_copy: "不复制 layout-mode 断言"
```

**接口 / 数据契约**

`RestoreStatus({metadata})` props 签名不变；内部 resolveRestoreTone 四档；恢复承载独立于来源承载（DEC-S06/NEG-03）。

**TDD 范围**
- Behavior under test: 恢复态四档分色 + 技术态收详情 + 独立承载
- Red scope: E2E 断言 restored 无警告色 + failed 需关注 + 恢复/来源独立元素（改前失败，全态黄条）
- Green scope: 四档分色
- Refactor scope: 技术态收详情结构
- Out of scope: 快照读写/STM-07 逻辑
- Required assertions: restored/partial/default_fallback 无 .notice--warning；failed/坏布局有需关注；restore-status 与 source-authority 独立元素（NEG-03）
- Test data boundary: 四态快照 fixture
- Test doubles boundary: Playwright route + 快照 fixture
- Fault / mutation signal: restored 被染警告色 → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- restore-layout"
    expected_signal: "失败（restored 仍复用黄条 .data-notice）"
  green:
    cwd: "."
    command: "npm run test:e2e -- restore-layout"
    expected_signal: "通过（四档分色 + 正常态无警告色 + 独立承载）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e"
    expected_signal: "build exit 0 + 全量 E2E 全绿（含既有 restore 回归）"
```

**证据**
- red_report: restore-layout E2E 失败日志
- green_report: restore-layout E2E 通过日志
- regression_report: build + 全量 E2E
- restore_states_report: 四态逐态 DOM + 截图

**停止条件**
- 若四档分色需改快照读写/STM-07 判定逻辑 → 停下（范围外，不改）。

---

#### AT-0602

**标题：** ChartSurface.tsx:207 chart-degradation-note 迁 .notice--warning（范围内 data-notice 收尾 1/4）

**父任务（Parent task）：** PT-06 - 恢复态四档归位 + 范围内 data-notice 收尾迁移

**队列元数据：** detail_ref: "AT-0602"。

**目标**

把 ChartSurface.tsx:207 chart-degradation-note 的 `.data-notice`（来源降级合法 warning 档）迁到 `.notice--warning` 新类，完成范围内 data-notice 迁移 4/4；chart-source-status(203) 保留为派生一致性指示（PT-05 已框定非来源权威主源）。

**执行边界**
- 纳入（Include）：ChartSurface:207 className `.data-notice` → `.notice--warning`。
- 排除（Exclude）：不改 chart-source-status(203)/quote-line(344 price-authority，PT-05)；不改 :379；不改图表数据逻辑。
- 停止前置点（Stop before）：不改 ChartSurface 其他 data-notice 之外结构。

**文件行动**
```yaml
files:
  - path: "src/features/chart/ChartSurface.tsx"
    action: "modify"
    purpose: ":207 chart-degradation-note .data-notice → .notice--warning"
```

**输入**
- ChartSurface 既有 chart-degradation-note(:205-209)；PT-01 `.notice--warning` 类

**输出**
- ChartSurface 降级提示用独立 warning 承载；范围内 data-notice 迁移 4/4

**代码模式参考**
```yaml
references:
  - path: "src/features/chart/ChartSurface.tsx"
    pattern_type: "same_surface"
    symbol: "chart-degradation-note (205-209)：<div className='data-notice' data-testid='chart-degradation-note'>{isDegraded ? `${status}·${sourceSummary}` : sourceSummary}</div>"
    observed_convention: "图表降级提示用 .data-notice，条件 isDegraded||error||loading||!payload 呈现"
    apply_to_this_task: "className 'data-notice' → 'notice--warning'；保留 chart-degradation-note testid 与渲染条件"
    do_not_copy: "不改 :379 定义；不改 chart-source-status/quote-line；不改渲染条件逻辑"
  - path: "src/App.tsx"
    pattern_type: "same_surface"
    symbol: "AT-0201 已迁 App.tsx:640/645 → .notice--warning"
    observed_convention: "范围内 data-notice → .notice--warning 的既定迁移手法（M3 已做 2/4）"
    apply_to_this_task: "沿用同迁移手法，此为 4/4 收尾"
    do_not_copy: "不改共享 .data-notice 定义"
```

**接口 / 数据契约**

无接口变更；className 迁移（SR-01 范围内 4/4，DATA/状态无变更）。

**TDD 范围**
- Behavior under test: ChartSurface 降级提示独立 warning 承载
- Red scope: DOM 断言 chart-degradation-note class 为 .notice--warning 非 .data-notice（改前失败）
- Green scope: className 迁移
- Refactor scope: 无
- Out of scope: chart-source-status/quote-line/domain
- Required assertions: chart-degradation-note class == .notice--warning；:379 .data-notice 定义未改；范围内 data-notice 迁移 4/4 完成（grep 范围内仅剩 0 处旧类）
- Test data boundary: stale/degraded 来源 fixture
- Test doubles boundary: Playwright route
- Fault / mutation signal: 仍用 .data-notice → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- restore-layout"
    expected_signal: "失败（chart-degradation-note 仍 .data-notice）"
  green:
    cwd: "."
    command: "npm run test:e2e -- restore-layout"
    expected_signal: "通过（chart-degradation-note 用 .notice--warning）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e && grep -rn 'data-notice' src/App.tsx src/features/restore src/features/chart | grep -v 'notice--' || echo RANGE_INTERNAL_MIGRATED"
    expected_signal: "build exit 0 + 全量 E2E 全绿 + 输出 RANGE_INTERNAL_MIGRATED（范围内旧 .data-notice 用法已清 4/4）"
```

**证据**
- red_report: restore-layout E2E 失败日志
- green_report: restore-layout E2E 通过日志
- regression_report: build + 全量 E2E + 范围内迁移 4/4 grep 证据

**停止条件**
- 若迁移波及 chart-source-status/quote-line 或 :379 定义 → 停下回 PT-06 边界（SR-01 隔离）。

---

### PT-07: 跨呈现一致性 + 范围外零改动回归验证 / RISK-04 一致性·SR-01 隔离·RISK-07 无回归 / tests/e2e 集成回归（终局验证切片）

```yaml
parent_task:
  id: "PT-07"
  title: "跨呈现一致性+范围外零改动回归验证 / NEG-01 一致性·SR-01 范围外零改动·axe+E2E 无回归 / tests/e2e 集成回归"
  depends_on: ["PT-02", "PT-03", "PT-04", "PT-05", "PT-06"]
  authorized_path_summary:
    - "tests/e2e/**（跨呈现一致性 NEG-01/03 + 唯一主源计数=1 聚合 + axe 无新增违规 + 既有路径无回归）"
  required_evidence:
    - "E2E：来源 stale → 信号卡 source_degraded 不显 ready 不给价位（NEG-01）；恢复态vs来源态独立（NEG-03）"
    - "范围外 5 处 .data-notice 零改动：grep 证 :379 定义未改 + 范围外 5 用法 class 未改 + 改造前后 preview 截图 + DOM 断言未被重着色"
    - "axe 无新增可访问性违规 + 既有 E2E 全绿 + npm run build exit 0（EVD-01 前提）"
  atomic_task_queue:
    status: "ready"
    review_status: "pending"
    execution_units:
      - id: "AT-0701"
        title: "跨呈现一致性 E2E：来源 stale→信号卡 source_degraded（NEG-01）+ 恢复态vs来源态独立（NEG-03）+ 唯一主源计数=1 聚合"
        execution_order: 1
        depends_on: ["PT-02", "PT-03", "PT-05", "PT-06"]
        write_scope: ["tests/e2e/gate/consistency.spec.ts"]
        read_scope: ["tests/e2e/", "src/App.tsx", "src/features/chart/ChartSurface.tsx", "src/features/restore/RestoreStatus.tsx"]
        detail_ref: "AT-0701"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
      - id: "AT-0702"
        title: "SR-01 范围外零改动回归（grep + 改造前后 preview 截图 + DOM 断言未重着色）+ axe 无新增违规 + 既有 E2E 无回归"
        execution_order: 2
        depends_on: ["AT-0701", "PT-04"]
        write_scope: ["tests/e2e/gate/scope-guard.spec.ts"]
        read_scope: ["tests/e2e/", "src/features/alerts/AlertRulePanel.tsx", "src/features/layout/LayoutController.tsx", "src/features/workbench/WorkbenchShell.tsx", "src/styles.css"]
        detail_ref: "AT-0702"
        reviewer_verdict: "pending"
        evidence_required: [red_report, green_report, regression_report]
```

**依赖（Depends on）：** PT-02, PT-03, PT-04, PT-05, PT-06（需全部实现落地后做集成/回归）

**本轮增量价值：** 以 E2E + 回归证据锁定三项终局约束——① 跨呈现一致性（来源 stale 时来源权威承载/MTS 卡/交易信号卡三处一致降级、恢复态与来源态独立承载）；② 唯一主源计数=1 聚合校验；③ 范围外 5 处 `.data-notice` 零改动 + axe 无新增违规 + 既有 E2E 用户路径无回归。

**风险处理目标：** RISK-04/INV-07（一致性门控只读，三处读同一 domain 结果，不重实现门控）；SR-01（范围外零改动阻断类硬约束）；RISK-07/NEG-07（axe + E2E 无回归）。证据来源：tech-design §5.4 / §7 SR-01/RISK-04/RISK-07 / DEC-S06。

**授权变更集边界：**
- 纳入（Include）：新增 tests/e2e 集成/回归 spec（consistency + scope-guard）。
- 排除（Exclude）：不改任何 src 产品代码（本切片纯验证，若发现缺陷回对应实现父任务修，不在此处补实现）；不改范围外组件。
- 延后（Deferred）：无。

**目标：** 完成后有可复核的一致性 + 范围外零改动 + 无回归证据，锁定 SR-01/RISK-04/RISK-07。

**完成边界：** NEG-01/NEG-03 E2E 通过 + 唯一主源计数=1 聚合断言 + 范围外零改动回归（grep + 截图 + DOM）+ axe 无新增违规 + 既有 E2E 全绿 + build exit 0。

**父任务级实现边界（Parent-level implementation boundary）：**
- 纯验证切片：产出 E2E/回归 spec 与证据，不写产品实现；发现缺陷回 PT-02~06 对应父任务修复。
- 范围外零改动判据：范围外 5 处 `.data-notice`（AlertRulePanel:136、LayoutController:75/121、WorkbenchShell:78/135）改造前后零可观察变化 + :379 定义未改。

**测试要求：**
- **Given** 全部实现（PT-02~06）已落地；来源 stale 态；恢复态与来源态并存；范围外组件（AlertRulePanel/LayoutController/WorkbenchShell）
- **When** 运行集成 E2E + axe + 范围外零改动回归
- **Then** 信号卡 source_degraded 一致降级、恢复/来源独立、唯一主源计数=1、范围外零改动、axe 无新增违规、既有路径无回归

**测试驱动开发范围契约（TDD Scope Contract）：**

| 项 | 内容 |
|----|------|
| Behavior under test | 跨呈现一致性 + 唯一主源聚合 + 范围外零改动 + 无回归 |
| Red scope | consistency/scope-guard spec 先失败（一致性未接入或范围外被波及则失败） |
| Green scope | 全部实现落地后 spec 通过 |
| Refactor scope | 无（纯验证） |
| Out of scope | 不写产品实现；不改范围外组件 |
| Required assertions | 来源 stale→信号卡 source_degraded 不显 ready 不给价位（NEG-01）；恢复承载≠来源承载元素（NEG-03）；source-authority/price-authority 计数=1；范围外 5 处 data-notice class 未改 + :379 未改；axe 无新增违规；既有 E2E 全绿 |
| Test data boundary | 复用各 fixture（stale 来源、四态快照、范围外组件默认态） |
| Allowed test doubles | Playwright route + @axe-core/playwright |
| Forbidden shortcuts | 不得用改范围外组件让断言通过；不得在此切片补产品实现掩盖缺陷 |
| Fault / mutation signal | 来源 stale 而信号卡仍 ready、或范围外被重着色、或 axe 新增违规 → 断言失败 |
| Command source | parent_local_atomic_task_queue |
| Red command / queue refs | AT-0701 / AT-0702 red |
| Green command / queue refs | AT-0701 / AT-0702 green |
| Regression command / queue refs | npm run test:e2e（全量）+ npm run build |

**测试义务（Test Obligation）：**
```yaml
risk_level: "high"
surfaces:
  - "cross_presentation_consistency"
  - "out_of_scope_zero_change"
required_capabilities:
  - "e2e(playwright)"
  - "axe(@axe-core/playwright)"
  - "dom_assertion"
  - "grep_diff_guard"
evidence_required:
  - "NEG-01/NEG-03 E2E 通过"
  - "范围外零改动 grep + 截图 + DOM 断言"
  - "axe 无新增违规 + 既有 E2E 全绿 + build exit 0"
accepted_alternatives:
  "axe(@axe-core/playwright)":
    - "无（NEG-07 要求 axe 无回归）"
```

**端到端义务（E2E Obligation）：**
```yaml
risk_level: "high"
user_surfaces:
  - "全看盘界面主要态（来源/信号/恢复/范围外组件）"
required_capabilities:
  - "e2e_consistency"
  - "e2e_axe_no_regression"
  - "e2e_out_of_scope_guard"
evidence_required:
  - "来源 stale→信号卡 source_degraded 一致 Playwright（NEG-01）"
  - "恢复态vs来源态独立 DOM（NEG-03）"
  - "范围外 5 处零改动回归 + axe 无新增违规"
accepted_alternatives:
  "e2e_out_of_scope_guard":
    - "范围外组件改造前后 preview 截图并置 + grep 证 class/定义未改"
```

**授权路径摘要（Authorized path summary）：**
| 文件 | 变更类型 |
|-----|---------|
| tests/e2e/gate/consistency.spec.ts | 新增 |
| tests/e2e/gate/scope-guard.spec.ts | 新增 |

**Prohibited paths：** 任何 `src/**` 产品代码（本切片纯验证）；范围外组件；`styles.css:379`。

**父任务完成清单（Parent completion checklist）：**
- [ ] AT-0701/0702 完成 Red→Green→Regression
- [ ] NEG-01 一致性 + NEG-03 独立承载 + 唯一主源计数=1 聚合通过
- [ ] 范围外 5 处 data-notice 零改动 + :379 未改 + axe 无新增违规 + 既有 E2E 无回归
- [ ] e2e_obligation required capabilities 有证据

**原子任务详情（Atomic Task details）：**

#### AT-0701

**标题：** 跨呈现一致性 E2E：来源 stale→信号卡 source_degraded（NEG-01）+ 恢复态vs来源态独立（NEG-03）+ 唯一主源计数=1 聚合

**父任务（Parent task）：** PT-07 - 跨呈现一致性 + 范围外零改动回归验证

**队列元数据：** detail_ref: "AT-0701"。

**目标**

新增 consistency.spec.ts：构造 stale 来源态断言信号卡呈 source_degraded、不显 ready、不给买卖价位（NEG-01，三处读同一 domain 门控结果一致）；断言恢复承载与来源承载为独立元素（NEG-03）；断言 source-authority/price-authority 各计数=1（聚合校验）。

**执行边界**
- 纳入（Include）：consistency.spec.ts（NEG-01 + NEG-03 + 唯一主源聚合）。
- 排除（Exclude）：不写产品实现（缺陷回 PT-03/05/06 修）；不改 src。
- 停止前置点（Stop before）：不在此 spec 内 mock 掉 domain 门控（须走真实 domain 只读路径证一致性）。

**文件行动**
```yaml
files:
  - path: "tests/e2e/gate/consistency.spec.ts"
    action: "create"
    purpose: "NEG-01 来源 stale→信号卡 source_degraded + NEG-03 独立承载 + 唯一主源计数=1"
```

**输入**
- stale 来源 envelope fixture；PT-03 signal 卡 source_degraded；PT-05 source-authority/price-authority；PT-06 RestoreStatus

**输出**
- consistency.spec.ts 通过（NEG-01/NEG-03/计数=1）

**代码模式参考**
```yaml
references:
  - path: "tests/e2e/mts/card.spec.ts"
    pattern_type: "test_pattern"
    symbol: "envelope(symbol, 'unavailable') degraded fixture (22-60)"
    observed_convention: "envelope() 构造 sourceHealth.status='unavailable'/degraded fixture，Playwright route 注入驱动降级态"
    apply_to_this_task: "复用 envelope 构造 stale 态，断言信号卡 source_degraded 人话 + 无 ready + 无价位"
    do_not_copy: "不复制 bars 生成细节外的断言"
  - path: "tests/e2e/gate/acceptance-matrix.spec.ts"
    pattern_type: "test_pattern"
    symbol: "getByTestId + toContainText/toHaveCount (58-103)"
    observed_convention: "Playwright getByTestId 断言跨面文本/计数"
    apply_to_this_task: "断言 source-authority/price-authority toHaveCount(1) + restore-status 与 source-authority 独立元素"
    do_not_copy: "不复制 alert/layout 断言"
  - path: "tests/e2e/restore-layout/resume.spec.ts"
    pattern_type: "test_pattern"
    symbol: "restore 快照 fixture 驱动"
    observed_convention: "restore-layout 用快照 fixture 驱动恢复态"
    apply_to_this_task: "NEG-03 构造恢复态+来源态并存，断言独立承载元素"
    do_not_copy: "不复制布局切换断言"
```

**接口 / 数据契约**

只读消费 domain 门控（trade-signals.ts:619-627 source_degraded，DEC-S01/S06）；三处读同一结果（INV-07）。

**TDD 范围**
- Behavior under test: 跨呈现一致性 + 唯一主源聚合
- Red scope: consistency.spec 断言（PT-03/05/06 未落地前失败）
- Green scope: 全部实现落地后通过
- Refactor scope: 无
- Out of scope: 产品实现
- Required assertions: 来源 stale→信号卡 source_degraded 不显 ready 不给价位；恢复承载≠来源承载元素；source-authority/price-authority 计数=1
- Test data boundary: stale envelope + 恢复快照 fixture
- Test doubles boundary: Playwright route（不 mock domain 门控）
- Fault / mutation signal: 来源 stale 而信号卡仍 ready → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- gate/consistency"
    expected_signal: "失败（实现未落地/一致性未达成）"
  green:
    cwd: "."
    command: "npm run test:e2e -- gate/consistency"
    expected_signal: "通过（NEG-01/NEG-03/计数=1）"
  regression:
    cwd: "."
    command: "npm run build && npm run test:e2e"
    expected_signal: "build exit 0 + 全量 E2E 全绿"
```

**证据**
- red_report: consistency E2E 失败日志
- green_report: consistency E2E 通过日志
- regression_report: build + 全量 E2E
- consistency_report: NEG-01/NEG-03/计数=1 断言输出

**停止条件**
- 若一致性只有靠呈现层重实现门控才能通过 → 停下回 tech-design §5.4（DEC-S01 越界，禁）。

---

#### AT-0702

**标题：** SR-01 范围外零改动回归（grep + 改造前后 preview 截图 + DOM 断言未重着色）+ axe 无新增违规 + 既有 E2E 无回归

**父任务（Parent task）：** PT-07 - 跨呈现一致性 + 范围外零改动回归验证

**队列元数据：** detail_ref: "AT-0702"。

**目标**

新增 scope-guard.spec.ts：断言范围外 5 处 `.data-notice`（AlertRulePanel:136、LayoutController:75/121、WorkbenchShell:78/135）改造前后零可观察变化（DOM class 未变 + 截图并置）+ grep 证 :379 `.data-notice` 定义未改；运行 @axe-core/playwright 证无新增可访问性违规；既有 E2E 用户路径全绿（NEG-07）。

**执行边界**
- 纳入（Include）：scope-guard.spec.ts（范围外零改动 + axe + 既有回归汇总）。
- 排除（Exclude）：不改任何 src；不改范围外组件。
- 停止前置点（Stop before）：若发现范围外被波及，回对应实现父任务修，不在此改范围外文件掩盖。

**文件行动**
```yaml
files:
  - path: "tests/e2e/gate/scope-guard.spec.ts"
    action: "create"
    purpose: "范围外 5 处 data-notice 零改动 + :379 未改 grep + axe 无新增违规 + 既有 E2E 无回归"
```

**输入**
- 范围外组件（AlertRulePanel/LayoutController/WorkbenchShell）；styles.css:379；@axe-core/playwright

**输出**
- scope-guard.spec.ts 通过（零改动 + axe + 无回归）

**代码模式参考**
```yaml
references:
  - path: "src/features/alerts/AlertRulePanel.tsx"
    pattern_type: "same_surface"
    symbol: ".data-notice (:136，范围外，禁改)"
    observed_convention: "范围外组件仍引用共享 .data-notice；DOM class 应保持不变"
    apply_to_this_task: "断言 AlertRulePanel 承载 class 仍含 data-notice、未被迁到 notice--*（证零改动）"
    do_not_copy: "禁止编辑此文件"
  - path: "src/features/workbench/WorkbenchShell.tsx"
    pattern_type: "same_surface"
    symbol: ".data-notice (:78/:135，范围外，禁改)"
    observed_convention: "范围外 WorkbenchShell 两处 .data-notice"
    apply_to_this_task: "断言 WorkbenchShell 承载 class 仍 .data-notice 未变"
    do_not_copy: "禁止编辑此文件"
  - path: "tests/e2e/alerts/panel.spec.ts"
    pattern_type: "test_pattern"
    symbol: "既有 alerts E2E 用户路径"
    observed_convention: "既有 spec 覆盖范围外组件用户路径，作无回归基线"
    apply_to_this_task: "既有 alerts/workbench/watchlist E2E 全绿作 NEG-07 无回归基线；scope-guard 补 axe + 范围外 class 断言"
    do_not_copy: "不复制断言体，引用既有 spec 作回归基线"
```

**接口 / 数据契约**

范围外零改动判据（SR-01）：范围外 5 处 class 未改 + :379 定义未改 + 零可观察变化；axe 无新增违规（RISK-07/NEG-07）。

**TDD 范围**
- Behavior under test: 范围外零改动 + axe 无回归 + 既有路径无回归
- Red scope: scope-guard spec 断言（若范围外被波及/axe 新增违规则失败）
- Green scope: 范围外零改动 + axe 通过
- Refactor scope: 无
- Out of scope: 产品实现/范围外文件
- Required assertions: 范围外 5 处 class 含 data-notice 未迁 notice--*；grep :379 定义未改；axe 无新增违规；既有 alerts/workbench/watchlist E2E 全绿
- Test data boundary: 范围外组件默认态 + 既有 fixture
- Test doubles boundary: Playwright route + @axe-core/playwright
- Fault / mutation signal: 范围外被重着色或 axe 新增违规 → 断言失败

**执行期验证命令**
```yaml
commands:
  red:
    cwd: "."
    command: "npm run test:e2e -- gate/scope-guard"
    expected_signal: "失败（若范围外被波及/axe 新增违规/基线未接入）"
  green:
    cwd: "."
    command: "npm run test:e2e -- gate/scope-guard"
    expected_signal: "通过（范围外零改动 + axe 无新增违规）"
  regression:
    cwd: "."
    command: "git diff --exit-code src/features/alerts/AlertRulePanel.tsx src/features/layout/LayoutController.tsx src/features/workbench/WorkbenchShell.tsx && grep -nE '\\.data-notice\\s*\\{' src/styles.css && npm run build && npm run test:e2e"
    expected_signal: "范围外 3 文件 git diff 无变化 + :379 .data-notice 定义存在未改 + build exit 0 + 全量 E2E 全绿"
```

**证据**
- red_report: scope-guard E2E 失败日志
- green_report: scope-guard E2E 通过日志
- regression_report: 范围外 git diff 无变化 + :379 未改 + build + 全量 E2E
- axe_report: @axe-core/playwright 无新增违规报告
- scope_guard_report: 范围外 5 处零改动截图并置 + DOM 断言

**停止条件**
- 若范围外组件被本任务改造波及（class 变/截图差异）→ 停下回对应实现父任务（PT-02/03/06）修复迁移，不在范围外文件掩盖（SR-01 阻断类硬约束）。

---

## Definition of Done

- [ ] 全部 Parent completion checklist（PT-01~PT-07）勾选
- [ ] 9/9 SUC-xx-OP-xx + 25/25 ADDED Scenario + 22 COND + NEG-01~07 均有对应测试覆盖
- [ ] 无回归（既有 E2E 全部通过 + axe 无新增违规 + build exit 0）
- [ ] 范围外 5 处 .data-notice 零改动 + styles.css:379/:403-409 未改
- [ ] 代码已提交，branch 干净

---

## 上游文档引用

| 文档 | 路径 | 章节 |
|-----|------|---------|
| 任务契约 | `harness-runtime/harness/missions/20260721-watchboard-ui-friendliness/mission-contract.md` | 验收条件、约束 |
| 验收场景 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/product/acceptance-scenarios.md` | SCN-01~07 / 22 COND / NEG-01~07 |
| 差量规格 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/product/specs/watchboard-presentation/spec.md` | 8 Requirement / 25 ADDED Scenario |
| 方案 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/solution/solution.md` | DEC-S01~S09 / SR-01 / §3.3 禁止路径 |
| 技术设计 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/technical-analysis/tech-design.md` | M1~M8 / §2 SUC 映射 / §4 接口 / §5 数据状态 / §7 验证策略 |
| 依赖影响 | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/discovery/dependency-impact.md` | GAP-D1/D2/D3 / .data-notice blast radius |
