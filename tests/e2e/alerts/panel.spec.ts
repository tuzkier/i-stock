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

async function seed(page: Page, alerts: unknown[] = []) {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.watchlist",
      JSON.stringify([
        { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
        { id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" }
      ])
    );
  });
  await page.addInitScript((initialAlerts) => {
    window.localStorage.setItem(
      "myinvestment.alerts",
      JSON.stringify(initialAlerts)
    );
  }, alerts);
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope(symbol)) });
  });
}

test("创建分类提醒后命中可确认并保留历史", async ({ page }) => {
  await seed(page);
  await page.goto("/");

  await page.getByTestId("detail-tab-alerts").click();
  await page.getByTestId("alert-taxonomy-select").selectOption("price");
  await page.getByTestId("alert-level-select").selectOption("观察");
  await page.getByTestId("alert-condition-input").fill("190");
  await page.getByTestId("alert-save-button").click();

  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("价格型");
  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("enabled / triggered");
  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("历史：triggered");
  await page.getByTestId("alert-ack-button").click();
  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("enabled / acknowledged");
  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("历史：acknowledged");
});

test("归档 active 标的会暂停绑定提醒并展示暂停说明", async ({ page }) => {
  await seed(page);
  await page.goto("/");

  await page.getByTestId("detail-tab-alerts").click();
  await page.getByTestId("alert-taxonomy-select").selectOption("mts");
  await page.getByTestId("alert-level-select").selectOption("强信号");
  await page.getByTestId("alert-save-button").click();
  await page.getByLabel("归档 Apple").click();

  await expect(page.getByTestId("alert-rule-row-archive")).toContainText("suspended_by_archive");
  await expect(page.getByTestId("alert-rule-row-archive")).toContainText("归档暂停");
});

test("定时提醒在浏览器重开后记录 missed_while_closed 并展示触发历史", async ({ page }) => {
  const createdAt = Date.now() - 24 * 60 * 60 * 1000;
  await seed(page, [
    {
      id: `alert-scheduled-AAPL-${createdAt}`,
      symbol: "AAPL",
      label: "AAPL 定时提醒 00:00",
      taxonomy: "scheduled",
      level: "观察",
      condition: { kind: "daily_time", localTime: "00:00", timezone: "local" },
      direction: "above",
      enabled: true,
      activationState: "enabled",
      triggerState: "idle",
      history: []
    }
  ]);
  await page.goto("/");

  await page.getByTestId("detail-tab-alerts").click();
  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("定时提醒");
  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("enabled / idle");
  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("missed_while_closed");
});
