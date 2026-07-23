import { expect, test, type Page } from "@playwright/test";

// 注意：`restoreMetadata` 不是由客户端直接信任 localStorage 里写的字段——
// `src/domain/workspace.ts` 的 readWorkspaceSnapshot/restoreSnapshot/migrateLegacy
// 会重新按快照 payload 的真实结构（layoutBySymbol 是否可解析、globalLayoutFallback
// 是否合法、v2 快照 key 是否存在）推导出 status/discardedLayoutKeys。
// 所以这里的种子数据必须构造成会让真实恢复逻辑推出目标状态，而不是直接写死
// restoreMetadata 期望值（那样会被恢复逻辑忽略/覆盖，测试形同虚设）。

const nowSeconds = Math.floor(Date.now() / 1000);
const nowMs = nowSeconds * 1000;

function bars(count = 90) {
  return Array.from({ length: count }, (_, index) => {
    const close = 160 + index * 0.4;
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

async function routeMarketData(page: Page) {
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(envelope(symbol)) });
  });
}

/** 写入一个可被 restoreSnapshot() 正常解析恢复的 v2 快照（status -> "restored"）。 */
function seedRestoredSnapshot(page: Page) {
  return page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.workspace.v2",
      JSON.stringify({
        version: 2,
        watchlist: [{ id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" }],
        alerts: [],
        selectedSymbol: "AAPL",
        range: "6mo",
        selectedMobileTab: "chart",
        layoutBySymbol: {
          AAPL: { mode: "focus", selectedMobileTab: "chart" }
        },
        globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" },
        updatedAt: Date.now()
      })
    );
  });
}

/**
 * 写入一个 globalLayoutFallback 不合法（mode 不在 layoutModes 枚举内）、
 * 但 layoutBySymbol 条目本身合法的 v2 快照：normalizeLayout(globalLayoutFallback)
 * 返回 undefined、discardedLayoutKeys 仍为空 -> restoreSnapshot() 推出
 * status="default_fallback" 且 discardedLayoutKeys.length===0。
 */
function seedDefaultFallbackWithoutDiscardedKeys(page: Page) {
  return page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.workspace.v2",
      JSON.stringify({
        version: 2,
        watchlist: [{ id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" }],
        alerts: [],
        selectedSymbol: "AAPL",
        range: "6mo",
        selectedMobileTab: "chart",
        layoutBySymbol: {
          AAPL: { mode: "focus", selectedMobileTab: "chart" }
        },
        globalLayoutFallback: { mode: "not_a_real_layout_mode" },
        updatedAt: Date.now()
      })
    );
  });
}

/**
 * layoutBySymbol 里混入一个 mode 不合法的条目（会被 normalizeLayoutMap 判为
 * 不可解析并计入 discardedLayoutKeys），globalLayoutFallback 合法。
 * restoreSnapshot() 因 discardedLayoutKeys.length>0 推出 status="default_fallback"，
 * 且 discardedLayoutKeys=["0700.HK"] 非空。
 */
function seedDiscardedLayoutKeys(page: Page) {
  return page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.workspace.v2",
      JSON.stringify({
        version: 2,
        watchlist: [
          { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" },
          { id: "0700.HK", symbol: "0700.HK", name: "腾讯控股", market: "HK", status: "active" }
        ],
        alerts: [],
        selectedSymbol: "AAPL",
        range: "6mo",
        selectedMobileTab: "chart",
        layoutBySymbol: {
          AAPL: { mode: "focus", selectedMobileTab: "chart" },
          "0700.HK": { mode: "not_a_real_layout_mode", selectedMobileTab: "chart" }
        },
        globalLayoutFallback: { mode: "focus", selectedMobileTab: "chart" },
        updatedAt: Date.now()
      })
    );
  });
}

/**
 * 不写入 v2 快照 key，只写入旧版 legacy key（myinvestment.watchlist /
 * myinvestment.alerts）。readWorkspaceSnapshot() 在 v2 key 缺失时会走
 * migrateLegacy()，产出 status="partial"、migratedFromLegacy=true，
 * 且不带 discardedLayoutKeys。
 */
