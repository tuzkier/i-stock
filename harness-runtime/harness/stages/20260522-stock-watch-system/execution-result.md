# Execution Result

- Contract: contracts/execution-result.contract.yaml

## Execute Session

| Field | Value |
|-------|-------|
| Skill | execute |
| Carrier | execute |
| Execute Mode | sdd |
| Mission | `20260522-stock-watch-system` |
| Task Node | `TASK-STOCK-WATCH-T002` → batch slice `TASK-STOCK-WATCH-T002` / `T003` / `T004` / `T005` / `T006` |
| Scope Decision | 当前 Mission Slice 已按 upgraded Board Router 规则扩展为同一 execution brief batch；T002-T006 已执行，尚未推进 Gate / Work Graph |

## Dispatch Summary

| Execution Unit | Primary Executors | Supporting Executors | Reviewers | Status |
|----------------|-------------------|----------------------|-----------|--------|
| `T002-A1` | `backend-engineer` | - | pending `spec-reviewer` | DONE_WITH_CONCERNS |
| `T002-A2` | `frontend-engineer` | - | pending `spec-reviewer` | DONE |
| `T003-A1` | `frontend-engineer` | - | pending `spec-reviewer` | DONE |
| `T003-A2` | `frontend-engineer` | - | pending `spec-reviewer` | DONE |
| `T004-A1` | `frontend-engineer` | - | pending `spec-reviewer` | DONE |
| `T004-A2` | `frontend-engineer` | - | pending `spec-reviewer` | DONE |
| `T005-A1` / `T005-A2` | `frontend-engineer` | - | pending `spec-reviewer` | DONE |
| `T006-A1` / `T006-A2` | `test-engineer` | - | pending `spec-reviewer` | DONE |

## Baseline Evidence

| Evidence ID | Decision | Command / Reused Evidence | Result | Covers | Reason |
|-------------|----------|---------------------------|--------|--------|--------|
| `EV-FRAME-T002-001` | frame_check | `harness-runtime/bin/harness frame current --mission 20260522-stock-watch-system --json` | PASS | `TASK-STOCK-WATCH-T002` | 确认当前 Mission Slice 已切回 `development-lane/execute` 且 primary node 为 T002。 |
| `EV-GRAPH-T002-001` | graph_lint | `harness lint graph --json` | PASS | `TASK-STOCK-WATCH-T002` | 切回后工作图结构有效。 |

## TDD Evidence

