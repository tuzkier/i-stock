# T002 Fault Injection Report

## Faults

| ID | Injected Condition | Evidence | Expected Behavior | Result |
|----|--------------------|----------|-------------------|--------|
| `FAULT-T002-001` | Market data fetch throws `network unreachable` with no cached entry. | `tests/unit/source/market-data-source.spec.ts` test `returns unavailable when the network fails without usable cache`. | Envelope status is `unavailable`, retry state is actionable, affected objects include `chart`, `mts`, and `alerts`, and no successful refresh time is fabricated. | PASS |
| `FAULT-T002-002` | Workbench API route returns `sourceHealth.status = unavailable` for `600519.SS`. | `tests/e2e/workbench/default.spec.ts` test `unavailable 来源健康穿透到图表、信号与提醒区域`. | Source panel, chart status/degradation note, signal degradation note, and alert surface remain visible with the unavailable reason. | PASS |
| `FAULT-T002-003` | Short price series has only five bars. | `tests/e2e/workbench/default.spec.ts` test `数据不足时副图局部降级，不展示伪造读数`. | RSI secondary pane shows `unavailable` and explains data insufficiency instead of fabricating indicator values. | PASS |

## Commands

| Command | Result |
|---------|--------|
| `node --test tests/unit/source/market-data-source.spec.ts` | PASS, 7 tests |
| `npx playwright test workbench/default.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | PASS, 6 tests |

## Notes

- These are T002-specific fault injections and do not reuse T001 mutation evidence.
- The implementation still displays fallback price bars for chart continuity when the source is `unavailable`, but source health and degradation text remain explicit and user-visible.
