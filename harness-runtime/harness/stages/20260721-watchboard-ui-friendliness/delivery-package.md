# 交付包: 20260721-watchboard-ui-friendliness

> **来源**：交付技能 → `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/delivery-package.md`
> **参考方法论**：文档结构框架（Diátaxis Framework）；配置即代码（GitOps）；站点可靠性工程（SRE）服务水平目标 / 指标（SLO / SLI）
> **原则**：内部归档和追溯用；用户验收以 `acceptance-result.md` 为准。
> **上游**：`harness-runtime/harness/missions/20260721-watchboard-ui-friendliness/mission-contract.md` | `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/breakdown/execution-brief.md` | `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/code-review.md` | `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/verification-report.md` | `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/acceptance-result.md`

**作者:** release-readiness-expert（子智能体，受 delivery 编排调度）
**日期:** 2026-07-22
**mission-id:** 20260721-watchboard-ui-friendliness
**最终状态:** `完成`

---

## 控制契约

- Contract: `contracts/delivery.contract.yaml`
- 权威来源：外部 YAML 是程序化权威来源；本文件只作解释说明，不内嵌围栏式 YAML 契约。
- **已知控制面限制**：`harness contract check` 对本契约的 `type: delivery_contract` 报 `unknown_contract_type`——安装版本的 `.harness/common/skills/stage-gate/scripts/check_contracts.py` 尚未注册该契约类型的 schema 分支（当前只识别 `intent_contract`/`behaviour_contract`/`action_contract`/`guide_contract`/`evidence_contract`/`memory_update_contract`）。这是一个控制面探测口径缺口，与本 mission 此前 `e2e-status.json`/`toolchain-status.json` 的探测误报同类，不是本交付内容本身的缺陷；契约字段级内容已通过 `harness contract patch` 完整填充（29 条 acceptance_trace、风险接受、交付边界、DORA 信号等），并经人工逐项核对与 `acceptance-package-reviewer` 审查。建议 Harness 框架后续在 `check_contracts.py` 补充 `delivery_contract` 类型的 schema 校验分支。

---

## 填写方法

| 步骤 | 说明 |
|------|------|
| 1 | 事实汇总自 `mission-contract.md`、`execution-brief.md`、`code-review.md`、`verification-report.md`、`acceptance-result.md` 及本次交付整理时的真实工作区差异（`git status`/`git diff`）与真实浏览器人工核验（2026-07-22）。 |
| 2 | 交付边界四分类（已交付 / 未交付 / 范围外 / 延后）严格按来源标注，不混淆。 |
| 3 | 部署 / 使用就绪检查覆盖入口、环境、配置、权限、数据、迁移、回滚、可观测性七项。 |
| 4 | 证据链接只做索引指向，不重复展开验收结果正文。 |
| 5 | 残留风险与遗留项按严重性判定矩阵（安全 / 数据 / 权限 / 验收阻断 / 不可逆 → 必须处理；有 workaround → 建议处理；无用户可感后果 → 可忽略）逐项定级，不凭印象。 |

---

## 交付摘要

### 一句话概括

把多市场看盘终端界面从「像调试台」改成「像给人用的看盘工具」：状态色语义归位、内部枚举人话化、重复信息去重、顶部与信息层级重排、侧栏与交易信号卡密度优化——用户打开界面即可低成本扫读关键信息，不再被误导性警告色和原始技术字段干扰。

### 交付边界

