# TDD Toolchain 控制面

## 定位

HarnessV2 不重新实现测试工具。HarnessV2 负责把开源测试工具接入控制面：根据任务和任务项风险生成测试义务，自动解析项目可用工具，自动安装白名单内缺失工具，运行工具并归一化工具链状态。`tdd-reviewer` 使用这些状态和报告判断测试是否足以支撑交付。

计划阶段如何设计 TDD 见 `.harness/docs/tdd-planning-contract.md`。本文件只定义工具链、证据和审查消费方式。

TDD 工具链必须接入 Harness 的统一有效性链路。它不单独决定交付是否完成，只负责满足 TDD 类 obligation，并把工具证据写入 Evidence Graph。

核心链路：

```text
AC / task / risk / surface
 -> Obligation Engine
 -> test_obligation
 -> toolchain_resolver
 -> auto_install / reuse existing tools
 -> toolchain_runner
 -> normalize_toolchain_status
 -> Evidence Graph
 -> Toolchain Gate
 -> tdd-reviewer
 -> Gate 策略
```

人的职责不是逐项批准测试工具。人只处理 Harness 越过安全边界的决策：外部服务、全局安装、密钥、白名单外工具、破坏性操作或重大框架迁移。

## 控制权

| 决策 | 决策者 | 依据 |
|------|--------|------|
| 本任务项需要哪些测试能力 | Harness 拆解 | AC / Scenario / risk_level / surfaces |
| 用哪个具体工具满足能力 | Harness toolchain resolver | 项目技术栈、已有工具、白名单 policy |
| 是否安装缺失工具 | Harness toolchain installer | `test_toolchain.install_policy` |
| 是否触发 Decision Gate | Harness Stage Gate / resolver | 是否越过 `decision_gate_required_for` |
| 工具链是否满足测试义务 | Harness Toolchain Gate | `toolchain-status.json` |
| 测试是否真的能抓错 | `tdd-reviewer` | `toolchain-status.json` + 工具报告 + 必要抽样 |

执行 Agent 不得随意降低 required tool 或 required evidence。缺 required evidence 时必须修复、安装工具、使用等价证据，或触发 Harness Toolchain Gate；不得把工具链缺口包装成 TDD 审查员的专业结论。

## 有效性边界

TDD 有效性不等于“有测试文件”或“测试命令通过”。TDD obligation 只有在以下条件同时满足时才可被视为支持交付：

- 测试映射到具体 AC / 任务项 / changed file。
- Red 失败来自目标行为未实现，而不是环境、fixture 或无关断言。
- Green / regression 结果来自当前 worktree 或当前 git ref。
- 关键 diff 有 coverage 或等价证据。
- 高风险行为有 mutation report 或 targeted fault injection 证明错误实现会红。
- `tdd-reviewer` 对 evidence 的有效性给出 Role Verdict。
- Gate 策略未发现缺证据、旧证据、矛盾证据或未处理 HOLD。

TDD 审查员只能判断测试是否能发现错误实现；它不能把缺工具、缺报告、缺 obligation 判成测试质量问题，也不能用整体 PASS 覆盖某个 AC 的证据缺口。

## Test Obligation

`execution-brief.md` 中每个任务项应声明 `test_obligation`。它描述测试能力义务，不描述具体工具。若旧项目或旧任务缺少该字段，Harness 会按 `harness.yaml` policy、任务项文本和授权路径推导；推导结果进入 `toolchain-plan.json` / `toolchain-status.json`，Stage Gate 记录 `inferred_test_obligation` WARN。

显式声明优先级最高。Harness 推导只用于保持升级兼容和避免人工决策，不允许执行 Agent 借此降低测试义务。

```yaml
test_obligation:
 risk_level: high
 surfaces:
 - backend_api
 - state_machine
 - frontend_ui
 - client_ui
 required_capabilities:
 - test_result
 - coverage
 - diff_coverage
 - mutation_or_fault_injection
 - ui_component_or_e2e
 evidence_required:
 - red_report
 - green_report
 - regression_report
 - diff_coverage_report
 - mutation_or_fault_report
 accepted_alternatives:
 mutation_or_fault_injection:
 - mutation_report
 - targeted_fault_injection_report
```

