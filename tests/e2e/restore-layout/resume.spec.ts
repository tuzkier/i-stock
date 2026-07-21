import { expect, test, type Page } from "@playwright/test";

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;

function bars(count = 90) {
  return Array.from({ length: count }, (_, index) => {
    const close = 160 + index * 0.4;
    return {
      time: nowSeconds - (count - index - 1) * 86_400,
      open: close - 0.4,
      high: close + 1.2,
      low: close - 1.4,
      close,
      volume: 1_000_000 + index * 10_000
    };
  });
}

function envelope(symbol: string) {
  const seriesBars = bars();
  const latest = seriesBars.at(-1);
  const previous = seriesBars.at(-2);
  return {
    symbol,
    range: "6mo",
    interval: "1d",
    meta: {
      shortName: symbol,
      currency: "USD",
      exchangeName: "Test",
      previousClose: previous?.close,
      regularMarketPrice: latest?.close,
      regularMarketTime: latest?.time
    },
    priceSeries: {
      symbol,
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
      status: "formal",
      affectedObjects: [],
      retryState: { attempt: 0, canRetry: false },
      lastRefreshedAt: nowMs
    },
    sourceName: "Yahoo Finance",
    lastRefreshedAt: nowMs,
    retryState: { attempt: 0, canRetry: false },
    dataSource: "yahoo"
  };
}

async function routeMarketData(page: Page) {
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope(symbol)) });
  });
}

test("浏览器重开后恢复 selected symbol、alerts 和 per-symbol dense layout", async ({ page }) => {
  await routeMarketData(page);
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.workspace.v2",
      JSON.stringify({
        version: 2,
        watchlist: [
          { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
          { id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" }
        ],
        alerts: [
          {
            id: "0700-risk",
            symbol: "0700.HK",
            label: "MTS 风控",
            taxonomy: "mts",
            level: "风控",
            direction: "above",
            enabled: true,
            activationState: "enabled",
            triggerState: "acknowledged",
            history: [{ at: Date.now(), type: "acknowledged", reason: "用户确认" }]
          }
        ],
        selectedSymbol: "0700.HK",
        range: "6mo",
        selectedMobileTab: "source",
        layoutBySymbol: {
          AAPL: { mode: "focus", selectedMobileTab: "chart" },
          "0700.HK": { mode: "dense", selectedMobileTab: "source" }
        },
        globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" },
        restoreMetadata: { status: "restored", migratedFromLegacy: false, snapshotBytes: 0 },
        updatedAt: Date.now()
      })
    );
  });

  await page.goto("/");

  await expect(page.getByTestId("restore-status")).toContainText("已恢复");
  await expect(page.getByTestId("workbench-selection-summary")).toContainText("0700.HK");
  await expect(page.getByTestId("layout-controller")).toContainText("总览");
  await expect(page.getByTestId("layout-mode-dense")).toHaveClass(/active/);
  await page.getByTestId("detail-tab-alerts").click();
  await expect(page.getByTestId("alert-rule-row-risk")).toContainText("acknowledged");
});

test("坏 layout snapshot 只回退默认 focus，页面仍可用", async ({ page }) => {
  await routeMarketData(page);
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.workspace.v2",
      JSON.stringify({
        version: 2,
        watchlist: [{ id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" }],
        alerts: [],
        selectedSymbol: "AAPL",
        selectedMobileTab: "chart",
        layoutBySymbol: {
          AAPL: { mode: "broken", selectedMobileTab: "missing" }
        },
        globalLayoutFallback: { mode: "broken", selectedMobileTab: "chart" },
        restoreMetadata: { status: "restored", migratedFromLegacy: false, snapshotBytes: 0 },
        updatedAt: Date.now()
      })
    );
  });

  await page.goto("/");

  await expect(page.getByTestId("restore-status")).toContainText("已回退默认布局");
  await expect(page.getByTestId("layout-mode-focus")).toHaveClass(/active/);
  await expect(page.getByTestId("chart-main-panel")).toContainText("AAPL");
});

test("mobile_tab 与活动 tab 会按 symbol 恢复", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 820 });
  await routeMarketData(page);
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.workspace.v2",
      JSON.stringify({
        version: 2,
        watchlist: [{ id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" }],
        alerts: [],
        selectedSymbol: "AAPL",
        selectedMobileTab: "source",
        layoutBySymbol: {
          AAPL: { mode: "mobile_tab", selectedMobileTab: "source" }
        },
        globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" },
        restoreMetadata: { status: "restored", migratedFromLegacy: false, snapshotBytes: 0 },
        updatedAt: Date.now()
      })
    );
  });

  await page.goto("/");

  await expect(page.getByTestId("layout-mode-mobile-tab")).toHaveClass(/active/);
  await page.getByTestId("detail-tab-source").click();
  await expect(page.getByTestId("source-health-panel")).toBeVisible();
});

test("用户切换布局与移动 tab 后 reload 会按真实写入恢复", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 820 });
  await routeMarketData(page);
  await page.goto("/");

  await page.getByText("腾讯控股").click();
  await page.getByTestId("layout-mode-dense").click();
  await expect
    .poll(async () =>
      page.evaluate(() => {
        const stored = window.localStorage.getItem("myinvestment.workspace.v2");
        if (!stored) return "";
        const snapshot = JSON.parse(stored);
        return `${snapshot.selectedSymbol}:${snapshot.layoutBySymbol?.["0700.HK"]?.mode}`;
      })
    )
    .toBe("0700.HK:dense");

  await page.getByText("Apple").click();
  await page.setViewportSize({ width: 390, height: 820 });
  await page.getByTestId("layout-mode-mobile-tab").click();
  await page.getByTestId("detail-tab-source").click();
  await expect
    .poll(async () =>
      page.evaluate(() => {
        const stored = window.localStorage.getItem("myinvestment.workspace.v2");
        if (!stored) return "";
        const snapshot = JSON.parse(stored);
        return `${snapshot.selectedSymbol}:${snapshot.layoutBySymbol?.AAPL?.mode}`;
      })
    )
    .toBe("AAPL:mobile_tab");

  await page.reload();

  await expect(page.getByTestId("workbench-selection-summary")).toContainText("AAPL");
  await expect(page.getByTestId("layout-mode-mobile-tab")).toHaveClass(/active/);
  await page.getByTestId("detail-tab-source").click();
  await expect(page.getByTestId("source-health-panel")).toBeVisible();

  await page.setViewportSize({ width: 1024, height: 820 });
  await page.getByText("腾讯控股").click();
  await expect(page.getByTestId("workbench-selection-summary")).toContainText("0700.HK");
  await expect(page.getByTestId("layout-mode-dense")).toHaveClass(/active/);
});
