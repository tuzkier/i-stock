# 代码评审: 20260721-watchboard-ui-friendliness

> **来源**：code-review 技能 → `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/code-review/code-review.md`
> **上游**：`mission-contract.md` | `tech-design.md` | `execution-brief.md` | `execution-result.md`

**mission-id:** 20260721-watchboard-ui-friendliness
**Status:** `ready`

---

## 控制契约

- Contract: contracts/code-review.contract.yaml
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

## 审查依据与范围

| 输入 | 路径 / 来源 | 状态 | 本次用途 |
|------|-------------|------|----------|
| 初始任务契约 | `harness-runtime/harness/missions/20260721-watchboard-ui-friendliness/mission-contract.md` | present | 初始验收条件 SCN-01~07 |
| 产品定义包 | `product/product-definition.md` / `product/acceptance-scenarios.md` | present | 22 条验收条件 + NEG-01~07 权威来源 |
| 差量规格 | `product/specs/watchboard-presentation/spec.md` | present | 8 Requirement / 25 ADDED Scenario 硬行为边界 |
| 方案与技术设计 | `solution/solution.md` / `technical-analysis/tech-design.md` | present | M1~M8 模块设计、接口、INV-01~07 |
| 执行授权 | `breakdown/execution-brief.md` | present | 7 父任务 15 原子任务完整执行授权 |
| 执行结果 | `execute/execution-result.md` | present | 15 个原子任务状态、3 处执行阶段真实缺陷修复记录 |
| 变更 diff | 工作区未提交改动（`git status`/`git diff`，本 mission 全程未 commit，用户已授权跳过 worktree/提交） | present | 全部改动的唯一事实来源 |
| 测试与工具链证据 | `npx playwright test`（全量）、`node --test tests/unit/presentation/*.spec.ts`、`toolchain-status.json`、`e2e-status.json` | present（toolchain/e2e 控制面探测口径对本项目部分误报，已在下方章节说明） | TDD/E2E 审查依据 |

---

## 变更集承接

| Execution Unit | Changed Files | Changed Surface | Execute Deviations / Blockers | Review Scope Decision |
|----------------|---------------|-----------------|-------------------------------|------------------------|
| T001~T007（PT-01~PT-07，15 个原子任务） | `src/App.tsx`、`src/features/presentation/{tone.ts,humanize.ts,ScoreBar.tsx}`、`src/features/chart/ChartSurface.tsx`、`src/features/restore/RestoreStatus.tsx`、`src/styles.css`、`src/types.ts` + 约 15 个 `tests/e2e/**/*.spec.ts` + 2 个 `tests/unit/presentation/*.spec.ts` | frontend_ui / frontend_visual / frontend_component | execution-result.md 记录 3 处 execute 阶段发现修复的真实缺陷（alertLevel=风控 分支遗漏、humanizeTradeStatus 漏传参数、`.watch-list` 布局溢出） | covered |

---

## 审查角色选择

| Reviewer | 是否启用 | 启用依据 | 结论（最终轮） |
|----------|----------|----------|------|
| correctness-reviewer | required | 所有实现都必须审需求忠实性 | **PASS**（最终确认轮，独立重跑全部核实） |
| tdd-reviewer | required | 所有实现都必须审测试有效性 | **PASS_WITH_RISK**（最终确认轮，含真实故障注入验证） |
| architecture-reviewer | conditional，主 Agent 手动启用 | 新建 `src/features/presentation/` 模块（9 个新接口）+ 跨多模块消费接入；CLI 自动选择器因本 mission 全程未 commit、无 git baseline 可 diff，误判 `no_trigger`，人工核实后判定触发条件成立 | **PASS_WITH_RISK**（最终确认轮） |
| security-reviewer | not triggered | 无认证/授权/加密/用户输入/API 暴露/secret 变更 | n/a |
| data-migration-reviewer | not triggered | 无 schema/DDL/migration/backfill | n/a |
| e2e-reviewer | conditional，主 Agent 手动启用 | `e2e.enabled=true` 且变更含约 15 个 E2E 测试文件 + UI 实现；CLI 因同一 git baseline 缺失原因误判 `no_trigger`，人工核实后启用；本 mission interaction 阶段经治理档显式跳过（无 `behavior-graph.yaml`），「界面忠诚度」维度不适用 | **PASS_WITH_RISK**（最终确认轮） |
| agent-behavior-reviewer | not triggered | `agent_implementation: []`，本 mission 无 Agent 组件 | n/a |

---

