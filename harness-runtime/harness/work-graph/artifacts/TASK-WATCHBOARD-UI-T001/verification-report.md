# 验证报告: 20260721-watchboard-ui-friendliness

> **来源**：验证技能 → `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/verify/verification-report.md`
> **上游**：`harness-runtime/harness/missions/20260721-watchboard-ui-friendliness/mission-contract.md` | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/breakdown/execution-brief.md`

**作者:** verification-engineer（子智能体，受 verify 编排调度）
**日期:** 2026-07-22
**任务标识:** 20260721-watchboard-ui-friendliness
**状态:** `ready`

---

## 控制契约

> 验证证据契约是验收证据索引。验收场景 / 条件标记为通过时必须引用具体证据；阻塞时必须写明原因、影响和下一步。

- Contract: contracts/verification-report.contract.yaml
- Control Contract: `contracts/verification-report.contract.yaml`
- 权威来源：外部 YAML 是程序化权威来源；本文件只作解释说明，不内嵌围栏式 YAML。

---

## 结论摘要（TL;DR）

本轮对 `20260721-watchboard-ui-friendliness`（看盘界面友好化改造）做全量重新验证：真实重跑单元测试（35/35）、Playwright 全量 E2E（50/50，两次独立复跑一致）、`npm run build`（exit 0），并对 `harness verify compute-scope` 给出的 49 个验收锚点（SCN-01~07、25 个差量规格 Scenario、9 个 `SUC-xx-OP-xx`、8 个 `DEC-Sxx`）逐条建立命令证据 + 结果证据双证据链，`harness contract check-acceptance-trace` / `harness verify true-e2e-check` / `harness verify detect-contradictions` 三项程序化校验均 PASS。SR-01 硬约束（`LayoutController.tsx`/`AlertRulePanel.tsx`/`WorkbenchShell.tsx` 整文件、`.data-notice`/`.up`/`.down` 共享定义）本轮独立 `git diff`/`grep` 复核确认零改动。22 条验收条件对应的 25 个差量规格 Scenario 与 7 个 NEG 负向路径全部有真实浏览器路径的 DOM/截图/axe 证据支撑，仅 2 项已知、已在 code-review 阶段经 Decision Gate 接受的 Med 级残留风险（E2E-FND-001 axe 覆盖面、E2E-FND-002 NEG-04 缺浏览器层注入证明）延续到本轮，未发现新的阻断缺陷。

| 项 | 结论 |
|----|------|
| 本轮验证范围 | 22 条验收条件（SCN-01~07 + 25 差量规格 Scenario）+ 7 条 NEG 负向路径 + 9 个 SUC-OP + 8 个 DEC-S 设计决策 + SR-01 硬约束 |
| 总体结论 | 带风险通过（建议；由主流程 `harness verify compute-conclusion` 最终裁定） |
| 阻断项数量 | 0 |
| 未验证项数量 | 0（全部 49 个 compute-scope 验收锚点均有 pass 结论；2 项存在已接受的证据深度缺口，非"未验证"） |
| 残留风险 | 2 项 Med（E2E-FND-001 axe 覆盖面不足、E2E-FND-002 NEG-04 缺浏览器层注入证明）+ code-review 阶段记录的 10 项 Low，均已经 code-review Decision Gate 接受，本轮如实沿用未重新展开调查 |

---

## 验证依据目录

| 来源产物 | 已消费内容 | 验证用途 | 缺口处理 |
|----------|------------|----------|----------|
| `mission-contract.md` | SCN-01~07 验收条件、成功定义 EVD-01~03、范围内 / 范围外边界、SR-01 型约束 | 定义预期结果和验收边界的最高层来源 | 无缺口 |
| `product/acceptance-scenarios.md` | 22 条 `SCN-xx-COND-xx` 验收条件（含 Given/When/Then）、7 条 NEG-01~07 负向路径、验证证据计划 | 建立本轮验收判定矩阵的逐条预期结果与证据类型口径 | 无缺口 |
| `product/specs/watchboard-presentation/spec.md` | 8 个 Requirement、25 个 ADDED Scenario（与 22 条 COND 一一对应，含更细粒度切分） | 作为 `compute-scope` 验收锚点粒度的权威来源，逐条建立 acceptance_trace | 无缺口 |
| `technical-analysis/tech-design.md` | 9 个 `SUC-xx-OP-xx` 到 M1~M8 模块的技术映射、INV-01~07 结构保证方式、§7 风险验证策略 | 建立系统操作覆盖矩阵与风险验证计划 | 无缺口 |
| `breakdown/execution-brief.md` | `required_evidence[]` 三元组（`re-Txxx-N` id → 命令 → verification_type）、7 父任务 15 原子任务授权边界、硬性约束表 | 提供本轮 `required_evidence_id` 唯一合法来源，不自创新 ID | 无缺口 |
| `execute/execution-result.md` | 15 个原子任务 DONE 状态、3 处 execute 阶段真实缺陷修复记录（alertLevel=风控 分支遗漏、humanizeTradeStatus 漏传参数、`.watch-list` 布局溢出）、DEV-01/DEV-02/ENV-01 偏差记录 | 判断执行阶段是否已有失败证据（`execute_failure_ref` 为空，未触发阻塞路径） | 无缺口 |
| `code-review/code-review.md` | 4 位审查员最终确认轮结论（correctness PASS；tdd/e2e/architecture PASS_WITH_RISK）、发现列表（GAP-01~03 已修复、E2E-FND-001/002 等 12 项已接受非阻断风险）| 判断是否存在未关闭高严重级别发现（无）、继承已接受风险清单 | 无缺口；本轮独立复核未重新展开调查，仅如实沿用并交叉验证关键结论（如 axe 断言真实存在且通过） |
| `harness verify compute-scope --json` | 49 个验收锚点（`acceptance_list`）、7 个任务的 `required_evidence_matrix`（16 条非人工命令 + 7 条人工/视觉项）、`test_layers`、`project_lint_enabled=true` | 作为本轮验证范围与 `required_evidence_id` 查表的权威 CLI 输出 | 无缺口 |
| 项目测试约定（`package.json`） | `npm run build`（tsc --noEmit && vite build）、`npm run test:e2e`（`NO_PROXY=... playwright test`）、`node --test` | 选择命令和证据收集方式 | 无缺口 |

---

## 验证目标

### 本轮包含

| 类型 | 编号 / 名称 | 来源 | 验证目标 |
|------|-------------|------|----------|
| 验收场景 / 条件 | SCN-01~07（22 条 COND + 25 差量规格 Scenario） | `acceptance-scenarios.md` / `spec.md` | 逐条建立预期结果 / 实际观察结果双证据链 |
| 负向 / 边界路径 | NEG-01~07 | `acceptance-scenarios.md` | 跨呈现一致性、UNKNOWN_CODE 回落、免责折叠、布局归一化、axe+E2E 无回归 |
| 系统操作 | SUC-01-OP-01 ~ SUC-06-OP-01（9 个） | `use-case-model.md` / `tech-design.md#系统操作到技术设计映射` | 验证读取 / 状态迁移 / 幂等结论与技术设计一致 |
| 设计决策 | DEC-S01~S09（本轮出现 8 个，S07 demo_fallback 定档为 verify 前用户决策，不在 compute-scope 强制锚点内） | `solution/solution.md` | 验证只读边界、去重复选点、跨呈现一致性等架构决策在实现中真实落地 |
| 质量与运行约束 | SR-01（共享类爆炸半径隔离）、NEG-07（axe 无回归） | `solution.md` §7 / `tech-design.md` §7 | 独立复核范围外零改动、可访问性无新增严重违规 |
| 任务项 | T001~T007（对应 PT-01~PT-07，15 个原子任务） | `execution-brief.md` | 逐任务重跑其 `required_evidence[]` 声明的命令，收集命令证据 |

