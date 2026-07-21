# 代码评审: 20260522-stock-watch-system

> **来源**：code-review 技能 -> `harness-runtime/harness/artifacts/20260522-stock-watch-system/code-review/code-review.md`
> **上游**：`mission-contract.md` | `solution.md` | `tech-design.md` | `execution-brief.md` | `execution-result.md`

**Author:** Codex  
**Date:** 2026-06-06  
**mission-id:** `20260522-stock-watch-system`  
**Scope:** `TASK-STOCK-WATCH-T002` ~ `TASK-STOCK-WATCH-T006`  
**Status:** `ready`  
**Review Verdict:** `PASS_WITH_RISK`

---

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/code-review.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本 Markdown 记录人读解释、复审闭环和证据索引。
- 当前仓目录不是 git repo，`git status` / diff 证据不可用；本轮以执行结果、源码现状、测试运行和复审角色结论替代 diff 证据。

---

## 审查依据与范围

| 输入 | 路径 / 来源 | 状态 | 本次用途 |
|------|-------------|------|----------|
| 初始任务契约 | `harness-runtime/harness/missions/20260522-stock-watch-system/mission-contract.md` | present | AC-01~AC-05 与非目标边界 |
| 产品定义包 | `harness-runtime/harness/stages/20260522-stock-watch-system/product/product-definition.md` | present | FR / RULE / BUC 的业务语义核对 |
| 方案与技术设计 | `harness-runtime/harness/stages/20260522-stock-watch-system/solution.md` / `tech-design.md` | present | SourceHealth、MTS、Alert、WorkspaceSnapshotV2、E2E obligation 边界 |
| 执行授权 | `harness-runtime/harness/stages/20260522-stock-watch-system/execution-brief.md` | present | T002~T006 任务边界、authorized paths、stop conditions |
| 执行结果 | `harness-runtime/harness/artifacts/20260522-stock-watch-system/execute/execution-result.md` | present | changed surface 与执行证据索引 |
| 变更 diff | git unavailable | missing | 目录不是 git repo，未使用 diff 作为权威证据 |
| 测试与工具链证据 | `npm run build`; `playwright test`; `node --test tests/unit/alerts/rule-model.spec.ts tests/replay/alerts/trigger-flow.spec.ts` | present | 真实运行验证 |

---

## 变更集承接

| Execution Unit | Changed Surface | Execute Deviations / Blockers | Return Condition Hits | Review Scope Decision |
|----------------|-----------------|-------------------------------|-----------------------|-----------------------|
| T002 SourceHealth / workbench | `src/domain/market-data-source.ts`, `src/features/source/*`, `src/features/chart/*`, `src/App.tsx` | 初审发现 UI 仍猜 legacy source 状态；已修为只认 `sourceHealth`，缺失统一 `unavailable` | ARCH-01 fixed | covered |
| T003 MTS explanation / registry | `src/lib/signals.ts`, `src/domain/mts-registry.ts`, `src/types.ts`, MTS E2E/replay | 初审发现旧 `CompositeSignal` 外泄、registry vocabulary 漂移；已修为 `MtsExplanation` 对外合同 | ARCH-02 / ARCH-03 fixed | covered |
| T004 Alert taxonomy / scheduled | `src/domain/alert.ts`, `src/features/alerts/AlertRulePanel.tsx`, alert replay/E2E | 初审发现 scheduled missed 会重开即补触发；已修为 missed 只记历史并保持 idle | CR-01 fixed | covered |
| T005 WorkspaceSnapshotV2 / restore | `src/domain/workspace.ts`, `src/App.tsx`, restore E2E | 初审发现 roundtrip E2E 不足；已补 selectedSymbol + per-symbol layout/tab 真实写入后 reload 验证 | E2E-FND-001 fixed | covered |
| T006 Fixture gate / acceptance matrix | `fixtures/*`, `tests/e2e/gate/*`, replay corpus | 本轮修复后完整 E2E 24 passed | no blocker | covered |

---

## 审查角色选择与结论

| Reviewer | 是否启用 | 启用依据 | 角色边界 | 结论 |
|----------|----------|----------|----------|------|
| correctness-reviewer | yes | 所有实现必须审需求忠实性；T004 曾 HOLD | 只审用户可观察行为与状态语义 | PASS |
| tdd-reviewer | yes | 所有实现必须审测试有效性 | 只审测试能否抓错，不审实现正确性 | PASS_WITH_RISK |
| e2e-reviewer | yes | `e2e.enabled=true` 且 T004/T005 涉浏览器路径 | 只审用户路径证明力 | PASS |
| architecture-reviewer | yes | SourceHealth / MTS / WorkspaceSnapshotV2 触及接口与模块边界 | 只审架构边界和设计一致性 | PASS |
| security-reviewer | no | 本轮无 auth / secret / permission / API exposure 变更 | n/a | n/a |
| data-migration-reviewer | no | 仅 localStorage snapshot 迁移，无线上数据迁移 | n/a | n/a |
| agent-behavior-reviewer | no | 产品运行时不含 Agent 组件 | n/a | n/a |