| 分类 | 内容 | 来源 | 对用户的含义 |
|------|------|------|--------------|
| 已交付 | DEL-01~07 全部 7 项界面呈现层改造：状态色四档归位（正常/信息/谨慎/警告）、内部枚举人话化+进度条评分、来源/价格去重复收敛唯一主源、顶部标题主位+控件降级、主看信息层级建立（主卡突出/次级降灰/免责常驻）、侧栏扫读优化（名称代码同行/来源小圆点/归档弱化）、交易信号卡密度优化（默认关键数字/明细可折叠） | mission-contract.md 成功定义 + acceptance-scenarios.md 29 条验收条件，全部「通过」（acceptance-result.md） | 打开应用即可直接体验全部 7 类改造，无需额外配置 |
| 未交付 | 无（本次 mission 契约范围内的全部交付物均已完成，无因资源/时间原因搁置的既定交付项） | — | — |
| 范围外 | 交易信号 / 回测算法本身、数据源 / 后端 / server、新增业务功能、alibaba mission（20260720）在途策略代码、全量界面重构 / 无关技术债清理 | mission-contract.md「范围外」表 | 本次改造不改变任何计算结果或数据口径，只改变「同样的结果怎么显示」 |
| 延后 | 折叠态持久化（不做，DEC-S04 明确决策）；demo_fallback 最终色档定档（DEC-01，待用户在有需要时确认，当前默认信息级口径已实现且已验证） | mission-contract.md / solution.md DEC-S04 / DEC-S07 | 用户展开的明细在刷新页面后会恢复默认折叠（非缺陷，是既定设计）；demo_fallback 目前既有代码尚未接通，色档为预留默认口径 |

### 变更范围

| 维度 | 数量 | 关键模块/文件 |
|-----|------|------------|
| 新增文件 | 11 | `src/features/presentation/{tone.ts, humanize.ts, ScoreBar.tsx}`（3 个新呈现层模块）；`tests/unit/presentation/{tone.spec.ts, humanize.spec.ts}`（2 个新单测）；`tests/e2e/{gate/consistency.spec.ts, gate/scope-guard.spec.ts, mts/friendliness.spec.ts, restore-layout/tone.spec.ts, watchlist/friendliness.spec.ts, workbench/friendliness.spec.ts}` + `tests/e2e/trade-signal/friendliness.spec.ts`（6 个新 E2E 套件） |
| 修改文件 | 10 | `src/App.tsx`（+335/-约129 行，mts-card/trade-signal-card/watchlist/market-workspace 段重排）、`src/styles.css`（+180 行，新增四档语义色 token/notice variant/score tone/score-bar 类，共享 `.data-notice`/`.up`/`.down` 定义零改动）、`src/types.ts`（+1 行，仅新增 `Tone` 类型）、`src/features/chart/ChartSurface.tsx`、`src/features/restore/RestoreStatus.tsx`；及 5 个既有 E2E spec 文件的断言适配（`acceptance-matrix.spec.ts`/`card.spec.ts`/`resume.spec.ts`/`t001-watchlist-archive-restore.spec.ts`/`default.spec.ts`） |
| 删除文件 | 0 | 无删除，全部为新增能力或既有文件内的呈现层重排 |

### 关键技术决策

| 决策 | 选择 | 理由摘要 |
|-----|------|---------|
| 共享 `.data-notice` 爆炸半径隔离（SR-01） | 新建独立 `notice--info`/`notice--warning` 类，不改 `.data-notice`（:379）共享定义本体，范围内 4 处迁移到新类，范围外 5 处（`AlertRulePanel.tsx`/`LayoutController.tsx`/`WorkbenchShell.tsx`）零改动 | 该类被范围外文件依赖，直接改共享定义会波及未授权文件；本轮 `git diff`/`grep` 独立复核确认全程零改动 |
| 顶部标题主位实现路径 | `LayoutController.tsx` 整文件被冻结（不改 JSX），只能通过 `styles.css` 对其既有 DOM 类（`.workspace-header h2`/`.range-controls` 等）做 CSS-only 重排 | 授权路径边界明确禁止修改该文件；CSS-only 方案是唯一不违反其他硬约束（唯一主源、禁改文件）的可行落点，经 architecture-reviewer 最终确认轮核实为合规（非 SR-01 违规） |
| 负向评分色（caution）与来源故障色（warning）物理区分 | 新建 `.tone-caution` 类而非复用 `.data-notice`/`.notice--warning`，语义命名从旧的 `risk` 改为 `caution` | INV-03 结构不变量：「技术面看空」是市场业务结论，不能与「数据/系统故障」共用告警色，否则误导用户把正常的看空信号当成系统异常 |
| 折叠交互不持久化 | 组件本地 `useState`，刷新页面后恢复默认折叠 | DEC-S04 明确决策：interaction 阶段经治理档跳过，折叠状态持久化不在本次契约范围内 |
| demo_fallback 色档 | 默认按「信息级、不用高危警告色」实现并验证，不派生成硬性阻断验收条件 | DEC-01 为待用户确认的产品决策；当前真实数据源尚无路径产出该状态（见「残留风险」新披露项），色档口径可在后续需要时低成本调整（改一处映射，不改结构） |

