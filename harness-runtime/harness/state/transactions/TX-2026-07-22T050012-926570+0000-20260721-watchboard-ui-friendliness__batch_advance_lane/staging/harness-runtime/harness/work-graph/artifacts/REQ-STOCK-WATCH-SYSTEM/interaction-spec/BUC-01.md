# BUC-01 管理多市场自选与归一预览

## 用户目标

把 US / HK / CN / KR 标的加入同一本地观察清单；在写入前先确认市场、原始代码和归一代码，避免歧义输入静默写入 active。

## Entry / Exit

- Entry: 用户打开自选面板，或在任意界面点击“新增自选”。
- Exit: 标的进入 active、进入 archived，或在归档后恢复 active。

## ASCII Wireframe

```text
[恢复状态] 已恢复本地现场 / 触发历史可见
[市场] [原始代码] [归一预览] [加入]
归一预览：HK / 0700 -> 0700.HK

US  AAPL      AAPL        [看盘] [归档]
HK  0700.HK   0700.HK     [看盘] [归档]
CN  600519.SS 600519.SS   [看盘] [归档]
KR  005930.KS 005930.KS   [看盘] [归档]
归档区：600519.SS [恢复]
```

## Screen Priority

1. 市场、原始代码与归一预览。
2. active 自选行与当前选中标的。
3. archived 行与恢复入口。
4. 归档导致的提醒暂停提示。

Primary / secondary content: primary 是“写入前预览”和“active / archived 行”；secondary 是来源状态摘要、排序和触发历史摘要。

## Actions

- `AddWatchSymbol`
- `ArchiveWatchSymbol`
- `RestoreWatchSymbol`
- `SelectWatchSymbol`

## Interaction Rules

- 歧义代码在市场未确认前不得写入 active。
- 同一市场同一归一代码重复添加时，应恢复或聚合同一观察对象，不制造重复标的。
- 归档不等于删除；绑定提醒进入 `suspended_by_archive`。
- 列表行必须同时显示市场、原始代码、归一代码和来源状态摘要。

## States

- `active`
- `archived`
- `suspended_by_archive`
- 归一预览中的 `待确认 / 已归一 / 歧义待确认`

## Recovery

- 恢复时保持原 market、rawSymbol、normalizedSymbol 与提醒启停意图。
- 歧义输入恢复到预览态，不应被写入 active。

## Locator / E2E Obligations

- `watchlist-panel`
- `watchlist-add-input`
- `watchlist-market-select`
- `normalization-preview`
- `preview-market`
- `preview-raw-symbol`
- `preview-normalized-symbol`
- `watchlist-add-button`
- `market-group-us`
- `market-group-hk`
- `market-group-cn`
- `market-group-kr`
- `symbol-row-aapl`
- `symbol-row-0700-hk`
- `symbol-row-600519-ss`
- `symbol-row-005930-ks`
- `symbol-archive-button`
- `symbol-restore-button`

P0 E2E seed: 输入一条数字代码并切换市场，断言归一预览变化；归档后断言 `suspended_by_archive` 与恢复按钮出现。

## E2E Locator Matrix

| Priority | Scenario | Locator strategy |
|---|---|---|
| P0 | E2E-BUC-01 | data-testid + accessible name strategy declared in `Locator / E2E Obligations` |

## Trace to BUC / BO / AC / Delta spec

- BUC: `BUC-01`
- BO: `BO-001`, `BO-002`, `BO-006`
- AC: `AC-01`, `AC-05`
- Delta spec: `多市场自选与归一预览`, `自选列表状态摘要`

## Universal State Coverage

- `STATE-LOADING`: 使用骨架屏、加载标记或保留上一次可解释状态。
- `STATE-EMPTY`: 使用空列表、无数据或无可用规则提示，不留白。
- `STATE-SUCCESS`: 用户动作完成后显示确认反馈并进入下一可操作状态。
- `STATE-ERROR`: 归一失败、数据不可用、重试失败或保存失败时显示可恢复错误。
- `STATE-PERMISSION`: 本地网页不需要账号；云同步、自动交易、外部通知等越权动作显示为不可用或范围外。
- `STATE-DISABLED`: 数据不足、标的归档、来源不可用或布局上下文不适用时禁用相关操作并说明原因。

## Review Notes

- 归档必须比删除更弱，避免用户误解为永久清除。
- 市场与归一代码必须可见，不能只显示输入后的最终代码。