---

## 评审摘要

本轮 code-review 初审出现多项 HOLD，主要集中在四类问题：

1. MTS 与 registry 合同没有完全替代旧 `CompositeSignal`。
2. UI 仍在 `sourceHealth` 缺失时根据旧 `dataSource` / timestamp 猜测来源状态。
3. scheduled alert 的 missed 语义错误：浏览器重开时记录 `missed_while_closed` 的同时直接触发。
4. restore-layout E2E 只证明读侧恢复，不足以证明真实用户写入后的 selectedSymbol + per-symbol layout/tab 恢复。

已完成修复并复审：

- correctness-reviewer：PASS。
- e2e-reviewer：PASS。
- architecture-reviewer：PASS。
- tdd-reviewer：PASS_WITH_RISK，无 High 阻断；风险为 red artifact 与控制面状态刷新。

最终结论：**可进入 verification-lane / verify，但带非阻断风险追踪。**

---

## 发现列表

| ID | 严重级别 | 类别 | 关联项 | 摘要 | 状态 | 处理引用 |
|----|----------|------|--------|------|------|----------|
| CR-01 | High | correctness | T004 / DATA-06 / SF-04 | scheduled missed 不应重开即补触发 | fixed | `src/domain/alert.ts`; `tests/replay/alerts/trigger-flow.spec.ts`; `tests/e2e/alerts/panel.spec.ts` |
| E2E-FND-001 | High | e2e | T005 / AC-05 | restore roundtrip 未证明 selectedSymbol + per-symbol layout/tab 真实写入恢复 | fixed | `tests/e2e/restore-layout/resume.spec.ts` |
| ARCH-01 | High | architecture | T002 / INT-02/03 | App 仍猜 legacy source 状态 | fixed | `src/App.tsx` |
| ARCH-02 | High | architecture | T003 / INT-05 | 旧 `CompositeSignal` 仍是 UI 外部合同 | fixed | `src/lib/signals.ts`; `src/types.ts`; `src/App.tsx` |
| ARCH-03 | High | architecture | T003 / DATA-03 | `MtsReasonRegistry` metadata vocabulary 漂移 | fixed | `src/domain/mts-registry.ts`; `src/types.ts` |
| TDD-RISK-001 | Med | tdd | T004 / T005 | 本轮新增修复没有独立 red artifact，审计性弱于完整 Red->Green 轨迹 | open_non_blocking | 后续补 red/regression trace |
| TDD-RISK-002 | Low | control-plane | T006 | `toolchain-status.json` / `e2e-status.json` 仍是旧范围/旧 22 条快照 | open_non_blocking | 后续刷新控制面状态 |
| NBR-ARCH-01 | Med | architecture | MOD-03 / MOD-04 | `buildSignal` 对外已是 `MtsExplanation`，但内部仍从 bars 重算部分指标，未来可能与 observation drift | open_non_blocking | 后续把 MTS 内部输入收敛到 `MarketObservation.indicators` |

---

## 正确性

**Reviewer:** correctness-reviewer  
**Verdict:** PASS

### Behavior Matrix

| 场景 | 期望 | 实现证据 | 测试证据 | 结论 |
|------|------|----------|----------|------|
| T004 scheduled missed | 浏览器关闭期间错过的 scheduled tick 只记录 `missed_while_closed`，重开当次保持 `enabled / idle`，不写 `lastTriggeredAt` / `lastScheduledTriggerKey` | `src/domain/alert.ts` 的 `ScheduledEvaluation` 分离 `missed` 与 `trigger` | `tests/replay/alerts/trigger-flow.spec.ts`; `tests/e2e/alerts/panel.spec.ts` | pass |
| 非 scheduled 触发/确认 | price/MTS 等规则命中后仍进入 `triggered`，确认后进入 `acknowledged` | `evaluateAlertRules` 非 scheduled 分支与 `acknowledgeAlertRule` | alert replay + alerts panel E2E | pass |
| 归档暂停回归 | 归档提醒仍保持 `suspended_by_archive`，不会被 scheduled 分支误触发 | `activationState === "enabled"` 才可评估 | alert unit + E2E archive case | pass |