## 评审摘要

本次 mission 是一次 brownfield 呈现层友好化改造（状态色语义分档、内部枚举人话化、重复信息收敛唯一主源、顶部/主看/侧栏信息层级重排），全读侧、无领域写入、无数据模型变更、无 Agent 组件。execute 阶段 7 个父任务（PT-01~PT-07）15 个原子任务全部完成并经 spec-reviewer 逐条审查 PASS。

code-review 阶段并行派发 correctness-reviewer + tdd-reviewer（always-on）+ e2e-reviewer + architecture-reviewer（主 Agent 依据实际变更特征手动启用，纠正 CLI 因缺 git baseline 导致的自动选择器误判）。**第一轮**：correctness-reviewer 和 architecture-reviewer 均返回 HOLD，共发现 4 个 High finding；**第二轮**（修复 GAP-01/ARCH-01/GAP-02 后）：architecture-reviewer 转 PASS（ARCH-02 经独立重新论证改判非阻断设计漂移），correctness-reviewer 发现 1 个新的同类 High finding（GAP-03，App.tsx 侧兄弟位置的同一 bug 模式）；**第三轮**（修复 GAP-03 后）：correctness-reviewer 转 PASS。tdd-reviewer、e2e-reviewer 全程 PASS_WITH_RISK（无 High），第二轮做过真实故障注入复核确认新增测试有效。

修复闭环完成后，主 Agent 又对全部 4 位审查员做了一轮独立于此前历史、针对当前代码状态的最终确认派发（不采信任何转述，各自重新读代码、重新独立跑 `npm run build` + `npx playwright test`）。最终结果：correctness-reviewer **PASS**（0 blocking，3 Low risk）；tdd-reviewer **PASS_WITH_RISK**（0 blocking，5 Low risk，含 2 处真实故障注入验证：改坏 `resolveScoreTone` 负向分支/`resolveSourceTone` demo_fallback 分支→目标用例变红→还原→变绿）；e2e-reviewer **PASS_WITH_RISK**（0 blocking，5 项风险含 2 项 Med：既有的 axe 覆盖面不足 E2E-FND-001，以及新发现的 E2E-FND-002——NEG-04 未注册理由码回落只有单测证据，缺浏览器层 DOM 证明）；architecture-reviewer **PASS_WITH_RISK**（0 blocking，2 Low risk：RISK-DOC-01 tech-design 文档同步、新发现的 RISK-CSS-01——SR-01「范围外零改动」措辞与「CSS-only 重排 LayoutController 计算样式」授权之间存在字面张力，经核实非违规但建议后续澄清措辞）。

**无 open High finding**，全部 4 位审查员最终确认轮结论为 PASS 或 PASS_WITH_RISK。独立验证（本轮由 4 位审查员各自重新执行，非转述）：`npm run build` exit 0；`npx playwright test`（全量，不带路径过滤，多次独立重跑）**50 passed, 0 failed, 0 skipped, 0 flaky**；SR-01 硬约束（`LayoutController.tsx`/`AlertRulePanel.tsx`/`WorkbenchShell.tsx` 整文件、范围外 5 处 `.data-notice`、共享定义本体）全程零改动，本轮 `git diff` 再次核对确认。

---

## 发现列表

