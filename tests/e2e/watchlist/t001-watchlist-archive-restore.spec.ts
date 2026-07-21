import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const now = Math.floor(Date.now() / 1000);

function chartPayload(symbol: string) {
  const bars = [
    { time: now - 86_400 * 2, open: 175, high: 181, low: 174, close: 180, volume: 1200000 },
    { time: now - 86_400, open: 181, high: 189, low: 180, close: 188, volume: 1500000 },
    { time: now, open: 188, high: 191, low: 185, close: 190, volume: 1400000 }
  ];
  const latest = bars.at(-1);
  return {
    symbol,
    range: "6mo",
    interval: "1d",
    meta: {
      shortName: symbol,
      currency: symbol.endsWith(".HK") ? "HKD" : "USD",
      exchangeName: "Test",
      fullExchangeName: "Fixture market data",
      previousClose: 180,
      regularMarketPrice: latest?.close,
      regularMarketTime: now
    },
    priceSeries: {
      symbol,
      range: "6mo",
      interval: "1d",
      bars,
      latestOhlc: latest,
      latestPrice: latest?.close,
      changeSummary: { absolute: 10, percent: 5.5555555556 }
    },
    bars,
    servedAt: now * 1000,
    cacheState: "miss",
    sourceHealth: {
      status: "formal",
      affectedObjects: [],
      retryState: { attempt: 0, canRetry: false },
      lastRefreshedAt: now * 1000
    },
    sourceName: "Yahoo Finance",
    lastRefreshedAt: now * 1000,
    retryState: { attempt: 0, canRetry: false },
    dataSource: "yahoo"
  };
}

test.beforeEach(async ({ page }) => {
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(chartPayload(symbol))
    });
  });

  await page.addInitScript(() => {
    if (!window.localStorage.getItem("myinvestment.watchlist")) {
      window.localStorage.setItem(
        "myinvestment.watchlist",
        JSON.stringify([
          { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
          { id: "9988.HK", symbol: "9988.HK", name: "阿里巴巴", market: "HK", status: "active" }
        ])
      );
    }
    if (!window.localStorage.getItem("myinvestment.alerts")) {
      window.localStorage.setItem(
        "myinvestment.alerts",
        JSON.stringify([
          {
            id: "alert-9988-strong-sell",
            symbol: "9988.HK",
            label: "9988.HK 触发 strong-sell",
            direction: "above",
            signal: "strong-sell",
            enabled: true,
            activationState: "enabled"
          }
        ])
      );
    }
  });
});

test("归档后暂停提醒，重新加入已归档港股时恢复提醒", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText(/9988\.HK · 港股/)).toBeVisible();
  await expect(page.getByText(/正式 · 190\.00 · 5\.56%/).first()).toBeVisible();

  await page.getByRole("button", { name: "阿里巴巴 9988.HK · 港股 正式 · 190.00 · 5.56%" }).click();
  await page.getByTestId("detail-tab-alerts").click();
  await expect(page.getByLabel("9988.HK 触发 strong-sell")).toBeChecked();

  await page.getByLabel("归档 阿里巴巴").click();
  await expect(page.getByText("9988.HK · 港股 · 提醒已暂停")).toBeVisible();
  await expect
    .poll(async () =>
      page.evaluate(() => {
        const watchlist = JSON.parse(window.localStorage.getItem("myinvestment.watchlist") ?? "[]");
        const alerts = JSON.parse(window.localStorage.getItem("myinvestment.alerts") ?? "[]");
        return {
          archived: watchlist.find((item: { symbol: string }) => item.symbol === "9988.HK")?.status,
          activationState: alerts.find((item: { symbol: string }) => item.symbol === "9988.HK")?.activationState,
          enabled: alerts.find((item: { symbol: string }) => item.symbol === "9988.HK")?.enabled
        };
      })
    )
    .toEqual({ archived: "archived", activationState: "suspended_by_archive", enabled: false });
  await page.reload();
  await expect(page.getByText("9988.HK · 港股 · 提醒已暂停")).toBeVisible();

  await page.getByTestId("add-symbol-toggle").click();
  await page.locator(".market-tabs").getByRole("button", { name: "港股" }).click();
  await page.getByPlaceholder("0700.HK / 9988.HK").fill("9988");
  await expect(page.getByText("港股 · 9988 → 9988.HK")).toBeVisible();
  await expect(page.getByText("确认后恢复已归档标的")).toBeVisible();

  await page.getByRole("button", { name: "确认加入" }).click();
  await expect(page.getByText("9988.HK · 港股 · 提醒已暂停")).toHaveCount(0);
  await expect(page.getByText(/9988\.HK · 港股/)).toBeVisible();
  await page.getByTestId("detail-tab-alerts").click();
  await expect(page.getByLabel("9988.HK 触发 strong-sell")).toBeChecked();
  await page.reload();
  await expect(page.getByText(/9988\.HK · 港股/)).toBeVisible();
  await page.getByRole("button", { name: /阿里巴巴 9988\.HK · 港股/ }).click();
  await page.getByTestId("detail-tab-alerts").click();
  await expect(page.getByLabel("9988.HK 触发 strong-sell")).toBeChecked();
});

test("歧义数字输入不会写入 active 自选", async ({ page }) => {
  await page.goto("/");

  await page.getByTestId("add-symbol-toggle").click();
  await page.locator(".market-tabs").getByRole("button", { name: "美股" }).click();
  await page.getByPlaceholder("AAPL / MSFT / TSLA").fill("0700");
  await expect(page.getByText("纯数字代码可能属于多个市场，请先选择对应市场")).toBeVisible();
  await expect(page.getByRole("button", { name: "确认加入" })).toBeDisabled();

  await expect(page.getByText(/0700\.HK · 港股/)).toHaveCount(0);
  const stored = await page.evaluate(() => window.localStorage.getItem("myinvestment.watchlist"));
  expect(stored ?? "").not.toContain("0700.HK");
});

test("看盘主流程没有自动化可访问性严重违规", async ({ page }) => {
  await page.goto("/");

  const results = await new AxeBuilder({ page }).include("main").analyze();
  expect(results.violations).toEqual([]);
});
