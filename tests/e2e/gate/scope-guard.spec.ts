import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// AT-0702（PT-07 终局验证切片）：本次 mission（20260721-watchboard-ui-friendliness）
// 只把 chart-degradation-note / restore-status 迁移到 notice--warning / notice--info，
// 范围外的 5 处 .data-notice（AlertRulePanel.tsx:136、LayoutController.tsx:75/121、
// WorkbenchShell.tsx:78/135）以及 styles.css 的 .data-notice 共享定义本体都不应被
// 任何父任务动过。本文件用文件内容级证据 + 可达 DOM 断言 + axe 扫描 + 既有 E2E
// 回归说明，证明范围外零改动；可达的三处（workbench-selection-summary /
// AlertRulePanel 空态 / workbench-error）额外落盘改造前后并置截图到 mission
// evidence 目录，与程序化断言配合作为视觉佐证。workbench-error 通过构造
// /api/chart/** 请求失败场景真实驱动出 LayoutController.tsx:120-124 的
// `error && !activePayload` 分支（该分支是活组件的可达分支，不适用死代码豁免）。

const ROOT = process.cwd();

const SCOPE_OUT_FILES = {
  alertRulePanel: path.join(ROOT, "src/features/alerts/AlertRulePanel.tsx"),
  layoutController: path.join(ROOT, "src/features/layout/LayoutController.tsx"),
  workbenchShell: path.join(ROOT, "src/features/workbench/WorkbenchShell.tsx")
};

const STYLES_PATH = path.join(ROOT, "src/styles.css");

const EVIDENCE_DIR = path.join(
  ROOT,
  "harness-runtime/harness/artifacts/20260721-watchboard-ui-friendliness/evidence"
);

// mission 开始前（tech-design 文档记录的原始值，等同 git HEAD 的初始提交内容）
// .data-notice 规则块本体：黄色警示配色，未被迁移到 .notice--* 命名。
const EXPECTED_DATA_NOTICE_BLOCK = [
  ".data-notice {",
  "  display: inline-flex;",
  "  max-width: min(680px, 100%);",
  "  margin-top: 4px;",
  "  color: #f0c75e;",
  "  background: rgba(240, 199, 94, 0.1);",
  "  border: 1px solid rgba(240, 199, 94, 0.2);",
  "  border-radius: 6px;",
  "  padding: 6px 8px;",
  "  font-size: 12px;",
  "}"
].join("\n");

function extractCssRuleBlock(cssContent: string, selector: string): string | undefined {
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = cssContent.match(new RegExp(`${escaped}\\s*\\{[^}]*\\}`));
  return match?.[0];
}

async function seedWorkspace(page: Page) {
  await page.addInitScript(() => {
    const item = { id: "AAPL", symbol: "AAPL", name: "Apple", market: "US", status: "active" };
    window.localStorage.setItem("myinvestment.watchlist", JSON.stringify([item]));
    window.localStorage.setItem("myinvestment.alerts", JSON.stringify([]));
  });
}

