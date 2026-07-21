---
name: e2e-setup
description: '当 Harness 项目级检查发现 e2e.enabled=true 且 tests/e2e/ 目录不存在时自动触发，用于初始化项目 E2E 测试框架；每个项目只运行一次，不触发 Stage Gate，不产出阶段文档，结果写入 project-context.md。'
---

按 [workflow.md](workflow.md) 执行详细步骤。
# E2E Setup 工作流

> 本技能是项目级一次性初始化，不是 按任务步骤。
> 完成后自治循环的项目级检查条件（tests/e2e/ 存在）变为 true，后续循环跳过。

---

## 初始化

1. 调用 `harness-cli` 执行 `harness config snapshot --json`，提取 E2E 策略摘要；不得直接读取 `harness-runtime/config/harness.yaml`。若 CLI 尚未返回 E2E 具体字段，记录 CLI 能力缺口并使用默认值：
 - `e2e.framework`（playwright / cypress）
 - `e2e.base_url`
 - `e2e.test_dir`（默认 `tests/e2e`）
 - `e2e.browser_automation`
2. 调用 `harness-cli` 执行 `harness context check --json`；PASS 则读取 `project-context.md` 了解项目技术栈；FAIL 时按 `project-context` 规则处理（init 或在 e2e-setup evidence 中记录 `inputs_missing.project_context=true`），不得静默继续

---

## 执行

<workflow skill="e2e-setup" version="2">

<step n="1" goal="确认框架并安装依赖">
 - 根据 e2e.framework 执行对应安装：

 **Playwright（默认）：**
 ```bash
 npm install --save-dev @playwright/test
 npx playwright install --with-deps chromium
 ```

 **Cypress：**
 ```bash
 npm install --save-dev cypress
 ```

 - 条件：安装失败
 - 报告依赖安装错误，等待用户处理后继续
</step>

<step n="2" goal="生成框架配置文件">

 **Playwright — 生成 `playwright.config.ts`：**

 ```typescript
 import { defineConfig, devices } from '@playwright/test';

 export default defineConfig({
 testDir: './<test_dir>',
 fullyParallel: true,
 forbidOnly: !!process.env.CI,
 retries: process.env.CI ? 2 : 0,
 workers: process.env.CI ? 1 : undefined,
 reporter: 'html',
 use: {
 baseURL: '<base_url>',
 trace: 'on-first-retry',
 screenshot: 'only-on-failure',
 },
 projects: [
 { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
 ],
 });
 ```

 将 `<test_dir>` 和 `<base_url>` 替换为 `harness config snapshot` 返回的实际值或默认值。

 **Cypress — 生成 `cypress.config.ts`：**

 ```typescript
 import { defineConfig } from 'cypress';

 export default defineConfig({
 e2e: {
 baseUrl: '<base_url>',
 specPattern: '<test_dir>/**/*.cy.ts',
 supportFile: '<test_dir>/support/index.ts',
 },
 });
 ```
</step>

<step n="3" goal="建立目录结构和支持文件">
 - 创建以下通用目录（Playwright 和 Cypress 共用）：

 ```
 <test_dir>/
 ├── support/
 │ ├── fixtures/
 │ │ └── base.ts ← 基础 fixture / 命令骨架
 │ ├── factories/
 │ │ └── index.ts ← 测试数据工厂入口（预置 faker）
 │ └── helpers/
 │ └── index.ts ← 通用工具函数
 └── .gitkeep
 ```

 **若 framework = playwright：生成 `support/fixtures/base.ts`**

 ```typescript
 import { test as base, expect } from '@playwright/test';

 // 基础 fixture — 预置 network-first 拦截骨架
 // 扩展时在此添加 auth、mock 等 fixture
 export const test = base.extend<{
 // 示例：authenticated: void;
 }>({
 // authenticated: async ({ page }, use) => {
 // await page.route('**/api/auth/**', route => route.fulfill({ ... }));
 // await use();
 // },
 });

 export { expect };
 ```

 **若 framework = cypress：生成 `support/fixtures/base.ts` 和 `support/index.ts`**

 ```typescript
 // support/fixtures/base.ts — Cypress 自定义命令骨架
 // 在 cypress/support/commands.ts 中引入
 // 示例：
 // Cypress.Commands.add('login', (email, password) => { ... });
 ```

 ```typescript
 // support/index.ts — Cypress support 入口
 import './fixtures/base';
 // import './commands';
 ```

 **生成 `support/factories/index.ts`（通用）：**

 ```typescript
 // 测试数据工厂 — 使用 @faker-js/faker 生成随机数据，避免硬编码
 // import { faker } from '@faker-js/faker';
 // export const createUser = (overrides = {}) => ({
 // email: faker.internet.email(),
 // name: faker.person.fullName(),
 // ...overrides,
 // });
 ```

 - 安装 faker（可选，若项目中已有则跳过）：
 ```bash
 npm install --save-dev @faker-js/faker
 ```
