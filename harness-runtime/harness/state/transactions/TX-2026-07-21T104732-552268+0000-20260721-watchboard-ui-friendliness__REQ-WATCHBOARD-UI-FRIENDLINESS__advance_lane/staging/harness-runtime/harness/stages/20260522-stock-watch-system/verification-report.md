# 验证报告: 20260522-stock-watch-system

> **来源**：验证技能 -> `harness-runtime/harness/artifacts/20260522-stock-watch-system/verify/verification-report.md`
> **上游**：`mission-contract.md` | `execution-brief.md` | `code-review.md`

**Author:** Codex
**Date:** 2026-06-07
**mission-id:** `20260522-stock-watch-system`
**Scope:** `TASK-STOCK-WATCH-T002` ~ `TASK-STOCK-WATCH-T006`
**Status:** `ready`

---

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/verification-report.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本 Markdown 记录验证模型、命令证据、结果证据和交付判断。

---

## TL;DR

当前 verify 范围是 `TASK-STOCK-WATCH-T002` 到 `TASK-STOCK-WATCH-T006`。本轮重新运行 build、unit/replay 矩阵和全量 Playwright E2E：build PASS，unit/replay matrix PASS，E2E 在启动 5174 dev server 后 PASS，24 tests / 0 failed。第一次 E2E 失败是 `ERR_CONNECTION_REFUSED`，原因是 no-webserver config 不自动启动服务；服务启动后同一命令通过。

结论：T002-T006 的 verify 证据支持进入 delivery；仍保留 code-review 已登记的非阻断风险：后续可补更细的 final-round red artifact，并在最终交付前继续刷新控制面状态。

---

## 验证依据目录

| 来源产物 | 已消费内容 | 验证用途 | 缺口处理 |
|----------|------------|----------|----------|
| `mission-contract.md` | AC-01~AC-05、范围内 / 范围外边界 | 定义整体验收边界 | 无阻断缺口 |
| `product-definition.md` / `interaction-spec/` | 默认工作台、来源降级、MTS、提醒、恢复和冻结样本语义 | 建立用户可观察结果口径 | 无阻断缺口 |
| `tech-design.md` | SourceHealth、MtsExplanation、AlertRule、WorkspaceSnapshotV2、fixture gate 设计 | 验证实现是否覆盖关键技术风险 | 非阻断风险 `NBR-ARCH-01` 后续跟踪 |
| `execution-brief.md` | T002-T006 任务、required evidence、E2E obligation | 绑定命令证据和结果证据 | 部分早期 vitest 命令已由当前可运行 Node/esbuild matrix 替代 |
| `execution-result.md` | 执行证据、changed surface、red/green/regression 记录 | 确认验证范围和复用证据 | 无阻断缺口 |
| `code-review.md` | fixed High findings、TDD/E2E/architecture 结论、非阻断风险 | 确认无 open High | 非阻断风险保留在验证交接 |
| `project-context.md` / project knowledge | 本地 React/Vite/Express、Playwright、fixture-first 运行约束 | 选择命令和运行方式 | 无阻断缺口 |

---

## 验证目标

| Task | 验证目标 |
|------|----------|
| T002 | 默认工作台、来源健康、指标切换、数据不足和来源降级的可见状态 |
| T003 | MTS 解释卡、ReasonRegistry、非投资建议边界、来源降级时 MTS 降级 |
| T004 | 分类提醒、触发确认、归档暂停、scheduled missed 只记录不补触发 |
| T005 | WorkspaceSnapshotV2、selectedSymbol、per-symbol layout、mobile tab、坏 snapshot 回退 |
| T006 | 冻结样本、fixture checksum、unit/replay 矩阵和 AC-01~AC-05 浏览器验收矩阵 |

---

## 验证模型

