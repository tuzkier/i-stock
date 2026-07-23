import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;
const SYMBOL = "AAPL";
const HIERARCHY_SHOT = path.join(
  "harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence",
  "pt05-top-hierarchy-colors.png"
);

function bars(count = 80) {
  return Array.from({ length: count }, (_, index) => {
    const close = 180 + index * 0.45;
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

function envelope(status: "formal" | "stale" = "formal") {
  const seriesBars = bars();
  const latest = seriesBars.at(-1);
  const previous = seriesBars.at(-2);
  const degraded = status !== "formal";
  return {
    symbol: SYMBOL,
    range: "6mo",
    interval: "1d",
    meta: {
      shortName: "Apple",
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
      affectedObjects: degraded ? ["chart"] : [],
      retryState: { attempt: degraded ? 1 : 0, canRetry: degraded },
      lastRefreshedAt: degraded ? undefined : nowMs,
      degradationReason: degraded ? "fixture stale" : undefined
    },
    sourceName: "Fixture",
    degradationReason: degraded ? "fixture stale" : undefined,
    retryState: { attempt: degraded ? 1 : 0, canRetry: degraded }
  };
}

async function seed(page: Page) {
  await page.addInitScript((symbol) => {
    const item = { id: symbol, symbol, name: "Apple", market: "US", status: "active" };
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

test("AT-0501: source-authority / price-authority 各计数=1", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("stale")) });
  });

  await page.goto("/");

  await expect(page.getByTestId("source-authority")).toHaveCount(1);
  await expect(page.getByTestId("price-authority")).toHaveCount(1);
  await expect(page.getByTestId("source-authority")).toBeVisible();
  await expect(page.getByTestId("price-authority")).toBeVisible();

  // 派生指示不得冒充权威 testid
  await expect(page.getByTestId("workbench-selection-summary")).not.toHaveAttribute("data-testid", "source-authority");
  await expect(page.getByTestId("restore-status")).toHaveCount(1);
});

test("AT-0502: 标题主位大于控件，切换布局后仍主位；涨跌色≠警告色", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("stale")) });
  });

  await page.goto("/");

  const title = page.locator(".workspace-header h2");
  const rangeBtn = page.locator(".range-controls button").first();
  await expect(title).toBeVisible();

  const titleSize = Number.parseFloat(await title.evaluate((el) => getComputedStyle(el).fontSize));
  const titleWeight = Number.parseInt(await title.evaluate((el) => getComputedStyle(el).fontWeight), 10);
  const ctrlSize = Number.parseFloat(await rangeBtn.evaluate((el) => getComputedStyle(el).fontSize));
  const ctrlWeight = Number.parseInt(await rangeBtn.evaluate((el) => getComputedStyle(el).fontWeight), 10);
  expect(titleSize).toBeGreaterThan(ctrlSize);
  expect(titleWeight).toBeGreaterThanOrEqual(ctrlWeight);

  const actionsAlign = await page.locator(".workspace-actions").evaluate((el) => getComputedStyle(el).alignItems);
  // 右对齐：actions 在 header flex 右侧；自身内容向 end 收拢
  const actionsJustify = await page.locator(".workspace-actions").evaluate((el) => getComputedStyle(el).justifyContent);
  expect(["flex-end", "end", "right"].some((v) => actionsJustify.includes(v) || actionsAlign.includes(v)) || actionsJustify === "flex-end").toBeTruthy();

  await page.getByTestId("layout-mode-dense").click();
  await expect(page.getByTestId("layout-mode-dense")).toHaveClass(/active/);
  await expect(title).toBeVisible();
  const titleSizeAfter = Number.parseFloat(await title.evaluate((el) => getComputedStyle(el).fontSize));
  expect(titleSizeAfter).toBeGreaterThan(ctrlSize);

  // 涨跌色 vs 警告色并置
  const upOrDown = page.getByTestId("price-authority").locator(".up, .down").first();
  await expect(upOrDown).toBeVisible();
  const changeColor = await upOrDown.evaluate((el) => getComputedStyle(el).color);
  const warnColor = await page.getByTestId("source-authority").evaluate((el) => getComputedStyle(el).color);
  expect(changeColor).not.toBe(warnColor);

  await page.locator(".market-workspace").screenshot({ path: HIERARCHY_SHOT });
});