---

## 部署 / 使用就绪检查

| 检查项 | 当前结论 | 证据 / 路径 | 不满足时处理 |
|--------|----------|-------------|--------------|
| 交付入口 | 就绪 | `npm run dev` → `http://localhost:4271`；本次交付整理时已实际启动验证可访问 | 不适用 |
| 环境前提 | 就绪 | Node.js + `npm install`（既有项目依赖，无新增外部依赖，solution.md §4 明确不引入组件库/新依赖） | 不适用 |
| 配置要求 | 就绪，无新增配置 | 沿用既有 `server/index.js`（默认端口 4271）；`playwright.config.ts` 沿用既有 E2E 端口 5174 | 不适用 |
| 账号 / 权限 | 就绪，无需账号 / 权限 | 纯前端呈现层改造，不涉及认证 / 授权（security-reviewer 未触发） | 不适用 |
| 数据准备 / 迁移 | 就绪，无数据 / schema 变更 | 全读侧改造，无新增数据模型、无迁移脚本（tech-design.md §5.1「全读侧：无领域写入」） | 不适用 |
| 回滚 / 恢复 | 就绪 | 全部改动为 additive（新增 CSS 类 / 函数 / 组件），既有共享定义 / 涨跌色 / 归档业务逻辑 / 快照读写逻辑零改动；回滚路径为 `git checkout` 恢复改动前文件（本 mission 全程未 commit，工作区差异即完整改动集） | 不适用 |
| 可观测性 | 部分就绪 | 已有：`npm run build`/`npx playwright test`/`node --test` 三层验证证据 + axe 可访问性扫描（覆盖 formal 首页 + alerts 面板）。已知缺口：axe 未覆盖本次新增颜色语义状态（E2E-FND-001，已接受） | 建议下一迭代补充 axe 覆盖面（见「残留风险」） |

---

## 验收状态

> 本节只做归档摘要。面向人的验收入口和预期 / 实际结果证明见 `acceptance-result.md`。

| 验收场景 / 条件 | 追溯锚点 | 结论 | 用户结果证据 | 内部验证证据 | 交付归宿 |
|----------------|----------|------|--------------|--------------|----------|
| SCN-01（状态色语义归位，6 条细项） | SCN-01-COND-01~06 | 通过（COND-01/02 附证据形式限制说明） | acceptance-result.md | verification-report.md（EV-RESULT-01~06） | delivered |
| SCN-02（内部枚举人话化，4 条细项） | SCN-02-COND-01~04 | 通过 | acceptance-result.md | verification-report.md（EV-RESULT-07~10） | delivered |
| SCN-03（去重复收敛唯一主源，2 条细项） | SCN-03-COND-01~02 | 通过 | acceptance-result.md | verification-report.md（EV-RESULT-11~12） | delivered |
| SCN-04（顶部标题主位，2 条细项） | SCN-04-COND-01~02 | 通过 | acceptance-result.md | verification-report.md（EV-RESULT-13~14） | delivered |
| SCN-05（主看信息层级，2 条细项） | SCN-05-COND-01~02 | 通过 | acceptance-result.md | verification-report.md（EV-RESULT-15~16） | delivered |
| SCN-06（侧栏扫读优化，3 条细项） | SCN-06-COND-01~03 | 通过 | acceptance-result.md | verification-report.md（EV-RESULT-17~19） | delivered |
| SCN-07（交易信号卡密度，3 条细项） | SCN-07-COND-01~03 | 通过（COND-01 附证据形式限制说明） | acceptance-result.md | verification-report.md（EV-RESULT-20~22） | delivered |
| NEG-01~07（负向 / 边界路径） | NEG-01~07 | 通过（NEG-04/07 为已接受残留风险） | acceptance-result.md | verification-report.md（EV-RESULT-23~29） | delivered |