| Evidence ID | Phase | Type | Command / Path | Exit Code | Signal | Covers |
|-------------|-------|------|----------------|-----------|--------|--------|
| `EV-T002-RED-001` | red | red_report | `harness-runtime/harness/traces/20260522-stock-watch-system/t002-red-report.md` | 1 | spec-reviewer HOLD exposed T002 evidence and contract gaps before corrective pass | T002 required evidence closure |
| `EV-T002-UNIT-001` | green | unit_report | `node --test tests/unit/source/market-data-source.spec.ts` | 0 | 7 tests / 1 suite / 0 fail | T002-A1 来源健康、缓存、fallback、force refresh、unavailable |
| `EV-T002-E2E-001` | e2e | e2e_report | `npx playwright test workbench/default.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | 0 | 6 passed | T002-A2 默认工作台、指标切换、短样本降级、demo fallback、stale、unavailable |
| `EV-T002-BUILD-001` | regression | regression_report | `npm run build` | 0 | `tsc --noEmit` + Vite production build passed | T002-A1, T002-A2 |
| `EV-T002-FAULT-001` | fault-injection | cache_or_fault_injection_report | `harness-runtime/harness/traces/20260522-stock-watch-system/t002-fault-injection-report.md` | 0 | network failure without cache, unavailable UI propagation, and short-series indicator degradation pass | T002-A1, T002-A2 |
| `EV-T002-WALKTHROUGH-001` | walkthrough | screenshot_or_trace | `harness-runtime/harness/traces/20260522-stock-watch-system/t002-browser-walkthrough.md` + `t002-workbench-unavailable.png` | 0 | unavailable workbench path captured with source/chart/signal/alert visibility | T002-A2 |
| `EV-T001-REGRESSION-001` | regression | e2e_report | `npx playwright test watchlist/t001-watchlist-archive-restore.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | 0 | 3 passed | T001 自选归档/恢复、歧义输入、a11y 回归 |
| `EV-T002-RUNNER-001` | toolchain | runner_issue | `npx playwright test tests/e2e/workbench/default.spec.ts --reporter=list` | 1 | `Timed out waiting 60000ms from config.webServer` | 记录原生 Playwright webServer 启动等待问题；同套用例在手动 server 配置下 PASS |
| `EV-T003-RED-001` | red | red_report | `harness-runtime/harness/traces/20260522-stock-watch-system/t003-red-report.md` | 1 | isolated registry red proof fails when unknown MTS code pass-through is asserted | T003-A1 ReasonRegistry fallback and free-text drift boundary |
| `EV-T003-UNIT-001` | green | unit_report | `./node_modules/.bin/esbuild tests/unit/signals/mts.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t003-unit/mts.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t003-unit/mts.spec.mjs` | 0 | 3 tests / 1 suite / 0 fail | T003-A1 MTS 结构化字段、ReasonRegistry、数据不足、来源降级 |
| `EV-T003-BUILD-001` | regression | regression_report | `npm run build` | 0 | `tsc --noEmit` + Vite production build passed | T003-A1, T003-A2 |
| `EV-T003-E2E-001` | e2e | e2e_report | `npx playwright test workbench/default.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | 0 | 7 passed | T002 回归 + T003 MTS 卡、非投资建议、数据不足、来源降级 |
| `EV-T003-REGISTRY-001` | green | registry_report | `./node_modules/.bin/esbuild tests/unit/mts/registry.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t003-unit/registry.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t003-unit/registry.spec.mjs` | 0 | 2 tests / 0 fail | T003-A1 registry key/code validation and unknown-code fallback |
| `EV-T003-REPLAY-001` | green | replay_report | `./node_modules/.bin/esbuild tests/replay/mts/replay.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t003-replay/replay.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t003-replay/replay.spec.mjs` | 0 | 2 tests / 0 fail | T003-A1 deterministic MTS replay, source degraded, data insufficient, registry mutation |
| `EV-T003-MTS-E2E-001` | e2e | e2e_run_report + trace_or_video | `npx playwright test mts/card.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list --trace=on` | 0 | 2 passed; trace zips under `test-results/mts-card-*/trace.zip` | T003-A2 MTS card visible fields, source degraded state, non-advice copy |
| `EV-T003-COPY-001` | review | screenshot_or_copy_review | `harness-runtime/harness/traces/20260522-stock-watch-system/t003-copy-review.md` | 0 | PASS: product copy has no return promise, win-rate, deterministic buy/sell language | T003-A2 copy review |
| `EV-T004-RED-001` | red | red_report | `./node_modules/.bin/esbuild tests/unit/alerts/rule-model.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t004-unit/rule-model.spec.mjs` | 1 | Could not resolve `../../../src/domain/alert.ts` before domain implementation | T004-A1 alert domain missing |
| `EV-T004-UNIT-001` | green | unit_report | `./node_modules/.bin/esbuild tests/unit/alerts/rule-model.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t004-unit/rule-model.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t004-unit/rule-model.spec.mjs` | 0 | 3 tests / 1 suite / 0 fail | T004-A1 taxonomy, activation/trigger state separation, archive/restore/ack |
| `EV-T004-REPLAY-001` | green | state_transition_report | `./node_modules/.bin/esbuild tests/replay/alerts/trigger-flow.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t004-unit/trigger-flow.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t004-unit/trigger-flow.spec.mjs` | 0 | 2 tests / 1 suite / 0 fail | T004-A2 triggered, acknowledged-safe, suspended, missed_while_closed |
| `EV-T004-E2E-001` | e2e | e2e_run_report | `npx playwright test alerts/panel.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | 0 | 2 passed | T004-A2 create flow, ack flow, archive suspend flow |
| `EV-T004-BUILD-001` | regression | regression_report | `npm run build` | 0 | `tsc --noEmit` + Vite production build passed | T004-A1, T004-A2 |
| `EV-T004-WORKBENCH-REGRESSION-001` | regression | e2e_report | `npx playwright test workbench/default.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | 0 | 7 passed | T002/T003 workbench regression after AlertRulePanel extraction |
| `EV-T005-RED-001` | red | red_report | `./node_modules/.bin/esbuild tests/unit/workspace/snapshot-migration.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t005-unit/snapshot-migration.spec.mjs` | 1 | Could not resolve `../../../src/domain/workspace` before workspace snapshot domain implementation | T005-A1 workspace snapshot missing |
| `EV-T005-UNIT-001` | green | unit_report | `./node_modules/.bin/esbuild tests/unit/workspace/snapshot-migration.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t005-unit/snapshot-migration.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t005-unit/snapshot-migration.spec.mjs` | 0 | 4 tests / 0 fail | T005-A1 legacy migration, corrupt fallback, per-symbol layout, large history |
| `EV-T005-BUILD-001` | regression | regression_report | `npm run build` | 0 | `tsc --noEmit` + Vite production build passed | T005-A1, T005-A2 |
| `EV-T005-E2E-001` | e2e | e2e_run_report | `npx playwright test restore-layout/resume.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | 0 | 3 passed | T005-A2 browser reopen restore, fallback focus, mobile_tab restore |
| `EV-T005-TRACE-001` | trace | screenshot_or_restore_trace | `fixtures/workspace/t005-restore-trace.json` | 0 | Frozen restore trace records selected symbol, per-symbol dense layout, corrupt fallback, mobile source tab | T005-A2 restore trace evidence |
| `EV-T005-REPLAY-001` | green | migration_report + replay_report | `./node_modules/.bin/esbuild tests/replay/workspace/migration-replay.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t005-replay/migration-replay.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t005-replay/migration-replay.spec.mjs` | 0 | 1 test / 0 fail; report at `harness-runtime/harness/traces/20260522-stock-watch-system/t005-migration-report.md` | T005-A1 legacy migration, corrupt fallback, normalized per-symbol layout replay |
| `EV-T005-ALERT-REGRESSION-001` | regression | e2e_report | `npx playwright test alerts/panel.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | 0 | 2 passed | T004 alert regression after workspace snapshot persistence |
| `EV-T005-WORKBENCH-REGRESSION-001` | regression | e2e_report | `npx playwright test workbench/default.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | 0 | 7 passed | T002/T003 workbench regression after controlled layout extraction |
| `EV-T006-RED-001` | red | red_report | `./node_modules/.bin/esbuild tests/replay/gate/fixture-corpus.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t006-replay/fixture-corpus.spec.mjs` | 1 | Could not resolve `fixtures/gate/stock-watch-core.json` / `.sha256.json` before fixture corpus existed | T006-A1 fixture-first gate missing |
| `EV-T006-REPLAY-001` | green | fixture_checksum_or_replay_log | `./node_modules/.bin/esbuild tests/replay/gate/fixture-corpus.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t006-replay/fixture-corpus.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t006-replay/fixture-corpus.spec.mjs` | 0 | 5 tests / 0 fail; checksum `d736698feeab15da6df2685c2240f409cd87f3eb9bf4ba62c35b7c672f031471` | T006-A1 fixture corpus, AC matrix, deterministic replay |
| `EV-T006-UNIT-REPLAY-MATRIX-001` | regression | unit_report + replay_report | `for file in tests/unit/**/*.spec.ts tests/replay/**/*.spec.ts; esbuild + node --test into harness-runtime/harness/traces/20260522-stock-watch-system/t006-all-tests/*.mjs` | 0 | 43 tests / 0 fail | T001-T006 unit and replay gate matrix |
| `EV-T006-E2E-GATE-001` | green | e2e_run_report + trace_or_video | `npx playwright test gate/acceptance-matrix.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list --trace=on` | 0 | 5 passed; gate trace zips under `test-results/gate-acceptance-matrix-*/trace.zip` | AC-01~AC-05 fixture-first browser gate |
| `EV-T006-E2E-REGRESSION-001` | regression | e2e_run_report + trace_or_video | `npx playwright test --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list --trace=on` | 0 | 22 passed | All current E2E surfaces after T006 and reviewer fixes |
| `EV-T006-BUILD-001` | regression | regression_report | `npm run build` | 0 | `tsc --noEmit` + Vite production build passed | T001-T006 final build gate |
| `EV-T006-SAFETY-001` | safety | forbidden_terms_scan | `rg -n "自动下单|系统通知|后台 worker|保证收益|胜率|强买点|强卖点" src tests fixtures || true` | 0 | Product code has no hits; matches are negative assertions or fixture forbidden terms | Non-advice and no notification/worker boundary |