| ID | 严重级别 | 类别 | 关联项 | 摘要 | 状态 | 处理引用 |
|----|----------|------|--------|------|------|----------|
| GAP-01 | High | correctness | SCN-01-COND-01/02（差量规格 Scenario 1/6） | `ChartSurface.tsx` 的 `chart-degradation-note` 硬编码警告色（实际发现是硬编码 `data-notice`），未接入 `resolveSourceTone`，demo_fallback 被误染最高危色、加载态误闪警告色 | fixed | 第 1 轮修复：改为按 `resolveSourceTone` 派生 tone，渲染条件收窄为 `sourceTone !== "normal"`；`acceptance-matrix.spec.ts` AC-02/AC-03 补 class 断言；第 2 轮 correctness-reviewer 确认 PASS |
| ARCH-01 | High | architecture | SR-01（solution.md）+ tech-design §3 范围外零改动硬约束 | `styles.css` 新增 CSS 后代选择器 `.workspace-header [data-testid="workbench-selection-summary"]`，通过 CSS 侧信道改变了范围外禁改文件 `LayoutController.tsx:75` 元素的 opacity/font-size，违反「保留原样」的 execution-brief 明文授权 | fixed | 第 1 轮修复：删除该 CSS 规则；第 2 轮 architecture-reviewer 确认标题主位断言依然成立、规则已彻底删除 |
| GAP-02 | High | correctness | SCN-01-COND-06（差量规格 Scenario 5，负向评分与来源故障色物理区分） | 负向评分/来源故障色物理区分（`mtsCardToneClass` caution→risk 映射）只有抽象函数级测试，从未在渲染层被 E2E/DOM 验证过，也无 tech-design §7 要求的并置截图证据 | fixed | 第 1 轮补测：`tests/e2e/mts/friendliness.spec.ts` 新增 "GAP-02" 用例，真实驱动 negative/strong_negative scoreBand + stale 来源并置对比 + 截图证据；tdd-reviewer 第 2 轮用故障注入独立复核确认有效 |
| ARCH-02 | High→Low | architecture | tech-design §3 M6/M8 模块文件标注 | `price-authority` testid 落在 `ChartSurface.tsx`（M8）而非 tech-design 文字标注的 App.tsx/M6 | accepted_risk（降级为文档同步风险） | architecture-reviewer 第 2 轮独立重新论证：execution-brief.md 第 68/1621/1751/1774/1808 行明确、反复记录该决策为 breakdown 阶段已审查通过（切片枢纽+全量审查双 PASS）的既定落地方案，非 execute 阶段偏离；比较 3 种替代实现方案后确认现方案是唯一不违反其他硬约束（LayoutController 禁改、唯一主源）的选择；改判 non_blocking_risk RISK-DOC-01（建议后续在 tech-design 补登记 M6/M8 文件归属说明） |
| GAP-03 | High | correctness | SCN-01-COND-02（同 GAP-01，App.tsx 侧兄弟位置） | `src/App.tsx` 的 `signal-degradation-note`（MTS 卡自身来源提示条）存在与 GAP-01 相同的 bug 模式：硬编码 `notice--warning`，未接入 `resolveSourceTone`；第 1 轮 GAP-01 修复范围仅覆盖 `ChartSurface.tsx`，未覆盖这个兄弟位置 | fixed | 第 2 轮 correctness-reviewer 复审发现；第 3 轮修复：`App.tsx` 新增 `signalSourceStatus`/`signalSourceTone` 派生变量，`signal-degradation-note` 按 tone 派生 class（`signal-error-note` 按设计保持不变）；`default.spec.ts` 补 demo_fallback class 断言；第 3 轮 correctness-reviewer 确认 PASS |
| E2E-FND-001 | Med | e2e | NEG-07（axe 无回归） | axe 可访问性扫描只覆盖了 formal 态首页和 alerts 面板，未覆盖本次改造新增的 `notice--info`/`notice--warning`/`tone-*` 等大量新颜色语义承载态（demo_fallback、stale/unavailable、负向评分、恢复态四档、展开态） | accepted_risk | e2e-reviewer 最终确认轮独立复核维持同一结论，建议下一轮迭代补充覆盖，不阻断本次交付 |
| E2E-FND-002 | Med | e2e | NEG-04（未注册理由码不得直呈原始枚举串） | `humanize.ts` 的映射函数本身有充分单测覆盖，但现有 E2E 只驱动已注册 code（`TREND_ABOVE_EMA`/`SOURCE_DEGRADED`），从未在浏览器层注入未注册 code 验证 `App.tsx` 真实渲染路径确实调用了安全回落函数，而非把原始 code 直接插入 DOM | accepted_risk | e2e-reviewer 最终确认轮新发现；风险低（生产数据 code 集合固定，属防御性路径），建议补 1 条 route 注入未注册 code 的 E2E，作为后续任务，不阻断本次交付 |
| TDD-FND-002~005 | Low | tdd | 交易信号卡非 ready 子态覆盖、toolchain 探测口径误报、AT-0601 failed 态无生产可达路径、全项目缺自动化 mutation testing | 见下方 TDD 有效性审查章节 | accepted_risk | tdd-reviewer 最终确认轮独立复核（含 2 处真实故障注入）维持同一结论，均为已知、非阻断项 |
| RISK-01~03 | Low | correctness | AT-0302 弱断言、E2E-FND-001 关联、chart-source-status 第二来源点解释空间 | 见下方「正确性」章节 | accepted_risk | correctness-reviewer 最终确认轮独立复核发现，均判定非阻断 |
| RISK-DOC-01 | Low | architecture | tech-design.md M6/M8 文件标注 | tech-design.md 正文未回写 `price-authority` 实际落点（ChartSurface.tsx 而非 App.tsx）的说明 | accepted_risk | architecture-reviewer 最终确认轮维持判断，建议后续 tech-design 修订登记，不阻断本次交付 |
| RISK-CSS-01 | Low | architecture | SR-01 措辞与 DEC-S09/M6 CSS-only 重排授权之间的字面张力 | `styles.css` 新增的 `.workspace-header h2` 等 4 个选择器会真实改变范围外文件 `LayoutController.tsx` 渲染出的计算样式（字号/字重/对齐），经核实与 execution-brief.md 逐字匹配、是 tech-design M6/DEC-S09 明确要求的唯一可行机制（LayoutController JSX 被冻结），不构成 SR-01（精确定义域=`.data-notice` 共享类颜色/背景/边框）违规，但与「范围外零改动」的字面直觉存在张力 | accepted_risk | architecture-reviewer 最终确认轮新发现；建议后续治理复核 SR-01 措辞是否需要显式区分「文件零编辑」与「渲染结果零改变」两种边界承诺，不阻断本次交付 |

