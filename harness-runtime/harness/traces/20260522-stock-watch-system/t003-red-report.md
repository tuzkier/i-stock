# T003 Red Report

## Scope

- Mission: `20260522-stock-watch-system`
- Task: `TASK-STOCK-WATCH-T003`
- Atomic task: `T003-A1`
- Evidence type: `red_report`
- Red target: MTS ReasonRegistry must not allow removed or unknown reason codes to pass through as free-text explanations.

## Command

```bash
./node_modules/.bin/esbuild harness-runtime/harness/traces/20260522-stock-watch-system/t003-red/registry-red.spec.ts --bundle --platform=node --format=esm --outfile=harness-runtime/harness/traces/20260522-stock-watch-system/t003-red/registry-red.spec.mjs && node --test harness-runtime/harness/traces/20260522-stock-watch-system/t003-red/registry-red.spec.mjs
```

## Result

- Exit code: `1`
- Tests: `1`
- Pass: `0`
- Fail: `1`

## Failure Signal

```text
AssertionError [ERR_ASSERTION]: Red proof: a broken registry implementation that lets unknown codes pass through would satisfy this assertion
+ actual - expected

+ 'UNKNOWN_CODE'
- 'REMOVED_REASON_ENTRY'
```

## Interpretation

This is an isolated red proof under `harness-runtime/harness/traces/**`, not part of the production test suite. It demonstrates that a broken T003 implementation allowing unknown MTS reason codes to pass through would violate the registry fallback contract. The green counterpart is `EV-T003-REGISTRY-001`, where `resolveMtsReason("REMOVED_REASON_ENTRY")` resolves to `UNKNOWN_CODE`.