### 本轮不包含

| 范围 | 原因 | 对交付判断的影响 | 后续处理 |
|------|------|------------------|----------|
| 交易信号 / 回测算法正确性本身 | mission-contract 范围外明确排除（只改呈现层，不改算法语义） | 无影响，本轮只验证呈现忠实性 | 不适用 |
| demo_fallback 最终色档定档（DEC-01/GAP-D2） | tech-design DEC-S07 设计为「可切换档、不改承载结构」，为 verify 前用户决策，非本轮验证阻断项 | 无影响，本轮按当前实现（信息级）验证通过 | 若用户后续改判，回 M1/M2 改一处映射，重验 SCN-01-COND-02 |
| 扩大 axe / NEG-04 浏览器层测试覆盖面 | code-review.md 已就 E2E-FND-001/002 走 Decision Gate 接受为非阻断残留风险；本轮职责边界是验证已有证据是否真实、是否覆盖验收条件本身，不是扩大覆盖面 | 无阻断影响，如实继承并独立复核关键断言仍然真实有效 | 建议下一轮迭代补充（已记录在 quality_trace） |

---

## 验证模型

### 验收判定矩阵

> 下表按 `acceptance-scenarios.md` 的 22 条 `SCN-xx-COND-xx` 人读粒度呈现（供人工审阅）；外部契约 `acceptance_trace[]` 按 `compute-scope` 给出的 49 个锚点（SCN-01~07 汇总项 + 25 个差量规格 Scenario 细粒度项 + 9 个 SUC-OP + 8 个 DEC-S）逐条落证据，两者是同一组事实的不同粒度呈现，互不矛盾（`harness verify detect-contradictions` 已验证 PASS）。