| 验收场景 / 条件 | 预期结果 | 实际观察方式 | 验证动作 | 命令证据 | 结果证据 | 回流建议 |
|----------------|----------|--------------|----------|----------|----------|----------|
| 默认工作台与来源健康 | 主图、成交量、副图、OHLC、来源健康和刷新 / 降级语义可见 | Playwright DOM assertions | 全量 E2E + workbench spec | `cmd-e2e-2026-06-07-05-47-19` | `result-t002-workbench` | 失败回 execute |
| MTS 解释卡 | 展示结构化字段，不承诺收益、不表达确定性买卖建议 | Playwright DOM assertions + copy review | E2E + unit/replay matrix | `cmd-unit-2026-06-07-05-46-38`, `cmd-e2e-2026-06-07-05-47-19` | `result-t003-mts` | 失败回 execute / code-review |
| 提醒触发与 scheduled missed | 本地提醒可创建、触发、确认；missed 只记录 history，不补触发 | unit/replay + E2E DOM assertions | unit/replay matrix + alerts E2E | `cmd-unit-2026-06-07-05-46-38`, `cmd-e2e-2026-06-07-05-47-19` | `result-t004-alerts` | 失败回 execute |
| 浏览器重开恢复 | selectedSymbol、alerts、per-symbol layout/tab reload 后恢复；坏 layout fallback | unit/replay + E2E DOM assertions | unit/replay matrix + restore-layout E2E | `cmd-unit-2026-06-07-05-46-38`, `cmd-e2e-2026-06-07-05-47-19` | `result-t005-restore` | 失败回 execute |
| 冻结样本验收矩阵 | AC-01~AC-05 由 fixture-first replay 和 browser gate 覆盖 | replay checksum + Playwright gate spec | unit/replay matrix + gate acceptance matrix E2E | `cmd-unit-2026-06-07-05-46-38`, `cmd-e2e-2026-06-07-05-47-19` | `result-t006-gate` | 失败回 execute |

---

## 验证方法

| 层级 | 命令 / 方法 | 证据编号 | 结果 | 覆盖目标 |
|------|-------------|----------|------|----------|
| Build / typecheck | `npm run build` | `cmd-unit-2026-06-07-05-46-31` | PASS, exit 0 | TypeScript + Vite build |
| Unit / replay | `node --test harness-runtime/harness/traces/20260522-stock-watch-system/t006-all-tests/*.mjs` | `cmd-unit-2026-06-07-05-46-38` | PASS, exit 0 | T002-T006 unit/replay matrix |
| E2E first attempt | `playwright test --config ...playwright-no-webserver.config.ts --trace=on` | `cmd-e2e-2026-06-07-05-46-43` | FAIL, `ERR_CONNECTION_REFUSED` | 环境前置检查，确认 no-webserver 需要先启动服务 |
| E2E rerun | `playwright test --config ...playwright-no-webserver.config.ts --trace=on` | `cmd-e2e-2026-06-07-05-47-19` | PASS, 24 tests / 0 failed | T001-T006 browser paths, T002-T006 为本轮重点 |
| E2E control | `harness verify e2e-status --mission 20260522-stock-watch-system` | `e2e-status.json` | PASS | E2E control-plane status |
| True E2E check | `harness verify true-e2e-check --mission 20260522-stock-watch-system` | control output | PASS | UI evidence policy check |

---

## 验证结果

| 验收场景 / 条件 | 预期结果 | 实际观察结果 | 命令证据 | 结果证据 | 结论 | 缺口 / 风险 |
|----------------|----------|--------------|----------|----------|------|-------------|
| T002 默认工作台 / 来源健康 | 工作台展示主图、成交量、副图、OHLC、来源状态；demo/stale/unavailable 降级穿透 UI | E2E 输出显示 workbench 默认、指标切换、数据不足、demo fallback、stale、unavailable 用例全部通过 | `cmd-e2e-2026-06-07-05-47-19` | `result-t002-workbench` | pass | 无阻断 |
| T003 MTS | MTS 卡展示结构化字段和非投资建议文案；source unavailable 时降级 | E2E 输出显示 MTS structured fields/non-advice 和 unavailable 降级用例通过；unit/replay matrix 通过 | `cmd-unit-2026-06-07-05-46-38`, `cmd-e2e-2026-06-07-05-47-19` | `result-t003-mts` | pass | 无阻断 |
| T004 提醒 | 提醒可创建、触发、确认；归档暂停；scheduled missed 记录 history 且保持 idle | E2E 输出显示 alerts panel 三条路径通过；unit/replay matrix 通过 | `cmd-unit-2026-06-07-05-46-38`, `cmd-e2e-2026-06-07-05-47-19` | `result-t004-alerts` | pass | 无阻断 |
| T005 恢复 | reload 后恢复 selectedSymbol、alerts、per-symbol dense/mobile tab；坏 layout fallback | E2E 输出显示 restore-layout 四条路径通过；unit/replay matrix 通过 | `cmd-unit-2026-06-07-05-46-38`, `cmd-e2e-2026-06-07-05-47-19` | `result-t005-restore` | pass | 无阻断 |
| T006 验收矩阵 | 冻结样本和浏览器 gate 覆盖 AC-01~AC-05 | E2E 输出显示 gate acceptance matrix 五条路径通过；unit/replay matrix 通过 | `cmd-unit-2026-06-07-05-46-38`, `cmd-e2e-2026-06-07-05-47-19` | `result-t006-gate` | pass | 无阻断 |