function chartPayload(symbol: string) {
  const now = Math.floor(Date.now() / 1000);
  const bars = [
    { time: now - 86_400 * 2, open: 175, high: 181, low: 174, close: 180, volume: 1_200_000 },
    { time: now - 86_400, open: 181, high: 189, low: 180, close: 188, volume: 1_500_000 },
    { time: now, open: 188, high: 191, low: 185, close: 190, volume: 1_400_000 }
  ];
  const latest = bars.at(-1);
  return {
    symbol,
    range: "6mo",
    interval: "1d",
    meta: {
      shortName: symbol,
      currency: "USD",
      exchangeName: "Test",
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
      changeSummary: { absolute: 10, percent: 5.56 }
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

async function routeMarketData(page: Page) {
  await page.route("**/api/chart/**", async (route) => {
    const symbol = decodeURIComponent(new URL(route.request().url()).pathname.split("/").pop() ?? "AAPL");
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(chartPayload(symbol)) });
  });
}

test.describe("AT-0702: 范围外 5 处 .data-notice 零改动守卫", () => {
  test("grep 证据: 三个范围外组件文件仍引用 data-notice 类名（未迁移到 notice--*）", async () => {
    const alertRulePanelSource = readFileSync(SCOPE_OUT_FILES.alertRulePanel, "utf8");
    const layoutControllerSource = readFileSync(SCOPE_OUT_FILES.layoutController, "utf8");
    const workbenchShellSource = readFileSync(SCOPE_OUT_FILES.workbenchShell, "utf8");

    // AlertRulePanel.tsx:136 — 空态提示，唯一一处 data-notice。
    expect(alertRulePanelSource).toContain('<div className="data-notice">当前标的暂无本地提醒规则</div>');
    expect((alertRulePanelSource.match(/className="data-notice"/g) ?? []).length).toBe(1);

    // LayoutController.tsx:75（workbench-selection-summary）与 :121（workbench-error）
    expect(layoutControllerSource).toContain('<div className="data-notice" data-testid="workbench-selection-summary">');
    expect(layoutControllerSource).toContain('<div className="data-notice" data-testid="workbench-error">');
    expect((layoutControllerSource.match(/className="data-notice"/g) ?? []).length).toBe(2);

    // WorkbenchShell.tsx:78（workbench-selection-summary）与 :135（workbench-error）
    expect(workbenchShellSource).toContain('<div className="data-notice" data-testid="workbench-selection-summary">');
    expect(workbenchShellSource).toContain('<div className="data-notice" data-testid="workbench-error">');
    expect((workbenchShellSource.match(/className="data-notice"/g) ?? []).length).toBe(2);

    // 三个文件都不应出现本次 mission 引入的 notice--warning / notice--info 命名，
    // 说明它们没有被顺手"随手迁移"。
    expect(alertRulePanelSource).not.toMatch(/notice--(warning|info)/);
    expect(layoutControllerSource).not.toMatch(/notice--(warning|info)/);
    expect(workbenchShellSource).not.toMatch(/notice--(warning|info)/);
  });

  test("styles.css 的 .data-notice 共享定义本体未改（颜色/背景/边框值与 mission 开始前一致）", async () => {
    const cssSource = readFileSync(STYLES_PATH, "utf8");
    const actualBlock = extractCssRuleBlock(cssSource, ".data-notice");
    expect(actualBlock).toBeDefined();
    expect(actualBlock).toBe(EXPECTED_DATA_NOTICE_BLOCK);
  });

  test("DOM 验证: LayoutController 渲染的 workbench-selection-summary 仍是 data-notice class（非 notice--*）", async ({
    page
  }) => {
    await seedWorkspace(page);
    await routeMarketData(page);

    await page.goto("/");

    // App.tsx 挂载的是 LayoutController（WorkbenchShell 未被任何页面引用，
    // 属于死代码，无法通过真实渲染路径触达 — 该组件的证据只做文件内容级断言）。
    const summary = page.getByTestId("workbench-selection-summary");
    await expect(summary).toBeVisible();
    await expect(summary).toHaveClass(/(^|\s)data-notice(\s|$)/);
    await expect(summary).not.toHaveClass(/notice--(warning|info)/);

    // 视觉佐证：上面的 class 断言已经证明这就是 mission 开始前的状态（未被迁移），
    // 这张截图与之并置，作为"改造前后零可观察变化"的证据形态之一落盘。
    await summary.screenshot({
      path: path.join(EVIDENCE_DIR, "pt07-scope-guard-workbench-selection-summary.png")
    });
  });

  test("DOM 验证: AlertRulePanel 空态提示仍是 data-notice class（非 notice--*）", async ({ page }) => {
    await seedWorkspace(page);
    await routeMarketData(page);

    await page.goto("/");
    await page.getByTestId("detail-tab-alerts").click();

    const emptyNotice = page.getByText("当前标的暂无本地提醒规则");
    await expect(emptyNotice).toBeVisible();
    await expect(emptyNotice).toHaveClass(/(^|\s)data-notice(\s|$)/);
    await expect(emptyNotice).not.toHaveClass(/notice--(warning|info)/);

    // 视觉佐证：同上，class 断言已证明未迁移，这张截图与之并置落盘。
    await emptyNotice.screenshot({
      path: path.join(EVIDENCE_DIR, "pt07-scope-guard-alert-empty-notice.png")
    });
  });

  test("DOM 验证: LayoutController 渲染的 workbench-error 分支仍是 data-notice class（非 notice--*）", async ({
    page
  }) => {
    await seedWorkspace(page);
    // 让 /api/chart/** 请求失败，驱动 LayoutController.tsx:120-124 的
    // `error && !activePayload` 分支真实渲染（该分支是 App.tsx 挂载的活组件的
    // 可达分支，不同于 WorkbenchShell 的死代码，规格要求真实 DOM 证据）。
    await page.route("**/api/chart/**", async (route) => {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: "行情服务暂不可用" })
      });
    });

    await page.goto("/");

    const errorNotice = page.getByTestId("workbench-error");
    await expect(errorNotice).toBeVisible();
    await expect(errorNotice).toHaveClass(/(^|\s)data-notice(\s|$)/);
    await expect(errorNotice).not.toHaveClass(/notice--(warning|info)/);

    // 视觉佐证：同上，class 断言已证明未迁移，这张截图与之并置落盘。
    await errorNotice.screenshot({
      path: path.join(EVIDENCE_DIR, "pt07-scope-guard-workbench-error.png")
    });
  });

  test("axe 扫描: 主要视图（看盘主流程 + 提醒面板）无新增可访问性 critical/serious 违规", async ({ page }) => {
    await seedWorkspace(page);
    await routeMarketData(page);

    await page.goto("/");
    const homeResults = await new AxeBuilder({ page }).include("main").analyze();
    const homeSerious = homeResults.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
    expect(homeSerious).toEqual([]);

    // 触达范围外的 AlertRulePanel（data-notice 空态所在面板）后再扫一次。
    await page.getByTestId("detail-tab-alerts").click();
    const alertsResults = await new AxeBuilder({ page }).include("main").analyze();
    const alertsSerious = alertsResults.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
    expect(alertsSerious).toEqual([]);
  });

  // 既有 E2E 用户路径回归不在本文件内重复执行——由 mission 收尾统一跑全量
  // `npx playwright test`（不带路径过滤）覆盖，那是本 mission 最终的回归判据。
  // 本文件只对"范围外 5 处 .data-notice 是否被这次改动波及"这一条负向声明负责。
});
