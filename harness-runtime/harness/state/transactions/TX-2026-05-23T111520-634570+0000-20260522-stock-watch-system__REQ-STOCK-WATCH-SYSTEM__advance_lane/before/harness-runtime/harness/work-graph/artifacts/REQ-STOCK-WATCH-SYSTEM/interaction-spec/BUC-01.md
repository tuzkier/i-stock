# BUC-01 管理多市场自选标的

## 用户目标
把 US/HK/CN/KR 标的加入同一本地观察清单，看到市场分组、原始代码、归一代码，并能归档与恢复。

## Entry / Exit
- Entry: 用户打开自选工作台或在任意页面点击“新增自选”。
- Exit: 标的进入 active 分组、进入 archived 分组，或从 archived 恢复 active。

## ASCII Wireframe
```text
[来源状态] Yahoo Finance 正式 / 降级提示
[新增代码 input][市场 selector][加入]
US  AAPL  -> AAPL      [看盘][归档]
HK  0700  -> 0700.HK   [看盘][归档]
归档  9988.HK          [恢复]
```

## Screen Priority
1. 新增输入与市场识别结果。
2. 四市场分组与 active 标的。
3. 归档区和恢复入口。
4. 绑定提醒暂停提示。

Primary-secondary content: primary 是新增/归档/恢复结果；secondary 是排序、来源摘要和历史状态。

## Actions
- `AddWatchSymbol`
- `ArchiveWatchSymbol`
- `RestoreWatchSymbol`
- `SelectWatchSymbol`

## Interaction Rules
- 不可识别市场不得进入 active。
- 同一市场同一归一代码重复添加时恢复或聚合同一观察对象。
- 归档不等于删除；绑定提醒进入 `suspended_by_archive`。

## States / Recovery
- `draft_added -> active -> archived -> active`
- 失败：显示“当前市场无法识别或不在支持范围”。
- 恢复：恢复原 market、rawSymbol、normalizedSymbol 和提醒启停意图。

## E2E Locators
- `watchlist-shell`
- `watchlist-add-input`
- `watchlist-market-select`
- `watchlist-add-button`
- `market-group-us`, `market-group-hk`, `market-group-cn`, `market-group-kr`
- `symbol-row-aapl`, `symbol-row-0700-hk`
- `symbol-restore-button`

## E2E Obligation / Locator Strategy
P0 path uses `watchlist-add-input -> watchlist-add-button -> symbol-row-*`; assertions check market group, raw symbol, normalized symbol, active/archived state.
Restore path clicks `symbol-restore-button` and asserts archived symbol returns to active with prior market identity.

| Scenario | Priority | Locator Strategy |
|---|---|---|
| E2E-BUC-01-S01 新增多市场标的 | P0 | data-testid: `watchlist-add-input`, `watchlist-add-button`, `market-group-hk`, `symbol-row-0700-hk` |
| E2E-BUC-01-S02 恢复归档标的 | P0 | data-testid: `symbol-restore-button`, `symbol-row-aapl`; accessibility role=button |

## Common State Coverage
- STATE-LOADING: 代码识别中显示“正在识别市场”。
- STATE-EMPTY: 无自选时显示新增入口。
- STATE-SUCCESS: 新增/恢复成功后显示 active 分组结果。
- STATE-ERROR: 市场不可识别时不进入 active。
- STATE-PERMISSION: 本地网页无账号权限要求；localStorage 不可用时提示只能临时观察。
- STATE-DISABLED: archived 标的绑定提醒 disabled/suspended_by_archive。

## UX Review Notes
自选列表需要先让用户确认“系统识别成什么代码”，再提供看盘动作；归档操作必须比删除更弱，避免误解为永久清除。

## Traces To
US-01, US-04, AC-01, AC-05, BO-001, BO-002, BO-006, BR-001, BR-002