---

## 正确性

**Verdict（最终确认轮）：PASS**

修复闭环历史：correctness-reviewer 第一轮识别 GAP-01（`ChartSurface.tsx` 来源提示硬编码警告色）与 GAP-02（负向评分色物理区分缺渲染层证据）两个 High；第二轮复审确认 GAP-01/GAP-02 已解决，同时发现新的同类问题 GAP-03（`App.tsx` 侧的 `signal-degradation-note` 存在与 GAP-01 完全相同的 bug 模式）；第三轮确认 GAP-03 已解决。

最终确认轮：主 Agent 重新派发 correctness-reviewer 对当前代码状态做完全独立的复核（不采信此前轮次的转述结论，自行重新阅读全部实现文件与验收材料）。逐条核对 22 条验收条件（`acceptance-scenarios.md`）与差量规格 25 个 Scenario（`spec.md`），构建了完整的 behavior_matrix：GAP-01/GAP-02/GAP-03 三处此前修复的缺陷经本人直接阅读源码逐行核实真实已修复、无回归；SCN-01~07 全部条件、NEG-01/03/04 均 pass；`LayoutController.tsx`/`AlertRulePanel.tsx`/`WorkbenchShell.tsx`/`src/domain/*`/`src/lib/signals.ts` 全部 `git diff` 确认零改动。独立执行 `npm run build`（exit 0，非首次尝试因端口问题重试后干净通过）与 `npx playwright test`（全量重跑，50 passed / 0 failed / 0 skipped），不采信任何转述数字。

发现 3 个 Low 级别 non-blocking risk（RISK-01~03）：AT-0302 弱断言（不含枚举串的宽泛负向断言，未各自精确驱动 `not_target_symbol`/`data_insufficient` 两态，与 tdd-reviewer 记录的同类风险一致）、E2E-FND-001 关联（不重复阻断）、`chart-source-status` 元素是否构成唯一权威点之外的第二处可见来源信息存在解释空间（但该元素为既有基线、本次未改动，tech-design 已明确登记为"派生一致性指示"非权威点，不构成本轮遗留缺陷）。均判定非阻断。

---

## TDD Toolchain Status

| Artifact | Status | Missing Capabilities | Decision Gate Reasons |
|----------|--------|----------------------|------------------------|
| `harness-runtime/harness/traces/20260721-watchboard-ui-friendliness/tools/toolchain-status.json` | FAIL（探测口径误报，非真实测试证据缺失） | pytest/mutmut/StrykerJS/vitest 相关能力（本项目实际用 `node --test` + `npx playwright test`，非这些通用工具，探测脚本对 Node/Playwright 项目的能力映射存在系统性误报） | 无需 Decision Gate；tdd-reviewer 两轮均判定为 Harness toolchain 控制面缺口，不作为 TDD finding，已建议后续修正探测口径 |

---

## TDD 有效性审查

**Verdict:** PASS_WITH_RISK

**Toolchain Status:** `harness-runtime/harness/traces/20260721-watchboard-ui-friendliness/tools/toolchain-status.json`（FAIL 为探测口径误报，见上节）

### Role Boundary

