# BUC-09 使用冻结样本验收关键路径

## User Goal

验证者使用冻结样本证明 AC-01 到 AC-05 的关键路径，不依赖 live 行情作为门禁证据。

## Entry / Exit

- Entry: 验证阶段准备四市场标的、歧义输入、指标充足/不足、MTS strong_signal/risk、提醒触发、来源降级、本地恢复样本。
- Exit: 验证报告能把每个样本映射到页面状态、locator 和预期结果。

## ASCII Wireframe

```text
+ 验证样本入口 ------------------------------------------------+
| 四市场样本 | 歧义样本 | 指标不足 | MTS 风控 | 来源降级 | 恢复 |
| 预期路径   | locator  | expected state | result evidence      |
+--------------------------------------------------------------+
```

## Screen Priority

- Primary: fixture 名称、覆盖 BUC/AC、expected state、关键 locator。
- Secondary: 样本来源、可回放步骤、截图或状态断言入口。

## Actions

- 选择一组冻结样本。
- 打开对应 prototype deep link 或后续 E2E path。
- 对照 expected state 运行断言。

## Interaction Rules

- Trigger: 验证者选择样本。
- System response: 页面进入对应数据状态，展示应有的自选、图表、MTS、提醒、来源或恢复反馈。
- UI feedback: 每个样本必须有中文可见状态和稳定 locator。
- Next state: 进入通过、失败或 blocked 证据记录。

## States

- `STATE-LOADING`: 样本加载时显示加载态。
- `STATE-EMPTY`: 样本为空时显示无数据原因。
- `STATE-SUCCESS`: 样本断言通过后记录通过状态。
- `STATE-ERROR`: 样本与预期不符时记录错误和复现路径。
- `STATE-PERMISSION`: 样本不得要求账号、云同步、自动交易或外部通知权限。
- `STATE-DISABLED`: 非本次范围的 live 行情、外部推送和自动交易样本保持禁用。

## Recovery

- fixture 缺失时标记 blocked，不用 live 行情替代门禁证据。
- 样本执行失败时保留 expected vs actual 和截图入口。

## Locator / E2E Obligations

- `fixture-sample-list`
- `fixture-case-row-*`
- `fixture-expected-state`
- `fixture-result-status`
- `watchlist-add-input`
- `source-status-banner`
- `mts-signal-card`
- `alert-rule-row-risk`
- `restore-banner`

P0 E2E seed: 使用冻结样本覆盖 AC-01 到 AC-05，断言关键 locator 和用户可见状态一致。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-09 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-09`
- BO: `BO-001` ~ `BO-008`
- AC: `AC-01`, `AC-02`, `AC-03`, `AC-04`, `AC-05`
- Delta spec: `Fixture-first 验收输入`

## Review Notes

- BUC-09 是验证映射，不新增产品界面目标。
- 原型主入口可以通过现有 BUC-01 到 BUC-08 的 deep link 承载这些样本；后续 verify 阶段再落到真实 E2E。