**整体结论：** 全部通过（29/29 验收条件通过，0 未通过，0 阻塞；2 项 Med 级残留风险已在 verify 阶段经用户 Decision Gate 显式接受，approval_id=`APR-20260722-007`）。

### 最终用户验收

| 字段 | 值 |
|-----|---|
| 验收结论 | 待用户确认（pending） |
| 验收时间 | — |
| 审批记录 | `harness-runtime/harness/state/approvals.json` |
| 用户反馈摘要 | — |

---

## 证据链接

| 文档类型 | 路径 | 关键结论 |
|---------|------|---------|
| 用户验收结果 | `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/acceptance-result.md` | 29/29 验收条件通过，0 未通过，0 阻塞 |
| 验证报告 | `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/verification-report.md` | 49/49 `compute-scope` 验收锚点 `conclusion=pass`；建议结论「带风险通过」 |
| 代码评审 | `harness-runtime/harness/stages/20260721-watchboard-ui-friendliness/code-review.md` | Approved；4 位审查员最终确认轮 PASS / PASS_WITH_RISK，0 open High finding |
| 测试结果 | `node --test`：35/35；`npx playwright test`：50/50（0 failed / 0 skipped）；`npm run build`：exit 0 | 全部真实重跑通过，两次独立复跑一致 |

---

## 遗留项

> 来源：验收结果证据形式限制、代码审查低严重级别建议、实现中发现的新风险。

### 阻断性遗留项

无。本次 29 条验收条件全部通过，无命中「安全 / 数据 / 权限 / 验收阻断 / 不可逆」判定矩阵的项目。

### 建议性遗留项

| 遗留项 | 来源 | 用户影响 | 严重性 | 建议处理方式 |
|-------|------|----------|--------|-----------|
| E2E-FND-001：axe 可访问性扫描未覆盖本次新增的大量颜色语义状态（demo_fallback/notice--warning/notice--info/tone-* 等），仅测了首页正常态和 alerts 面板 | 代码审查 / 验证报告，Med 级；用户已在 verify 阶段接受（`APR-20260722-007`） | 新增颜色状态的可访问性尚未被自动化专项扫描确认，存在 workaround（现有色彩体系复用既有对比度结构，人工审阅未见异常） | 建议处理 | 下一迭代补充 demo_fallback/warning/展开态的 axe 扫描 |
| E2E-FND-002：NEG-04 未注册理由码兜底只有单元测试证据，无真实浏览器路径 DOM/截图证据 | 代码审查 / 验证报告，Med 级；用户已在 verify 阶段接受（`APR-20260722-007`） | 极端边缘输入场景，有 workaround（纯函数层已证明安全，生产理由码集合固定） | 建议处理 | 补 1 条浏览器层 route 注入未注册 code 的 E2E |
| demo_fallback 状态当前无法通过真实用户操作复现（本次交付整理新发现并披露） | delivery 阶段 release-readiness-expert 本轮复核新发现；既有产品限制，非本次改造引入 | 无用户可感后果（该状态目前根本不会被触发，用户不会遇到"验证不足"的实际场景） | 建议处理 | 若未来产品决定接通该数据源路径，需在 `market-data-source.ts` 补真实产出路径并补浏览器层可复现的验收证据 |

### 可忽略遗留项