---

## TDD Toolchain Status

此节是 Harness 控制面状态，不是 TDD 审查员结论。

| Artifact | Status | Missing Capabilities | Decision Gate Reasons |
|----------|--------|----------------------|-----------------------|
| `harness-runtime/harness/traces/20260522-stock-watch-system/tdd/toolchain-status.json` | stale / not authoritative for this final state | scope/report freshness | 仍有旧 T001/控制面归一化噪音 |

### TDD 有效性审查

**Reviewer:** tdd-reviewer  
**Verdict:** PASS_WITH_RISK

| 验收场景/条件/Task | 测试追溯 | Red 有效性 | 断言强度 | 充分性 | Fault Detection | 结论 |
|------------------|----------|------------|----------|--------|-----------------|------|
| T004 scheduled / alert state | `tests/unit/alerts/rule-model.spec.ts`; `tests/replay/alerts/trigger-flow.spec.ts`; `tests/e2e/alerts/panel.spec.ts`; gate AC-04 | valid | strong | adequate | proven | pass |
| T005 restore / layout persistence | `tests/unit/workspace/snapshot-migration.spec.ts`; `tests/replay/workspace/migration-replay.spec.ts`; `tests/e2e/restore-layout/resume.spec.ts`; gate AC-05 | valid | strong | adequate | proven | pass |
| T006 fixture gate | `tests/replay/gate/fixture-corpus.spec.ts`; `tests/e2e/gate/acceptance-matrix.spec.ts`; full E2E | valid | strong | adequate | proven | pass |

### TDD Non-blocking Risks

| ID | 严重性 | 关联项 | 风险 | 建议 |
|----|--------|--------|------|------|
| TDD-RISK-001 | Med | T004 / T005 | 新增 scheduled missed 与 restore roundtrip 没有独立 red artifact | 后续补对应 red/regression evidence 到 trace |
| TDD-RISK-002 | Low | 控制面 | `toolchain-status.json` / `e2e-status.json` 陈旧 | 进入正式 gate 前刷新 control-plane snapshot |

---

## E2E 控制面 Status

此节是 Harness 控制面状态，不是 E2E 审查员结论。

| Artifact | Status | Missing Capabilities | Decision Gate Reasons | Artifacts |
|----------|--------|----------------------|-----------------------|-----------|
| `harness-runtime/harness/traces/20260522-stock-watch-system/e2e/e2e-status.json` | stale / not authoritative for this final state | current file records old 22-test snapshot | control-plane freshness drift | latest run: full Playwright 24 passed |

## E2E 审查

**Reviewer:** e2e-reviewer  
**Verdict:** PASS

| 验收场景/条件/Task | E2E obligation | Traceability | User Result | 数据真实性 | 负向路径 | 可靠性 | 结论 |
|------------------|----------------|--------------|-------------|------------|----------|--------|------|
| AC-05 / T005 真实写入后 reload/reopen 恢复 | browser_flow + user_visible_assertion + local_persistence_replay | FR-07/FR-08 -> T005 -> `resume.spec.ts` | 先点击 0700.HK -> dense，再回 AAPL -> mobile_tab/source；reload 后验证 AAPL source，切回 0700.HK 验证 dense | fixture + real localStorage + real app reload | bad layout fallback covered | stable | pass |
| AC-05 / BUC-07 首次打开恢复 | browser_flow + user_visible_assertion | `resume.spec.ts`; gate AC-05 | 恢复 selected symbol、dense layout、acknowledged alert | fixture | covered | stable | pass |
| T004 scheduled missed | browser_flow + user_visible_assertion | `alerts/panel.spec.ts` | 同一行显示 `enabled / idle` 与 `missed_while_closed` | fixture | boundary path covered | stable | pass |

---

## 设计一致性

**Reviewer:** architecture-reviewer  
**Verdict:** PASS

| Design Obligation | Implementation Evidence | 结论 |
|-------------------|-------------------------|------|
| UI 不得根据旧 `dataSource` / timestamp 猜 formal/demo/stale；`sourceHealth` 是唯一状态权威 | `src/App.tsx` 的 `getSourceStatus` 只读 `payload.sourceHealth.status`，缺失统一 `unavailable`；surface 也以 `sourceHealth?.status ?? "unavailable"` 消费 | pass |
| 对外合同从 `CompositeSignal` 切到 `MtsExplanation` | `buildSignal()` 返回 `MtsExplanation`；`CompositeSignal` 已从 `src/types.ts` 移除；App 直接消费 `mts` 与 `mts.interpretability.technicalLevels` | pass |
| `MtsReasonRegistry` metadata vocabulary 对齐设计 | `kind=reason|invalidator`; `severityHint=info|watch|confirm|strong_signal|risk`; `introducedIn=mts-registry-v2` | pass |

