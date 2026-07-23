# 验收结果: 20260522-stock-watch-system

> **面向对象**：用户 / 验收人
> **目的**：用可观察结果证明本次交付是否满足要求，而不是展示内部验证过程。
> **上游**：`mission-contract.md` | `verification-report.md` | 命令输出 | 浏览器端到端结果证据

**日期:** 2026-06-07
**mission-id:** `20260522-stock-watch-system`
**验收状态:** `accepted`

---

## 控制契约

- Contract: `harness-runtime/harness/stages/20260522-stock-watch-system/contracts/acceptance-result.contract.yaml`
- Authority: 外部 YAML 是程序化权威来源；本 Markdown 面向用户验收。

---

## 填写方法

| 步骤 | 填写要求 | 当前状态 |
|------|----------|----------|
| 1 | 交付入口真实可访问，写清环境前提、数据和命令。 | 已填写本地入口与复核命令 |
| 2 | 逐条写明原要求、预期结果、实际结果、复现步骤和结果证据。 | 已覆盖 T002-T006 |
| 3 | 每条通过项必须引用结果证据。 | 已引用 `EV-RESULT-*` |
| 4 | 失败、部分满足、无法验收、接受风险事项必须披露。 | 当前无阻断项，非阻断风险已披露 |
| 5 | 验收决定只能由用户确认后填写。 | 当前保持待验收 |

---

## 交付入口

| 类型 | 入口 | 说明 |
|------|------|------|
| 应用 / 页面 | `http://localhost:5174` | 先执行 `PORT=5174 npm run dev`，然后在浏览器打开该地址。 |
| 命令行复核 | `npm run build`；`node --test harness-runtime/harness/traces/20260522-stock-watch-system/t006-all-tests/*.mjs`；`./node_modules/.bin/playwright test --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list --trace=on` | 分别对应 `CMD-VERIFY-BUILD`、`CMD-VERIFY-UNIT-REPLAY`、`CMD-VERIFY-E2E-RERUN`。 |
| 测试账号 / 数据 | 本地冻结样本 + 浏览器本地持久化 | 不需要外部账号；验收依赖仓内 fixture、localStorage 和回放证据。 |
| 分支 / 提交 | N/A | 当前项目不是 git repo，交付追溯依赖 Harness runtime 产物。 |

---

## 你要验收什么

本次交付的是本地网页形态的多市场股票看盘系统，当前验收范围覆盖 `TASK-STOCK-WATCH-T002` 到 `TASK-STOCK-WATCH-T006`：

- 默认工作台、来源健康、指标切换与可见降级；
- MTS 多周期趋势解释卡与非投资建议边界；
- 分类提醒、触发、确认、归档暂停与 scheduled missed 语义；
- 浏览器重开后的工作台 / 布局恢复；
- 冻结样本、单元 / 回放 / 浏览器门禁的整体验收矩阵。

### 验收前提

| 前提类型 | 具体内容 | 缺失时怎么办 |
|----------|----------|--------------|
| 环境 | 本机已安装依赖，能执行 `npm` 与 `node`；浏览器可访问 `http://localhost:5174`。 | 先执行 `npm install`，再启动 `PORT=5174 npm run dev`。 |
| 配置 | 以本地开发服务为入口，Playwright 复核使用 no-webserver 配置。 | 若未先启动 5174 端口，E2E 会出现 `ERR_CONNECTION_REFUSED`，需先起服务再重跑。 |
| 权限 / 账号 | 不需要云账号、外部 token 或服务端写权限。 | 本次验收不依赖外部登录；生产化接入属于后续范围。 |
| 数据准备 | 使用仓内冻结样本、回放数据和浏览器本地持久化。 | 若本地状态损坏，可清理 localStorage 后重开页面，或重新启动 dev server。 |

---

## 结果验收清单

