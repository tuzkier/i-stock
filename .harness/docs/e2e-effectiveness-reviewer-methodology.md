# E2E Effectiveness Reviewer Methodology

本文定义 HarnessV2 安装后可执行的 E2E 有效性审查方法。它不是工具安装说明，也不是 Playwright / Cypress checklist，而是 `e2e-reviewer` 判断 E2E 是否做到位、充分、准确、可靠的依据。

## 定位

E2E 有效性审查回答一个问题：

> 当前 E2E 是否能证明真实用户路径正确，并且在关键跨层行为被破坏时失败？

| 层 | 负责 |
|----|------|
| Harness E2E control plane | obligation 推导、工具选择、安装边界、运行、report / trace / screenshot / video 归一化、`e2e-status.json` 一致性 |
| E2E effectiveness reviewer | 判断 E2E 是否覆盖真实用户目标、是否断言用户可观察结果、是否足够真实、稳定、可诊断 |
| verify / stage-gate | 验收结果证据、验收追溯、contract 与 artifact 一致性 |

Reviewer 不把工具缺失、report 缺失、artifact 路径错误当作专家 finding；这些属于控制面。Reviewer 只判断测试设计和测试证据是否真的证明用户路径。

## 业界依据

| 来源 | 可借鉴原则 | Harness 落点 |
|------|------------|--------------|
| Playwright Locators | locator 应尽量接近用户感知，避免长 CSS / XPath 链和实现细节定位 | `Diagnostics` / `brittle_flow` |
| Playwright Assertions | web-first assertions 会自动重试，适合等待 UI 达到期望状态 | `Oracle Quality` / `Repeatability` |
| Playwright Trace Viewer | trace 可回放 action、DOM snapshot、network 等上下文 | `Diagnostics` |
| Cypress Best Practices | spec 隔离、程序化登录、控制应用状态、稳定 selector | `Repeatability` / `State Reality` |
| Cypress Test Isolation | 测试应独立运行，不能依赖前一个测试留下的状态 | `Repeatability` |
| Testing Library principles | 测试应尽量像用户使用应用一样，包括 accessibility interface | `Journey Modeling` / `Oracle Quality` |
| Cucumber / Gherkin | Given 描述上下文，When 描述动作，Then 描述可观察结果 | `Journey Modeling` / `Oracle Quality` |
| Google Testing Blog: Test Sizes | E2E 属于 large/system test，成本高、反馈慢、定位难 | `Necessity` / `Risk Coverage` |
| Google Testing Blog: Just Say No to More E2E Tests | E2E 不应泛滥，应覆盖关键用户路径而不是替代低层测试 | `Necessity` / `overbroad_flow` |
| Google Testing Blog: Flaky Tests | large tests 更易 flaky，可靠性本身是质量门槛 | `Repeatability` |
| Playwright accessibility + axe-core | 可对浏览器页面做 accessibility smoke，但不能替代完整人工无障碍验证 | `Accessibility Smoke` |
| W3C Accessible Name / ARIA guidance | role / accessible name 支撑用户语义定位和可访问断言 | `Diagnostics` / `Oracle Quality` |

参考链接：

- Playwright Locators: https://playwright.dev/docs/locators
- Playwright Assertions: https://playwright.dev/docs/test-assertions
- Playwright Trace Viewer: https://playwright.dev/docs/trace-viewer-intro
- Cypress Best Practices: https://docs.cypress.io/app/core-concepts/best-practices
- Cypress Test Isolation: https://docs.cypress.io/app/core-concepts/test-isolation
- Testing Library Accessibility API: https://testing-library.com/docs/dom-testing-library/api-accessibility/
- Cucumber Gherkin Reference: https://cucumber.io/docs/gherkin/reference
- Google Testing Blog, Test Sizes: https://testing.googleblog.com/2010/12/test-sizes.html
- Google Testing Blog, Just Say No to More End-to-End Tests: https://testing.googleblog.com/2015/04/just-say-no-to-more-end-to-end-tests.html
- Google Testing Blog, Where Do Our Flaky Tests Come From: https://testing.googleblog.com/2017/04/where-do-our-flaky-tests-come-from.html
- Playwright Accessibility Testing: https://playwright.dev/docs/next/accessibility-testing
- W3C Accessible Names and Descriptions: https://www.w3.org/WAI/ARIA/apg/practices/names-and-descriptions/