| 遗留项 | 来源 | 用户影响 | 严重性 | 建议处理方式 |
|-------|------|----------|--------|-----------|
| TDD-FND-002：交易信号卡非 ready 子态（data_insufficient/not_target_symbol）仅单测等价验证，E2E 未逐态交叉覆盖 | 代码审查，Low 级 | 无用户可感后果（单测已证明纯函数等价性，E2E 已覆盖 formal/source_degraded 两态） | 可忽略 | 后续可选补充独立 E2E |
| TDD-FND-003：Harness toolchain 探测口径对 node:test/Playwright 项目存在系统性误报 | 代码审查，Low 级 | 无用户可感后果（控制面探测口径问题，非真实测试缺失，已用真实命令重跑确认） | 可忽略 | 建议 Harness 框架修正探测脚本 |
| TDD-FND-004：`restoreMetadata.status=failed` 具体枚举值在当前 `src/domain/workspace.ts` 无生产可达路径，仅单测覆盖 | 代码审查，Low 级 | 无用户可感后果（`discardedLayoutKeys` 非空这一同条件下的等价「需关注」分支已有完整浏览器层证据） | 可忽略 | 若未来该状态变为生产可达需补 E2E |
| TDD-FND-005：全项目未配置 JS/TS mutation testing 工具（StrykerJS 等） | 代码审查，Low 级 | 无用户可感后果（本轮对 2 处最高风险分支已做人工故障注入证明测试有效性） | 可忽略 | 建议后续引入 StrykerJS 等工具形成常态化信号 |
| RISK-DOC-01：tech-design.md 未回写 `price-authority` 实际落点（`ChartSurface.tsx` 而非文字标注的 `App.tsx`/M6） | 代码审查，Low 级 | 无用户可感后果（纯文档同步问题，功能落点已经 architecture-reviewer 核实合规） | 可忽略 | 后续在 tech-design.md 补登记 |
| RISK-CSS-01：SR-01「范围外零改动」措辞与「CSS-only 重排 LayoutController 计算样式」授权之间存在字面张力 | 代码审查，Low 级 | 无用户可感后果（经核实非违规，只是治理措辞可以更精确） | 可忽略 | 建议后续澄清 SR-01 措辞，区分「文件零编辑」与「渲染结果零改变」两种边界承诺 |
| `harness contract check` 报 `unknown_contract_type: delivery_contract` | delivery 阶段控制面探测缺口 | 无用户可感后果（契约业务内容已完整填充并经人工核对，问题是安装版本的 checker 脚本尚未注册该类型） | 可忽略 | 建议 Harness 框架后续在 `check_contracts.py` 补充 `delivery_contract` schema 分支 |

### 残留风险

| 风险 | 来源 | 用户后果 | 接受状态 | 处理建议 |
|------|------|----------|----------|----------|
| E2E-FND-001（axe 覆盖面不足） | verify 阶段 Decision Gate | 新增颜色语义状态的可访问性未被自动化扫描逐一确认 | 已接受（`APR-20260722-007`） | 下一迭代补充扫描覆盖 |
| E2E-FND-002（NEG-04 缺浏览器层证据） | verify 阶段 Decision Gate | 未注册理由码回落的浏览器渲染安全性未端到端验证 | 已接受（`APR-20260722-007`） | 补 1 条浏览器层 E2E |

---

## 下一步建议

| 优先级 | 建议 | 背景 |
|--------|------|------|
| 中 | 补充 axe 可访问性扫描覆盖 demo_fallback/notice--warning/notice--info/tone-* 及展开态 | E2E-FND-001 已接受残留风险，建议纳入下一迭代 |
| 中 | 补 1 条浏览器层 route 注入未注册理由码的 E2E | E2E-FND-002 已接受残留风险，建议纳入下一迭代 |
| 低 | 若产品决定启用 demo_fallback 真实数据路径，需在 `market-data-source.ts` 补真实产出该状态的代码路径，并补浏览器层可复现的验收证据 | 本次交付整理时新发现：该状态目前是既有产品未接通的类型定义，非本次改造引入 |
| 低 | tech-design.md 补登记 `price-authority` 实际文件落点；澄清 SR-01「范围外零改动」措辞 | RISK-DOC-01 / RISK-CSS-01，纯文档同步类 |

---

## 移交说明

