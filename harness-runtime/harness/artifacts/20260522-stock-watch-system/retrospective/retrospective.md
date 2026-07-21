# Retrospective: 20260522-stock-watch-system

> **来源**：retrospective 技能 -> `harness-runtime/harness/artifacts/20260522-stock-watch-system/retrospective/retrospective.md`
> **上游**：`mission-contract.md` | `verification-report.md` | `acceptance-result.md` | `code-review.md`

**Author:** Codex
**Date:** 2026-06-07
**mission-id:** 20260522-stock-watch-system
**Status:** `ready`

---

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/retrospective.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；Markdown 只作解释说明。

---

## 执行摘要

本次 `T002` 到 `T006` 已完成交付并由用户确认验收，核心本地看盘路径、MTS 解释卡、提醒状态机、浏览器恢复和 fixture-first 验收矩阵均有验证证据支撑。复盘未发现需要推翻 delivered 结论的问题，但发现四类可改进系统条件：delivery contract/checker 漂移发现过晚、no-webserver E2E 前置条件未在验证前显式化、晚轮修复 red/regression 证据粒度不足、控制面派生状态刷新滞后。

## 复盘输入与链路边界

本复盘消费已接受阶段产物，不重新定义交付范围。`retrospective-data` 返回 PASS，`mission artifacts` 显示除 retrospective 外主要阶段产物均存在；交付包和验收结果已进入 delivery artifact 目录，用户验收审批为 `APR-20260607-005`。

| 输入 | 是否存在 | 用途 | 证据 |
|------|----------|------|------|
| 交付包 | 是 | 交付范围、验收路径、残留风险 | `harness-runtime/harness/artifacts/20260522-stock-watch-system/delivery/delivery-package.md` |
| 验收结果 | 是 | 用户可验收结果和未满足条件 | `harness-runtime/harness/artifacts/20260522-stock-watch-system/delivery/acceptance-result.md` |
| 验证报告 | 是 | 命令证据、结果证据、未覆盖范围 | `harness-runtime/harness/artifacts/20260522-stock-watch-system/verify/verification-report.md` |
| 代码审查 | 是 | 发现列表、修复闭环、验证交接 | `harness-runtime/harness/artifacts/20260522-stock-watch-system/code-review/code-review.md` |
| 阶段门报告 / 工作图历史 | 是 | 返工、HOLD、WARN、推进记录 | `harness-runtime/harness/state/gate-reports/20260522-stock-watch-system/delivery__advance_stage.json` |

## 计划偏差

规划路径本身成立，但多个质量约束在晚阶段才被控制面或审查暴露。偏差集中在验证环境前置、设计合同到实现的替代确认、TDD 证据粒度和 delivery gate 契约一致性。

| 计划点 | 实际发生 | 偏差类型 | 原因 | 影响 | 证据 |
|--------|----------|----------|------|------|------|
| fixture-first + E2E 应形成稳定验证门禁 | 首次 E2E 因 5174 未监听出现 `ERR_CONNECTION_REFUSED`，启动 dev server 后 24 tests PASS | 环境前置未显式化 | no-webserver 配置不自动起服务，verify 前未先做端口 preflight | 形成 1 次 verification failure，交付说明必须披露启动前提 | `verification-report.md` |
| tech-design / execution-brief 已冻结 `SourceHealth`、`MtsExplanation`、scheduled alert、reload 恢复语义 | code-review 初审仍发现 legacy source 状态猜测、合同外泄、missed/trigger 语义和恢复证明不足 | 设计合同收敛过晚 | 缺少执行后、review 前的领域合同替代检查 | 返工后移到 code-review，修复密度增高 | `code-review.md` |
| TDD 证据应支撑执行契约 | 最终 `PASS_WITH_RISK`，晚轮修复缺更细 red artifact，派生 status 快照陈旧 | 证据粒度前强后弱 | Red-Green 义务覆盖早期切片，不覆盖 review 后 corrective fix | 功能通过但审计链不够干净 | `code-review.md` |
| delivery 用户验收后应平滑进入 retrospective | 初次 delivery gate 因 `delivery_contract` 缺 v1 外壳且 checker 未注册而 `cannot_continue`，修复后转为 `continue_with_warnings` | contract/checker 漂移 | contract 模板、runtime 文件和 stage-gate checker 未同源校验 | 已验收交付仍发生治理返工 | `delivery__advance_stage.json` |