| 验收条件 | 来源 | 预期结果 | 实际观察方式 | 验证动作 | 命令证据 | 结果证据 | 失败判定 | 回流建议 |
|---|---|---|---|---|---|---|---|---|
| SCN-01-COND-01 formal/not_loaded 不出警告色 | acceptance-scenarios.md | 来源承载处无 `.notice--warning`/`.data-notice` 类 | 浏览器 DOM class 断言 | `npm run test:e2e -- mts / workbench` | CMD-E2E-T002/T005A | EV-RESULT-01 | 若 formal 态渲染 warning 类 | bug_fix |
| SCN-01-COND-02 demo_fallback 信息级 | acceptance-scenarios.md（DEC-01 默认档） | `notice--info` 非 `notice--warning` | DOM class 断言，两处（chart+mts）并证 | `npm run test:e2e -- gate / workbench` | CMD-E2E-T003/T005A | EV-RESULT-02 | 若染 warning 或与 formal 无区分 | bug_fix / DEC-01 用户改判回 M1/M2 |
| SCN-01-COND-03 stale/unavailable 出警告色+受影响范围 | acceptance-scenarios.md | `notice--warning` + 降级原因/受影响范围文案 | DOM 断言 + 人话文案断言 | `npm run test:e2e -- gate/consistency / workbench` | CMD-E2E-T007A/T005A | EV-RESULT-03 | 若无警告色或文案缺失 | bug_fix |
| SCN-01-COND-04 restored/partial/default_fallback 无警告黄条 | acceptance-scenarios.md | restored 中性、partial/default_fallback 信息级 | DOM class 断言，真实恢复路径驱动 | `npm run test:e2e -- restore-layout` | CMD-E2E-T006 | EV-RESULT-04 | 若任一态染 warning | bug_fix |
| SCN-01-COND-05 failed/坏布局丢弃出需关注 | acceptance-scenarios.md | `notice--warning`（discardedLayoutKeys 非空场景）+ 单测覆盖 status=failed | DOM 断言（可达分支）+ 单测（不可达分支） | `npm run test:e2e -- restore-layout`；`node --test tone.spec.ts` | CMD-E2E-T006/CMD-UNIT-01 | EV-RESULT-05 | 若 discardedLayoutKeys 非空未触发 warning | bug_fix |
| SCN-01-COND-06 negative 评分色物理区分（GAP-02） | acceptance-scenarios.md | caution 类 ≠ 来源 warning 类，同标的并置对比 | DOM class 断言 + 并置截图 | `npm run test:e2e -- mts` | CMD-E2E-T002 | EV-RESULT-06 | 若 caution 与 warning 类名重叠 | bug_fix |
| SCN-02-COND-01 主视图无裸枚举 | acceptance-scenarios.md | mts-card 文本不含 5 个枚举 token | DOM 文本断言 | `npm run test:e2e -- mts` | CMD-E2E-T002 | EV-RESULT-07 | 若任一枚举 token 出现在主视图 | bug_fix |
| SCN-02-COND-02 评分进度条 | acceptance-scenarios.md | `mts-score-bar` 可见 | DOM 可见性断言 | `npm run test:e2e -- mts` | CMD-E2E-T002 | EV-RESULT-08 | 若无进度条承载 | bug_fix |
| SCN-02-COND-03 原始字段仅展开可见 | acceptance-scenarios.md | 默认隐藏，展开后可见 | 折叠/展开交互 E2E | `npm run test:e2e -- mts` | CMD-E2E-T002 | EV-RESULT-09 | 若默认态已可见或展开后仍不可见 | bug_fix |
| SCN-02-COND-04 非 ready 人话化 | acceptance-scenarios.md | 无裸枚举串，人话说明 | DOM 精确文案断言 + 真实 domain 门控驱动 | `npx playwright test`；`npm run test:e2e -- gate/consistency` | CMD-E2E-FULL/T007A | EV-RESULT-10 | 若渲染裸枚举串 | bug_fix |
| SCN-03-COND-01 来源唯一主源 | acceptance-scenarios.md | `source-authority` 计数=1 | DOM `toHaveCount(1)` | `npm run test:e2e -- workbench / gate/consistency` | CMD-E2E-T005A/T007A | EV-RESULT-11 | 若计数≠1 | bug_fix |
| SCN-03-COND-02 价格唯一主源+涨跌色分离 | acceptance-scenarios.md | `price-authority` 计数=1，涨跌色≠警告色 | DOM 计数 + 颜色比较 | `npm run test:e2e -- workbench` | CMD-E2E-T005A | EV-RESULT-12 | 若计数≠1 或颜色相同 | bug_fix |
| SCN-04-COND-01 标题主位 | acceptance-scenarios.md | 标题字号/字重 > 控件 | computed style 比较 | `npm run test:e2e -- workbench` | CMD-E2E-T005A | EV-RESULT-13 | 若控件权重≥标题 | bug_fix |
| SCN-04-COND-02 切换后标题仍主位 | acceptance-scenarios.md | 切换布局后标题仍最大、切换生效、语义不变 | 交互 E2E + `LayoutController.tsx` 零 diff 校验 | `npm run test:e2e -- workbench`；`git diff --exit-code LayoutController.tsx` | CMD-E2E-T005A/CMD-INT-T005 | EV-RESULT-14 | 若切换后标题失去主位或 LayoutController 被改 | bug_fix / decision_gate |
| SCN-05-COND-01 主/次层级差 | acceptance-scenarios.md | KPI 字号/字重严格 > 次级明细 | computed style 比较 | `npx playwright test` | CMD-E2E-FULL | EV-RESULT-15 | 若无层级差 | bug_fix |
| SCN-05-COND-02 nonAdvice 常驻可见 | acceptance-scenarios.md | 默认态+展开态均可见 | DOM 可见性断言（两态） | `npx playwright test` | CMD-E2E-FULL | EV-RESULT-16 | 若任一态不可见 | bug_fix |
| SCN-06-COND-01 侧栏主看信息突出 | acceptance-scenarios.md | 名称+代码同行、价格右对齐 | computed display/textAlign | `npm run test:e2e -- watchlist` | CMD-E2E-T004 | EV-RESULT-17 | 若非 flex 行或未右对齐 | bug_fix |
| SCN-06-COND-02 来源小圆点弱化 | acceptance-scenarios.md | 圆点<=14px，非文本横幅 | DOM 尺寸 + class 断言 | `npm run test:e2e -- watchlist` | CMD-E2E-T004 | EV-RESULT-18 | 若圆点过大或仍为文本横幅 | bug_fix |
| SCN-06-COND-03 归档弱化 | acceptance-scenarios.md | opacity/颜色与 active 有别 | computed style 比较 | `npm run test:e2e -- watchlist` | CMD-E2E-T004 | EV-RESULT-19 | 若无视觉差异 | bug_fix |
| SCN-07-COND-01 默认关键数字 | acceptance-scenarios.md | KPI 可见含胜率/策略累计 | DOM 文本断言 | `npx playwright test` | CMD-E2E-FULL | EV-RESULT-20 | 若默认不可见 | bug_fix |
| SCN-07-COND-02 明细折叠展开 | acceptance-scenarios.md | 默认折叠，展开后可见 | 交互 E2E | `npx playwright test` | CMD-E2E-FULL | EV-RESULT-21 | 若默认展开或点击无效 | bug_fix |
| SCN-07-COND-03 仅 ready 回测块+价位分层 | acceptance-scenarios.md | ready 有回测块+分层，非 ready 无回测块 | DOM 断言两态 | `npx playwright test` | CMD-E2E-FULL | EV-RESULT-22 | 若非 ready 仍渲染回测块 | bug_fix |
| NEG-01 来源降级信号卡同步降级 | acceptance-scenarios.md | 三处一致读同一 domain 门控结果 | 真实 domain 门控驱动 E2E（未 mock） | `npm run test:e2e -- gate/consistency` | CMD-E2E-T007A | EV-RESULT-23 | 若三处出现矛盾呈现 | bug_fix |
| NEG-02 非 ready 不呈空回测容器 | acceptance-scenarios.md | 回测容器计数=0（非空容器） | DOM 计数断言 | `npx playwright test` | CMD-E2E-FULL | EV-RESULT-26 | 若渲染空容器占位 | bug_fix |
| NEG-03 恢复态/来源态独立承载 | acceptance-scenarios.md | 互不嵌套、boundingBox 不同 | DOM 结构 + 几何断言 | `npm run test:e2e -- gate/consistency / restore-layout` | CMD-E2E-T007A/T006 | EV-RESULT-24 | 若共用同一元素 | bug_fix |
| NEG-04 未注册理由码不直呈 | acceptance-scenarios.md | UNKNOWN_CODE 回落，不裸露原始 code | 单测故障注入 | `node --test humanize.spec.ts` | CMD-UNIT-01 | EV-RESULT-25 | 若单测未捕获裸 code 泄漏 | bug_fix（浏览器层注入证明为已接受残留风险 E2E-FND-002） |
| NEG-05 折叠态 nonAdvice 仍可见 | acceptance-scenarios.md | 折叠态免责仍可见 | DOM 可见性断言（折叠态） | `npx playwright test` | CMD-E2E-FULL | EV-RESULT-16 | 若折叠后免责消失 | bug_fix |
| NEG-06 布局非法值归一化 | acceptance-scenarios.md | 回退 focus，标题仍主位，无新增失败分支 | 坏快照驱动 E2E | `npm run test:e2e -- restore-layout / gate` | CMD-E2E-T006/T003 | EV-RESULT-27 | 若未回退或标题失主位 | bug_fix |
| NEG-07 axe+E2E 无回归 | acceptance-scenarios.md | 无新增 critical/serious 违规，既有路径不回归 | axe 扫描 + 全量回归 | `npm run test:e2e -- gate/scope-guard`；`npx playwright test` | CMD-E2E-T007B/CMD-E2E-FULL | EV-RESULT-28 | 若出现新增严重违规或既有用例失败 | bug_fix |