### Architecture Non-blocking Risk

| ID | 严重性 | 关联设计 | 风险 | 建议 |
|----|--------|----------|------|------|
| NBR-ARCH-01 | Med | MOD-03 / MOD-04 / SF-03 | `observation` 已生成 indicators，但 MTS 内部仍从 bars 重算 EMA/RSI/MACD/ATR | 后续把 `buildSignal` 内部输入进一步收敛到 `MarketObservation.indicators` |

---

## 安全与可靠性

未触发 `security-reviewer`。本轮变更集中在本地前端状态、localStorage snapshot、MTS explanation 与浏览器 E2E；未引入认证、授权、secret、外部写 API 或破坏性数据操作。

可靠性关注点：

- `e2e-status.json` / `toolchain-status.json` 仍陈旧，后续 Gate 前应刷新。
- Node 直接运行部分 TS 单元文件会遇到无扩展名 ESM 解析限制；`npm run build` 已覆盖 TypeScript 编译，alert unit/replay 可直接运行。

---

## 修复闭环

| Round | High Findings | 修复动作 | 重审范围 | 重审结论 |
|-------|---------------|----------|----------|----------|
| R1 | CR-01 | 拆分 scheduled `missed` 与 `trigger`，missed 后保持 idle | correctness-reviewer | PASS |
| R1 | E2E-FND-001 | 补真实 selectedSymbol + per-symbol layout/tab 写入后 reload roundtrip | e2e-reviewer | PASS |
| R1 | ARCH-01 / ARCH-02 / ARCH-03 | source status 只认 `sourceHealth`；MTS 对外合同切到 `MtsExplanation`；registry metadata vocabulary 对齐 | architecture-reviewer | PASS |
| R1 | TDD control risks | 保留为非阻断风险；命令验证已覆盖最新实现 | tdd-reviewer | PASS_WITH_RISK |

---

## 验证交接

| 验证关注点 | 来源 Finding / Risk | 建议验证层次 | 证据要求 |
|------------|---------------------|--------------|----------|
| scheduled missed 后保持 idle，不补触发 | CR-01 | unit / replay / e2e | alert replay + alerts panel E2E |
| selectedSymbol + per-symbol layout/tab reload 恢复 | E2E-FND-001 | e2e | restore-layout roundtrip |
| SourceHealth 权威状态 | ARCH-01 | e2e / unit | workbench source health cases |
| MTS explanation 对外合同 | ARCH-02 / ARCH-03 | unit / replay / e2e | MTS unit/replay + card E2E |
| control-plane status freshness | TDD-RISK-002 | operational | 重新生成 `toolchain-status.json` / `e2e-status.json` |
| observation -> MTS 指标单源 | NBR-ARCH-01 | architecture / unit | 后续重构时补 unit/replay 防漂移 |

---

## 最新命令证据

| Evidence | Command | Result |
|----------|---------|--------|
| BUILD-CR-20260606 | `npm run build` | PASS |
| E2E-CR-20260606 | `./node_modules/.bin/playwright test` | PASS, 24 tests |
| ALERT-UNIT-REPLAY-20260606 | `node --test tests/unit/alerts/rule-model.spec.ts tests/replay/alerts/trigger-flow.spec.ts` | PASS, 6 tests |
| ARCH-SEARCH-20260606 | `rg 'CompositeSignal|signal\\.mts|signal\\.kind|signal\\.buyLine|signal\\.sellLine|signal\\.stopLine|payload\\.dataSource|kind: "signal"|kind: "fallback"|severityHint: "warning"|severityHint: "critical"|category: "registry"' src tests` | No obsolete contract hits except function name `getSourceStatus` |

---

## 评审结论

`TASK-STOCK-WATCH-T002` ~ `TASK-STOCK-WATCH-T006` code-review 结论为 **PASS_WITH_RISK**：

- High blockers：0。
- correctness-reviewer：PASS。
- e2e-reviewer：PASS。
- architecture-reviewer：PASS。
- tdd-reviewer：PASS_WITH_RISK。

建议进入 `verification-lane / verify`。非阻断风险继续追踪：补 red artifact / 刷新 control-plane status / 后续收敛 MTS 内部指标输入。