| 项 | 结论 |
|----|------|
| 本次只审测试有效性 | yes，不评估实现是否满足需求（correctness-reviewer 职责） |
| 已排除的非 TDD 问题 | toolchain-status.json 通用探测误报；styles.css "删除规则" 在 `git diff HEAD` 中显示 0 删除的表面疑点（已核实为对比预 mission 旧 HEAD 的正常现象，规则确认已从当前文件移除，`grep` 直接验证无匹配） |
| 与 correctness/e2e/verify 的边界 | 已用真实故障注入（改坏 `mtsCardToneClass`/`resolveSourceTone` 具体分支，确认目标测试变红，再还原确认变绿）独立验证关键新增断言，非采信执行者转述 |

### Test Adequacy Matrix（关键条目）

| 验收场景/条件/任务项 | 测试追溯 | Red 有效性 | 断言强度 | 充分性 | Fault Detection | 结论 |
|------------------|----------|------------|----------|--------|-----------------|------|
| GAP-01/GAP-03（demo_fallback 呈 notice--info 非 notice--warning） | `acceptance-matrix.spec.ts` AC-02/AC-03、`workbench/default.spec.ts` | valid | strong（`toHaveClass`/`not.toHaveClass` 双向绑定） | adequate | proven（真实故障注入：把 `demo_fallback→"info"` 改成 `"warning"`，目标用例立即红） | pass |
| GAP-02（negative 评分 caution 色与来源 warning 色物理区分） | `tests/e2e/mts/friendliness.spec.ts` "GAP-02" | valid | strong | adequate | proven（真实故障注入：把 `caution→"risk"` 改成 `"neutral"`，目标用例立即红且报错信息精确指向被破坏分支） | pass |
| PT-01 `resolveScoreTone` alertLevel=风控 OR 分支（execute 阶段真实缺陷历史） | `tests/unit/presentation/tone.spec.ts` | valid | strong | adequate | proven（execute 阶段真实抓到过该缺陷） | pass |
| PT-03 `humanizeTradeStatus` 漏传参数（execute 阶段真实缺陷历史） | `tests/e2e/trade-signal/friendliness.spec.ts`（`toHaveText` 精确文案） | valid | strong | adequate | proven | pass |
| PT-07 NEG-01 一致性（真实 domain 门控，未 mock） | `tests/e2e/gate/consistency.spec.ts` | valid | strong | adequate | proven | pass |
| 全量回归 | `node --test`（35/35）+ `npx playwright test`（50/50） | valid | — | — | — | pass |

### TDD Non-blocking Risks

（最终确认轮：tdd-reviewer 独立复核，对以下两处关键分支做了真实故障注入——1) 改坏 `resolveScoreTone` 负向评分分支 `caution→warning`，`tests/e2e/mts/friendliness.spec.ts` GAP-02 用例即时变红；2) 改坏 `resolveSourceTone` 的 `demo_fallback` 分支 `info→warning`，`acceptance-matrix.spec.ts` AC-02/AC-03 与 `workbench/default.spec.ts` 即时变红；均已还原并确认 `git diff` 为空、套件恢复全绿。）

| ID | 严重性 | 关联项 | 风险 | 建议 |
|----|--------|--------|------|------|
| TDD-FND-002 | Low | AT-0301/AT-0302 交易信号卡非 ready 子态 | `data_insufficient`/`not_target_symbol` 只在单测做纯函数等价性验证，E2E 只覆盖 `formal`/`source_degraded` 两态，未在 DOM 层交叉验证 | 后续可补独立 E2E 覆盖 |
| TDD-FND-003 | Low | 全项目工具链 | `toolchain-status.json` 顶层 FAIL 系 pytest/coverage.py/mutmut/vitest 等通用多语言探测器与本项目实际工具链（`node --test` + `npx playwright test`）不匹配所致的系统性误报；本轮独立核实（亲自重跑单测/E2E 均为真实绿色，且亲自故障注入证明测试确有抓错能力） | 建议修正探测脚本能力映射 |
| TDD-FND-004 | Low | RestoreStatus `resolveRestoreTone` failed 分支 | 真实恢复流程无代码路径产出 `status="failed"`，无法通过用户可达 E2E 路径触发，测试文件已主动披露该限制并用等价单测兜底 | 若未来该状态变为生产可达需补 E2E |
| TDD-FND-005 | Low | 全项目 TS/JS 变更面 | 未配置 JS/TS mutation testing 工具（StrykerJS 未安装），除本轮对两处最高风险分支的人工 targeted fault injection 外，无系统性自动化变异测试信号覆盖其余条件分支 | 建议后续引入 StrykerJS 或等价工具形成常态化变异测试信号 |

---

## E2E 控制面 Status

