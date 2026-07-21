import { expect, test, type Page } from "@playwright/test";
import { buildFixtureEnvelope, loadGateCorpus, type GateSourceCase } from "../../replay/gate/fixture-loader";

const corpus = loadGateCorpus();

function sourceCase(id: string): GateSourceCase {
  const found = corpus.source.find((item) => item.id === id);
  if (!found) throw new Error(`missing source fixture: ${id}`);
  return found as GateSourceCase;
}

async function routeFixtureMarketData(page: Page, bySymbol: Record<string, GateSourceCase>) {
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    const fixture = bySymbol[symbol] ?? sourceCase("source-formal-aapl");
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(buildFixtureEnvelope(fixture)) });
  });
}

async function seedWorkspace(page: Page, snapshot = corpus.workspace.restoreLayout) {
  await page.addInitScript((seed) => {
    window.localStorage.setItem("myinvestment.workspace.v2", JSON.stringify(seed));
  }, snapshot);
}

test("AC-01 fixture gate covers four-market watchlist and ambiguous input block", async ({ page }) => {
  await seedWorkspace(page, corpus.workspace.fourMarket);
  await routeFixtureMarketData(page, {
    AAPL: sourceCase("source-formal-aapl"),
    "0700.HK": sourceCase("source-demo-hk"),
    "600519.SS": sourceCase("source-unavailable-cn"),
    "005930.KS": sourceCase("source-stale-kr")
  });

  await page.goto("/");

  await expect(page.getByRole("button", { name: /Apple AAPL/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /腾讯控股 0700\.HK/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /贵州茅台 600519\.SS/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Samsung Electronics 005930\.KS/ })).toBeVisible();
  await page.getByTestId("add-symbol-toggle").click();
  await page.getByPlaceholder("AAPL / MSFT / TSLA").fill("0700");
  await expect(page.locator(".normalization-preview")).toContainText("纯数字代码可能属于多个市场");
  await expect(page.getByRole("button", { name: "确认加入" })).toBeDisabled();
});

test("AC-02 and AC-03 fixture gate covers source degradation and non-advice MTS", async ({ page }) => {
  await seedWorkspace(page, corpus.workspace.fourMarket);
  await routeFixtureMarketData(page, {
    AAPL: sourceCase("source-formal-aapl"),
    "0700.HK": sourceCase("source-demo-hk"),
    "600519.SS": sourceCase("source-unavailable-cn")
  });

  await page.goto("/");
  await page.getByRole("button", { name: /腾讯控股 0700\.HK/ }).click();

  await expect(page.getByTestId("chart-degradation-note")).toContainText("fixture demo fallback");
  await expect(page.getByTestId("mts-state-grid")).toContainText("trend_state");
  await expect(page.getByTestId("mts-non-advice")).toContainText("不构成收益承诺");
  await expect(page.getByTestId("mts-card")).not.toContainText(/强买点|强卖点|胜率/);
  await page.getByTestId("detail-tab-source").click();
  await expect(page.getByTestId("source-health-panel")).toContainText("demo_fallback");
});

test("AC-04 fixture gate covers local alert trigger and acknowledgement", async ({ page }) => {
  await seedWorkspace(page, corpus.workspace.fourMarket);
  await routeFixtureMarketData(page, { AAPL: sourceCase("source-formal-aapl") });

  await page.goto("/");
  await page.getByTestId("detail-tab-alerts").click();
  await page.getByTestId("alert-taxonomy-select").selectOption("price");
  await page.getByTestId("alert-level-select").selectOption("观察");
  await page.getByTestId("alert-condition-input").fill("190");
  await page.getByTestId("alert-save-button").click();

  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("enabled / triggered");
  await page.getByTestId("alert-ack-button").click();
  await expect(page.getByTestId("alert-rule-row-watch")).toContainText("enabled / acknowledged");
});

test("AC-05 fixture gate covers browser restore", async ({ page }) => {
  await seedWorkspace(page, corpus.workspace.restoreLayout);
  await routeFixtureMarketData(page, {
    AAPL: sourceCase("source-formal-aapl"),
    "0700.HK": sourceCase("source-demo-hk")
  });

  await page.goto("/");

  await expect(page.getByTestId("restore-status")).toContainText("已恢复");
  await expect(page.getByTestId("workbench-selection-summary")).toContainText("0700.HK");
  await expect(page.getByTestId("layout-mode-dense")).toHaveClass(/active/);
});

test("AC-05 fixture gate covers corrupt layout fallback", async ({ page }) => {
  await seedWorkspace(page, corpus.workspace.corruptLayout);
  await routeFixtureMarketData(page, { AAPL: sourceCase("source-formal-aapl") });

  await page.goto("/");

  await expect(page.getByTestId("restore-status")).toContainText("已回退默认布局");
  await expect(page.getByTestId("layout-mode-focus")).toHaveClass(/active/);
});
