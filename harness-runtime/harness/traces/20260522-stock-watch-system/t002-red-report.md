# T002 Red Report

## Scope

- Task: `TASK-STOCK-WATCH-T002`
- Stage: `development-lane/execute`
- Review trigger: `spec-reviewer` verdict `HOLD`
- Purpose: record T002-specific red evidence before the corrective pass.

## Red Signals

| ID | Source | Failure / Gap | Expected Fix |
|----|--------|---------------|--------------|
| `RED-T002-001` | `spec-reviewer` `BG-01` | T002 required evidence was not closed: no T002-specific red report, fault-injection evidence, or screenshot/trace evidence. Existing mutation/browser artifacts were T001-only. | Add T002-specific red, fault-injection, and walkthrough evidence. |
| `RED-T002-002` | `spec-reviewer` `BG-02` | `unavailable` source health was implemented but not proven by unit or E2E evidence. | Add unit coverage for network failure without cache and E2E coverage for unavailable propagation to source panel, chart, signal, and alert area. |
| `RED-T002-003` | `spec-reviewer` `BG-03` | `SourceHealthStatus` was widened to include `not_loaded`, drifting beyond the frozen four-state source health contract. | Keep `SourceHealthStatus` to `formal | demo_fallback | stale | unavailable`; make `not_loaded` UI-only via `SourceStatus`. |

## Corrective Commands

| Command | Result |
|---------|--------|
| `node --test tests/unit/source/market-data-source.spec.ts` | PASS, 7 tests |
| `npm run build` | PASS |
| `npx playwright test workbench/default.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | PASS, 6 tests |
| `npx playwright test watchlist/t001-watchlist-archive-restore.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | PASS, 3 tests |

## Fix Summary

- `src/types.ts`: split `SourceHealthStatus` from UI-only `SourceStatus`.
- `tests/unit/source/market-data-source.spec.ts`: added network failure without usable cache assertion for `unavailable`.
- `tests/e2e/workbench/default.spec.ts`: added unavailable propagation scenario across source panel, chart, signal, and alert area.