## 跨阶段失败模式

这些问题不推翻交付结论，但揭示了 Harness 控制面和项目验证流程的长期改进点。复盘按偶发、重复、系统性分层，避免把一次环境失败误判为产品失败。

| 失败模式 | 出现阶段 | 重复性 | 根因 | 影响面 | 证据 |
|----------|----------|--------|------|--------|------|
| E2E runner 前提未显式化 | verify / delivery | one-off | no-webserver 配置与服务启动职责分离 | 验证命令首次失败，交付说明增加运行前提 | `verification-report.md` |
| 控制面派生状态刷新滞后 | code-review / delivery gate | repeated | toolchain/e2e/project_lint 快照未随最终 rerun 同步刷新 | 审查和 gate 需要解释当前事实与旧快照差异 | `code-review.md`, `delivery__advance_stage.json` |
| 证据粒度前强后弱 | execute / code-review | repeated | late-stage corrective fix 未绑定独立 red/regression 证据义务 | 最终为 PASS_WITH_RISK，审计细度不足 | `execution-result.md`, `code-review.md` |
| contract/checker 漂移 | delivery / stage-gate | systemic | delivery contract schema 已存在，但 checker 注册表和 runtime 文件外壳未一致 | 阶段推进被治理层阻断，发现时点过晚 | `check_contracts.py`, `delivery.contract.yaml` |
| DORA / 复盘信号压平真实摩擦 | delivery / retrospective | systemic | contract 聚合保留最终数字，未从 artifact 提取内部 HOLD 轨迹 | 后续趋势分析可能低估 review 返工 | `delivery.contract.yaml`, `code-review.md` |

## 交付真实性回查

交付真实性结论保持 delivered。已交付范围与验证证据一致，用户验收路径可执行，残留风险已在验收结果和交付包中披露。

| 回查点 | 结论 | 依据 | 处理 |
|--------|------|------|------|
| 交付范围是否与验证证据一致 | 一致 | T002-T006 均有 build、unit/replay 或 E2E 证据；E2E 24 tests PASS | keep |
| 用户验收路径是否可独立执行 | 可执行，但依赖本地 dev server | `PORT=5174 npm run dev` 与 `http://localhost:5174` 已在交付包写明 | keep |
| 残留风险是否已披露 | 已披露 | final-round red 粒度、MTS 输入单源化、SCN 闭包 WARN、供应商 SLA/auth/quota 均列为非阻断风险 | keep |

## 流程 / 模板 / 检查器改进

本次已当场修复 delivery contract 外壳和 checker 注册；其余项进入后续改进。改进项都指向具体 workflow、hook、lint 或 methodology，不作为泛泛建议。

| 改进 | target_kind | 目标位置 | 优先级 | 证据 | 预期效果 | 归宿 |
|------|-------------|----------|--------|------|----------|------|
| delivery contract 写入时即检查 v1 必填外壳，并让 checker 注册 `delivery_contract` | hook / schema | `.harness/common/skills/stage-gate/scripts/check_contracts.py` | P0 | `delivery__advance_stage.json` | 避免用户验收后 gate 因契约漂移阻断 | applied |
| 派生治理指标校验：artifact 有初审 HOLD 时，复盘指标不得仍只呈现 0 摩擦 | lint_check | DORA 聚合与 contract lint | P0 | `code-review.md` | 让 retrospective 数据保留真实返工 | proposed |
| verify workflow 对 no-webserver Playwright 增加端口/URL preflight | workflow | `.harness/common/skills/verify/workflow.md` | P1 | `verification-report.md` | 把环境前提从失败后解释前移到运行前确认 | proposed |
| review 后补修复成功 rerun 后刷新 toolchain/e2e/project_lint 快照 | hook | gate advance 前置 hook | P1 | `code-review.md`, `delivery__advance_stage.json` | 减少派生状态漂移 | proposed |
| late-stage corrective fix 必须带独立 red/regression 证据 | methodology | `.harness/docs/tdd-planning-contract.md` | P2 | `execution-result.md`, `code-review.md` | 降低因证据粒度不足导致的 PASS_WITH_RISK | proposed |

