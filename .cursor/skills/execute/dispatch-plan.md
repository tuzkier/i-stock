# execute dispatch plan

## Goal

在 execute 阶段每个 Atomic Task 开始实现前，生成可审计的 dispatch plan，约束执行者选择、角色包引用、brief范围、证据要求、write scope、并行边界和停止条件。执行单位只能是 `execution-brief.md#Execution Units` 中某个 Parent task 内的 Atomic Task；Parent task 只提供边界、顺序、DoD、规格引用和证据权威。

`execute` 是唯一执行 skill；本文件只是 `execute` 内部的计划生成步骤。dispatch plan 描述“谁以什么 role prompt package、在什么范围内使用 `execute` skill”。专家 Agent 的 role prompt package 必须由 execute 主流程读取，并作为子 Agent prompt 第一段原样注入；dispatch plan 只记录 package 来源、Task Envelope 边界和调度关系，不得生成“专家 Agent 独立执行整个 Atomic Task”的临时 prompt。本文件不执行、不用 `spawn_agent` 派发、不推进 execute 状态机；它只给 `execute` 主流程提供可消费的调度上下文。

**Your Role:** 你是 execute 调度规划器。你只生成 dispatch plan 和brief边界，不直接实现代码，也不把专家 Agent 当成独立执行入口。

---

<workflow skill="execute-dispatch-plan" version="2">

<step n="1" goal="准备输入">
 - 按「输入准备」读取当前 Atomic Task、Parent task、execution-brief / action contract 绑定、规格引用、scope、依赖和风险字段。
</step>

<step n="2" goal="程序化解析">
 - 按「Step 1：程序化解析」调用 `execute_role_policy.py`，只解析角色、证据、未知 surface、blockers 和 rationale。
</step>

<step n="3" goal="补齐调度上下文">
 - 按「Step 2：补齐固定调度上下文」从当前 Atomic Task / Parent 绑定补齐 queue status、scope、依赖、并行边界和 `execution_context`。
</step>

<step n="4" goal="执行阻塞检查">
 - 按「Step 3：阻塞检查」设置 `blocked`、`blockers` 和 `conflict_risk`；阻塞时不得继续派发。
</step>

<step n="5" goal="生成brief边界">
 - 按「Step 4：生成brief边界」为 primary、supporting 和 reviewer 生成可审计brief。
</step>

<step n="6" goal="输出 dispatch plan">
 - 按「Step 5：输出 dispatch plan」输出结构化 YAML。
 - Hard gate：`execute` 不得在缺少 dispatch plan 的情况下用 `spawn_agent` 调用执行子 Agent。
 - Hard gate：dispatch plan 为 `blocked=true` 时，必须先解决 blockers 或进入 Decision Gate，不得继续实现。
 - Hard gate：dispatch plan 缺少 `execution_context.skill=execute` 或缺少 role package 引用时，不得派发可写 Agent；execute 主流程用 `spawn_agent` 派发时未注入 role prompt package 正文，也不得派发。这类 Task Envelope 不可审计，必须回到 dispatch plan 修正。
</step>

</workflow>

---

## 输入准备

1. 读取当前执行单位完整文本，不只读取标题。
2. 同时读取其 Parent task 的完整文本、完成边界、DoD、规格引用、required evidence 和前序依赖摘要。
3. 提取 `task_id` / Atomic Task ID、surface / `user_surfaces`、risk、`test_obligation`、`e2e_obligation`、规格引用和 DoD。
4. 读取 execution-brief 的全局约束和当前 Parent task 的前序依赖摘要。
5. 读取 execution-brief / action contract 中当前 Parent task 的 parent-local `atomic_task_queue` 绑定。
6. 读取 `harness-runtime/harness/artifacts/<mission-id>/breakdown/execution-brief.md` 的 `Execution Units` 中当前 Parent task 内的 Atomic Task 片段，并确认当前执行单位来自该片段。
7. 若 `spec.enabled=true`，确认当前执行单位继承的 Parent task 是否有差量规格 Scenario 引用。
8. 从执行单位、Atomic Task 片段和测试要求中提取 `write_scope`、`read_scope`、`depends_on`、候选 `parallel_group` 和 `conflict_risk`；无法确认时显式标注为空或 high risk，交给 execute 主流程保守串行。

## Step 1：程序化解析

调用策略引擎：

```bash
python3 .harness/common/skills/execute/scripts/execute_role_policy.py --surface <surface> --json
```

若 task item 已被导出为 JSON：

```bash
python3 .harness/common/skills/execute/scripts/execute_role_policy.py --task-json <task.json> --json
```

解析结果必须包含：

- `primary_executors`
- `supporting_executors`
- `reviewers`
- `required_evidence`
- `missing_surfaces`
- `blocked`
- `blockers`
- `rationale`

## Step 2：补齐固定调度上下文

1. 确认 `spec-reviewer` 存在于 `reviewers`，除非当前任务明确不是 SDD task item；若策略引擎已返回则不得重复添加。
2. 保留策略引擎返回的条件 reviewer，例如 `security-reviewer`、`data-migration-reviewer`。
3. 不加入已废止的质量审查或视觉工程/审查角色。
4. `primary_executors`、`supporting_executors`、`reviewers` 是必须完整执行的列表，不能只取第一个角色生成调度计划；它们默认由 execute 主流程按 barrier 并行消费，除非 `depends_on` / `write_scope` / `conflict_risk` 证明必须串行。
5. 从当前 Atomic Task 和 Parent 绑定补齐 `atomic_task_queue_status`、`write_scope`、`read_scope`、`depends_on`、`parallel_group` 和 `conflict_risk`；这些字段不是 `execute_role_policy.py` 的职责。
6. 设置 `execution_context.skill: execute`。
7. 为全部 primary / supporting / reviewer 角色生成 `execution_context.role_package_refs`，路径必须指向 `.harness/common/agents/<role>.md`。

