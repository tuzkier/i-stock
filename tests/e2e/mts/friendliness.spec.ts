import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;
// 不写 Playwright outputDir（会被后续 suite 清空）；落 harness evidence 目录
const NEGATIVE_SCORE_SHOT = path.join(
  "harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence",
  "pt02-mts-negative-score-tone.png"
);

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

// GAP-02: 持续下跌 + 缩量的走势，用来驱动 buildSignal 产出 negative/strong_negative scoreBand。
function decliningBars(count = 90) {
  return Array.from({ length: count }, (_, index) => {
    const close = 260 - index * 1.6;
    return {
      time: nowSeconds - (count - index - 1) * 86_400,
      open: close + 0.4,
      high: close + 1.2,
      low: close - 1.4,
      close,
      volume: 1_000_000 - index * 6_000
    };
  });
}

function envelope(
  symbol: string,
  status: "formal" | "unavailable" | "stale" = "formal",
  seriesBars = bars()
) {
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

const ENUM_TOKENS = ["trend_state", "mts_score", "score_band", "signal_type", "alert_level"] as const;

test("AT-0201: MTS 主视图无人话前枚举 token，且有 ScoreBar", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("AAPL")) });
  });

  await page.goto("/");

  const card = page.getByTestId("mts-card");
  await expect(card).toBeVisible();
  await expect(page.getByTestId("mts-score-bar")).toBeVisible();

  for (const token of ENUM_TOKENS) {
    await expect(card).not.toContainText(token);
  }

  // 默认折叠：原始字段网格不可见
  await expect(page.getByTestId("mts-state-grid")).toHaveCount(0);

  await page.getByTestId("mts-details-toggle").click();
  await expect(page.getByTestId("mts-state-grid")).toBeVisible();
  await expect(page.getByTestId("mts-state-grid")).toContainText("trend_state");
});

test("AT-0201: 来源降级 note 使用 notice--warning 而非 data-notice", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("AAPL", "unavailable")) });
  });

  await page.goto("/");

  const note = page.getByTestId("signal-degradation-note");
  await expect(note).toBeVisible();
  await expect(note).toHaveClass(/notice--warning/);
  await expect(note).not.toHaveClass(/data-notice/);
});

test("AT-0202: reason-list 主视图无裸理由码，展开后可见原始 code", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("AAPL")) });
  });

  await page.goto("/");

  const list = page.getByTestId("mts-reason-list");
  await expect(list).toBeVisible();
  await expect(list).not.toContainText("TREND_ABOVE_EMA");
  await expect(list.locator("code")).toHaveCount(0);

  await page.getByTestId("mts-reason-details-toggle").click();
  await expect(page.getByTestId("mts-reason-codes")).toContainText("TREND_ABOVE_EMA");
});

test("AT-0202: 来源降级时 invalidators 主视图不直呈 SOURCE_DEGRADED", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope("AAPL", "unavailable")) });
  });

  await page.goto("/");

  const list = page.getByTestId("mts-reason-list");
  await expect(list).not.toContainText("SOURCE_DEGRADED");
  await page.getByTestId("mts-reason-details-toggle").click();
  await expect(page.getByTestId("mts-reason-codes")).toContainText("SOURCE_DEGRADED");
});

test("GAP-02: negative 评分色与 stale 来源警告色物理区分", async ({ page }) => {
  await seed(page);
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(envelope("AAPL", "formal", decliningBars()))
    });
  });

  await page.goto("/");

  const card = page.getByTestId("mts-card");
  await expect(card).toBeVisible();

  // 确认 fixture 确实驱动出 negative/strong_negative scoreBand，而不是巧合通过
  await page.getByTestId("mts-details-toggle").click();
  await expect(page.getByTestId("mts-state-grid")).toContainText(/score_band (strong_negative|negative)/);

  // GAP-02: 负向评分走既有 .risk 类，class 不含来源故障的 notice--warning / data-notice
  const cardClass = (await card.getAttribute("class")) ?? "";
  expect(cardClass).toMatch(/\brisk\b/);
  expect(cardClass).not.toMatch(/notice--warning/);
  expect(cardClass).not.toMatch(/data-notice/);
  await expect(page.getByTestId("signal-degradation-note")).toHaveCount(0);

  await card.screenshot({ path: NEGATIVE_SCORE_SHOT });

  // 并置对比：同一标的来源转为 stale 后，来源故障走 notice--warning，与上面的 negative 评分 class 物理不同
  await page.route("**/api/chart/**", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(envelope("AAPL", "stale", decliningBars()))
    });
  });
  await page.reload();
  await page.getByTestId("mts-details-toggle").click();

  const staleNote = page.getByTestId("signal-degradation-note");
  await expect(staleNote).toBeVisible();
  await expect(staleNote).toHaveClass(/notice--warning/);

  const staleCardClass = (await page.getByTestId("mts-card").getAttribute("class")) ?? "";
  expect(staleCardClass).not.toMatch(/notice--warning/);
});