## Execution Results

| Role | Status | Changed Files | Evidence |
|------|--------|---------------|----------|
| backend-engineer | DONE_WITH_CONCERNS | `server/index.js`, `src/domain/market-data-source.ts`, `src/types.ts`, `tests/unit/source/market-data-source.spec.ts` | `EV-T002-UNIT-001`, `EV-T002-BUILD-001`, `EV-T002-FAULT-001` |
| frontend-engineer | DONE | `src/features/chart/ChartSurface.tsx`, `src/features/source/SourceHealthPanel.tsx`, `src/features/workbench/WorkbenchShell.tsx`, `src/App.tsx`, `tests/e2e/workbench/default.spec.ts` | `EV-T002-E2E-001`, `EV-T002-BUILD-001`, `EV-T002-FAULT-001`, `EV-T002-WALKTHROUGH-001`, `EV-T001-REGRESSION-001` |
| frontend-engineer | DONE | `src/domain/mts-registry.ts`, `src/lib/signals.ts`, `src/App.tsx`, `src/types.ts`, `fixtures/mts/replay-corpus.json`, `tests/unit/mts/registry.spec.ts`, `tests/replay/mts/replay.spec.ts`, `tests/e2e/mts/card.spec.ts`, `harness-runtime/harness/traces/20260522-stock-watch-system/t003-copy-review.md`, `harness-runtime/harness/traces/20260522-stock-watch-system/t003-red-report.md` | `EV-T003-RED-001`, `EV-T003-UNIT-001`, `EV-T003-REGISTRY-001`, `EV-T003-REPLAY-001`, `EV-T003-MTS-E2E-001`, `EV-T003-COPY-001`, `EV-T003-BUILD-001`, `EV-T003-E2E-001` |
| frontend-engineer | DONE | `src/domain/alert.ts`, `src/lib/alerts.ts`, `src/types.ts`, `src/features/alerts/AlertRulePanel.tsx`, `src/App.tsx`, `tests/unit/alerts/rule-model.spec.ts`, `tests/replay/alerts/trigger-flow.spec.ts`, `tests/e2e/alerts/panel.spec.ts` | `EV-T004-UNIT-001`, `EV-T004-REPLAY-001`, `EV-T004-E2E-001`, `EV-T004-BUILD-001`, `EV-T004-WORKBENCH-REGRESSION-001` |
| frontend-engineer | DONE | `src/domain/workspace.ts`, `src/lib/storage.ts`, `src/types.ts`, `src/features/layout/LayoutController.tsx`, `src/features/restore/RestoreStatus.tsx`, `src/App.tsx`, `tests/unit/workspace/snapshot-migration.spec.ts`, `tests/replay/workspace/migration-replay.spec.ts`, `tests/e2e/restore-layout/resume.spec.ts`, `fixtures/workspace/t005-restore-trace.json`, `fixtures/workspace/migration-cases.json`, `harness-runtime/harness/traces/20260522-stock-watch-system/t005-migration-report.md` | `EV-T005-RED-001`, `EV-T005-UNIT-001`, `EV-T005-REPLAY-001`, `EV-T005-BUILD-001`, `EV-T005-E2E-001`, `EV-T005-TRACE-001`, `EV-T005-ALERT-REGRESSION-001`, `EV-T005-WORKBENCH-REGRESSION-001` |
| test-engineer | DONE | `fixtures/gate/stock-watch-core.json`, `fixtures/gate/stock-watch-core.sha256.json`, `tests/replay/gate/fixture-loader.ts`, `tests/replay/gate/fixture-corpus.spec.ts`, `tests/e2e/gate/acceptance-matrix.spec.ts` | `EV-T006-RED-001`, `EV-T006-REPLAY-001`, `EV-T006-UNIT-REPLAY-MATRIX-001`, `EV-T006-E2E-GATE-001`, `EV-T006-E2E-REGRESSION-001`, `EV-T006-BUILD-001`, `EV-T006-SAFETY-001` |