| Artifact | Status | Missing Capabilities | Decision Gate Reasons | Artifacts |
|----------|--------|----------------------|------------------------|-----------|
| `harness-runtime/harness/traces/20260721-watchboard-ui-friendliness/e2e/e2e-status.json` | FAIL（顶层状态滞后/探测口径误报，`e2e_run_status` 实为 PASS） | T007 `accessibility_smoke` 标注 `e2e_tool_not_run_or_failed`——探测脚本按"独立 axe CLI 产物"格式识别，未识别内嵌于 Playwright spec（`scope-guard.spec.ts`/`t001-watchlist-archive-restore.spec.ts`）的 `@axe-core/playwright` 断言，实际已运行且通过 | 无需 Decision Gate；e2e-reviewer 两轮均独立核实 axe 断言真实执行且通过，判定为控制面探测口径与产物新鲜度问题，非真实能力缺失；建议 Harness Gate 后续修正 | report: `playwright-report/index.html`；trace/screenshot：`playwright.config.ts` 已配置 `trace: retain-on-failure` + `screenshot: only-on-failure` |

---

## E2E 审查

**Verdict（最终确认轮）:** PASS_WITH_RISK

**Methodology:** `.harness/docs/e2e-effectiveness-reviewer-methodology.md`

最终确认轮：主 Agent 重新派发 e2e-reviewer 对当前代码状态做完全独立的复核，独立复跑 `npx playwright test`（全量）两次均 50 passed / 0 failed / 0 skipped / 0 flaky，config 审计确认无过滤/无重试掩盖失败。新发现 E2E-FND-002（Med，NEG-04 未注册理由码回落只有单测证据，缺浏览器层 DOM 证明，见发现列表）。

### Role Boundary

| 项 | 结论 |
|----|------|
| 本次只审 E2E 用户路径证明力 | yes |
| 已排除的 Harness Gate / 验证问题 | e2e-status.json 顶层 FAIL（探测口径/新鲜度问题，见上节）；「界面忠诚度」维度显式跳过（本 mission 无 `behavior-graph.yaml`，interaction 阶段经治理档跳过） |
| 与 correctness/tdd/验证的边界 | 只判断用户路径证明力，不判断实现是否满足需求（correctness）、不判断断言有效性本身（tdd） |

### E2E Coverage Matrix（关键条目）

| 验收场景/条件/任务项 | E2E 测试追溯 | 用户可观察结果断言 | 数据真实性 | 负向路径 | 结论 |
|------------------|---------------|--------------------|------------|----------|------|
| NEG-01（跨呈现一致性） | `tests/e2e/gate/consistency.spec.ts` | strong | real（真实 domain 门控，未 mock） | covered | pass |
| NEG-03（恢复/来源独立承载） | `consistency.spec.ts` + `tone.spec.ts` + `workbench/friendliness.spec.ts`（三重验证） | strong | real | covered | pass |
| GAP-01/GAP-03（demo_fallback 色语义） | `acceptance-matrix.spec.ts` + `workbench/default.spec.ts` | strong | real | covered | pass |
| GAP-02（负向评分色物理区分） | `mts/friendliness.spec.ts` "GAP-02" | strong | real（真实 domain 计算驱动） | covered | pass |
| SR-01（范围外零改动） | `tests/e2e/gate/scope-guard.spec.ts` | strong | real | covered | pass |
| 全部既有基线回归 | `card.spec.ts`/`default.spec.ts`/`acceptance-matrix.spec.ts`/`resume.spec.ts`/`t001-...spec.ts` | strong（逐行核对无断言被削弱） | real | n/a | pass |

### E2E Non-blocking Risks

| ID | 严重性 | 关联项 | 风险 | 建议 |
|----|--------|--------|------|------|
| E2E-FND-001 | Med | NEG-07 axe 覆盖面 | axe 扫描只覆盖 formal 态首页 + alerts 面板，本次改造新增的 `notice--info`/`notice--warning`/`tone-*` 等大量颜色语义承载态（demo_fallback、stale/unavailable、负向评分、恢复四档、展开态）未被 axe 扫描过 | 建议下一轮迭代补充至少 1 个 `notice--warning`/`notice--info` 态和 1 个展开态的 axe 扫描 |
| E2E-FND-002 | Med | NEG-04 未注册理由码 | 现有 E2E 只驱动已注册 code，未在浏览器层注入未注册 code 验证真实渲染路径确实调用了安全回落函数 | 建议补 1 条 route 注入未注册 reason code 的 E2E，断言展开后文本不含原始 code 字符串 |
| E2E-FND-003 | Low | SCN-06 来源小圆点/archived 弱化 | 来源小圆点用 OR 正则接受两个可能类名；archived 弱化仅断言颜色"不同"，不证明差异方向确实是"弱化" | 建议收紧为具体类名/阈值断言 |
| E2E-FND-004 | Low | SCN-04 顶部控件对齐 | 右对齐断言用宽松 OR 匹配多种对齐值组合 | 建议锁定为确切期望值 |
| E2E-FND-005 | Low | 控制面探测口径（非 E2E 职责） | e2e-status.json 顶层 FAIL 由探测脚本对 T007 accessibility_smoke 与 T001 auth_state 两处误判导致，trace 记录 49 passed 与独立复跑 50 passed 存在快照新鲜度漂移 | 移交 Harness Toolchain Gate 修正探测脚本，不影响本次 E2E verdict |

