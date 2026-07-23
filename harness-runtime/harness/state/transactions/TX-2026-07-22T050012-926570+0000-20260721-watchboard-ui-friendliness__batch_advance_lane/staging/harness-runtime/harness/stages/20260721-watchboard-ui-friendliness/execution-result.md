# 执行结果: 20260721-watchboard-ui-friendliness

- Contract: contracts/execution-result.contract.yaml
- 上游执行授权: `harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/breakdown/execution-brief.md`
- 执行原则: 单个 Atomic Task 是唯一实现单位；Parent task 只作为交付边界和排序边界。

## 执行会话（Execute Session）

| 字段 | 值 |
|-------|-------|
| Skill | execute |
| Carrier | execute |
| Execute Mode | sdd |
| Mission | 20260721-watchboard-ui-friendliness |
| Task Nodes | TASK-WATCHBOARD-UI-T001~T007（对应 PT-01~PT-07） |
| Parent Tasks | PT-01, PT-02, PT-03, PT-04, PT-05, PT-06, PT-07 |
| Atomic Task Queue | AT-0101~AT-0103, AT-0201~AT-0202, AT-0301~AT-0302, AT-0401~AT-0402, AT-0501~AT-0502, AT-0601~AT-0602, AT-0701~AT-0702（共 15 项） |

## 调度摘要（Dispatch Summary）

| Execution Unit | Parent Task | Primary Executors | Reviewers | Status | Boundary Result |
|----------------|-------------|-------------------|-----------|--------|-----------------|
| AT-0101 | PT-01 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0102 | PT-01 | frontend-engineer | spec-reviewer | DONE（1 轮修复后 PASS） | in_boundary |
| AT-0103 | PT-01 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0201 | PT-02 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0202 | PT-02 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0301 | PT-03 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0302 | PT-03 | frontend-engineer | spec-reviewer | DONE（1 轮修复后 PASS） | in_boundary |
| AT-0401 | PT-04 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0402 | PT-04 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0501 | PT-05 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0502 | PT-05 | frontend-engineer | spec-reviewer | DONE（1 轮修复后 PASS） | in_boundary |
| AT-0601 | PT-06 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0602 | PT-06 | frontend-engineer | spec-reviewer | DONE | in_boundary |
| AT-0701 | PT-07 | test-engineer | spec-reviewer | DONE | in_boundary |
| AT-0702 | PT-07 | test-engineer | spec-reviewer | DONE（2 轮修复后 PASS） | in_boundary |

全部 15 个原子任务最终审查结论：**PASS**。

## 授权边界检查

全部执行单位的 `authorized_paths`/`prohibited_paths` 按 `execution-brief.contract.yaml` 的 `tasks[].authorized_paths`/`prohibited_paths` 执行，审查逐条核对无越界改动。关键硬约束验证：

| 约束 | 验证方式 | 结果 |
|------|----------|------|
| `src/features/layout/LayoutController.tsx` 整文件禁改（PT-05） | 每轮审查 `git diff` 核对 | 全程空 diff，零改动 |
| `src/styles.css:379` `.data-notice` 共享定义禁改 | 每轮审查字符级比对规则块 | 未改动 |
| `src/styles.css` `.up`/`.down`（涨跌色）禁改 | grep 校验 | 未改动 |
| 范围外 5 处 `.data-notice`（AlertRulePanel:136、LayoutController:75/121、WorkbenchShell:78/135）禁改 | AT-0702 grep + DOM + 截图三重证据 | 零改动，含 3 处可达位置的真实渲染证据 + 2 处死代码的文件级证据 |
| `archiveSymbol`/`restoreSymbol`/STM-01 归档业务逻辑禁改（PT-04） | 审查核对 onClick 逻辑体逐字未变 | 未改动 |
| 快照读写/STM-07 判定逻辑禁改（PT-06） | 审查核对 `src/domain/workspace.ts` 无改动 | 未改动 |
| 来源→信号降级门控（DEC-S01）禁在呈现层重实现 | 审查核对呈现层只读消费 `tradeSignal.status` | 未改动，只读消费 |

## TDD 证据（TDD Evidence）

