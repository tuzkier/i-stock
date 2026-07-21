# BUC Coverage

| BUC | AC / Rule | BO | Flow | State Coverage | Locator Coverage | Status |
|---|---|---|---|---|---|---|
| BUC-01 | AC-01, AC-05, BR-001, BR-002 | BO-001, BO-002, BO-006 | 新增、归档、恢复 | active, archived, suspended_by_archive | `watchlist-add-*`, `symbol-row-*` | covered |
| BUC-02 | AC-02, BR-004, BR-006, BR-015 | BO-001, BO-003, BO-004, BO-008 | 选择标的进入详情 | ready, partial, unavailable | `chart-main-panel`, `chart-volume-panel`, `chart-secondary-panel` | covered |
| BUC-03 | AC-02, BR-006 | BO-004, BO-008 | 副图切换 | default, customized | `indicator-tab-*` | covered |
| BUC-04 | AC-03, AC-04, BR-008 ~ BR-011, BR-014 | BO-003, BO-004, BO-005 | MTS 解释 | interpretable, data_insufficient, watch, confirmed, strong, risk | `mts-signal-card` | covered |
| BUC-05 | AC-04, AC-05, BR-012, BR-013 | BO-001, BO-005, BO-006 | 创建、触发、停用、确认 | enabled, disabled, triggered, acknowledged | `alert-create-form`, `alert-rule-row-*` | covered |
| BUC-06 | AC-05, BR-002, BR-015 | BO-001, BO-006, BO-008 | 重开恢复 | restored, default layout fallback | `restore-banner` | covered |
| BUC-07 | AC-02, AC-03, AC-04, BR-004, BR-005, BR-016 | BO-007, BO-003, BO-004, BO-005, BO-006 | 来源降级 | formal, demo_fallback, unavailable, data_insufficient | `source-status-banner` | covered |

## Gaps

无阻断缺口。ChartLayout 恢复粒度、MarketDataSource 信息密度、MTS reason code 完整枚举保留给 solution / technical_analysis 定稿。
