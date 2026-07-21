# TDD Planning Contract

## 定位

`execution-brief.md` 不是执行后的测试报告；它负责在 execute 前设计 TDD。计划阶段必须把测试要证明什么、先红在哪里、绿到哪里为止、哪些行为不许顺手扩写、如何证明测试能抓错写清楚。

TDD planning 的输出被 execute、code-review、tdd-reviewer 和 Stage Gate 共同消费：

```text
AC / Scenario / risk / surface
 -> execution-brief Parent task TDD boundary
 -> execution-brief Atomic Task Queue TDD scope
 -> execute Red / Green / Refactor evidence
 -> tdd-reviewer effectiveness review
```

## 分层职责

| 产物 | TDD 职责 | 不做什么 |
|------|----------|----------|
| `execution-brief.md` | 定义 Parent task 的行为边界、验收追溯、证据义务和 TDD 总边界 | 不写完整测试文件，不替代 Atomic Task 的文件级计划 |
| `contracts/execution-brief.contract.yaml` | 用结构化 `tdd_scope` 声明每个 task 的 TDD 设计契约 | 不记录执行后的 Red/Green 结果 |
| `execution-brief.md#Execution Units` | 为每个 Atomic Task 设计可执行的 Red / Green / Refactor 范围、断言、数据和命令 | 不写可复制粘贴的完整实现或完整测试 |
| `execution-result.md` | 记录实际 Red / Green / Regression / toolchain evidence | 不回填或改写计划边界 |

## TDD Scope 必填项

每个会进入 execute 的 task / Atomic Task 必须包含以下字段。不能只写“补测试”“按 TDD”或“覆盖 AC”。

| 字段 | 说明 |
|------|------|
| `behavior_under_test` | 本任务要证明的可观察行为，必须追溯到 AC / Scenario / Parent task |
| `red_scope` | Red 阶段先写哪些失败测试；失败原因必须指向目标行为缺失、缺陷复现或边界未实现 |
| `green_scope` | Green 阶段允许实现到哪个行为边界；不能借通过测试扩写相邻需求 |
| `refactor_scope` | 绿灯后允许清理哪些结构；不得改变公共行为、接口、数据契约或未授权路径 |
| `out_of_scope` | 明确排除的行为、surface、历史问题、性能优化、重构或未来扩展 |
| `required_assertions` | 必须断言的返回值、状态、错误、权限、持久化、事件、UI 或副作用 |
| `test_data_boundary` | fixture / seed 数据形状、必要前置状态、隔离要求和禁止依赖的外部状态 |
| `test_doubles_boundary` | 允许和禁止的 mock / stub / fake；说明哪些必须走真实集成或 contract |
| `commands` | Red、Green、Regression 的运行目录、命令、预期失败/通过信号；若 Parent task 已委托 Atomic Task Queue，写队列引用 |
| `validity_probe` | 如何证明测试能抓错。高风险行为必须声明 mutation、targeted fault injection、旧缺陷复现或等价证明 |

## 设计顺序

1. 从 AC / Scenario 提取行为模型：输入空间、决策规则、状态迁移、错误路径和不变量。
2. 根据 risk / surface 决定测试层级和 `test_obligation`，不得由执行 Agent 临时降低。
3. 先写 Red 目标：测试名、断言、测试数据和预期失败原因。
4. 再写 Green 边界：只实现让 Red 变绿所需的真实行为。
5. 再写 Refactor 边界：允许整理的结构和禁止触碰的契约。
6. 为关键行为设计 fault detection：反转条件、删除权限判断、漏字段、改状态码、改状态迁移、吞异常等 targeted probe。
7. 写清命令和证据：Red / Green / Regression / coverage / diff coverage / mutation 或等价证据。

## Parent Task vs Atomic Task

Parent task 永远是交付切片 / Work Graph TASK 边界，只保留行为边界、完成边界、DoD、Parent 级 TDD scope 和 evidence 权威。

Atomic Task 永远是 execute 的实际执行单位，必须内嵌在对应 Parent task 的 `atomic_task_queue.execution_units[]` 下。简单 Parent task 也至少有一个 Atomic Task；复杂 Parent task 拆成多个 Atomic Tasks。

- breakdown 首次写 `execution-brief.md` 前必须完成 Parent task + Atomic Task Queue 的联合设计。
- 每个会改生产代码的 Atomic Task 必须有独立 TDD scope。
- Atomic Task 的 TDD scope 不得扩大 Parent task 的行为边界。

## 反例

| 错误写法 | 问题 | 正确写法 |
|----------|------|----------|
| “补单元测试，确保通过” | 没有 Red 目标、断言和抓错能力 | 写明行为、测试数据、断言、预期失败原因和 fault signal |
| “实现接口并测试 happy path” | 忽略错误路径和边界 | 按 AC / Scenario 写合法、非法、权限、状态、数据边界 |
| “Green 阶段完成相关能力” | 允许顺手扩写 | Green scope 只覆盖当前 task，新增行为必须回上游规格 |
| “使用 mock 隔离依赖” | 可能只测试 mock 行为 | 写明哪些依赖可 mock，哪些必须真实集成或 contract |
| “有 coverage 即可” | 覆盖不等于能抓错 | 高风险行为必须有 fault / mutation / 等价证明 |

## 审查口径

`execution-plan-effectiveness-reviewer` 审查 plan 时，必须检查 TDD scope 是否足以让 execute 按 Red → Green → Refactor 执行，并能被 `tdd-reviewer` 后续验证。缺少 Red 失败目标、Green 边界、断言、测试数据边界或 fault signal 的计划不能进入 execute。