| Execution Unit | Red | Green | Regression | 备注 |
|----------------|-----|-------|------------|------|
| AT-0101 | N/A（CSS 纯新增，accepted_alternative：下游 DOM/构建守护） | `npm run build` exit 0 | `git diff` 证 `.data-notice`/`.up`/`.down` 未改 | |
| AT-0102 | `node --test tone.spec.ts` 失败（tone.ts 未实现） | 20→24 条断言全绿（含 alertLevel=风控 修复后新增 4 条） | `npm run build` exit 0 | 首轮审查发现遗漏 `alertLevel=风控` OR 分支，修复后 PASS |
| AT-0103 | `node --test humanize.spec.ts` 失败 | 11 条全绿 | 联合 tone+humanize 35 条全绿 + build 0 | |
| AT-0201 | `npx playwright test mts` 故障注入验证 | `tests/e2e/mts/friendliness.spec.ts` 2 条 + card.spec.ts 2 条全绿 | mts 套件 6/6 | 独立浏览器实测复核（端口 5174 一度被无关项目占用，已用隔离端口验证） |
| AT-0202 | 同上（同一改动批次） | reason-list 人话化 + 折叠展开 2 条全绿 | 同上 | |
| AT-0301 | `npx playwright test trade-signal` | 2 条全绿 | trade-signal+mts 8/8 | |
| AT-0302 | 运行时探针实测 `trade-signal-status` 曾渲染空字符串 | 修复补传 `stanceLabel` 后精确文案断言通过 | 8/8 | **真实 bug**：`humanizeTradeStatus(status)` 漏传第二参数导致非 ready 态文案消失，审查用运行时探针抓到，修复后验证 |
| AT-0401 | `npx playwright test watchlist` | AT-0401/0402 2 条 + t001 基线 3 条全绿 | watchlist 5/5 | 过程中额外发现并修复真实布局回归（`.watch-list` 缺 `grid-template-columns` 导致条目溢出压住归档按钮） |
| AT-0402 | 同上 | 同上 | 同上 | |
| AT-0501 | `npx playwright test workbench` | AT-0501 计数=1 断言通过 | workbench+restore-layout 13/13（含 2 处既有基线折叠适配修复） | |
| AT-0502 | 同上 | AT-0502 标题主位断言通过 | 同上；NEG-06（非法值归一化+标题主位）组合路径首轮缺失，修复后覆盖 | 审查发现 NEG-06 required assertion 未被任何测试合并验证，补充后 PASS |
| AT-0601 | 直接写死 restoreMetadata 首版 4/7 失败（证真实恢复路径会重算） | 改用真实种子数据驱动四态，10/10 全绿 | mts+trade-signal+watchlist+workbench+restore-layout 32/32 | `status="failed"` 态无生产可达路径，改用既有单测 `tone.spec.ts:140-142` 覆盖，审查认可 |
| AT-0602 | grep 证 4/4 范围内 `.data-notice` 迁移完成 | class 迁移 + 既有回归 | 同上 | |
| AT-0701 | 走真实 domain 门控（未 mock） | NEG-01/NEG-03/计数=1 聚合 3/3 全绿 | 全量 48/48 | |
| AT-0702 | grep+DOM+axe 断言 | 首版缺截图证据（HOLD）→ 补 2 张截图（仍缺 workbench-error 可达分支证据，二次 HOLD）→ 补第 3 张截图+真实错误态渲染，6/6 全绿 | 全量 49/49 | 两轮审查发现证据缺口，均属"规格要求的证据形式未产出"而非功能缺陷，修复后 PASS |

## 执行结果（Execution Results）

全部 15 个原子任务状态 DONE。执行过程中发现并修复的真实缺陷（非测试适配类）：

| 缺陷 | 发现方式 | 修复 |
|------|----------|------|
| `resolveScoreTone` 遗漏 `alertLevel=风控` OR 分支（AT-0102） | spec-reviewer 交叉核对 tech-design/business-object-analysis 4 处文档一致要求 | 补分支 + 4 条新测试 |
| `humanizeTradeStatus(status)` 调用漏传 `stanceLabel`，导致非 ready 态文案渲染为空字符串（AT-0302） | spec-reviewer 运行时 Playwright 探针实测 | 补传第二参数 + 精确文案正向断言 |
| `.watch-list` 缺 `grid-template-columns` 导致条目溢出压住归档按钮，用户点不到（AT-0401） | 执行者用 debug 脚本量测真实 boundingClientRect + elementFromPoint 命中测试 | 加一行 `grid-template-columns: minmax(0, 1fr)` |

