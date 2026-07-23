import { expect, test, type Page } from "@playwright/test";

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;

type SourceStatus = "formal" | "demo_fallback" | "stale" | "unavailable";

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

function envelope(symbol: string, options: { status?: SourceStatus; count?: number; reason?: string } = {}) {
  const status = options.status ?? "formal";
  const seriesBars = bars(options.count ?? 80);
  const latest = seriesBars.at(-1);
  const previous = seriesBars.at(-2);
  const degraded = status !== "formal";
  const reason = options.reason ?? `${status} fixture`;

  return {
    symbol,
    range: "6mo",
    interval: "1d",
    meta: {
      shortName: symbol,
      currency: "USD",
      exchangeName: "Test",
      fullExchangeName: "Fixture market data",
      regularMarketPrice: latest?.close,
      previousClose: previous?.close,
      regularMarketTime: latest?.time,
      timezone: "UTC"
    },
    priceSeries: {
      symbol,
      range: "6mo",
      interval: "1d",
      bars: seriesBars,
      latestOhlc: latest
        ? { time: latest.time, open: latest.open, high: latest.high, low: latest.low, close: latest.close }
        : undefined,
      latestPrice: latest?.close,
      changeSummary:
        latest && previous
          ? { absolute: latest.close - previous.close, percent: ((latest.close - previous.close) / previous.close) * 100 }
          : undefined
    },
    bars: seriesBars,
    servedAt: nowMs,
    cacheState: status === "stale" ? "stale_fallback" : "miss",
    sourceHealth: {
      status,
      affectedObjects: degraded ? ["chart", "mts", "alerts"] : [],
      retryState: {
        attempt: degraded ? 1 : 0,
        canRetry: degraded,
        lastAttemptAt: degraded ? nowMs : undefined,
        reason: degraded ? reason : undefined
      },
      lastRefreshedAt: status === "formal" || status === "stale" ? nowMs - (status === "stale" ? 120_000 : 0) : undefined,
      degradationReason: degraded ? reason : undefined
    },
    sourceName: status === "demo_fallback" ? "Demo" : "Yahoo Finance",
    degradationReason: degraded ? reason : undefined,
    lastRefreshedAt: status === "formal" || status === "stale" ? nowMs - (status === "stale" ? 120_000 : 0) : undefined,
    retryState: {
      attempt: degraded ? 1 : 0,
      canRetry: degraded,
      lastAttemptAt: degraded ? nowMs : undefined,
      reason: degraded ? reason : undefined
    },
    dataSource: status === "demo_fallback" ? "demo" : "yahoo",
    notice: degraded ? `来源降级：${reason}` : undefined
  };
}

async function seedWatchlist(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.watchlist",
      JSON.stringify([
        { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
        { id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" },
        { id: "600519.SS", symbol: "600519.SS", name: "贵州茅台", market: "CN", status: "active" }
      ])
    );
    window.localStorage.setItem("myinvestment.alerts", JSON.stringify([]));
  });
}

async function routeBySymbol(page: Page, resolve: (symbol: string) => unknown) {
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(resolve(symbol)) });
  });
}

test("默认工作台展示主图、成交量、副图、OHLC，并按需进入来源", async ({ page }) => {
  await seedWatchlist(page);
  await routeBySymbol(page, (symbol) => envelope(symbol));

  await page.goto("/");

  await expect(page.getByTestId("workbench-shell")).toContainText("AAPL ·");
  await expect(page.getByTestId("chart-main-panel")).toBeVisible();
  await expect(page.getByTestId("chart-volume-panel")).toBeVisible();
  await expect(page.getByTestId("chart-secondary-panel")).toBeVisible();
  await expect(page.getByTestId("price-authority")).toContainText("O ");
  await expect(page.getByTestId("source-health-panel")).toHaveCount(0);
  await page.getByTestId("detail-tab-source").click();
  await expect(page.getByTestId("source-health-panel")).toContainText("formal");
});