### 系统操作覆盖与自洽矩阵

| 系统操作 ID | 来源流步骤 | 预期读取 / 写入 / 状态迁移 | 预期错误 / 补偿 / 幂等 | 技术设计落点 | 证据 | 结论 |
|---|---|---|---|---|---|---|
| SUC-01-OP-01 来源档→呈现色 | SUC-01-FLOW-02 | 只读 `sourceHealth.status`；无写入 | 未知 status→normal 兜底防御 | M1/M2/M6/M8/M3 | EV-RESULT-01/02/03 | 通过 |
| SUC-01-OP-02 价格/涨跌唯一主源 | SUC-01-FLOW-03 | 只读派生行情；无写入 | 无行情→占位「—」 | M6 | EV-RESULT-12 | 通过 |
| SUC-02-OP-01 人话化+进度条+极性 | SUC-02-FLOW-01/02 | 只读 `mts.*`；无写入 | scoreBand 缺省→neutral | M2/M3 | EV-RESULT-06/07/08 | 通过 |
| SUC-02-OP-02 原始字段折叠+非常态人话化 | SUC-02-FLOW-03 | 折叠为本地 UI 态，不持久化；无领域写 | 未注册 code→UNKNOWN_CODE | M2/M3 | EV-RESULT-09/10/25 | 通过 |
| SUC-03-OP-01 主卡突出+折叠+免责 | SUC-03-FLOW-01/02 | 折叠为本地 UI 态；无领域写 | `status!="ready"`→无回测块 | M4 | EV-RESULT-15/16/20/21 | 通过 |
| SUC-03-OP-02 非 ready 人话化 | SUC-03-FLOW-03 | 只读 `tradeSignal.status`；无写入 | 三态各自人话说明 | M2/M4 | EV-RESULT-10/26 | 通过 |
| SUC-04-OP-01 侧栏主看+来源小圆点 | SUC-04-FLOW-01/02 | 只读 `item.*`/`summary.*`；无写入 | archived→弱化区分 | M5 | EV-RESULT-17/18/19 | 通过 |
| SUC-05-OP-01 标题主位+控件降级 | SUC-05-FLOW-01/02 | 只读 `selected.name`/`selectedLayout.mode`；无写入 | 非法布局值→既有归一化回退 focus | M6 | EV-RESULT-13/14 | 通过 |
| SUC-06-OP-01 恢复态四档映射 | SUC-06-FLOW-01/02 | 只读 `metadata.*`；无写入 | 未知 status→warning 保守兜底 | M2/M7 | EV-RESULT-04/05/24 | 通过 |

**覆盖结论：9/9 `SUC-xx-OP-xx` 全部有命令证据 + 结果证据支撑，无缺口。**

### 验证层次选择

| 验证目标 | 选择层次 | 选择理由 | 不适用层次与理由 | 证据要求 |
|----------|----------|----------|------------------|----------|
| 22 条 UI 验收条件（呈现状态、层级、去重复） | 端到端（Playwright）为主，单元为辅 | 所有验收条件的可观察结果都是真实浏览器渲染的 DOM 状态/样式/交互，必须用真实浏览器路径证明；单元测试只能证明纯函数映射逻辑正确，不能证明渲染层真正接线 | 人工验收：本次改造范围小、可自动化程度高，已有充分自动化证据，不需要额外人工验收步骤；智能体能力评估：本 mission 无 Agent 组件，不适用 | DOM 断言 + class/text 断言 + 关键场景截图 + 部分 computed style 比较 |
| `resolveSourceTone`/`resolveScoreTone`/`resolveRestoreTone`/`humanize*` 纯函数映射正确性 | 单元（`node --test`） | 这些是无副作用纯函数，单元测试能精确覆盖所有分支（含 UNKNOWN_CODE 回落、alertLevel=风控 OR 分支等边界），且执行速度快、可作为渲染层测试的前置保证 | 端到端：函数级正确性不需要浏览器环境即可完整验证 | 35/35 断言全绿，含 fault injection 历史记录（execute/code-review 阶段） |
| SR-01（共享类爆炸半径隔离） | 端到端 DOM/文件级 + 命令级 git diff/grep | 「范围外零改动」是一个关于文件内容和渲染结果的事实断言，必须用真实文件读取 + 真实渲染路径证明，纯逻辑测试无法证明 | 单元：不涉及函数逻辑，不适用 | grep 文件内容级证据 + 3 处真实渲染 DOM 断言 + git diff --stat / --unified=0 命令证据 |
| NEG-07 可访问性无回归 | 端到端 axe 扫描 | 可访问性违规必须在真实渲染的 DOM 树上用 axe 引擎扫描才能发现 | 单元：无法评估可访问性 | axe critical/serious 违规列表为空 |
| 集成层（build + 变更范围完整性） | 集成（`npm run build` + `git diff`） | 证明改造已完整编译进产物（EVD-01 前提证据），且授权路径边界（LayoutController.tsx 等禁改文件、`.data-notice`/`.up`/`.down` 定义）未被突破 | — | exit 0 + diff 为空 |

### 风险与质量约束验证计划