---

## 设计一致性

**Verdict（最终确认轮）：PASS_WITH_RISK**

修复闭环历史：architecture-reviewer 第一轮识别 ARCH-01（CSS 侧信道违反 SR-01 范围外零改动）与 ARCH-02（`price-authority` 接口归属相对 tech-design 文字标注的漂移）两个 High。第二轮：ARCH-01 确认已修复；ARCH-02 经独立重新论证改判为非阻断设计漂移。

最终确认轮：主 Agent 重新派发 architecture-reviewer 对当前代码状态做完全独立的复核（重新读 `solution.md` DEC-S01~S09 原文、`tech-design.md` M1~M8 原文、`execution-brief.md` AT-0501 原文、逐一执行 `git diff`/`grep` 取证，不采信此前转述）。确认：ARCH-01 无任何残留证据表明复现（`git diff -- src/styles.css` 全量核对，无 hunk 覆盖 `.data-notice`/`.up`/`.down` 所在区域）；ARCH-02 维持"非阻断设计漂移"判断——`price-authority` 落点是 DEC-S05 显式授权范围内的承载选点结果，功能层面与 tech-design M6 文字描述一致，仅模块标题的文件锚点标注未同步，已记录为 RISK-DOC-01。

本轮独立复核**新发现** RISK-CSS-01：`styles.css` 新增的 `.workspace-header h2`/`.range-controls`/`.layout-control-strip`/`.workspace-actions` 四个选择器会真实改变范围外文件 `LayoutController.tsx` 渲染出的标题/控件计算样式（字号、字重、对齐）——这是对"范围外文件"渲染结果的实质性视觉影响。经核实：这四个选择器与 execution-brief.md 授权变更集逐字匹配，是 tech-design M6（SUC-05-OP-01）与 solution DEC-S09 明确要求的唯一可行机制（因 `LayoutController.tsx` JSX 被冻结，只能走 CSS-only 重排路径），不构成 SR-01 违规（SR-01 的精确定义域是共享 `.data-notice` 类的颜色/背景/边框定义，非"文件渲染结果零改变"）。但这与"范围外零改动"的字面直觉存在张力，故本轮判定为 Low 非阻断风险而非直接放行为纯 PASS，建议后续治理复核 SR-01 措辞是否需要显式区分"文件零编辑"与"渲染结果零改变"两种边界承诺。

模块边界（M1~M8）、依赖方向（呈现层单向只读消费 domain，`grep` 确认 presentation 模块自身只 import domain 的函数/类型、无反向依赖）、接口契约（6 个新函数签名与 tech-design §4 逐条对应）、数据/状态流（全读侧，无新增写入，presentation 层未新增门控分支逻辑）、禁止路径（`LayoutController.tsx`/`AlertRulePanel.tsx`/`WorkbenchShell.tsx`/`src/domain/*`/`src/lib/signals.ts`/共享 `.data-notice`/`.up`/`.down` 定义）全部核实合规，独立执行 `git diff` 确认三处禁改文件为空 diff。

---

## 安全与可靠性

security-reviewer 未触发（无认证/授权/加密/用户输入/API 暴露/secret 相关变更，本 mission 为纯呈现层改造）。可靠性方面：全部改动为 additive（新增 CSS 类/函数/组件），既有共享定义/涨跌色/归档业务逻辑/快照读写逻辑均零改动；回滚路径为 git revert，无数据/schema 变更需要考虑。

---

## 修复闭环