test("MTS 解释卡展示结构化字段且不表达投资建议", async ({ page }) => {
  await seedWatchlist(page);
  await routeBySymbol(page, (symbol) => envelope(symbol));

  await page.goto("/");

  await expect(page.getByTestId("mts-card")).toContainText("MTS 解释卡");
  // PT-02：score-grid / 理由码默认折叠
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

test("副图指标切换保持同一标的上下文", async ({ page }) => {
  await seedWatchlist(page);
  await routeBySymbol(page, (symbol) => envelope(symbol));

  await page.goto("/");
  await expect(page.getByTestId("chart-main-panel")).toContainText("AAPL");

  for (const id of ["rsi", "kdj", "atr", "macd"]) {
    await page.getByTestId(`indicator-tab-${id}`).click();
    await expect(page.getByTestId("chart-main-panel")).toContainText("AAPL");
    await expect(page.getByTestId("indicator-summary")).toContainText(id.toUpperCase());
  }
});

test("数据不足时副图局部降级，不展示伪造读数", async ({ page }) => {
  await seedWatchlist(page);
  await routeBySymbol(page, (symbol) => envelope(symbol, { count: 5 }));

  await page.goto("/");
  const secondaryPanel = page.getByTestId("chart-secondary-panel");
  await expect(secondaryPanel).toBeVisible();
  await expect(page.getByTestId("indicator-tab-rsi")).toBeVisible();
  await page.getByTestId("indicator-tab-rsi").click();
  await secondaryPanel.scrollIntoViewIfNeeded();
  await expect(secondaryPanel.getByTestId("indicator-state-badge")).toContainText("unavailable");
  await expect(secondaryPanel.getByTestId("indicator-summary")).toContainText("数据不足");
  await page.getByTestId("mts-details-toggle").click();
  await expect(page.getByTestId("mts-state-grid")).toContainText("trend_state data_insufficient");
  await expect(page.getByTestId("mts-state-grid")).toContainText("alert_level none");
  await expect(page.getByTestId("mts-reason-list")).not.toContainText("DATA_INSUFFICIENT");
  await page.getByTestId("mts-reason-details-toggle").click();
  await expect(page.getByTestId("mts-reason-codes")).toContainText("DATA_INSUFFICIENT");
});

test("demo fallback 来源健康和降级语义穿透到图表、信号与提醒区域", async ({ page }) => {
  await seedWatchlist(page);
  await routeBySymbol(page, (symbol) =>
    symbol === "0700.HK" ? envelope(symbol, { status: "demo_fallback", reason: "上游返回 500" }) : envelope(symbol)
  );

  await page.goto("/");
  await page.getByRole("button", { name: /腾讯控股 0700\.HK/ }).click();

  await expect(page.getByTestId("chart-degradation-note")).toContainText("demo_fallback");
  await expect(page.getByTestId("chart-degradation-note")).toContainText("上游返回 500");
  const signalDegradationNote = page.getByTestId("signal-degradation-note");
  await expect(signalDegradationNote).toContainText("demo_fallback");
  // GAP-03: demo_fallback 是信息级来源状态，MTS 卡的来源提示条也不应染成最高危警告色
  await expect(signalDegradationNote).toHaveClass(/notice--info/);
  await expect(signalDegradationNote).not.toHaveClass(/notice--warning/);
  await page.getByTestId("detail-tab-source").click();
  await expect(page.getByTestId("source-health-panel")).toContainText("demo_fallback");
});

test("stale 不伪装实时成功，重试失败保留可解释状态", async ({ page }) => {
  await seedWatchlist(page);
  let refreshRequested = false;
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    const body =
      symbol === "AAPL" && refreshRequested
        ? envelope("AAPL", { status: "stale", reason: "上次成功缓存仍可解释" })
        : envelope(symbol);
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
  });

  await page.goto("/");
  await page.getByTestId("detail-tab-source").click();
  await expect(page.getByTestId("source-health-panel")).toContainText("formal");

  refreshRequested = true;
  await page.getByLabel("刷新行情").click();

  await expect(page.getByTestId("source-health-panel")).toContainText("stale");
  await expect(page.getByTestId("source-health-panel")).toContainText("上次成功缓存仍可解释");
  await expect(page.getByTestId("chart-main-panel")).toContainText("AAPL");
});

test("unavailable 来源健康穿透到图表、信号与提醒区域", async ({ page }) => {
  await seedWatchlist(page);
  await routeBySymbol(page, (symbol) =>
    symbol === "600519.SS" ? envelope(symbol, { status: "unavailable", reason: "无缓存且上游网络失败" }) : envelope(symbol)
  );

  await page.goto("/");
  await page.getByRole("button", { name: /贵州茅台 600519\.SS/ }).click();

  await expect(page.getByTestId("chart-source-status")).toContainText("unavailable");
  await expect(page.getByTestId("chart-degradation-note")).toContainText("unavailable");
  await expect(page.getByTestId("signal-degradation-note")).toContainText("unavailable");
  // PT-02：score-grid / 理由码默认折叠，先展开再断言原始枚举字段
  await expect(page.getByTestId("mts-card")).toBeVisible();
  await page.getByTestId("mts-details-toggle").click();
  await expect(page.getByTestId("mts-state-grid")).toContainText("trend_state source_degraded");
  await expect(page.getByTestId("mts-state-grid")).toContainText("alert_level none");
  // 主视图理由列表默认不暴露裸理由码（GAP-D1），展开后才能看到原始 code
  await expect(page.getByTestId("mts-reason-list")).not.toContainText("SOURCE_DEGRADED");
  await page.getByTestId("mts-reason-details-toggle").click();
  await expect(page.getByTestId("mts-reason-codes")).toContainText("SOURCE_DEGRADED");
  await page.getByTestId("detail-tab-source").click();
  await expect(page.getByTestId("source-health-panel")).toContainText("unavailable");
  await expect(page.getByTestId("source-health-panel")).toContainText("无缓存且上游网络失败");
  await page.getByTestId("detail-tab-alerts").click();
  await expect(page.getByText("买卖提醒")).toBeVisible();
});