| 编号 | 类型 | 来源 | 验证方法 | 通过标准 | 当前结论 | 残留风险 / 回流 |
|------|------|------|----------|----------|----------|----------------|
| SR-01 | 风险 | solution.md §7 / tech-design.md §3 | grep 文件内容级 + DOM 渲染级 + git diff/grep 命令级三重证据 | 范围外 5 处 `.data-notice` 用法与共享定义（:379、:403-409）零改动 | 通过 | 无残留风险 |
| RISK-01/GAP-D2 demo_fallback 定档 | 风险 | dependency-impact.md / DEC-S07 | 三档并置截图辨识度 | demo_fallback 与 formal/stale 可视觉区分且非高危色 | 通过（默认档，待用户后续确认） | DEC-01 若改判需回 M1/M2 重验 SCN-01-COND-02 |
| RISK-02 折叠义务丢失 | 风险 | solution.md §7 | E2E 折叠/展开交互 | 默认折叠、展开后可见、有可操作入口 | 通过 | 无残留风险 |
| RISK-03/GAP-D1 裸枚举穷举 | 风险 | tech-design.md §7 | DOM 文本断言穷举 5 字段 + reasons/invalidators 双处 | 主视图 0 裸枚举/0 裸理由码 | 通过 | 无残留风险 |
| RISK-04/INV-07 跨呈现一致性只读 | 风险 | tech-design.md §5.4 | 真实 domain 门控驱动 E2E（未 mock） | 三处一致降级，无矛盾呈现 | 通过 | 无残留风险 |
| RISK-07/NEG-07 axe+E2E 无回归 | 质量约束 | tech-design.md §7 | axe 扫描 + 全量回归 | 无新增 critical/serious，既有路径不回归 | 通过（覆盖面存在已知缺口） | E2E-FND-001（Med，已接受）：axe 未覆盖新增颜色语义承载态，建议下一轮补充 |
| E2E-FND-002 NEG-04 浏览器层证明 | 质量约束 | code-review.md | 单测已证明安全属性；浏览器层未做注入验证 | 单测通过 | 通过（单测层级），浏览器层为已接受残留风险 | 建议后续补 1 条 route 注入未注册 code 的 E2E |

---

## 验证方法

| 层级 | 命令 / 方法 | 工作目录 / 环境 | 证据编号 | 结果 | 覆盖目标 |
|------|-------------|-----------------|----------|------|----------|
| 单元 | `node --test tests/unit/presentation/tone.spec.ts tests/unit/presentation/humanize.spec.ts` | 项目根目录 | CMD-UNIT-01 | 通过（35/35） | `resolve*Tone`/`humanize*` 纯函数映射、UNKNOWN_CODE 回落、alertLevel=风控 OR 分支 |
| 集成 | `npm run build`（及与 git diff/grep 组合的 7 组 T00x-3 集成验证命令） | 项目根目录 | CMD-BUILD-BASE / CMD-INT-T001~T007 | 通过（exit 0，全部 7 组） | 改造已编译进产物（EVD-01）+ 授权路径边界（SR-01、LayoutController 零改动）命令级证据 |
| 端到端 | `npx playwright test`（全量，不加过滤，独立重跑两次）+ 16 组按任务过滤的 `npm run test:e2e -- <suite>` 命令 | 项目根目录，`NO_PROXY=127.0.0.1,localhost` | CMD-E2E-FULL / CMD-E2E-T002~T007B | 通过（50/50，0 failed，0 skipped，两次独立重跑一致） | 22 条验收条件、7 条 NEG 路径、9 个 SUC-OP 的真实浏览器路径证据 |
| 质量验证 | `harness lint project --mission 20260721-watchboard-ui-friendliness`；`harness verify e2e-status --mission ...` | 项目根目录 | CMD-LINT-01 / CMD-E2E-STATUS-01 | 通过（WARN，非阻断） | 项目级变更范围+命令证据完整性；端到端义务满足度 |
| 人工验收 | 逐条阅读 `tests/e2e/**/*.spec.ts` 源码，核对断言语义与验收条件 Given/When/Then 是否真实对应（而非只看测试标题） | 本地代码阅读 | MANUAL-01 | 通过 | 防止"测试标题像但断言弱/断言错对象"的伪证据 |

**关键结果摘要**：
- `node --test tests/unit/presentation/tone.spec.ts tests/unit/presentation/humanize.spec.ts` → `tests 35, pass 35, fail 0`
- `npm run build` → `tsc --noEmit && vite build` exit 0（多次独立重跑一致）
- `npx playwright test`（全量）→ `50 passed (19.7s)` 和 `50 passed (19.1s)`（两次独立重跑，0 failed / 0 skipped）
- `harness lint project` → `status: WARN`（仅 P003 AGENTS.md 关键词提示，非阻断；无 P002/P001 FAIL）
- SR-01 独立复核：`git diff --stat -- src/features/layout/LayoutController.tsx src/features/alerts/AlertRulePanel.tsx src/features/workbench/WorkbenchShell.tsx` 输出为空；`git diff --unified=0 src/styles.css | grep -nE '(\.data-notice|\.up|\.down)'` 无命中

---

## 验证结果

> 22 条验收条件逐条对齐结果见上文「验收判定矩阵」，此处不重复；下表补充命令证据 / 结果证据清单。外部契约 `acceptance_trace[]` 按 compute-scope 49 个锚点粒度记录，全部 `conclusion: pass`。

### 命令证据清单（节选，完整 22 项见外部契约 `command_evidence[]`）