执行过程中同步修复的既有基线测试（因 PT-02 折叠交互变更导致断言过时，非功能回归）：`tests/e2e/mts/card.spec.ts`、`tests/e2e/workbench/default.spec.ts`、`tests/e2e/gate/acceptance-matrix.spec.ts`、`tests/e2e/watchlist/t001-watchlist-archive-restore.spec.ts`（后者另因 AT-0401 侧栏结构重排同步更新文本断言为 testid 断言）。

## 偏差、阻塞与回流

| Item | Execution Unit | Type | Trigger | Handling | Target Stage / Decision |
|------|----------------|------|---------|----------|--------------------------|
| DEV-01 | AT-0601 | deviation | `status="failed"` 恢复态在 `src/domain/workspace.ts` 无生产可达路径 | 改用既有单测 `tests/unit/presentation/tone.spec.ts:140-142` 覆盖纯函数正确性，E2E 层不伪造注入；spec-reviewer 认可该处理 | 无需回流；风险记录供上游知悉，若未来需要真实触发需新增 domain 层任务 |
| DEV-02 | AT-0702 | deviation | `WorkbenchShell.tsx` 未被任何页面挂载，是死代码，无法通过真实渲染路径触达其 `.data-notice` 用法 | 仅提供文件级 grep 证据，不构造虚假渲染场景；spec-reviewer 两轮均认可该例外 | 无需回流 |
| ENV-01 | AT-0201/0301/0401/0501/0601/0701/0702 全程 | environment | 本机端口 5174 反复被无关项目（AI 客服工作台等）dev server 占用，导致 E2E 误报连接失败/连到错误应用 | 使用隔离端口（5199 等）或本仓库已在运行的合法 dev server（5173）临时验证，测毕完整回滚 `playwright.config.ts`（每次均以 `git diff` 确认空 diff） | 已缓解，不影响交付；建议后续项目层面调整默认端口避免与常见开发端口冲突 |

无 BLOCKED 项，无需 Decision Gate。

## 审查结论（Reviewer Verdicts）

| Execution Unit | Verdict | 轮次 | Blocking Gaps（已解决） |
|----------------|---------|------|--------------------------|
| AT-0101 | PASS | 1 | 无 |
| AT-0102 | PASS | 2 | 缺 alertLevel=风控 OR 分支（已修复） |
| AT-0103 | PASS | 1 | 无 |
| AT-0201 | PASS | 1 | 无 |
| AT-0202 | PASS | 1 | 无 |
| AT-0301 | PASS | 1 | 无 |
| AT-0302 | PASS | 2 | humanizeTradeStatus 漏传参数导致空白（已修复） |
| AT-0401 | PASS | 1 | 无（含额外发现的布局溢出回归，已一并修复） |
| AT-0402 | PASS | 1 | 无 |
| AT-0501 | PASS | 1 | 无 |
| AT-0502 | PASS | 2 | NEG-06 组合路径测试覆盖缺失（已修复） |
| AT-0601 | PASS | 1 | 无 |
| AT-0602 | PASS | 1 | 无 |
| AT-0701 | PASS | 1 | 无 |
| AT-0702 | PASS | 3 | 截图证据缺失（已修复）→ workbench-error 可达分支证据缺失（已修复） |

## 最终验证证据

- `npm run build`：exit 0（tsc --noEmit && vite build）
- `npx playwright test`（全量，不带路径过滤）：**49 passed, 0 failed, 0 skipped**
- `git diff` 范围外文件（AlertRulePanel.tsx / LayoutController.tsx / WorkbenchShell.tsx）：空 diff，SR-01 硬约束全程守住
- `src/styles.css` 的 `.data-notice`（:379 原始位置，现约 :482）共享定义本体：字符级未改
- axe 扫描（主视图 + alerts 面板）：无新增 critical/serious 违规
- 证据截图：`harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence/` 下 6 张 PNG（pt03/pt04/pt05 各 1 张主观项证据 + pt07 scope-guard 3 张范围外零改动证据）
