# BUC-06 查看来源健康并处理降级

## 用户目标

在正式来源不可用、过期或降级时，仍能继续基础观察，同时清楚知道当前来源、降级原因和哪些结论不可解释。

## Entry / Exit

- Entry: 来源刷新失败、覆盖不足、过期或进入演示模式。
- Exit: 来源状态条和受影响对象同步更新。

## ASCII Wireframe

```text
[来源健康] formal / demo_fallback / stale / unavailable
降级原因：Yahoo Finance 本次不可用，当前展示演示 K 线
可继续观察：主图价格结构 / 最近价摘要
当前不可解释：MTS / 强信号提醒 / 部分指标
```

## Screen Priority

1. 来源模式。
2. 降级原因和最后刷新时间。
3. 可继续观察的内容。
4. 不可解释对象。

Primary / secondary content: primary 是来源模式与降级原因；secondary 是受影响对象和仍可观察的内容。

## Actions

- `RefreshObservationContext`
- `EvaluateMtsSignal`
- `ResolveAlertOutcome`

## Interaction Rules

- demo_fallback 不得伪装成正式实时行情。
- 来源降级必须传播到图表、MTS 和提醒。
- stale 表示旧数据可见，但不能伪装成实时刷新成功。
- 重试失败不能把页面变成空白或假成功。

## States

- `formal`
- `demo_fallback`
- `stale`
- `unavailable`
- `data_insufficient`
- `retry_idle / retry_pending / retrying`

## Recovery

- 保留上一次可解释状态与可继续观察的价格结构。
- 重试失败时保留降级说明，并提供再次重试入口。

## Locator / E2E Obligations

- `source-status-banner`
- `source-mode-label`
- `degradation-reason`
- `source-refresh-button`
- `affected-object-list`
- `data-insufficient-note`

P0 E2E seed: 切换到 `demo_fallback`、`stale`、`unavailable`，断言来源文案、MTS 降级和提醒说明同步变化。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-06 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-06`
- BO: `BO-003`, `BO-004`, `BO-005`, `BO-006`, `BO-007`
- AC: `AC-02`, `AC-03`, `AC-04`
- Delta spec: `来源健康与降级穿透`

## Universal State Coverage

- `STATE-LOADING`: 使用骨架屏、加载标记或保留上一次可解释状态。
- `STATE-EMPTY`: 使用空列表、无数据或无可用规则提示，不留白。
- `STATE-SUCCESS`: 用户动作完成后显示确认反馈并进入下一可操作状态。
- `STATE-ERROR`: 归一失败、数据不可用、重试失败或保存失败时显示可恢复错误。
- `STATE-PERMISSION`: 本地网页不需要账号；云同步、自动交易、外部通知等越权动作显示为不可用或范围外。
- `STATE-DISABLED`: 数据不足、标的归档、来源不可用或布局上下文不适用时禁用相关操作并说明原因。

## Review Notes

- 来源状态是一级语义，不是角标。
- “可继续观察”和“当前不可解释”要同时表达。
