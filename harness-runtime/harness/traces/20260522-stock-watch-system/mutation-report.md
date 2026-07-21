# T001 Fault Injection Report

Mission: `20260522-stock-watch-system`  
Task: `TASK-STOCK-WATCH-T001`

## Baseline Green

Command:

```bash
node --test harness-runtime/harness/traces/20260522-stock-watch-system/unit-build/tests/unit/watchlist/*.spec.js
```

Result: PASS, 10 tests / 3 suites / 0 failures.

## Mutation 1: Remove Numeric Ambiguity Gate

Mutation target:

- File: `harness-runtime/harness/traces/20260522-stock-watch-system/mutation-ambiguous/src/domain/market-normalization.js`
- Change: remove the `selectedMarket === "US" && candidates.length > 0` branch that returns `status: "ambiguous"`.

Command:

```bash
node --test harness-runtime/harness/traces/20260522-stock-watch-system/mutation-ambiguous/tests/unit/watchlist/normalization.spec.js
```

Result: FAIL, 1 failing test.

Failure signal:

- Test: `blocks ambiguous numeric input while US is selected`
- Expected: `ambiguous`
- Actual: `invalid`

Conclusion: the normalization tests detect removal of the ambiguity guard.

## Mutation 2: Replace Archive Suspension State With Disabled

Mutation target:

- File: `harness-runtime/harness/traces/20260522-stock-watch-system/mutation-suspend/src/domain/watchlist-state.js`
- Change: replace `activationState: "suspended_by_archive"` with `activationState: "disabled"` and remove the suspended reason.

Command:

```bash
node --test harness-runtime/harness/traces/20260522-stock-watch-system/mutation-suspend/tests/unit/watchlist/archive.spec.js
```

Result: FAIL, 2 failing tests.

Failure signals:

- Test: `suspends enabled alerts when a symbol is archived`; expected `suspended_by_archive`, actual `disabled`.
- Test: `restores archived symbols and alert activation intent together`; expected restored alert `enabled === true`, actual `false`.

Conclusion: the archive tests detect removal of `suspended_by_archive` and restore-intent behavior.