| 验收场景 / 条件 | 追溯锚点 | 原要求 / 预期结果 | 实际观察结果 | 复现步骤 | 结果证据 | 结论 |
|----------------|----------|------------------|--------------|----------|----------|------|
| 默认工作台与来源健康 | `T002` / `AC-02` | 打开页面后应看到主图、成交量、副图、OHLC、来源健康与指标切换；demo / stale / unavailable 必须可见且不伪装实时成功。 | `CMD-VERIFY-E2E-RERUN` 显示 workbench 默认、指标切换、数据不足、demo fallback、stale、unavailable 全部通过。 | 1. `PORT=5174 npm run dev`；2. 浏览器打开 `http://localhost:5174`；3. 观察默认工作台；4. 复核 E2E。 | `EV-RESULT-T002-WORKBENCH`；`harness-runtime/harness/stages/20260522-stock-watch-system/traces/cmd/cmd-e2e-2026-06-07-05-47-19.json`；`playwright-report/index.html` | 通过 |
| MTS 解释卡与非投资建议边界 | `T003` / `AC-03` | AAPL 的 MTS 卡应展示 `trend_state`、`mts_score`、`score_band`、`signal_type`、`alert_level` 和原因 `TREND_ABOVE_EMA`；文案必须包含“不构成收益承诺”，且不得出现“强买点 / 强卖点 / 胜率”。 | E2E 与 unit/replay 均通过；MTS 卡、非建议文案和 unavailable 降级均已验证。 | 1. `PORT=5174 npm run dev`；2. 浏览器打开 `http://localhost:5174`；3. 选择或保持 `AAPL`；4. 找到“MTS 解释卡”；5. 确认字段名包含上述 5 个结构化字段、原因列表包含 `TREND_ABOVE_EMA`、非建议文案出现“不构成收益承诺”；6. 若出现“强买点 / 强卖点 / 胜率”则判失败。 | `EV-RESULT-T003-MTS`；`CMD-VERIFY-UNIT-REPLAY`；`CMD-VERIFY-E2E-RERUN`；`tests/e2e/workbench/default.spec.ts` | 通过 |
| 分类提醒、触发、确认、归档暂停、scheduled missed | `T004` / `AC-04` | AAPL 价格型提醒阈值 `190` 应触发并可确认；MTS 强信号提醒在归档 Apple 后应显示 `suspended_by_archive` 和“归档暂停”；scheduled missed 只记录历史，不补发触发。 | alerts panel 的创建、确认、归档暂停路径通过；unit/replay 也通过。 | 1. `PORT=5174 npm run dev`；2. 打开 `http://localhost:5174`；3. 在提醒面板选择分类 `price`、等级“观察”、条件输入 `190` 并保存；4. 确认提醒行显示“价格型”“enabled / triggered”“历史：triggered”；5. 点击确认按钮后确认显示“enabled / acknowledged”“历史：acknowledged”；6. 再创建分类 `mts`、等级“强信号”的提醒并归档 Apple，确认提醒行显示 `suspended_by_archive` 与“归档暂停”；7. 若触发后不能确认、归档后仍 active，或 scheduled missed 被补发触发，则判失败。 | `EV-RESULT-T004-ALERTS`；`CMD-VERIFY-UNIT-REPLAY`；`CMD-VERIFY-E2E-RERUN`；`tests/e2e/alerts/panel.spec.ts`；`fixtures/gate/stock-watch-core.json` | 通过 |
| 浏览器重开恢复 | `T005` / `AC-05` | 重开后应恢复 `selectedSymbol=0700.HK`、`0700.HK` 的 dense layout、source mobile tab 和 `MTS 风控` acknowledged 提醒；坏布局应回退默认且页面仍可用。 | restore-layout 的 E2E 路径通过；unit/replay 也通过。 | 1. `PORT=5174 npm run dev`；2. 浏览器打开 `http://localhost:5174`；3. 选择“腾讯控股 / 0700.HK”；4. 切换布局到 dense；5. 在移动宽度下切到 mobile tab 并选 source tab；6. 刷新或重开页面；7. 确认恢复状态显示“已恢复”、选择摘要包含 `0700.HK`、布局控制器显示 `dense`、`MTS 风控` 提醒显示 `acknowledged`；8. 对坏 layout snapshot，确认恢复状态显示“已回退默认布局”且主图仍显示 AAPL；任一恢复点缺失则判失败。 | `EV-RESULT-T005-RESTORE`；`CMD-VERIFY-UNIT-REPLAY`；`CMD-VERIFY-E2E-RERUN`；`tests/e2e/restore-layout/resume.spec.ts`；`fixtures/workspace/t005-restore-trace.json` | 通过 |
| 冻结样本与验收门禁 | `T006` / `AC-01` ~ `AC-05` | 冻结样本、回放与浏览器门禁应覆盖全部核心验收场景。 | gate acceptance matrix 与 unit/replay matrix 均通过；全量 E2E 24 条通过。 | 1. 启动服务；2. 运行 unit/replay matrix；3. 运行 Playwright E2E rerun；4. 复核 gate matrix。 | `EV-RESULT-T006-GATE`；`CMD-VERIFY-BUILD`；`CMD-VERIFY-UNIT-REPLAY`；`CMD-VERIFY-E2E-RERUN` | 通过 |