---

## 端到端验证结果

| 字段 | 值 |
|------|----|
| E2E 状态产物 | `harness-runtime/harness/traces/20260522-stock-watch-system/e2e/e2e-status.json` |
| 当前 verify 新鲜证据 | `harness-runtime/harness/stages/20260522-stock-watch-system/traces/cmd/cmd-e2e-2026-06-07-05-47-19.json` |
| 状态 | PASS |
| HTML 报告 | `playwright-report/index.html` |
| 追踪 / 截图 | `test-results/.playwright-artifacts-*`；本轮 PASS，无失败截图作为最终证据 |
| N/A / BLOCKED / Decision Gate | none |

E2E 新鲜输出显示：`24 passed (6.7s)`。覆盖 workbench、MTS、alerts、restore-layout、gate acceptance matrix 和 T001 watchlist regression。

---

## 风险与质量约束验证

| 编号 | 类型 | 预期 / 约束 | 验证证据 | 实际结果 | 结论 | 后续 |
|------|------|-------------|----------|----------|------|------|
| CR-01 | correctness | scheduled missed 不得重开即补触发 | unit/replay matrix + alerts E2E | PASS | 已验证 | 无 |
| E2E-FND-001 | e2e | restore roundtrip 必须证明真实写入后 reload 恢复 | restore-layout E2E | PASS | 已验证 | 无 |
| ARCH-01/02/03 | architecture | SourceHealth/MTS/registry contract 不漂移 | build + unit/replay + E2E | PASS | 已验证 | 无 |
| TDD-RISK-001 | tdd | final-round red artifact 审计性不足 | code-review risk + verify regression | 当前回归通过，风险非阻断 | 带风险跟踪 | 后续补更细 red trace |
| TDD-RISK-002 | control-plane | 控制面状态需要刷新 | verify 新鲜证据 + e2e-status PASS | 当前 verify 命令证据已刷新 | 已缓解 | delivery 前继续检查 |
| NBR-ARCH-01 | architecture | MTS 内部指标输入未来可能 drift | unit/replay + E2E 当前通过 | 当前不阻断交付 | 非阻断 | 后续重构时收敛到 `MarketObservation.indicators` |

---

## 未覆盖范围

| 范围 | 原因 | 影响 | 下一步 |
|------|------|------|--------|
| 真实外部行情供应商 SLA / auth / quota | 本 mission 使用本地 Express + fixture/fallback，未锁定正式供应商 | 不影响本地看盘系统当前验收；影响未来生产化 | 后续 Provider Gate / integration mission |
| 系统级通知、后台 worker、自动下单 | 明确 scope out | 不影响交付 | 不进入本 mission |

---

## 遗留问题

| 问题 | 严重级别 | 状态 | 处理方式 |
|------|----------|------|----------|
| final-round red artifact 粒度可继续加强 | medium | open_non_blocking | delivery 后或后续质量任务补 red/regression trace |
| `buildSignal` 内部指标输入仍可进一步单源化 | medium | open_non_blocking | 后续架构改进任务处理 |

---

## 验证评价摘要

| 评价项 | 结论 | 证据 / 理由 |
|--------|------|-------------|
| 验收场景 / 条件是否逐项验证 | 是 | T002-T006 均有 unit/replay 或 E2E 证据 |
| 命令证据是否完整 | 是 | build、unit/replay matrix、E2E 均通过 Harness 收集 |
| 结果证据是否完整 | 是 | E2E 24 条用户路径 PASS；结果证据绑定 task 场景 |
| 验证层次是否匹配风险 | 是 | UI/恢复/提醒/fixture gate 用 E2E，领域逻辑用 unit/replay |
| 高优先级风险是否闭环 | 是 | code-review High findings 均 fixed 并由 verify 回归覆盖 |
| 是否可以进入交付 | 可以 | 无 open High / blocker；仅非阻断风险跟踪 |
