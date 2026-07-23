import { expect, test, type Page } from "@playwright/test";

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;

function bars(count = 90) {
  return Array.from({ length: count }, (_, index) => {
    const close = 150 + index * 0.5;
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

function envelope(symbol: string, status: "formal" | "unavailable" = "formal") {
  const seriesBars = bars();
  const latest = seriesBars.at(-1);
  const previous = seriesBars.at(-2);
  const degraded = status !== "formal";
  return {
    symbol,
    range: "6mo",
    interval: "1d",
    meta: {
      shortName: symbol,
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
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.watchlist",
      JSON.stringify([{ id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" }])
    );
    window.localStorage.setItem("myinvestment.alerts", JSON.stringify([]));
  });
}

test("MTS card exposes structured fields and non-advice copy", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("AAPL")) });
  });

  await page.goto("/");

  await expect(page.getByTestId("mts-card")).toContainText("MTS 解释卡");
  // AT-0201: score-grid 裸枚举默认收进折叠详情，需先展开再断言内容
  await page.getByTestId("mts-details-toggle").click();
  await expect(page.getByTestId("mts-state-grid")).toContainText("trend_state");
  await expect(page.getByTestId("mts-state-grid")).toContainText("mts_score");
  await expect(page.getByTestId("mts-state-grid")).toContainText("score_band");
  await expect(page.getByTestId("mts-state-grid")).toContainText("signal_type");
  await expect(page.getByTestId("mts-state-grid")).toContainText("alert_level");
  await expect(page.getByTestId("mts-reason-list")).not.toContainText("TREND_ABOVE_EMA");
  await page.getByTestId("mts-reason-details-toggle").click();
  await expect(page.getByTestId("mts-reason-codes")).toContainText("TREND_ABOVE_EMA");
  await expect(page.getByTestId("mts-non-advice")).toContainText("不构成收益承诺");
  await expect(page.getByTestId("mts-card")).not.toContainText(/强买点|强卖点|胜率/);
});

test("MTS card degrades when source is unavailable", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("AAPL", "unavailable")) });
  });

  await page.goto("/");

  await expect(page.getByTestId("signal-degradation-note")).toContainText("unavailable");
  // AT-0201: score-grid 裸枚举默认收进折叠详情，需先展开再断言内容
  await page.getByTestId("mts-details-toggle").click();
  await expect(page.getByTestId("mts-state-grid")).toContainText("trend_state source_degraded");
  await expect(page.getByTestId("mts-state-grid")).toContainText("alert_level none");
  await expect(page.getByTestId("mts-reason-list")).not.toContainText("SOURCE_DEGRADED");
  await page.getByTestId("mts-reason-details-toggle").click();
  await expect(page.getByTestId("mts-reason-codes")).toContainText("SOURCE_DEGRADED");
});
