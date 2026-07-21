# T001 Browser Walkthrough Evidence

Mission: `20260522-stock-watch-system`  
Task: `TASK-STOCK-WATCH-T001`  
Target: `http://localhost:5173`

## Environment

- Dev server: `npm run dev`
- Browser: Google Chrome via Computer Use accessibility tree
- Market data source during walkthrough: demo fallback, because upstream Yahoo requests returned 403

## Recorded Steps

| Step | Action | Observed UI Evidence | Result |
|------|--------|----------------------|--------|
| 1 | Open watch workbench | Active rows show `9988.HK`, `AAPL`, `0700.HK`, `600519.SS`, `005930.KS` with `演示 · <price> · <change>%` summaries | PASS |
| 2 | Archive `9988.HK` while it has enabled `strong-sell` alert | Active list removes `9988.HK`; archived section shows `9988.HK · 港股 · 提醒已暂停` | PASS |
| 3 | Select 港股 and type `9988` | Normalization preview shows `港股 · 9988 → 9988.HK` and `确认后恢复已归档标的`; confirm button enabled | PASS |
| 4 | Click `确认加入` | `9988.HK` returns to active watchlist; archived section no longer contains it | PASS |
| 5 | Inspect alert list after restore | Alert row shows checkbox `9988.HK 触发 strong-sell` with value `1` | PASS |

## Locator Notes

- Active row examples observed in accessibility tree:
  - `9988.HK 9988.HK · 港股 演示 · 315.08 · -0.75%`
  - `Apple AAPL · 美股 演示 · 124.30 · 0.30%`
  - `腾讯控股 0700.HK · 港股 演示 · 300.45 · -0.77%`
  - `贵州茅台 600519.SS · A股 演示 · 43.43 · -1.04%`
  - `Samsung Electronics 005930.KS · 韩股 演示 · 56,259.18 · -0.80%`
- Archive restore preview observed as `归一预览 港股 · 9988 → 9988.HK 确认后恢复已归档标的`.
- Restored alert observed as checkbox `9988.HK 触发 strong-sell, Value: 1`.
