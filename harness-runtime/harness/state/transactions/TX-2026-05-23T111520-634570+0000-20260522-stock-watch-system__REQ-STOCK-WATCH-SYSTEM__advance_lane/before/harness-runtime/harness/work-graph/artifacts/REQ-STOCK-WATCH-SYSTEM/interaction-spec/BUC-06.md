# BUC-06 重开浏览器恢复本地看盘现场

## 用户目标
在同一浏览器配置中重新打开应用时，恢复自选、提醒和基础看盘上下文，无需登录或重新录入。

## Entry / Exit
- Entry: 应用启动并读取本地存储。
- Exit: 展示恢复结果，进入最近标的或默认看盘布局。

## ASCII Wireframe
```text
[已恢复] 4 个 active 标的 / 2 条提醒 / 最近查看 AAPL
[继续看盘] [查看自选]
```

## Screen Priority
1. 恢复结果是否成功。
2. active/archived 自选数量。
3. 提醒启停状态。
4. 最近标的和默认布局回退。

Primary-secondary content: primary 是恢复结果和继续看盘入口；secondary 是恢复数量、提醒状态和布局回退说明。

## Actions
- `RestoreLocalWorkspace`
- `SelectWatchSymbol`

## Interaction Rules
- 不要求账号登录。
- 至少恢复自选和提醒。
- 布局恢复粒度未定时，必须回到可用默认布局。

## States / Recovery
- `LocalWorkspaceRestored`
- `ChartLayout.default`
- 本地数据不完整时，保留可识别对象并提示部分恢复。

## E2E Locators
- `restore-banner`
- `restore-summary`
- `restore-continue-button`
- `watchlist-shell`

## E2E Obligation / Locator Strategy
P0 path loads app with seeded localStorage and asserts `restore-banner`, `watchlist-shell`, active/archived rows and alert states.

| Scenario | Priority | Locator Strategy |
|---|---|---|
| E2E-BUC-06-S01 重开后恢复本地配置 | P0 | data-testid: `restore-banner`, `restore-summary`, `restore-continue-button`, `watchlist-shell`; aria label for continue button |

## Common State Coverage
- STATE-LOADING: 启动时显示正在恢复本地现场。
- STATE-EMPTY: 本地没有配置时显示新增自选入口。
- STATE-SUCCESS: 恢复完成显示数量摘要。
- STATE-ERROR: localStorage 读取失败时显示部分恢复/临时模式。
- STATE-PERMISSION: 无账号权限要求；localStorage 被禁用时提示限制。
- STATE-DISABLED: 已归档标的相关提醒恢复为 suspended_by_archive。

## UX Review Notes
恢复提示不应阻塞继续看盘；用户要快速理解“恢复了什么”和“没恢复什么”。

## Traces To
US-01, US-04, AC-05, BO-001, BO-006, BO-008, BR-002, BR-015