## Step 3：阻塞检查

设置 `blocked=true` 的情况：

- `spec.enabled=true` 且当前执行单位及其 Parent task 都缺少规格引用。
- 当前执行单位不是当前 Parent task 内 `atomic_task_queue.execution_units[]` 映射的 Atomic Task。
- 缺少当前 Atomic Task 片段、文件路径、代码模式参考（样板间 / 相似实现）、接口/数据契约、测试 fixture/seed data、验证命令、证据要求或停止条件。
- Atomic Task 与 Parent task 的完成边界、DoD、required evidence 或禁止越界项冲突。
- required evidence 无法由任何执行者或工具链产出。
- `execution_context.skill` 不是 `execute`，或无法为 primary / supporting / reviewer 中的角色解析 `execution_context.role_package_refs`。
- 策略引擎返回 `missing_surfaces` 非空，或 `primary_executors` 为空。
- `write_scope` 缺失且当前执行单位会修改代码；此时不阻塞实现，但必须设置 `conflict_risk=high`，execute 主流程只能串行派发。
- 当前执行单位的 surface 与任务内容明显冲突，例如 auth 任务只标了 frontend_ui。
- 需要用户授权的高风险操作没有 Decision Gate 记录。

## Step 4：生成brief边界

为 execute 主流程输出每类角色的brief边界：

- primary executors：为每个 `primary_executors[]` 角色生成独立brief，包含完整 Atomic Task、Parent Task Index 边界、该角色负责的 surface、相关规格 Scenario、相关代码文件、required evidence、禁止越界项。
- execute 主流程用 `spawn_agent` 派发时，子 Agent prompt 第一段必须是专家角色 role prompt package 完整原文；Task Envelope 再声明当前执行者正在使用 Harness `execute` skill。不得只写“你是 backend-engineer”来替代技能和角色包装载，也不得要求子 Agent 读取 role package 文件。
- 每个 primary executor brief必须包含当前 Atomic Task、Parent task 映射、文件路径、代码模式参考（样板间 / 相似实现）、接口/数据契约、测试 fixture/seed data、验证命令、事务/状态边界、证据要求和停止条件；不得只传 execution-brief 文件路径；不得把 Execution Units 当作源码草稿。代码模式参考只用于骨架、实现习惯和风格对齐；execute 阶段可以复制骨架并替换差异点，但不得搬运参考文件的业务逻辑。
- 每个 primary executor brief必须写明 `write_scope`、禁止编辑范围、已知同批并行角色信息和越界编辑时返回 `BLOCKED` 的要求。
- supporting executors：为每个 `supporting_executors[]` 角色生成独立brief，只给其证据职责相关的brief，不让其接管整体实现。
- reviewers：为每个 `reviewers[]` 角色生成独立brief，包含实现 diff、规格引用、dispatch plan、evidence 列表和执行结果。

## Step 5：输出 dispatch plan

输出结构：

```yaml
dispatch_plan:
  task_id: "<task-id>"
  execution_unit_id: "<single-atomic-task-id>"
  parent_task_id: "<task-id>"
  surfaces: []
  primary_executors: []
  supporting_executors: []
  reviewers:
    - spec-reviewer
  required_evidence: []
  execution_context:
    skill: execute
    role_package_refs:
      backend-engineer: .harness/common/agents/backend-engineer.md
      test-engineer: .harness/common/agents/test-engineer.md
      spec-reviewer: .harness/common/agents/spec-reviewer.md
  material_package_contract:
    must_include_execution_context: true
    must_include_role_package_ref: true
    must_include_atomic_task_text: true
    must_include_parent_task_boundary: true
    must_include_write_scope: true
  atomic_task_queue_status: ready # ready | missing | incomplete
  write_scope: []
  read_scope: []
  depends_on: []
  parallel_group: null
  conflict_risk: unknown # low | medium | high | unknown
  missing_surfaces: []
  blocked: false
  blockers: []
  rationale: []
  material_packages:
    primary_executors:
      "<role>": "execute skill + role package ref +完整执行单位 + Parent task 边界 + specs + relevant files + role surfaces + required evidence"
    supporting_executors:
      "<role>": "execute skill + role package ref + 对应 evidence 缺口和上下文"
    reviewers:
      "<role>": "role package ref + diff + specs + dispatch plan + evidence + execution_result"
```

- Hard gate：
`execute` 不得在缺少 dispatch plan 的情况下用 `spawn_agent` 调用执行子 Agent。
dispatch plan 为 `blocked=true` 时，必须先解决 blockers 或进入 Decision Gate，不得继续实现。
dispatch plan 缺少 `execution_context.skill=execute` 或缺少 role package 引用时，不得派发可写 Agent；execute 主流程用 `spawn_agent` 派发时未注入 role prompt package 正文，也不得派发。这类 Task Envelope 不可审计，必须回到 dispatch plan 修正。
