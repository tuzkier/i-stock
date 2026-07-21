# Consistency Report

| Check | Status | Evidence |
|---|---|---|
| `spec_vs_prd_drift` | none | `interaction-spec/` 仅表达 PRD 已授权的 8 个 prototype required BUC，没有新增用户目标、BO、AC、权限或范围 |
| `prototype_vs_spec_drift` | none | `visual-interaction/prototype/index.html` 已覆盖 `#buc-001` ~ `#buc-008`，并展示 dense / focus / mobile_tab |
| feedback_not_synced | none | 当前没有用户反馈要求先改原型后不回写 spec 的漂移 |
| `shared_surface_consistency` | pass | `WatchlistPanel` / `WorkbenchShell` / `MtsSignalCard` / `AlertRulePanel` / `SourceHealthPanel` / `LayoutController` / `RestoreStatus` 已形成统一 surface 词汇 |
| `e2e_seed_readiness` | pass | 每个 P0 / P1 BUC 都有稳定 `data-testid` 种子与可访问名称建议 |
| `copy_language` | pass | 默认中文；状态类文案采用“中文（English）”，例外仅限股票代码、市场代码、指标名、MTS、OHLC、MACD、RSI、KDJ、ATR、Yahoo Finance、dense / focus / mobile_tab 等必要术语 |

## Drift Notes

- BUC-09 是验证映射，不属于 prototype required 范围，因此不计入本次交互合同主覆盖。
- 本阶段未发现需要回流 PRD 的产品语义漂移。

## Verification Readiness

- `watchlist-add-input -> symbol-row-*` 已覆盖 BUC-01 的 P0 seed。
- `chart-main-panel -> indicator-tab-* -> chart-secondary-panel` 已覆盖 BUC-02 / BUC-03 的 P0 / P1 seed。
- `mts-signal-card` 与 `data-insufficient-note` 已覆盖 BUC-04 / BUC-06 的降级路径。
- `alert-create-form`, `restore-banner`, `source-status-banner`, `layout-toggle-*` 已覆盖提醒、恢复、来源与布局的关键状态切换。