---

## 关键结果证据

| 证据编号 | 类型 | 路径 / 内容 | 证明什么 |
|---------|------|-------------|----------|
| `CMD-VERIFY-BUILD` | 命令输出 | `npm run build`，exit 0 | TypeScript 与 Vite 构建通过。 |
| `CMD-VERIFY-UNIT-REPLAY` | 命令输出 | `node --test harness-runtime/harness/traces/20260522-stock-watch-system/t006-all-tests/*.mjs`，exit 0 | T002-T006 的 unit / replay 矩阵通过。 |
| `CMD-VERIFY-E2E-RERUN` | 命令输出 | `./node_modules/.bin/playwright test --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list --trace=on`，exit 0 | 全量 Playwright E2E 通过，24 tests / 0 failed。 |
| `EV-RESULT-T002-WORKBENCH` | 结果证据 | `harness-runtime/harness/stages/20260522-stock-watch-system/traces/cmd/cmd-e2e-2026-06-07-05-47-19.json` | 默认工作台、来源健康、降级语义可见。 |
| `EV-RESULT-T003-MTS` | 结果证据 | `harness-runtime/harness/stages/20260522-stock-watch-system/traces/cmd/cmd-e2e-2026-06-07-05-47-19.json` | MTS 结构化字段与非建议边界可见。 |
| `EV-RESULT-T004-ALERTS` | 结果证据 | `harness-runtime/harness/stages/20260522-stock-watch-system/traces/cmd/cmd-e2e-2026-06-07-05-47-19.json` | 提醒创建 / 触发 / 确认 / 暂停语义可见。 |
| `EV-RESULT-T005-RESTORE` | 结果证据 | `harness-runtime/harness/stages/20260522-stock-watch-system/traces/cmd/cmd-e2e-2026-06-07-05-47-19.json` | 浏览器重开恢复和坏布局回退可见。 |
| `EV-RESULT-T006-GATE` | 结果证据 | `harness-runtime/harness/stages/20260522-stock-watch-system/traces/cmd/cmd-e2e-2026-06-07-05-47-19.json` | AC-01 到 AC-05 的冻结样本门禁可见。 |

---

## 未满足 / 无法验收

| 项 | 状态 | 原因 | 用户影响 | 下一步 |
|----|------|------|----------|--------|
| 无阻断项 | 不适用 | 当前 verification 证据支持进入 delivery，未发现阻断性未满足项。 | 不影响当前本地验收。 | 等待用户签收。 |

### 残留风险说明

| 风险 | 来源 | 用户后果 | 是否需要用户接受 | 处理建议 |
|------|------|----------|------------------|----------|
| final-round red artifact 粒度还可以更细 | code-review / verification 非阻断风险 | 不影响当前功能验收，但会降低后续回溯审计的细度。 | 否 | 作为后续质量任务继续补强 red 证据粒度。 |
| MTS 内部指标输入未来需要单源化 | code-review 的架构风险 | 当前用户可见结果已通过，但内部实现仍存在未来漂移风险。 | 否 | 后续把输入进一步收敛到 `MarketObservation.indicators`。 |
| 真实外部行情供应商 SLA / auth / quota 不在本次范围 | mission-contract / verification 未覆盖项 | 当前本地看盘可验收；生产化接入外部供应商时仍需单独验证。 | 否 | 另起供应商接入 / 生产化 mission。 |
| 全 mission 闭包检查存在灰度 WARN | `harness-runtime/harness/traces/20260522-stock-watch-system/delivery-closure-check-20260607.json` | `SCN-01` 到 `SCN-05` 在全阶段 contract 中被引用但未定义；当前为灰度 WARN，不影响本次功能验收。 | 否 | 后续清理旧 contract 的 scenario id 定义或引用。 |

---

## 验收决定

| 字段 | 值 |
|------|----|
| 验收结论 | `approved` |
| 验收时间 | 2026-06-07T14:30:15+08:00 |
| 用户反馈 | 用户确认接受交付 |
| 审批记录 | `harness-runtime/harness/state/approvals.json` |