function seedLegacyMigration(page: Page) {
  return page.addInitScript(() => {
    window.localStorage.setItem(
      "myinvestment.watchlist",
      JSON.stringify([{ id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" }])
    );
    window.localStorage.setItem("myinvestment.alerts", JSON.stringify([]));
  });
}

test.describe("恢复状态四档分色（resolveRestoreTone，经真实 restoreSnapshot/migrateLegacy 恢复路径驱动）", () => {
  test("restored 态：不含 notice--warning 也不含 notice--info，class 为 restore-status--normal", async ({ page }) => {
    await routeMarketData(page);
    await seedRestoredSnapshot(page);

    await page.goto("/");

    const restoreStatus = page.getByTestId("restore-status");
    await expect(restoreStatus).toContainText("已恢复");
    await expect(restoreStatus).not.toHaveClass(/notice--warning/);
    await expect(restoreStatus).not.toHaveClass(/notice--info/);
    await expect(restoreStatus).toHaveClass(/restore-status--normal/);
  });

  test("default_fallback 态（无 discardedLayoutKeys）：notice--info，不含 notice--warning", async ({ page }) => {
    await routeMarketData(page);
    await seedDefaultFallbackWithoutDiscardedKeys(page);

    await page.goto("/");

    const restoreStatus = page.getByTestId("restore-status");
    await expect(restoreStatus).toContainText("已回退默认布局");
    await expect(restoreStatus).toHaveClass(/notice--info/);
    await expect(restoreStatus).not.toHaveClass(/notice--warning/);

    const details = page.getByTestId("restore-status-details");
    await expect(details).toContainText("invalid_layout_fallback");
  });

  test("partial 态（旧存储迁移）：notice--info，不含 notice--warning", async ({ page }) => {
    await routeMarketData(page);
    await seedLegacyMigration(page);

    await page.goto("/");

    const restoreStatus = page.getByTestId("restore-status");
    await expect(restoreStatus).toContainText("已从旧存储迁移");
    await expect(restoreStatus).toHaveClass(/notice--info/);
    await expect(restoreStatus).not.toHaveClass(/notice--warning/);
  });

  test("discardedLayoutKeys 非空：即使整体 status 为 default_fallback，仍得到 notice--warning（优先于 info）", async ({
    page
  }) => {
    await routeMarketData(page);
    await seedDiscardedLayoutKeys(page);

    await page.goto("/");

    const restoreStatus = page.getByTestId("restore-status");
    await expect(restoreStatus).toHaveClass(/notice--warning/);
    await expect(restoreStatus).not.toHaveClass(/notice--info/);

    const details = page.getByTestId("restore-status-details");
    await expect(details).toContainText("已丢弃坏布局");
    await expect(details).toContainText("0700.HK");
  });

  test("restore-status 与 source-authority 是两个独立的 DOM 元素（NEG-03）", async ({ page }) => {
    await routeMarketData(page);
    await seedRestoredSnapshot(page);

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
});

// resolveRestoreTone 的 status="failed" 分支目前在真实恢复流程
// （restoreSnapshot / migrateLegacy / fallbackSnapshot）里没有任何代码路径会产出
// "failed"（只会产出 restored / partial / default_fallback），因此无法通过用户可达的
// E2E 路径触发。该分支已由纯函数单元测试
// tests/unit/presentation/tone.spec.ts:140-142（"resolveRestoreTone: failed -> warning"）
// 覆盖，此处不做 DOM 层面的强行注入式伪造。

test.describe("chart-degradation-note 迁移到 notice--warning", () => {
  test("行情降级提示使用 notice--warning，不再是 data-notice", async ({ page }) => {
    await page.route("**/api/chart/**", async (route) => {
      const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
      const body = envelope(symbol);
      body.sourceHealth = {
        status: "stale",
        affectedObjects: [symbol],
        retryState: { attempt: 1, canRetry: true },
        lastRefreshedAt: nowMs,
        degradationReason: "行情延迟"
      };
      await route.fulfill({ contentType: "application/json", body: JSON.stringify(body) });
    });
    await seedRestoredSnapshot(page);

    await page.goto("/");

    const note = page.getByTestId("chart-degradation-note");
    await expect(note).toBeVisible();
    await expect(note).toHaveClass(/notice--warning/);
    await expect(note).not.toHaveClass(/(^|\s)data-notice(\s|$)/);
  });
});