</step>

<step n="4" goal="更新 package.json 和 .gitignore">
 - 在 `package.json` 的 `scripts` 中新增 E2E 快捷命令（若已有则跳过）：

 **Playwright：**
 ```json
 {
 "scripts": {
 "e2e": "playwright test",
 "e2e:debug": "playwright test --headed",
 "e2e:ui": "playwright test --ui"
 }
 }
 ```

 **Cypress：**
 ```json
 {
 "scripts": {
 "e2e": "cypress run",
 "e2e:open": "cypress open"
 }
 }
 ```

 - 在 `.gitignore` 中新增测试产物忽略项（若已有则跳过）：

 **Playwright：**
 ```
 # Playwright 测试产物
 test-results/
 playwright-report/
 .playwright/
 ```

 **Cypress：**
 ```
 # Cypress 测试产物
 cypress/screenshots/
 cypress/videos/
 cypress/downloads/
 ```

 - 条件：package.json 不存在（非 Node 项目）
 - 跳过本步骤，在 project-context.md 中记录手动运行命令
</step>

<step n="5" goal="更新 project-context.md">
 - 在 project-context.md 中新增或更新 E2E 约定章节，根据框架类型填写对应内容：

 **若 framework = playwright：**
 ```markdown
 ## E2E 测试约定

 - **框架**：Playwright
 - **配置文件**：playwright.config.ts
 - **测试目录**：<test_dir>/
 - **运行命令**：
 - 全套：`npm run e2e` / `npx playwright test`
 - 单文件：`npx playwright test <test_dir>/<feature>.spec.ts`
 - 调试模式：`npm run e2e:debug`（有浏览器 UI）
 - **Base URL**：<base_url>
 - **选择器规范**：只允许 getByRole / getByLabel / getByText / getByTestId，禁止 CSS class / XPath
 - **network-first**：page.route() 必须在 page.goto() 之前调用
 - **Fixture 目录**：<test_dir>/support/fixtures/
 - **Factory 目录**：<test_dir>/support/factories/
 ```

 **若 framework = cypress：**
 ```markdown
 ## E2E 测试约定

 - **框架**：Cypress
 - **配置文件**：cypress.config.ts
 - **测试目录**：<test_dir>/
 - **运行命令**：
 - 全套：`npm run e2e` / `npx cypress run`
 - 交互模式：`npm run e2e:open`
 - **Base URL**：<base_url>
 - **选择器规范**：只允许 cy.findByRole / cy.findByLabel / cy.findByText / cy.findByTestId（需 @testing-library/cypress），禁止 CSS class / XPath
 - **network-first**：cy.intercept() 必须在 cy.visit() 之前调用
 - **Fixture 目录**：<test_dir>/support/fixtures/
 - **Factory 目录**：<test_dir>/support/factories/
 ```

 将所有 `<占位符>` 替换为 `harness config snapshot` 返回的实际值或默认值。
</step>

<step n="6" goal="验证安装结果">
 - 运行框架自检命令，确认安装成功：

 **Playwright：**
 ```bash
 npx playwright --version
 ```

 **Cypress：**
 ```bash
 npx cypress --version
 ```

 - 条件：命令报错
 - 报告错误详情，停止，等待用户介入

 - 条件：命令成功
 - 输出确认信息：框架版本、测试目录、base_url
</step>

<step n="7" goal="完成报告">
 - 向用户输出初始化摘要：

 ```
 ✅ E2E 框架初始化完成

 框架：<framework> <version>
 测试目录：<test_dir>/
 Base URL：<base_url>

 目录结构：
 <test_dir>/support/fixtures/base.ts
 <test_dir>/support/factories/index.ts
 <test_dir>/support/helpers/index.ts

 下一步：
 - 在 interaction.md 中定义 E2E 场景和 data-testid 清单
 - execute 阶段将按 ATDD 模式写 test.skip() 测试
 ```

 - 不触发 Stage Gate，直接返回自治循环，继续下一个优先级检查
</step>

</workflow>
