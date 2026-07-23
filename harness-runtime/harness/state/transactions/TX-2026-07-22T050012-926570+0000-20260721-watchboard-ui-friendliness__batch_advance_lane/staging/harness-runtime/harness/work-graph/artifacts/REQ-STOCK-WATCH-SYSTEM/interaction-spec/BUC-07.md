# BUC-07 重开浏览器恢复本地工作台

## 用户目标

同一浏览器配置重开后，恢复自选、提醒、触发历史和基础布局，不需要登录，也不需要重新录入常用标的。

## Entry / Exit

- Entry: 应用启动并读取本地存储。
- Exit: 展示恢复结果，进入最近标的或默认可用布局。

## ASCII Wireframe

```text
[已恢复本地现场]
active 自选 4 个 / archived 1 个 / 提醒 3 条 / 最近查看 AAPL
[继续看盘]  [查看自选]
```

## Screen Priority

1. 恢复结果是否成功。
2. active / archived 自选数量。
3. 提醒启停和触发状态。
4. 最近标的与布局回退说明。

Primary / secondary content: primary 是恢复结果和继续看盘入口；secondary 是恢复数量、触发历史和布局回退说明。

## Actions

- `RestoreLocalWorkspace`
- `SelectWatchSymbol`

## Interaction Rules

- 不要求账号登录。
- 至少恢复自选和提醒状态。
- 触发历史要一并恢复，不能只恢复规则而丢失状态。
- 布局恢复失败时必须回退到默认可用工作台。

## States

- `restored`
- `partial restore`
- `default fallback`
- `restored layout`

## Recovery

- 本地数据不完整时，保留可识别对象并提示部分恢复。
- 布局损坏时，回退到默认日常看盘，但不删除自选和提醒。

## Locator / E2E Obligations

- `restore-banner`
- `restore-summary`
- `restore-continue-button`
- `watchlist-panel`
- `alerts-panel`

P0 E2E seed: 载入预置 localStorage 后断言恢复横幅、恢复摘要、自选行与提醒状态均可见。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-07 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-07`
- BO: `BO-001`, `BO-006`, `BO-008`
- AC: `AC-05`
- Delta spec: `本地工作台恢复`, `工作台布局模式`

## Universal State Coverage

- `STATE-LOADING`: 使用骨架屏、加载标记或保留上一次可解释状态。
- `STATE-EMPTY`: 使用空列表、无数据或无可用规则提示，不留白。
- `STATE-SUCCESS`: 用户动作完成后显示确认反馈并进入下一可操作状态。
- `STATE-ERROR`: 归一失败、数据不可用、重试失败或保存失败时显示可恢复错误。
- `STATE-PERMISSION`: 本地网页不需要账号；云同步、自动交易、外部通知等越权动作显示为不可用或范围外。
- `STATE-DISABLED`: 数据不足、标的归档、来源不可用或布局上下文不适用时禁用相关操作并说明原因。

## Review Notes

- 恢复提示不能阻塞继续看盘。
- 用户必须能快速理解“恢复了什么”和“没恢复什么”。
