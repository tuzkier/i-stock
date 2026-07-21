# T005 Workspace Migration Report

## Scope

- Mission: `20260522-stock-watch-system`
- Task: `TASK-STOCK-WATCH-T005`
- Storage key: `myinvestment.workspace.v2`

## Replay Corpus

Path: `fixtures/workspace/migration-cases.json`

| Case | Expected | Evidence |
|---|---|---|
| `legacy-watchlist-alerts-to-v2` | legacy watchlist and alerts migrate to `WorkspaceSnapshotV2`, alert history preserved | `tests/replay/workspace/migration-replay.spec.ts` |
| `corrupt-json-default-fallback` | corrupt snapshot falls back to default `focus` layout | `tests/replay/workspace/migration-replay.spec.ts` |
| `per-symbol-layout-normalization` | `0700.hk` normalizes to `0700.HK`; AAPL and 0700.HK layouts remain independent | `tests/replay/workspace/migration-replay.spec.ts` |

## Unit Coverage

Path: `tests/unit/workspace/snapshot-migration.spec.ts`

- Legacy key migration into `WorkspaceSnapshotV2`.
- Corrupt snapshot fallback to usable focus layout.
- Per-symbol layouts normalized by symbol.
- Large snapshot with 500 symbols and 2000 alert history entries remains below storage gate.

## Browser Coverage

Path: `tests/e2e/restore-layout/resume.spec.ts`

- Browser reopen restores selected symbol, alerts, acknowledged history and dense layout.
- Broken layout snapshot falls back to focus and keeps chart usable.
- Mobile viewport restores `mobile_tab` with source tab active.

## Verdict

PASS. T005 migration and restore evidence covers unit, replay, browser flow, storage migration assertion, corrupt fallback, large history and per-symbol restore trace.