## Implementation Notes

- `T002-A1`: 新增 `createMarketDataSource`，将 `/api/chart/:symbol` 返回结构升级为 `MarketDataEnvelope`，包含 `priceSeries`、`sourceHealth`、`cacheState`、`retryState`、降级原因与刷新时间；保留旧 `bars` 字段以兼容 T001 既有路径。
- `T002-A1`: 来源状态覆盖 `formal`、`demo_fallback`、`stale`、`unavailable`，支持 60 秒内存缓存、`forceRefresh` 绕过缓存、上游失败后的 stale fallback 与 demo fallback。
- `T002-A2`: 新增 `WorkbenchShell`、`ChartSurface`、`SourceHealthPanel`，默认工作台展示主图、成交量 pane、副图 pane、OHLC、来源健康、布局切换与刷新入口。
- `T002-A2`: 副图支持 MACD / RSI / KDJ / ATR 切换；短样本指标显示 `partial` / `unavailable`，不伪造读数。
- `T002-A2`: 来源降级语义穿透到图表、来源面板、信号与提醒区域；刷新失败时保留当前有效 payload，页面不被打空。
- `T002-A2`: `unavailable` 已通过网络失败单元测试和 workbench E2E 覆盖，证明无缓存失败时 source/chart/signal/alert surface 都保留可解释状态。
- 回归修复：`ChartSurface`、`WorkbenchShell`、`App.tsx` 对旧 `ChartPayload` fixture 中缺失的 `priceSeries` / `sourceHealth` 做兼容，保证 T001 旧 E2E 仍可渲染并通过。
- 合同修复：`SourceHealthStatus` 保持四态 `formal | demo_fallback | stale | unavailable`；`not_loaded` 只保留为 UI-only `SourceStatus`。
- `T003-A1`: `buildSignal` 输出 `MtsExplanation`，覆盖 `trend_state`、`mts_score`、`score_band`、`signal_type`、`alert_level`、`reason_codes`、`invalidators` 和 `technicalReminder`。
- `T003-A1`: 新增 `MtsReasonRegistry` 固定 reason code；未知或缺失解释不得替代为自由文本。
- `T003-A1` reviewer 修复：将 MTS registry 抽到 `src/domain/mts-registry.ts`，新增 registry validation 与 unknown-code fallback 单测，并补充 `fixtures/mts/replay-corpus.json` + `tests/replay/mts/replay.spec.ts`。
- `T003-A1`: 数据不足时输出 `data_insufficient`，`mts_score=null`，`alert_level=none`；来源非 `formal` 时输出 `source_degraded`，不输出有效提醒等级。
- `T003-A2`: 右侧信号面板改为 MTS 解释卡和 `ReasonRegistry` 展示，移除“强买点 / 强卖点 / 交易线”作为主文案，提醒入口改为“正向技术提醒 / 风险技术提醒”。
- `T003-A2` reviewer 修复：新增 `tests/e2e/mts/card.spec.ts` 与 `t003-copy-review.md`，T003 UI/copy 证据不再依赖 workbench 回归测试作为主证据。
- `T004-A1`: 新增 `AlertRule` taxonomy、level、condition、`activationState` / `triggerState` 双状态机、`history[]`、`acknowledgedAt`、scheduled `daily_time` 条件和恢复意图。
- `T004-A1`: 新增 `src/domain/alert.ts` 与 `src/lib/alerts.ts`，集中处理创建、校验、归档暂停、恢复、确认和本地触发评估；未引入外部通知、系统通知、后台 worker 或后端 route。
- `T004-A2`: 新增 `AlertRulePanel`，展示 taxonomy、等级、启停、触发状态、触发时间、触发原因、历史和确认动作；规则列表显示全部本地提醒，保证归档暂停状态可见。
- `T004-A2`: App 在当前 observation 更新时调用 `evaluateAlertRules`，只对 enabled 且 idle 的规则触发；acknowledged 规则不会在同一命中条件下立即重触发。
- `T005-A1`: 新增 `WorkspaceSnapshotV2` domain，集中处理 `myinvestment.workspace.v2`、旧 `watchlist` / `alerts` key 迁移、恢复元数据、normalized symbol layout key、坏 snapshot 回退和 storage gate 大小检查。
- `T005-A1` reviewer 修复：新增 `fixtures/workspace/migration-cases.json`、`tests/replay/workspace/migration-replay.spec.ts` 与 `t005-migration-report.md`，补齐 replay 能力和 migration_report。
- `T005-A1`: `src/lib/storage.ts` 增加 workspace 读写桥接，保留旧 `readWatchlist` / `readAlerts` 兼容入口；App 启动统一从 workspace snapshot 恢复 watchlist、alerts、selectedSymbol、range 与 layout。
- `T005-A2`: 新增受控 `LayoutController` 和 `RestoreStatus`，把 dense / focus / mobile_tab、活动 mobile tab、per-symbol layout 和默认 focus fallback 接为可见 UI 行为；未修改不在 T005 写入边界内的 `WorkbenchShell`。
- `T005-A2`: App 将 layoutBySymbol 与 globalLayoutFallback 写回 workspace snapshot；坏布局只丢弃对应 layout key 并显示恢复横幅，不阻断图表、来源健康或提醒区域。
- `T005` 兼容修复：`writeWorkspaceSnapshot` 在写入 `WorkspaceSnapshotV2` 的同时同步写回 legacy `myinvestment.watchlist` / `myinvestment.alerts`，避免旧测试与旧观察路径读到过期状态。
- `T006-A1`: 新增 `fixtures/gate/stock-watch-core.json` 与 checksum sidecar，覆盖四市场、歧义输入、formal / demo_fallback / stale / unavailable / insufficient 来源、MTS 非建议边界、提醒触发/归档、恢复和坏布局。
- `T006-A1`: 新增 fixture loader 与 replay spec，使用稳定序列化 SHA-256 锁定 fixture corpus，并验证 AC-01~AC-05 映射、无 live Yahoo URL、deterministic envelope replay。
- `T006-A2`: 新增 `tests/e2e/gate/acceptance-matrix.spec.ts`，用同一份 fixture seed 覆盖 AC-01~AC-05 浏览器门禁；最终全量 E2E 20 条 PASS 且 `--trace=on` 生成 trace 证据。