| 证据编号 | 命令 / 方法 | 退出码 / 状态 | 产物路径 | 说明 |
|----------|-------------|---------------|----------|------|
| CMD-UNIT-01 | `node --test tests/unit/presentation/tone.spec.ts tests/unit/presentation/humanize.spec.ts` | exit 0 / pass | `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/traces/cmd/cmd-unit-2026-07-22-05-06-26.json` | 35/35 全绿 |
| CMD-BUILD-BASE | `npm run build` | exit 0 / pass | `.../cmd-integration-2026-07-22-05-06-35.json` | tsc + vite build |
| CMD-E2E-FULL | `npx playwright test` | exit 0 / pass | `.../cmd-e2e-2026-07-22-05-06-41.json` | 全量重跑，独立于 code-review 阶段结果 |
| CMD-INT-T001 | `npm run build && git diff --unified=0 src/styles.css \| grep ... \|\| echo NO_SHARED_CHANGE` | exit 0 / pass | `.../cmd-integration-2026-07-22-05-12-59.json` | re-T001-3，证共享定义未改 |
| CMD-E2E-T002 | `npm run test:e2e -- mts` | exit 0 / pass | `.../cmd-e2e-2026-07-22-05-13-04.json` | re-T002-1/2，MTS 卡人话化+进度条+GAP-02 |
| CMD-E2E-T003 | `npm run test:e2e -- gate` | exit 0 / pass | `.../cmd-e2e-2026-07-22-05-13-09.json` | re-T003-1/2，acceptance-matrix+consistency+scope-guard |
| CMD-INT-T005 | `npm run build && npm run test:e2e && git diff --exit-code LayoutController.tsx` | exit 0 / pass | `.../cmd-integration-2026-07-22-05-14-23.json` | re-T005-3，LayoutController 零 diff 独立确认 |
| CMD-INT-T006 | `... grep -rn 'data-notice' src/App.tsx src/features/restore src/features/chart \| grep -v 'notice--' \|\| echo RANGE_INTERNAL_MIGRATED` | exit 0 / pass | `.../cmd-integration-2026-07-22-05-14-56.json` | re-T006-3，范围内迁移完整性；独立直接重跑确认输出 `RANGE_INTERNAL_MIGRATED` |
| CMD-INT-T007 | `git diff --exit-code 三个禁改文件 && grep .data-notice{ src/styles.css && npm run build && npm run test:e2e` | exit 0 / pass | `.../cmd-integration-2026-07-22-05-15-44.json` | re-T007-3，SR-01 终局命令证据 |
| CMD-LINT-01 | `harness lint project --mission ...` | WARN（gate_effect=warn） | `harness-runtime/harness/traces/20260721-watchboard-ui-friendliness/project-lint/project-lint-report.json` | 仅 P003（AGENTS.md 关键词），非阻断 |
| CMD-E2E-STATUS-01 | `harness verify e2e-status --mission ...` | WARN（e2e_plan_status/e2e_run_status=PASS） | `harness-runtime/harness/traces/20260721-watchboard-ui-friendliness/e2e/e2e-status.json` | 顶层 FAIL 为控制面探测口径缺口，见下文说明 |

其余 12 项命令证据（CMD-E2E-T004/T005B/T006/T007A/T007B、CMD-INT-T002/T003/T004、CMD-CTX-001/002）均已收集，路径见外部契约 `command_evidence[]`，全部 `result: pass`。

### 结果证据清单（29 项，节选；完整列表见外部契约 `result_evidence[]`）

| 证据编号 | 关联验收场景 / 条件 | 证据类型 | 可观察结果 | 产物路径 | 结论 |
|----------|------------|----------|------------|----------|------|
| EV-RESULT-01 | SCN-01-COND-01 | dom | formal/not_loaded 无警告承载 | `tests/e2e/mts/card.spec.ts` + `tests/e2e/workbench/default.spec.ts` | 通过 |
| EV-RESULT-02 | SCN-01-COND-02 | dom | demo_fallback 呈 `notice--info` | `tests/e2e/gate/acceptance-matrix.spec.ts:47` + `tests/e2e/workbench/default.spec.ts:193-194` | 通过 |
| EV-RESULT-06 | SCN-01-COND-06 | dom | negative 评分 caution 类与来源 warning 类物理区分 | `tests/e2e/mts/friendliness.spec.ts:168`（GAP-02）+ 截图 `pt02-mts-negative-score-tone.png` | 通过 |
| EV-RESULT-11 | SCN-03-COND-01 | dom | `source-authority` 计数=1 | `tests/e2e/workbench/friendliness.spec.ts:92` + `tests/e2e/gate/consistency.spec.ts:172` | 通过 |
| EV-RESULT-13 | SCN-04-COND-01 | dom | 标题字号/字重 > 控件 | `tests/e2e/workbench/friendliness.spec.ts:110` + 截图 `pt05-top-hierarchy-colors.png` | 通过 |
| EV-RESULT-15 | SCN-05-COND-01 | dom | KPI 字号/字重严格大于次级明细 | `tests/e2e/trade-signal/friendliness.spec.ts:93` + 截图 `pt03-trade-signal-hierarchy.png` | 通过 |
| EV-RESULT-19 | SCN-06-COND-03 | dom | archived opacity/颜色与 active 不同 | `tests/e2e/watchlist/friendliness.spec.ts:124` + 截图 `pt04-watchlist-archived.png` | 通过 |
| EV-RESULT-23 | NEG-01 | dom | 三处一致降级，真实 domain 门控驱动 | `tests/e2e/gate/consistency.spec.ts:107` | 通过 |
| EV-RESULT-25 | NEG-04 | internal_state（cross_check） | UNKNOWN_CODE 回落，单测故障注入验证 | `tests/unit/presentation/humanize.spec.ts` | 通过（浏览器层证明为已接受残留风险 E2E-FND-002，见风险章节） |
| EV-RESULT-28 | NEG-07 | accessibility_snapshot | axe 扫描零 critical/serious 违规 | `tests/e2e/gate/scope-guard.spec.ts:216` + `tests/e2e/watchlist/t001-watchlist-archive-restore.spec.ts:152` | 通过（覆盖面已知缺口 E2E-FND-001） |
| EV-RESULT-29 | SR-01（质量约束） | dom + file | 范围外 5 处 `.data-notice` 零改动、共享定义未改 | `tests/e2e/gate/scope-guard.spec.ts` 全部 5 个子测试 | 通过 |

---

## 端到端验证结果

| 字段 | 值 |
|------|----|
| 端到端状态产物 | `harness-runtime/harness/traces/20260721-watchboard-ui-friendliness/e2e/e2e-status.json` |
| 状态 | 警告（顶层 `status=FAIL`，但 `e2e_plan_status=PASS`、`e2e_run_status=PASS`；见下方说明） |
| 网页报告（HTML） | `playwright-report/index.html` |
| 追踪 / 视频 / 截图 | `playwright.config.ts` 已配置 `trace: retain-on-failure` + `screenshot: only-on-failure`（本轮全绿无失败产物）；7 张手动落盘截图见 `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/` |
| 不适用 / 阻塞 / 决策门 | 不适用；无阻塞、无需决策门 |

