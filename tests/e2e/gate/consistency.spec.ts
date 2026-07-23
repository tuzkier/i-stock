import { expect, test, type Page } from "@playwright/test";

// AT-0701（PT-07 终局验证切片）：
// 构造单一标的（腾讯 0700.HK，命中 trade-signals.ts 的定制策略）在真实来源
// stale 态下的场景，驱动真实 domain 门控（buildSignal / buildTradeSignalState /
// getSourceStatus，均以 envelope.sourceHealth.status !== "formal" 为共同触发条件）
// 产出一致降级，而不是在测试里直接伪造 DOM。
//
// 断言覆盖：
// - NEG-01：source-authority / MTS 卡降级子集 / 交易信号卡 三处读同一 domain
//   门控结果一致降级（人话文案、不显 ready、不给买卖价位）。
// - NEG-03：restore-status 与 source-authority 是物理独立的 DOM 元素。
// - 唯一主源计数=1 聚合：source-authority / price-authority 各 toHaveCount(1)。

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;
const SYMBOL = "0700.HK";

// MIN_BARS（trade-signals.ts）=80，buildSignal 需要 >=60 根才会走到 SOURCE_DEGRADED
// 分支而不是被 DATA_INSUFFICIENT 抢先短路；90 根同时满足两者。
function bars(count = 90) {
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

function envelope(status: "formal" | "stale" = "stale") {
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
      retryState: { attempt: degraded ? 1 : 0, canRetry: degraded, reason: degraded ? "行情延迟" : undefined },
      lastRefreshedAt: degraded ? undefined : nowMs,
      degradationReason: degraded ? "行情延迟" : undefined
    },
    sourceName: "Fixture",
    degradationReason: degraded ? "行情延迟" : undefined,
    retryState: { attempt: degraded ? 1 : 0, canRetry: degraded, reason: degraded ? "行情延迟" : undefined }
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

async function routeStale(page: Page) {
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("stale")) });
  });
}

test("NEG-01: source-authority / MTS 降级子集 / 交易信号卡三处读同一 domain 门控结果一致降级", async ({ page }) => {
  await seed(page);
  await routeStale(page);

  await page.goto("/");

  // 1) 来源权威承载：sourceHealth.status="stale" -> resolveSourceTone=warning，
  //    展示人话档位标签"过期"，非原始枚举值。
  const sourceAuthority = page.getByTestId("source-authority");
  await expect(sourceAuthority).toBeVisible();
  await expect(sourceAuthority).toContainText("过期");
  await expect(sourceAuthority).not.toContainText("stale");
  await expect(sourceAuthority).toHaveClass(/notice--warning/);

  // 2) MTS 卡降级子集：buildSignal 走 SOURCE_DEGRADED invalidator ->
  //    trendState="source_degraded"，展示降级提示条，而非 ready 态的趋势文案。
  const mtsCard = page.getByTestId("mts-card");
  await expect(mtsCard).toBeVisible();
  const degradationNote = page.getByTestId("signal-degradation-note");
  await expect(degradationNote).toBeVisible();
  await expect(degradationNote).toContainText("stale");
  await page.getByTestId("mts-details-toggle").click();
  await expect(page.getByTestId("mts-state-grid")).toContainText("trend_state source_degraded");
  await expect(page.getByTestId("mts-state-grid")).toContainText("alert_level none");
  await expect(mtsCard).not.toContainText(/强买点|强卖点|胜率/);

  // 3) 交易信号卡：buildTradeSignalState 命中同一
  //    "sourceHealth.status!=='formal'" 门控 -> status="source_degraded"，
  //    人话文案"来源不可用"、不显示 ready 态的持仓/空仓文案、不给出任何买卖价位
  //    （无回测块、无价位明细展开入口）。
  const tradeCard = page.getByTestId("trade-signal-card");
  await expect(tradeCard).toBeVisible();
  const topline = tradeCard.locator(".signal-topline");
  await expect(topline).not.toContainText("source_degraded");
  await expect(page.getByTestId("trade-signal-status")).toHaveText("来源不可用");
  await expect(page.getByTestId("trade-signal-status")).not.toHaveText(/持仓中|空仓/);
  await expect(page.getByTestId("trade-backtest-summary")).toHaveCount(0);
  await expect(page.getByTestId("trade-signal-details-toggle")).toHaveCount(0);
  await expect(page.getByTestId("trade-signal-details")).toHaveCount(0);
  await expect(page.getByTestId("trade-signal-non-advice")).toBeVisible();
});

test("NEG-03: restore-status 与 source-authority 是物理独立的 DOM 元素", async ({ page }) => {
  await seed(page);
  await routeStale(page);

  await page.goto("/");

  const restoreStatus = page.getByTestId("restore-status");
  const sourceAuthority = page.getByTestId("source-authority");

  await expect(restoreStatus).toHaveCount(1);
  await expect(sourceAuthority).toHaveCount(1);

  // 互不嵌套：一个的子树里不应能再找到另一个的 testid。
  await expect(sourceAuthority.getByTestId("restore-status")).toHaveCount(0);
  await expect(restoreStatus.getByTestId("source-authority")).toHaveCount(0);

  const restoreBox = await restoreStatus.boundingBox();
  const sourceBox = await sourceAuthority.boundingBox();
  expect(restoreBox).not.toBeNull();
  expect(sourceBox).not.toBeNull();
  expect(restoreBox).not.toEqual(sourceBox);
});

test("唯一主源计数=1 聚合: source-authority / price-authority 各 toHaveCount(1)", async ({ page }) => {
  await seed(page);
  await routeStale(page);

  await page.goto("/");

  await expect(page.getByTestId("source-authority")).toHaveCount(1);
  await expect(page.getByTestId("price-authority")).toHaveCount(1);
  await expect(page.getByTestId("source-authority")).toBeVisible();
  await expect(page.getByTestId("price-authority")).toBeVisible();

  // 派生指示不得冒充权威 testid（工作台标题下方的选中态摘要不是 source-authority）。
  await expect(page.getByTestId("workbench-selection-summary")).not.toHaveAttribute("data-testid", "source-authority");
});