## Scenario Coverage

| Scenario | Expected | Actual |
|----------|----------|--------|
| 默认看盘工作台 | 主图、成交量、副图、OHLC 与来源健康可见 | `tests/e2e/workbench/default.spec.ts` 第 1 条 PASS |
| 副图指标切换 | MACD / RSI / KDJ / ATR 切换保持同一标的上下文 | 第 2 条 PASS |
| 数据不足 | 指标局部降级为 unavailable，不展示伪造读数 | 第 3 条 PASS |
| demo fallback | 来源状态和原因穿透到图表、信号、提醒区域 | 第 4 条 PASS |
| stale retry | stale 不伪装实时成功，重试失败后保留可解释状态 | 第 5 条 PASS |
| unavailable | 无缓存失败时来源状态和原因穿透到图表、信号、提醒区域 | 第 6 条 PASS |
| T001 回归 | 自选归档/恢复、歧义阻止、a11y 无严重违规 | 3 条 T001 E2E PASS |
| 输出完整 MTS 卡 | 展示 trend_state、mts_score、score_band、signal_type、alert_level、reason_codes、invalidators | `tests/unit/signals/mts.spec.ts` 第 1 条 PASS；`tests/e2e/workbench/default.spec.ts` MTS 用例 PASS |
| MTS 不表达投资建议 | 文案使用技术提醒口径，不展示收益承诺、胜率或确定性买卖建议 | MTS E2E 用例 PASS；首次 E2E 曾捕获“胜率”否定句残留，已修复并重跑 PASS |
| 数据不足时不输出伪 MTS | data_insufficient / alert_level none / DATA_INSUFFICIENT 可见 | unit 第 2 条 PASS；workbench 短样本 E2E PASS |
| 来源降级时 MTS 降级 | source_degraded / alert_level none / SOURCE_DEGRADED 可见 | unit 第 3 条 PASS；unavailable E2E PASS |
| 创建分类提醒 | 保存 taxonomy、condition、activationState 和目标标的 | `tests/unit/alerts/rule-model.spec.ts` 第 1/2 条 PASS；`tests/e2e/alerts/panel.spec.ts` 第 1 条 PASS |
| 提醒触发后可确认 | enabled 规则命中后进入 triggered，页面显示触发时间/原因/确认动作，确认后进入 acknowledged | `tests/replay/alerts/trigger-flow.spec.ts` PASS；alerts E2E 第 1 条 PASS |
| 归档暂停提醒 | archived symbol 的绑定提醒进入 suspended_by_archive 且保留 restoreIntent/history | unit 第 3 条 PASS；alerts E2E 第 2 条 PASS |
| scheduled miss | 浏览器关闭期间不补发外部通知，只在本地历史记录 missed_while_closed | replay 第 1 条 PASS |
| 浏览器重开恢复工作台 | 恢复 selectedSymbol、alerts/history 与 per-symbol dense layout | `tests/e2e/restore-layout/resume.spec.ts` 第 1 条 PASS；`fixtures/workspace/t005-restore-trace.json` |
| 布局恢复失败回退默认 | 坏 layout snapshot 回退 focus，页面仍可用 | restore-layout E2E 第 2 条 PASS |
| 桌面 dense/focus 切换 | dense/focus 作为受控布局状态并按 symbol 写回 snapshot | `tests/unit/workspace/snapshot-migration.spec.ts` per-symbol layout PASS；restore-layout E2E 第 1/2 条 PASS |
| 移动端 tab 工作台 | mobile_tab 与活动 source tab 可按 symbol 恢复 | restore-layout E2E 第 3 条 PASS |
| 使用冻结样本验收核心路径 | AC-01~AC-05 均由 fixture corpus 和 browser gate 覆盖，live 行情不作为门禁 | `tests/replay/gate/fixture-corpus.spec.ts` 5 条 PASS；`tests/e2e/gate/acceptance-matrix.spec.ts` 5 条 PASS；全量 E2E 20 条 PASS |