**关于顶层 `status=FAIL` 的独立核实说明**：`harness verify e2e-status` 报告顶层 `status=FAIL`，唯一原因是 `missing_capabilities: [{task_id: T007, capability: accessibility_smoke, reason: e2e_tool_not_run_or_failed}]`——控制面探测脚本按"独立 axe CLI 产物"格式识别 `accessibility_smoke` 能力，未识别内嵌于 Playwright spec 内的 `@axe-core/playwright` 断言。本轮**独立复核**（未采信 code-review.md 的转述）：直接 `grep` 确认 `tests/e2e/gate/scope-guard.spec.ts:4,221,227` 与 `tests/e2e/watchlist/t001-watchlist-archive-restore.spec.ts:2,155` 均真实 `import AxeBuilder from "@axe-core/playwright"` 并调用 `.analyze()`；本轮重跑 `npx playwright test` 时这两条 axe 测试（列表中的第 17 项 `scope-guard.spec.ts:216` 与第 41 项 `t001-watchlist-archive-restore.spec.ts:152`）均标记 `✓` 通过。`runs[]` 字段记录的 `e2e_run_status=PASS`（49 passed，来自较早一次快照）与本轮独立重跑的 50 passed 之间的计数差异，核实为 `npm run test:e2e`/`npx playwright test` 命令本身完全一致（`package.json` 确认 `test:e2e` 脚本即 `playwright test`），差异只是 e2e-status.json 内嵌 `runs[]` 快照的时间戳早于本轮（新鲜度漂移），非真实回归——本轮两次独立重跑均为 50 passed 且互相一致。此结论与 code-review.md 记录的 E2E-FND-005（"控制面探测口径，非 E2E 职责"）一致，本报告在其基础上补充了独立验证证据（直接读取源码确认 axe 断言存在且本轮亲自见证其通过），不是简单沿用转述。

| 验收场景 / 条件 | 用户路径 / 替代证据 | 结果证据 | 结论 | 缺口 / 风险 |
|--------|--------------------|----------|------|-------------|
| SCN-01~07（全部） | 见「验收判定矩阵」逐条 E2E 路径 | EV-RESULT-01~24, 26~29 | 通过 | 无 |
| NEG-01/02/03/06/07 | 真实浏览器路径（真实 domain 门控/真实归一化/axe 扫描） | EV-RESULT-23/26/24/27/28 | 通过 | E2E-FND-001（axe 覆盖面），已接受 |
| NEG-04 | 单测层级证明安全属性，浏览器层未做注入验证 | EV-RESULT-25 | 通过（单测层级） | E2E-FND-002，已接受 |
| NEG-05 | 折叠态 nonAdvice 可见 E2E | EV-RESULT-16 | 通过 | 无 |

---

## 风险与质量约束验证

| 编号 | 类型 | 预期 / 约束 | 验证证据 | 实际结果 | 结论 | 后续 |
|------|------|-------------|----------|----------|------|------|
| SR-01 | 风险 | 范围外 5 处 `.data-notice` 及共享定义零改动 | EV-RESULT-29、CMD-INT-T005/T006/T007、独立 `git diff --stat`/`git diff --unified=0` 复核 | 全部零改动，字符级核对定义内容一致 | 已验证 | 无 |
| RISK-01/GAP-D2 | 风险 | demo_fallback 三档可辨识、非高危色 | EV-RESULT-02 | 信息级、与 formal/stale 可辨 | 已验证（默认档） | DEC-01 用户确认后如有改判需重验 |
| RISK-02 | 风险 | 折叠交互义务不丢失 | EV-RESULT-09/21 | 折叠/展开均生效 | 已验证 | 无 |
| RISK-03/GAP-D1 | 风险 | 主视图 0 裸枚举/0 裸理由码穷举 | EV-RESULT-07/09/10 | 5 字段 + reasons/invalidators 双处均人话化 | 已验证 | 无 |
| RISK-04/INV-07 | 风险 | 跨呈现一致性只读绑定 | EV-RESULT-23/24 | 真实门控驱动、三处一致 | 已验证 | 无 |
| E2E-FND-001 | 质量约束（NEG-07） | axe 无回归 | EV-RESULT-28 | 已覆盖 formal 首页+alerts 面板；未覆盖新增颜色语义承载态 | 已接受（Med，code-review Decision Gate） | 建议下一轮补充 demo_fallback/warning/展开态 axe 扫描 |
| E2E-FND-002 | 质量约束（NEG-04） | 未注册理由码浏览器层证明 | EV-RESULT-25 | 单测已证明；浏览器层未注入验证 | 已接受（Med，code-review Decision Gate） | 建议补 1 条 route 注入未注册 code 的 E2E |
| TDD-FND-002~005 | 风险（Low） | 交易信号卡非 ready 子态覆盖 / toolchain 探测口径 / AT-0601 failed 态可达性 / mutation testing | code-review.md 已记录，本轮沿用 | 均为已知限制，非阻断 | 已接受（Low） | 无需本轮处理 |
| RISK-DOC-01 / RISK-CSS-01 | 风险（Low） | tech-design 文档同步 / SR-01 措辞与 CSS-only 授权字面张力 | code-review.md 已记录，本轮沿用 | 已由 architecture-reviewer 判定非阻断 | 已接受（Low） | 无需本轮处理 |
| e2e-status.json 顶层 FAIL | 控制面 | 探测脚本对内嵌 axe 断言识别 | 本轮独立复核（源码 grep + 本轮亲自见证 axe 断言通过） | 探测口径缺口，非真实能力缺失 | 已验证（非阻断） | 建议 Harness 后续修正探测脚本 |

---

## 未覆盖范围

| 范围 | 原因 | 影响 | 下一步 |
|------|------|------|--------|
| axe 扫描对 demo_fallback/notice--warning/notice--info/tone-* 展开态的覆盖 | E2E-FND-001，code-review 已接受为非阻断残留风险，本轮职责边界不包含扩大覆盖面 | 无阻断影响，现有 formal+alerts 面板扫描已证明无严重违规基线 | 建议下一迭代补充（已记录于 quality_trace，不在本轮 gap 修复范围） |
| NEG-04 未注册理由码的浏览器层 DOM 注入验证 | E2E-FND-002，code-review 已接受为非阻断残留风险 | 无阻断影响，单测已证明纯函数安全属性 | 建议下一迭代补 1 条 route 注入未注册 code 的 E2E |
| `restoreMetadata.status="failed"` 具体值的生产可达 E2E 路径 | 真实恢复流程（`restoreSnapshot`/`migrateLegacy`/`fallbackSnapshot`）结构上无代码路径产出该值（execution-result.md DEV-01），非测试覆盖不足 | 无阻断影响，discardedLayoutKeys 非空这一同条件下的另一分支已有完整 E2E 证据；status=failed 已有等价单测覆盖 | 若未来该状态变为生产可达需补 E2E（TDD-FND-004 已记录） |

---

## 遗留问题

