import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "playwright";

const baseURL = "http://127.0.0.1:5174";
const now = Math.floor(Date.now() / 1000);
const evidencePath =
  "harness-runtime/harness/stages/20260522-stock-watch-system/traces/result/t001-ui-summary-fresh.json";

function chartPayload(symbol) {
  return {
    symbol,
    range: "6mo",
    interval: "1d",
    dataSource: "yahoo",
    meta: {
      shortName: symbol,
      currency: symbol.endsWith(".HK") ? "HKD" : "USD",
      exchangeName: "Test",
      fullExchangeName: "Fixture market data",
      previousClose: 180,
      regularMarketTime: now
    },
    bars: [
      { time: now - 86_400 * 2, open: 175, high: 181, low: 174, close: 180, volume: 1200000 },
      { time: now - 86_400, open: 181, high: 189, low: 180, close: 188, volume: 1500000 },
      { time: now, open: 188, high: 191, low: 185, close: 190, volume: 1400000 }
    ]
  };
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(chartPayload(symbol))
    });
  });
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.watchlist",
      JSON.stringify([
        { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
        { id: "9988.HK", symbol: "9988.HK", name: "阿里巴巴", market: "HK", status: "active" }
      ])
    );
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
  });

  await page.goto(baseURL);
  await page.getByText(/正式 · 190\.00 · 5\.56%/).first().waitFor();
  const rowSummary = await page.getByRole("button", { name: /阿里巴巴 9988\.HK · 港股/ }).first().innerText();

  await page.getByRole("button", { name: "阿里巴巴 9988.HK · 港股 正式 · 190.00 · 5.56%" }).click();
  assert(await page.getByLabel("9988.HK 触发 strong-sell").isChecked(), "expected alert checkbox checked before archive");
  await page.getByLabel("归档 阿里巴巴").click();
  const archivedLabel = await page.getByText("9988.HK · 港股 · 提醒已暂停").innerText();
  const archivedState = await page.evaluate(() => {
    const watchlist = JSON.parse(window.localStorage.getItem("myinvestment.watchlist") ?? "[]");
    const alerts = JSON.parse(window.localStorage.getItem("myinvestment.alerts") ?? "[]");
    return {
      archived: watchlist.find((item) => item.symbol === "9988.HK")?.status,
      activationState: alerts.find((item) => item.symbol === "9988.HK")?.activationState,
      enabled: alerts.find((item) => item.symbol === "9988.HK")?.enabled
    };
  });

  await page.locator(".market-tabs").getByRole("button", { name: "港股" }).click();
  await page.getByPlaceholder("0700.HK / 9988.HK").fill("9988");
  const restorePreview = await page.getByText("港股 · 9988 → 9988.HK").innerText();
  await page.getByRole("button", { name: "确认加入" }).click();
  const restoredAlertChecked = await page.getByLabel("9988.HK 触发 strong-sell").isChecked();

  await page.locator(".market-tabs").getByRole("button", { name: "美股" }).click();
  await page.getByPlaceholder("AAPL / MSFT / TSLA").fill("0700");
  const ambiguityMessage = await page.getByText("纯数字代码可能属于多个市场，请先选择对应市场").innerText();
  const confirmDisabled = await page.getByRole("button", { name: "确认加入" }).isDisabled();

  const evidence = {
    generatedAt: new Date().toISOString(),
    baseURL,
    command: "node harness-runtime/harness/traces/20260522-stock-watch-system/verify-t001-ui-evidence.mjs",
    rowSummary,
    archivedLabel,
    archivedState,
    restorePreview,
    restoredAlertChecked,
    ambiguityMessage,
    confirmDisabled
  };

  assert(rowSummary.includes("9988.HK · 港股"), "row summary missing normalized symbol and market");
  assert(rowSummary.includes("正式 · 190.00 · 5.56%"), "row summary missing source, price, and change");
  assert(JSON.stringify(archivedState) === JSON.stringify({ archived: "archived", activationState: "suspended_by_archive", enabled: false }), "archived state mismatch");
  assert(restoredAlertChecked, "expected restored alert checked");
  assert(confirmDisabled, "expected ambiguity confirm button disabled");

  mkdirSync("harness-runtime/harness/stages/20260522-stock-watch-system/traces/result", { recursive: true });
  writeFileSync(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`);
  console.log(JSON.stringify(evidence, null, 2));
} finally {
  await browser.close();
}