## 专家判断模型

E2E 有效性不是“有测试文件 + 命令通过”。Reviewer 必须按以下模型判断：

| 维度 | 判断问题 | High finding 示例 |
|------|----------|-------------------|
| Necessity | 这个验收场景 / user journey 是否真的需要浏览器级证明，还是已有低层证据足够 | 关键用户旅程没有 E2E，也没有有效替代 |
| Journey Modeling | 测试是否按用户目标和业务流程建模，而不是按组件实现细节拼步骤 | 测试只打开页面、点击控件，未覆盖完整用户意图 |
| Oracle Quality | 断言 oracle 是否能判定真实用户结果正确 | 只断言 URL、HTTP 200、元素存在或 mock called |
| State Reality | 数据、权限、路由、API 和持久化状态是否足够真实 | 只测前端假状态或无意义 mock |
| Risk Coverage | 本次风险涉及的权限、失败、空状态、realtime、刷新、边界是否覆盖 | auth / realtime / workspace 只有 happy path |
| Repeatability | 等待、隔离、fixture、teardown 是否让测试可重复运行 | hard sleep、顺序依赖、脏数据、共享账号污染 |
| Diagnostics | 失败时是否能定位用户路径、断言、数据和浏览器上下文 | 无 trace / screenshot 语义，失败信息无法定位 |
| Maintainability | 测试是否稳定表达用户行为，能随 UI 重构保持有效 | CSS / XPath 绑定实现细节，单测过宽且失败不可定位 |

## 问题类型

High / HOLD finding 必须使用明确类型：

| 类型 | 含义 |
|------|------|
| `missing_user_journey` | 关键验收场景 / P0-P1 用户路径没有 E2E 或有效替代 |
| `weak_user_result_assertion` | 有 E2E，但 oracle 不能证明用户可观察结果 |
| `data_reality_gap` | 测试数据、API、权限或持久化状态不真实 |
| `missing_negative_path` | 本次风险要求负向路径，但 E2E 只有 happy path |
| `missing_realtime_proof` | realtime / invalidation / refresh 行为没有用户结果证明 |
| `unreliable_e2e` | 等待、隔离、fixture 或状态污染让 E2E 不可重复 |
| `diagnostics_gap` | 失败不可诊断，无法定位用户路径或跨层状态 |
| `brittle_flow` | 选择器或步骤绑定实现细节，重构时易误报/漏报 |
| `overbroad_flow` | 一个 E2E 覆盖多个无关行为，失败不可定位 |
| `accepted_alternative_invalid` | 替代证据不能证明同一用户结果 |

## 审查流程

1. 先读 `e2e-status.json`，确认 obligations、runs、artifacts、missing_capabilities、decision_gate_reasons。
2. 把控制面缺口移交 Harness gate，不作为 E2E effectiveness finding。
3. 建立 `验收场景 / Scenario / Task -> user journey -> E2E test -> oracle -> evidence` 矩阵。
4. 对每条关键用户路径判断：如果关键行为被破坏，当前 E2E 是否会失败。
5. 按专家判断模型给出 `PASS` / `PASS_WITH_RISK` / `HOLD`。
6. 每个 High 必须说明为什么这是 E2E effectiveness 问题，而不是 correctness、TDD、verify 或 stage-gate 问题。

## 与工具的关系

Harness 默认支持 Playwright / Cypress / axe-core，但 reviewer 不应把工具偏好当作方法论本身：

- Playwright / Cypress 是执行浏览器路径的工具。
- Testing Library / accessible locators 是用户语义定位方法。
- Gherkin / Given-When-Then 是用户场景建模方法。
- axe-core 是 accessibility smoke 的自动化工具。
- trace / screenshot / video 是失败诊断证据。

工具可替换；方法论不应替换。