## 知识沉淀

确定性 promotion 已把 accepted delta spec 合入长期规格，并写入 promotion ledger。主 Agent 额外沉淀了验证 runbook、质量教训和测试模式；project-context 通过 CLI 追加教训，避免直接编辑。

| 知识类型 | 内容摘要 | 目标位置 | 来源 | 置信度 | 归宿 |
|----------|----------|----------|------|--------|------|
| behavior | 本地看盘工作台长期行为规格 | `project-knowledge/specs/local-stock-watch-workbench/spec.md` | delta spec | high | applied |
| operation | 本地验证命令、no-webserver 前置和解释规则 | `project-knowledge/operations/verification/README.md` | verify / delivery | high | applied |
| lesson | delivery gate 契约一致性、review 摩擦、证据粒度和派生状态刷新 | `project-knowledge/lessons/quality/README.md` | code-review / delivery gate | high | applied |
| engineering | fixture-first、真实 reload、投资文案负向断言测试模式 | `project-knowledge/engineering/testing/README.md` | execution / verify | high | applied |
| lesson | 本次三条执行教训追加到项目上下文 | `project-context.md#历史教训` | retrospective | high | applied |

## 跟进行动

后续行动不阻断当前交付，但应作为下一轮 Harness 维护或质量任务处理。涉及框架通用能力的项不混入产品功能 mission。

| 行动 | Owner | 触发条件 | 必要证据 | 阻断等级 | 状态 |
|------|-------|----------|----------|----------|------|
| 为 delivery contract 写入链路增加同源 schema/checker 自检 | Harness 维护者 | 下一次修改 delivery 模板或 checker | contract check + gate run PASS | advisory | applied locally / proposed upstream |
| 为 no-webserver Playwright 增加 verify preflight | Harness 维护者 | 下一次 verify workflow 更新 | 端口不可用时清晰 FAIL 或受控启动 | advisory | proposed |
| 为晚轮 review 修复增加 red/regression 证据要求 | Harness 维护者 | 下一次 TDD workflow 更新 | code-review 不再因 red 粒度不足 PASS_WITH_RISK | advisory | proposed |
| 清理 `SCN-01..SCN-05` 闭包 WARN | 项目维护者 | 下一次文档契约清理 | closure check 无该 WARN | advisory | proposed |
| 将 MTS 输入进一步单源化到 `MarketObservation.indicators` | 项目维护者 | 下一轮架构清理 | architecture-review PASS，回归测试 PASS | advisory | proposed |

## DORA 轻量信号

这些信号只用于趋势观察，不作为单次绩效评价。`review hold count` 同时记录 delivery contract 数字和 artifact-observed 事实，以免压平真实摩擦。

| 信号 | 数值 | 说明 | 证据 |
|------|------|------|------|
| lead time | 2026-05-22 到 2026-06-07 | mission contract 到用户验收交付 | `delivery.contract.yaml` |
| rework count | 1 | review 后存在修复闭环 | `delivery.contract.yaml`, `code-review.md` |
| review hold count | contract=0; artifact-observed=1 | code-review 初审多项 HOLD，最终 PASS_WITH_RISK | `code-review.md` |
| verification failure count | 1 | 首次 E2E 因服务未启动失败，启动 dev server 后 PASS | `verification-report.md` |
| rollback / follow-up count | 0 rollback; 3 advisory follow-ups | 无回滚；三项建议性 follow-up | `delivery.contract.yaml` |

## 更新 project-context.md

project-context 更新必须通过 `harness project-context add-lesson` 完成。本次复盘追加 delivery contract gate、no-webserver verify preflight、late-stage red/regression 三条教训；知识 promotion ledger 位于 `project-knowledge/operations/knowledge-promotions/20260522-stock-watch-system.md`。