## Reviewer Status

| Reviewer | Verdict | Reviewed Unit | Blocking Gaps |
|----------|---------|---------------|---------------|
| spec-reviewer | PASS | `TASK-STOCK-WATCH-T002` | 无剩余阻断缺口；`BG-01`/`BG-02`/`BG-03` 已闭合 |
| spec-reviewer | PASS | `TASK-STOCK-WATCH-T003` / `TASK-STOCK-WATCH-T004` / `TASK-STOCK-WATCH-T005` | Planck 复审确认 `BG-01`/`BG-02`/`BG-03` 均已闭合；`EV-T003-RED-001`、`EV-T003-REGISTRY-001`、`EV-T003-REPLAY-001`、`EV-T003-MTS-E2E-001`、`EV-T003-COPY-001`、`EV-T005-REPLAY-001` 构成补证据闭环 |
| spec-reviewer | PASS | `TASK-STOCK-WATCH-T006` | T006 验证矩阵、fixture-first gate、全量 E2E 和 safety scan 均已登记；execute reviewer barrier 可退出 |

## Residual Findings

- `server/index.js` 在开发运行时直接 import `../src/domain/market-data-source.ts`，依赖当前 Node 的 Type Stripping 能力；本地单元、构建和 dev server 验证通过，但这是运行时前提，应在 code-review 阶段确认部署 Node 版本策略。
- 未补充 stale 超过硬截止时间和 `cacheEnabled=false` 的额外单元用例；当前 T002 授权场景已覆盖 stale fallback、cache hit、force refresh、provider/range cache key、无缓存 network failure unavailable。
- 项目原生 Playwright `webServer` 配置在本轮仍出现 60 秒启动等待超时；为避免该 runner 问题阻断业务验证，T002 与 T001 E2E 均使用手动 dev server + no-webserver config 完成验证。
- 当前 batch slice 已包含 T002-T006，执行侧已全部完成；尚未运行 spec-reviewer 只读 recheck，因此未推进 Work Graph 到 code-review。
- `node --test tests/unit/signals/mts.spec.ts` 直接跑 TS 时会因源码 runtime import `./indicators` 的 extensionless specifier 失败；本轮采用仓内已有 `esbuild` 先 bundle 到 `harness-runtime/harness/traces/20260522-stock-watch-system/t003-unit/mts.spec.mjs` 再运行 Node test，命令已记录为 `EV-T003-UNIT-001`。
- T004 的 Node unit/replay 同样采用 esbuild bundle 后执行，避免 Type Stripping 对 extensionless import 的运行时限制。
