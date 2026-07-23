import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;
const SYMBOL = "0700.HK";
// 不写 Playwright outputDir（会被后续 suite 清空）；落 harness evidence 目录
const HIERARCHY_SHOT = path.join(
  "harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence",
  "pt03-trade-signal-hierarchy.png"
);

function bars(count = 220) {
  return Array.from({ length: count }, (_, index) => {
    const close = 300 + Math.sin(index / 9) * 25 + index * 0.05;
    return {
      time: nowSeconds - (count - index - 1) * 86_400,
      open: close - 0.8,
      high: close + 2,
      low: close - 2,
      close,
      volume: 2_000_000 + index * 5_000
    };
  });
}

function envelope(status: "formal" | "unavailable" = "formal") {
  const seriesBars = bars();
  const latest = seriesBars.at(-1);
  const previous = seriesBars.at(-2);
  const degraded = status !== "formal";
  return {
    symbol: SYMBOL,
    range: "6mo",
    interval: "1d",
    meta: {
      shortName: "Tencent",
      previousClose: previous?.close,
      regularMarketPrice: latest?.close,
      regularMarketTime: latest?.time
    },
    priceSeries: {
      symbol: SYMBOL,
      range: "6mo",
      interval: "1d",
      bars: seriesBars,
      latestOhlc: latest,
      latestPrice: latest?.close,
      changeSummary:
        latest && previous
          ? { absolute: latest.close - previous.close, percent: ((latest.close - previous.close) / previous.close) * 100 }
          : undefined
    },
    bars: seriesBars,
    servedAt: nowMs,
    cacheState: "miss",
    sourceHealth: {
      status,
      affectedObjects: degraded ? ["chart", "mts", "alerts"] : [],
      retryState: { attempt: degraded ? 1 : 0, canRetry: degraded, reason: degraded ? "fixture degraded" : undefined },
      lastRefreshedAt: degraded ? undefined : nowMs,
      degradationReason: degraded ? "fixture degraded" : undefined
    },
    sourceName: "Fixture",
    degradationReason: degraded ? "fixture degraded" : undefined,
    retryState: { attempt: degraded ? 1 : 0, canRetry: degraded, reason: degraded ? "fixture degraded" : undefined }
  };
}

async function seed(page: Page) {
  await page.addInitScript((symbol) => {
    const item = { id: symbol, symbol, name: "腾讯控股", market: "HK", status: "active" };
    window.localStorage.setItem("myinvestment.watchlist", JSON.stringify([item]));
    window.localStorage.setItem("myinvestment.alerts", JSON.stringify([]));
    window.localStorage.setItem(
      "myinvestment.workspace.v2",
      JSON.stringify({
        version: 2,
        watchlist: [item],
        alerts: [],
        selectedSymbol: symbol,
        range: "6mo",
        selectedMobileTab: "chart",
        layoutBySymbol: {},
        globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" },
        restoreMetadata: { status: "restored", migratedFromLegacy: false, snapshotBytes: 0 },
        updatedAt: Date.now()
      })
    );
  }, SYMBOL);
}

test("AT-0301: 默认关键数字、明细折叠、nonAdvice 常驻", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("formal")) });
  });

  await page.goto("/");

  const card = page.getByTestId("trade-signal-card");
  await expect(card).toBeVisible();
  await expect(page.getByTestId("trade-signal-stance")).toBeVisible();
  await expect(page.getByTestId("trade-signal-non-advice")).toBeVisible();

  // BG-03：默认关键数字（胜率 / 策略累计）可见
  const kpi = page.getByTestId("trade-backtest-summary");
  await expect(kpi).toBeVisible();
  await expect(kpi).toContainText("胜率");
  await expect(kpi).toContainText("策略累计");
  await expect(kpi).toHaveClass(/trade-signal-kpi/);

  // 默认不应铺开卖出侧/买入侧/反T 明细标题
  await expect(page.getByTestId("trade-signal-details")).toHaveCount(0);
  await expect(card).not.toContainText("卖出侧");
  await expect(card).not.toContainText("买入侧");

  // 折叠态 nonAdvice 仍可见（NEG-05 / DEC-S08）
  await expect(page.getByTestId("trade-signal-non-advice")).toBeVisible();

  await page.getByTestId("trade-signal-details-toggle").click();
  const details = page.getByTestId("trade-signal-details");
  await expect(details).toBeVisible();
  await expect(details).toContainText("卖出侧");
  await expect(details).toHaveClass(/secondary/);
  await expect(page.getByTestId("trade-signal-non-advice")).toBeVisible();

  // BG-01：主/次层级差 — KPI 字号/字重高于次级明细
  const kpiSize = Number.parseFloat(await kpi.evaluate((el) => getComputedStyle(el).fontSize));
  const detailsSize = Number.parseFloat(await details.evaluate((el) => getComputedStyle(el).fontSize));
  const kpiWeight = Number.parseInt(await kpi.evaluate((el) => getComputedStyle(el).fontWeight), 10);
  const detailsWeight = Number.parseInt(await details.evaluate((el) => getComputedStyle(el).fontWeight), 10);
  expect(kpiSize).toBeGreaterThan(detailsSize);
  expect(kpiWeight).toBeGreaterThan(detailsWeight);

  // BG-02：正式位无 level-secondary；ATR/观察位带 level-secondary
  const levels = page.getByTestId("trade-signal-levels");
  const atrRow = levels.locator(".level-secondary").filter({ hasText: "ATR20" });
  await expect(atrRow).toHaveCount(1);
  const formalRows = levels.locator(".level-grid > div:not(.level-secondary)");
  await expect(formalRows.first()).toBeVisible();
  await expect(formalRows.first()).not.toHaveClass(/level-secondary/);

  await card.screenshot({ path: HIERARCHY_SHOT });
});

test("AT-0302: 来源降级非 ready 人话化且无回测块", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("unavailable")) });
  });

  await page.goto("/");

  const card = page.getByTestId("trade-signal-card");
  await expect(card).toBeVisible();
  const topline = card.locator(".signal-topline");
  await expect(topline).not.toContainText("source_degraded");
  await expect(topline).not.toContainText("not_target_symbol");
  await expect(topline).not.toContainText("data_insufficient");
  await expect(page.getByTestId("trade-signal-status")).toHaveText("来源不可用");
  await expect(page.getByTestId("trade-backtest-summary")).toHaveCount(0);
  await expect(page.getByTestId("trade-signal-details-toggle")).toHaveCount(0);
  await expect(page.getByTestId("trade-signal-non-advice")).toBeVisible();
});
