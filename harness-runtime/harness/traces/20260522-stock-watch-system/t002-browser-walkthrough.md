# T002 Browser Walkthrough

## Environment

- Server: `PORT=5174 npm run dev`
- Browser: Playwright Chromium
- Screenshot: `harness-runtime/harness/traces/20260522-stock-watch-system/t002-workbench-unavailable.png`

## Walkthrough

| Step | User Action / State | Expected User-Visible Result | Observed |
|------|---------------------|------------------------------|----------|
| 1 | Seed watchlist with `AAPL` and `600519.SS`, then open `/`. | Workbench shell renders with default active symbol and source health surface. | PASS |
| 2 | Select `600519.SS`. | Same workbench context switches to the selected symbol. | PASS |
| 3 | Mock `/api/chart/600519.SS` with `sourceHealth.status = unavailable` and reason `无缓存且上游网络失败`. | Source panel shows `unavailable` and the failure reason. | PASS |
| 4 | Inspect chart panel. | Chart source status and degradation note show `unavailable`; chart remains usable. | PASS |
| 5 | Inspect signal and alert area. | Signal degradation note shows `unavailable`; `买卖提醒` surface remains visible. | PASS |

## Evidence Commands

| Command | Result |
|---------|--------|
| `npx playwright test workbench/default.spec.ts --config harness-runtime/harness/traces/20260522-stock-watch-system/playwright-no-webserver.config.ts --reporter=list` | PASS, 6 tests |
| Playwright screenshot script writing `t002-workbench-unavailable.png` | PASS |