`risk_level` 的默认推导：

| 条件 | 风险 |
|------|------|
| 文案、样式、非行为性整理 | low |
| 普通业务逻辑、普通 API、普通 UI 状态 | medium |
| 权限、认证、状态机、并发、幂等、迁移、数据一致性、安全、支付、Agent 行为 | high |

`surfaces` 决定工具能力：

| surface | required 能力 |
|---------|---------------------|
| backend_api / backend_logic | test_result, coverage, diff_coverage |
| state_machine / concurrency / auth / permission / migration / data_model | mutation_or_fault_injection |
| frontend_ui / frontend_component / frontend_visual | ui_component_or_e2e |
| client_ui / client_logic / mobile / desktop | test_result, coverage（按平台工具可用性调整） |
| user_journey / realtime | e2e_ui |
| accessibility | a11y |
| public_api / openapi | api_contract |

## Adequacy Policy

测试充分性按 risk 和 surface 决定，不由执行 Agent 临时降低。

| 风险 / surface | 最小证据 | 阻断规则 |
|----------------|----------|----------|
| low / 文案、样式、非行为整理 | targeted test 或明确无需测试的 rationale | 行为变更却无测试证据则 FAIL |
| medium / 普通业务逻辑、API、UI 状态 | test_result + changed-file coverage 或等价 targeted evidence | 无 AC / 任务项映射则 FAIL |
| high / auth、权限、状态机、并发、幂等、迁移、数据一致性、安全、支付、Agent 行为 | test_result + diff_coverage + mutation_or_fault_injection | 缺 fault detection 证据则 FAIL |
| frontend_ui / frontend_component | component test 或 e2e_ui evidence | 只测渲染不测用户可观察结果则 HOLD |
| client_ui / client_logic / mobile / desktop | 平台测试、模拟器/设备运行或等价客户端验证 | 只改客户端行为但没有可重复运行证据则 HOLD |
| public_api / openapi | API contract 或 schema-based test | 缺请求/响应契约证据则 FAIL |

覆盖率只能作为辅助信号。覆盖率达标但断言不能抓错时，TDD 审查员必须 HOLD。

## Toolchain Policy

`harness.yaml` 中的 `test_toolchain` 是项目级默认 policy。白名单工具 required 时自动安装，不问人。

默认白名单：

| 语言/领域 | 工具 |
|-----------|------|
| Python | pytest, pytest-cov, coverage, diff-cover, pytest-json-report, mutmut |
| TypeScript/JavaScript | vitest, @vitest/coverage-v8, @testing-library/react, @testing-library/jest-dom, jsdom, @playwright/test, @stryker-mutator/core |
| Accessibility | axe-core, @axe-core/playwright, jest-axe |
| API contract | schemathesis |

Decision Gate 只在以下情况触发：

- 外部服务或付费服务
- 全局安装或系统级依赖
- secret / token / CI 权限
- 白名单外工具
- 破坏性操作
- 重大测试框架迁移
- 用户在任务契约明确禁止新增依赖

## 工具阶段

### 1. Resolver

`toolchain_resolver.py` 输入：

- `harness.yaml`
- `execution-brief.md` 的 `test_obligation`
- 项目依赖和脚本
- 当前 diff / baseline

输出：

- `toolchain-plan.json`
- required capabilities 与 selected tools 的映射
- obligation_source：`explicit` / `explicit_plus_inferred` / `inferred`
- missing required tools
- auto install actions
- Decision Gate reasons

### 2. Runner

`toolchain_runner.py` 输入 `toolchain-plan.json`，执行：

- Red / Green / Regression test commands
- coverage / diff coverage
- mutation / targeted fault injection
- UI/E2E/a11y/API contract checks

输出结构化 tool reports 到：

