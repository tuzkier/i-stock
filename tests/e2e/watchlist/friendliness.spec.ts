import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;
const ARCHIVED_SHOT = path.join(
  "harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence",
  "pt04-watchlist-archived.png"
);

function chartPayload(symbol: string, status: "formal" | "unavailable" = "formal") {
  const bars = [
    { time: nowSeconds - 86_400 * 2, open: 175, high: 181, low: 174, close: 180, volume: 1_200_000 },
    { time: nowSeconds - 86_400, open: 181, high: 189, low: 180, close: 188, volume: 1_500_000 },
    { time: nowSeconds, open: 188, high: 191, low: 185, close: 190, volume: 1_400_000 }
  ];
  const latest = bars.at(-1);
  const degraded = status !== "formal";
  return {
    symbol,
    range: "6mo",
    interval: "1d",
    meta: {
      shortName: symbol,
      previousClose: 180,
      regularMarketPrice: latest?.close,
      regularMarketTime: nowSeconds
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
    servedAt: nowMs,
    cacheState: "miss",
    sourceHealth: {
      status,
      affectedObjects: degraded ? ["chart"] : [],
      retryState: { attempt: degraded ? 1 : 0, canRetry: degraded },
      lastRefreshedAt: degraded ? undefined : nowMs,
      degradationReason: degraded ? "fixture degraded" : undefined
    },
    sourceName: "Fixture",
    degradationReason: degraded ? "fixture degraded" : undefined,
    retryState: { attempt: degraded ? 1 : 0, canRetry: degraded }
  };
}

async function seedWatchlist(page: Page) {
  await page.addInitScript(() => {
    const active = [
      { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
      { id: "9988.HK", symbol: "9988.HK", name: "阿里巴巴", market: "HK", status: "active" }
    ];
    const archived = [
      { id: "MSFT", symbol: "MSFT", name: "Microsoft", market: "US", status: "archived", archivedAt: Date.now() - 86_400_000 }
    ];
    const watchlist = [...active, ...archived];
    window.localStorage.setItem("myinvestment.watchlist", JSON.stringify(watchlist));
    window.localStorage.setItem("myinvestment.alerts", JSON.stringify([]));
    window.localStorage.setItem(
      "myinvestment.workspace.v2",
      JSON.stringify({
        version: 2,
        watchlist,
        alerts: [],
        selectedSymbol: "AAPL",
        range: "6mo",
        selectedMobileTab: "chart",
        layoutBySymbol: {},
        globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" },
        restoreMetadata: { status: "restored", migratedFromLegacy: false, snapshotBytes: 0 },
        updatedAt: Date.now()
      })
    );
  });
}

test("AT-0401: 侧栏名称+代码一行、价格右对齐、来源小圆点非横幅", async ({ page }) => {
  await seedWatchlist(page);
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    const status = symbol === "9988.HK" ? "unavailable" : "formal";
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(chartPayload(symbol, status)) });
  });

  await page.goto("/");

  const apple = page.getByTestId("watch-item-AAPL");
  await expect(apple).toBeVisible();

  const identity = apple.getByTestId("watch-item-identity");
  await expect(identity).toContainText("Apple");
  await expect(identity).toContainText("AAPL");
  // 名称+代码同一行（非上下堆叠）
  const identityDisplay = await identity.evaluate((el) => getComputedStyle(el).display);
  expect(identityDisplay).toBe("flex");

  const quote = apple.getByTestId("watch-item-quote");
  await expect(quote).toBeVisible();
  const quoteAlign = await quote.evaluate((el) => getComputedStyle(el).textAlign);
  expect(quoteAlign).toBe("right");

  const dot = apple.getByTestId("watch-item-source-dot");
  await expect(dot).toBeVisible();
  const box = await dot.boundingBox();
  expect(box).toBeTruthy();
  expect(Math.max(box!.width, box!.height)).toBeLessThanOrEqual(14);

  // 来源不得以文本横幅 / data-notice 主源呈现
  await expect(apple.locator(".data-notice")).toHaveCount(0);
  await expect(apple.getByTestId("watch-item-main")).not.toContainText("正式");
  await expect(apple.getByTestId("watch-item-main")).not.toContainText("不可用");

  const alibaba = page.getByTestId("watch-item-9988.HK");
  await expect(alibaba.getByTestId("watch-item-source-dot")).toHaveClass(/tone-warning|source-dot--warning/);
});

test("AT-0402: archived 弱化区分 active", async ({ page }) => {
  await seedWatchlist(page);
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(chartPayload(symbol)) });
  });

  await page.goto("/");

  const active = page.getByTestId("watch-item-AAPL");
  const archived = page.getByTestId("watch-item-MSFT");
  await expect(archived).toBeVisible();
  await expect(archived).toHaveClass(/archived/);

  const activeOpacity = Number.parseFloat(await active.evaluate((el) => getComputedStyle(el).opacity));
  const archivedOpacity = Number.parseFloat(await archived.evaluate((el) => getComputedStyle(el).opacity));
  expect(archivedOpacity).toBeLessThan(activeOpacity);

  const activeColor = await active.evaluate((el) => getComputedStyle(el).color);
  const archivedColor = await archived.evaluate((el) => getComputedStyle(el).color);
  expect(archivedColor).not.toBe(activeColor);

  await page.locator(".archive-block").screenshot({ path: ARCHIVED_SHOT });
});
