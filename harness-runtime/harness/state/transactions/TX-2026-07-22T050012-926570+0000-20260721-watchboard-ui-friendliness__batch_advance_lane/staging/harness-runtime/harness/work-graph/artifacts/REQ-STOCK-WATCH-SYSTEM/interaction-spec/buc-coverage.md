# BUC Coverage

| BUC | AC / FR | BO | Flow | State Coverage | Locator Coverage | Status |
|---|---|---|---|---|---|---|
| BUC-01 | AC-01, AC-05, FR-01, FR-02 | BO-001, BO-002, BO-006 | 新增、归档、恢复、归一预览 | `active`, `archived`, `suspended_by_archive` | `watchlist-add-input`, `watchlist-market-select`, `normalization-preview`, `preview-market`, `preview-raw-symbol`, `preview-normalized-symbol`, `symbol-row-*`, `symbol-archive-button`, `symbol-restore-button` | covered |
| BUC-02 | AC-02, FR-03, FR-06, FR-08 | BO-001, BO-003, BO-004, BO-007, BO-008 | 选中标的进入默认工作台 | `formal`, `demo_fallback`, `stale`, `unavailable`, `ready`, `partial` | `workbench-shell`, `chart-main-panel`, `chart-volume-panel`, `chart-secondary-panel`, `chart-ohlc-readout` | covered |
| BUC-03 | AC-02, FR-03 | BO-003, BO-004, BO-008 | 副图切换 | `ready`, `partial`, `unavailable`, `dense`, `focus`, `mobile_tab` | `indicator-tab-*`, `indicator-status-note`, `chart-secondary-panel` | covered |
| BUC-04 | AC-03, AC-04, FR-04 | BO-003, BO-004, BO-005 | MTS 解释 | `interpretable`, `data_insufficient`, `watch`, `confirm`, `strong_signal`, `risk` | `mts-signal-card`, `mts-trend-state`, `mts-score-band`, `mts-signal-type`, `mts-alert-level`, `mts-reasons`, `mts-invalidators` | covered |
| BUC-05 | AC-04, FR-05 | BO-001, BO-003, BO-004, BO-005, BO-006 | 创建、触发、启停、确认 | `enabled`, `disabled`, `suspended_by_archive`, `idle`, `triggered`, `acknowledged` | `alert-create-form`, `alert-taxonomy-select`, `alert-level-select`, `alert-rule-row-*`, `alert-ack-button` | covered |
| BUC-06 | AC-02, AC-03, AC-04, FR-06 | BO-003, BO-004, BO-005, BO-006, BO-007 | 来源降级 | `formal`, `demo_fallback`, `stale`, `unavailable`, `data_insufficient` | `source-status-banner`, `source-mode-label`, `degradation-reason`, `affected-object-list`, `data-insufficient-note` | covered |
| BUC-07 | AC-05, FR-07 | BO-001, BO-006, BO-008 | 重开恢复 | `restored`, `default fallback`, `restored layout` | `restore-banner`, `restore-summary`, `restore-continue-button`, `watchlist-panel` | covered |
| BUC-08 | AC-02, AC-05, FR-08 | BO-008 | 布局切换 | `dense`, `focus`, `mobile_tab` | `layout-toggle-dense`, `layout-toggle-focus`, `layout-toggle-mobile-tab`, `mobile-tab-watchlist`, `mobile-tab-chart`, `mobile-tab-alerts`, `mobile-tab-source` | covered |

## 备注

- 所有 Prototype Required 为 `yes` 的 BUC 已覆盖。
- BUC-09 为验证映射，不属于本合同的 prototype required 范围。
