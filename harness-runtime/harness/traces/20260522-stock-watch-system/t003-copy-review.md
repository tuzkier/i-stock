# T003 MTS Copy Review

## Scope

- Mission: `20260522-stock-watch-system`
- Task: `TASK-STOCK-WATCH-T003`
- Surfaces: `SURF-MTS`, `SURF-WORKBENCH`

## Reviewed Copy

| Surface | Text Pattern | Verdict |
|---|---|---|
| MTS display label | `强正向技术提醒`, `正向技术观察`, `高风险技术提醒`, `风险技术观察`, `中性观察` | PASS |
| Data insufficient | `数据不足，暂不输出 MTS` | PASS |
| Source degraded | `来源降级，仅保留技术提醒` | PASS |
| Reminder | `MTS 仅用于技术提醒和风险观察，不构成收益承诺或确定性买卖建议。` | PASS |
| ReasonRegistry display | Stable reason codes plus explanation details | PASS |

## Forbidden Terms Scan

Command:

```bash
rg -n "保证收益|胜率|强买点|强卖点" src tests fixtures || true
```

Result:

- Product code: no hits.
- Test/fixture hits: negative assertions and `forbiddenCopy` fixture values only.

## User-visible Evidence

- `tests/e2e/mts/card.spec.ts` asserts structured fields: `trend_state`, `mts_score`, `score_band`, `signal_type`, `alert_level`.
- `tests/e2e/mts/card.spec.ts` asserts source degradation displays `source_degraded` and `alert_level none`.
- `tests/e2e/mts/card.spec.ts` asserts forbidden copy does not appear in `mts-card`.

## Verdict

PASS. T003 copy remains technical-observation language and does not express return promises, win rate, or deterministic buy/sell advice.