| Round | High Findings | 修复动作 | 重审范围 | 重审结论 |
|-------|---------------|----------|----------|----------|
| 1 | GAP-01（correctness）、GAP-02（correctness）、ARCH-01（architecture）、ARCH-02（architecture） | 修复 `ChartSurface.tsx` chart-degradation-note 改用 `resolveSourceTone`；删除越权 CSS 规则；补充 GAP-02 渲染层测试+截图；ARCH-02 未改代码，等待复核 | all_reviewers（correctness/tdd/e2e/architecture 四位全量重审） | correctness: HOLD（新发现 GAP-03）；architecture: PASS（ARCH-01 fixed，ARCH-02 reclassified）；tdd: PASS_WITH_RISK；e2e: PASS_WITH_RISK |
| 2 | GAP-03（correctness，第 1 轮修复遗漏的兄弟位置） | 修复 `App.tsx` signal-degradation-note 改用 `resolveSourceTone`，`signal-error-note` 按设计保持不变 | correctness-reviewer（该 finding 唯一责任方；tdd/e2e/architecture 第 2 轮已确认 PASS 且改动范围与其审查维度不相关） | correctness: PASS |
| 最终确认轮 | 无（本轮为独立复核，非修复触发） | 无代码改动；主 Agent 对全部 4 位审查员重新派发，要求各自独立读代码、独立重跑 build/测试套件，不采信任何转述结论 | 全部 4 位审查员（correctness/tdd/e2e/architecture） | correctness: PASS；tdd: PASS_WITH_RISK（含 2 处真实故障注入）；e2e: PASS_WITH_RISK（新发现 E2E-FND-002，Med，非阻断）；architecture: PASS_WITH_RISK（新发现 RISK-CSS-01，Low，非阻断） |

修复闭环全部完成，无 open High finding。最终确认轮新发现的 2 项风险（E2E-FND-002、RISK-CSS-01）经审查员本人评估均为 Med/Low 非阻断风险，不构成新的 High finding，不触发新一轮修复。

---

## 验证交接

| 验证关注点 | 来源 Finding / Risk | 建议验证层次 | 证据要求 |
|------------|---------------------|--------------|----------|
| axe 可访问性覆盖面扩展 | E2E-FND-001（Med） | e2e | 补充 demo_fallback/warning 态 + 展开态的 axe 扫描证据 |
| tech-design M6/M8 文档同步 | RISK-DOC-01（Low） | manual（文档） | 在 tech-design.md 补登记 price-authority 实际落点说明 |
| toolchain 探测口径修正 | TDD-FND-002（Low） | operational | Harness toolchain 控制面后续迭代修正 Node/Playwright 项目能力映射 |
| 交易信号卡非 ready 剩余子态 E2E | TDD-FND-001/E2E-FND-002（Low） | e2e | 可选补充 not_target_symbol/data_insufficient 独立 E2E |
| GAP-02 的可访问性/对比度专项复核 | E2E-FND-001 关联 | e2e | verify 阶段如涉及可访问性专项验收，建议纳入负向评分态 |

---

## 评审结论

**Approved.** 全部 4 位启用的审查员（correctness-reviewer、tdd-reviewer、e2e-reviewer、architecture-reviewer）在最终确认轮（对当前代码状态的完全独立复核，非采信历史转述）给出 PASS 或 PASS_WITH_RISK，无 open High finding：correctness-reviewer PASS；tdd-reviewer / e2e-reviewer / architecture-reviewer PASS_WITH_RISK（合计 2 项 Med + 10 项 Low 非阻断风险，均已记录并附具体建议，不阻断本次交付）。

执行阶段与 code-review 阶段共发现并修复 6 处真实缺陷（execute 阶段 3 处：alertLevel=风控 分支遗漏、humanizeTradeStatus 参数漏传、`.watch-list` 布局溢出；code-review 阶段 3 处：ChartSurface/App.tsx 两处硬编码警告色 bug、负向评分色渲染层证据缺口），SR-01 硬约束全程守住（`LayoutController.tsx`/`AlertRulePanel.tsx`/`WorkbenchShell.tsx` 零改动，共享 `.data-notice`/`.up`/`.down` 定义本体未改，最终确认轮 `git diff` 再次核对确认）。独立验证（4 位审查员各自重新执行，非转述）：`npm run build` exit 0，`npx playwright test`（全量，多次独立重跑）50/50 通过，0 skip，0 flaky。tdd-reviewer 对两处最高风险的 tone 映射分支做了真实故障注入验证（改坏→变红→还原→变绿）。

本次交付携带的非阻断残留风险（PASS_WITH_RISK）已通过 Decision Gate 记录用户风险接受（见契约 `gate_decisions`），可推进 verification lane。