`harness-runtime/harness/traces/<mission-id>/tdd/tools/`

### 3. Normalizer

`normalize_toolchain_status.py` 归一化工具报告：

```yaml
toolchain_status:
 mission_id: <id>
 status: PASS | WARN | FAIL | BLOCKED
 obligations:
 - task_id: T001
 required_capabilities: [...]
 satisfied_capabilities: [...]
 missing_capabilities: [...]
 reports:
 test_result: [...]
 coverage: [...]
 diff_coverage: [...]
 mutation: [...]
 ui_e2e: [...]
 a11y: [...]
 api_contract: [...]
 toolchain_signals: [...]
 decision_gate_reasons: [...]
```

`toolchain-status.json` 是 Harness 控制面产物，不是 TDD 审查员 verdict。

Normalizer 还必须为 Evidence Graph 提供 evidence 节点所需字段：`evidence_id`、`mission_id`、`status`、`path`、`command`、`observed_at`、`git_ref`、`covers.obligations`、`covers.ac`、`covers.files`。

## 审查员消费方式

`tdd-reviewer` 必须先读 Evidence Graph 和 `toolchain-status.json`：

1. required 能力是否都有工具报告或等价证据。
2. Red 是否是目标行为失败，不是环境或 fixture 失败。
3. diff coverage 是否覆盖本次关键变更。
4. mutation / fault evidence 是否证明错误实现会红。
5. UI/E2E/a11y 是否覆盖用户可观察结果。
6. 测试缺口是否阻断交付。

审查员可以打开代码和测试文件，但只能作为工具证据不足或冲突时的补充。

工具未安装、白名单外依赖、命令未执行、报告缺失属于 Harness toolchain 缺口；TDD 审查员只能把它作为“无法评估”的边界说明或返回上游补证据，不能把它冒充为 `weak_assertion` / `missing_fault_detection`。

Role Verdict 必须按 obligation 输出：

```yaml
role_verdict:
 role: tdd-reviewer
 verdict: PASS | HOLD | PASS_WITH_RISK | BLOCKED
 reviewed_obligations:
 - OBL-001
 review_basis:
 evidence:
 - EVD-001
 findings:
 - id: FND-001
 category: weak_fault_detection
 blocks:
 - OBL-001
```

## Stage Gate

Stage Gate 做结构检查：

- 每个任务项都有显式或 Harness 推导的 `test_obligation`
- 缺 `test_obligation` 时必须有 Harness 推导 WARN；无法推导则 FAIL
- `toolchain_probe` / `toolchain_status` 产物存在
- `code-review.md` 中的 `toolchain_status.status` / `missing_capabilities` / `decision_gate_reasons` 必须与真实 `toolchain-status.json` 一致
- required capabilities 有 satisfied/missing 记录
- `tdd-reviewer` 消费了 toolchain status 产物
- HOLD 必须有 blocking 缺口

Stage Gate 不替代专业判断。

同时，Gate 策略必须阻断这些假象充分：

- 测试命令 PASS，但 Evidence Graph 中 AC 没有 result evidence。
- coverage PASS，但 high-risk obligation 缺 mutation 或 targeted fault evidence。
- Red 报告存在，但失败原因不是目标行为。
- 审查员 PASS，但底层 toolchain status 为 FAIL / BLOCKED。
- 使用旧 git_ref 或旧 worktree 证据。

## Validity Fixtures

TDD 工具链必须有 negative fixtures 验证自己能抓错：

| Fixture | 注入问题 | 期望 |
|---------|----------|------|
| weak-tdd | 只测 happy path，不测声明边界 | `tdd-reviewer` HOLD |
| fake-red | Red 来自环境错误或 fixture 错误 | Gate FAIL |
| no-fault-detection | high-risk obligation 缺 mutation / fault evidence | Gate FAIL |
| stale-test-evidence | 复用旧 git_ref 的测试结果 | Gate FAIL |
| coverage-with-weak-assertion | coverage 达标但断言不能抓错 | `tdd-reviewer` HOLD |