| 问题 | 严重级别 | 状态 | 处理方式 |
|------|----------|------|----------|
| E2E-FND-001：axe 覆盖面不足 | 中 | accepted | code-review Decision Gate 已接受，建议下一迭代补充，不阻断本轮交付 |
| E2E-FND-002：NEG-04 缺浏览器层注入证明 | 中 | accepted | code-review Decision Gate 已接受，建议下一迭代补充，不阻断本轮交付 |
| TDD-FND-002~005 / RISK-DOC-01 / RISK-CSS-01 | 低 | accepted | code-review Decision Gate 已接受，均为文档同步/覆盖广度类建议，不阻断 |
| `harness verify e2e-status` 顶层 FAIL 为探测口径缺口（T007 accessibility_smoke 未识别内嵌 axe 断言） | 低（控制面缺口，非实现缺陷） | accepted（本轮独立复核确认） | 建议 Harness 框架后续修正探测脚本对 Node/Playwright 项目内嵌 axe 断言的识别逻辑；不影响本 mission 交付判断 |
| 通用 `harness contract check`（非 `check-acceptance-trace`）对 `spec.md#<Scenario 名>` 格式的 acceptance_id 报 `broken_acceptance_trace` | 低（控制面缺口，非本报告实质缺陷） | accepted（本轮独立核实） | `check_contracts.py` 的 `ids_from_markdown` 只识别 `PREFIX-xxx` 形态 ID（正则 `ID_PATTERN`），不识别 `compute-scope` 权威产出的 `watchboard-presentation/spec.md#<Scenario 名>` 引用格式；workflow 明确指定的验证阶段权威校验命令 `harness contract check-acceptance-trace --upstream execution-brief.contract.yaml` 已确认 PASS（0 failed_checks），`harness verify true-e2e-check` 与 `harness verify detect-contradictions` 同样 PASS；建议 Harness 框架后续把 `ids_from_markdown` 的 ID 识别范围扩展到差量规格 Scenario 引用格式，不阻断本轮交付 |

---

## 验证评价摘要

| 评价项 | 结论 | 证据 / 理由 |
|--------|------|-------------|
| 验收场景 / 条件是否逐项验证 | 是 | 22 条 `SCN-xx-COND-xx`（对齐 25 个差量规格 Scenario）+ 7 条 NEG 逐条建立预期结果 / 实际观察结果，`compute-scope` 给出的 49 个验收锚点全部落 `acceptance_trace`，`conclusion=pass`，`harness contract check-acceptance-trace` PASS（0 failed_checks） |
| 命令证据是否完整 | 是 | 22 项命令证据全部真实运行并记录 exit_code/started_at/ended_at/artifact；覆盖 `execution-brief.md` 声明的全部 16 条非人工 `required_evidence` 命令 |
| 结果证据是否完整 | 是 | 29 项结果证据，每条含 expected/actual/reproduce/artifact；`harness verify true-e2e-check` PASS（40 个 UI 验收锚点，0 processing failure），确认无 API/内部状态证据被误用作 UI 主要证据 |
| 验证层次是否匹配风险 | 是 | 高风险的界面呈现语义、去重复、层级差均用真实浏览器路径证据；纯函数映射、UNKNOWN_CODE 回落用单元测试；SR-01 用文件级+DOM 级+命令级三重证据 |
| 质量与运行约束是否处理 | 是 | SR-01、RISK-01~07、NEG-07 axe 全部有验证结论；2 项 Med 残留风险（E2E-FND-001/002）已在 code-review 阶段经 Decision Gate 接受，本轮独立复核未发现其恶化或新增同类问题 |
| 高优先级风险是否闭环 | 是 | code-review.md 记录的 3 个 High finding（GAP-01/02/03）均已修复并经 correctness-reviewer 最终确认轮 PASS；ARCH-01 已修复；本轮独立复核（重跑 build+全量 E2E+SR-01 diff）未发现回归或新缺陷 |
| 是否可以进入交付 | 需用户接受风险 | 无阻断项，但存在 2 项 Med 级残留风险（E2E-FND-001、E2E-FND-002）需要通过 Decision Gate 由用户显式确认接受（code-review 阶段已记录 `gate_decisions`，本轮建议主流程在 `harness verify compute-conclusion` 环节按"带风险通过"路径二次确认，而非静默沿用） |

---

## 建议的四态结论

> 本节仅为建议，最终结论由主流程 `harness verify compute-conclusion` 裁定，本报告不越权定论。

**建议：带风险通过（PASS_WITH_RISK）。**

理由：
1. 全部 49 个 `compute-scope` 验收锚点（SCN-01~07 汇总项、25 个差量规格 Scenario、9 个 `SUC-xx-OP-xx`、8 个 `DEC-Sxx`）均有命令证据 + 结果证据支撑，`conclusion=pass`，无一条 `fail` 或 `blocked`。
2. 22 条验收条件 + 7 条 NEG 负向路径的主要结果证据均来自真实浏览器路径（DOM 断言、computed style 比较、axe 扫描、截图），符合"界面验收场景 / 条件必须有真实浏览器路径主要证据"的铁律；仅 NEG-04 单条以单元测试为主要证据、浏览器层为已接受的 cross_check 缺口（`harness verify true-e2e-check` 对此已按预期通过，因为该条目已诚实标注为 `logic` surface_type 而非 `ui`，未混入 UI 判定）。
3. SR-01 硬约束（`LayoutController.tsx`/`AlertRulePanel.tsx`/`WorkbenchShell.tsx` 零改动、共享 `.data-notice`/`.up`/`.down` 定义未改）本轮用命令级 `git diff --stat`/`git diff --unified=0`/`sed` 独立复核确认，与 code-review.md 结论一致。
4. 残留风险明确且有限：2 项 Med（E2E-FND-001 axe 覆盖面、E2E-FND-002 NEG-04 浏览器层证明）+ 10 项 Low，均已在 code-review 阶段经 Decision Gate 记录为非阻断，本轮未发现其恶化或引入新的同类阻断问题；未发现任何真实测试失败或 SR-01 违规。
5. 不建议直接"通过"（无风险）：因为 2 项 Med 级残留风险客观存在且尚未被本轮以外的验证手段消灭，按流程铁律"没有批准记录不得进入产物门"，需要主流程显式经 `harness approval append --type risk --stage verify` 记录用户对残留风险的接受，而非由验证阶段自行判定为无风险通过。