| 事项 | 说明 |
|------|------|
| 维护者需要知道的上下文 | 本次改造新建了 `src/features/presentation/` 呈现层模块（`tone.ts`/`humanize.ts`/`ScoreBar.tsx`），承载状态色映射与人话化逻辑；后续新增状态色/枚举文案应在此模块扩展，不要在 `App.tsx` 内重新散落判断逻辑。共享 `.data-notice` 类（`styles.css:379` 附近）与涨跌色 `.up`/`.down` 定义是跨范围内外的共享资源，修改前必须先确认 `AlertRulePanel.tsx`/`LayoutController.tsx`/`WorkbenchShell.tsx` 三个文件对它的既有用法不受影响。 |
| 用户需要知道的限制 | 折叠态（MTS 卡/交易信号卡明细）不持久化，刷新页面后恢复默认折叠，这是既定设计（DEC-S04），不是缺陷。demo_fallback 色档为默认口径，当前真实数据源尚未接通该状态。 |
| 重新验证方式 | `npm run build`（exit 0）；`node --test tests/unit/presentation/*.spec.ts`（35/35，含既有信号测试）；`npx playwright test`（全量，50/50）；如需专项复核 SR-01 范围外零改动：`git diff --stat -- src/features/layout/LayoutController.tsx src/features/alerts/AlertRulePanel.tsx src/features/workbench/WorkbenchShell.tsx` 应为空 diff。 |
| 出现问题时的回退方式 | 本 mission 全程在工作区直接改动、未创建 commit（用户已在 execute 阶段授权跳过 worktree/提交流程）；如需完全回退，对上述「变更范围」列出的 10 个修改文件执行 `git checkout -- <file>`，并删除「变更范围」列出的 11 个新增文件即可恢复到改造前状态。 |
| 后续恢复入口 | 交付完成后按 Harness 流程暂停，等待用户或看板下一轮明确触发 `finishing-branch`（分支收尾）或 `retrospective`（复盘）。 |

---

## 轻量交付指标（DORA 信号）

| 指标 | 数值 | 说明 |
|------|------|------|
| 交付周期（Lead Time） | 约 2 天（2026-07-21 ~ 2026-07-22） | intake → delivery 在单个 Mission Slice 内完成，含 discovery/prd/solution/technical_analysis/breakdown/execute/code-review/verify 全部阶段 |
| 返工次数（Rework Count） | 7 | execute 阶段发现并修复 3 处真实缺陷（`resolveScoreTone` 遗漏 alertLevel=风控 分支、`humanizeTradeStatus` 漏传参数导致空白文案、`.watch-list` 布局溢出压住归档按钮）+ code-review 阶段发现并修复 4 处（GAP-01 `ChartSurface.tsx` 硬编码警告色、ARCH-01 越权 CSS 侧信道、GAP-02 负向评分色缺渲染层证据、GAP-03 `App.tsx` 侧同类硬编码警告色遗漏） |
| 审查暂停次数（Review Hold Count） | 3 | code-review 第 1 轮：correctness-reviewer HOLD + architecture-reviewer HOLD（2 次）；第 2 轮：correctness-reviewer 因新发现 GAP-03 再次 HOLD（1 次）；第 3 轮起转 PASS |
| 验证失败次数（Verification Failure Count） | 0 | verify 阶段一次性以 49/49 `compute-scope` 验收锚点 `conclusion=pass` 完成，无需回流重验；execute 阶段内部的 TDD Red→Green 循环失败属正常测试驱动开发流程，不计入此项 |
| 回滚 / 后续任务次数（Rollback / Follow-up Count） | 0（回滚）/ 4（建议性后续任务，见「下一步建议」） | 未发生任何回滚；4 项建议性后续任务均为非阻断的覆盖面扩展或文档同步 |

---

## 任务关闭记录

| 字段 | 值 |
|-----|---|
| 开始时间 | 2026-07-21（intake 阶段用户表达执行意图） |
| 完成时间 | 2026-07-22（delivery 阶段本轮交付整理） |
| 最终状态 | 完成（待用户最终验收确认） |
| Git 分支 | main（本 mission 全程未创建独立 mission 分支 / worktree，用户已在 execute 阶段授权跳过） |
| 最终提交（Commit） | 无（工作区未提交改动，改动集即当前 `git status`/`git diff` 所示差异） |
