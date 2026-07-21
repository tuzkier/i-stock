# 自治循环

## 这是什么

自治循环是 HarnessV2 模板中 AI 的主执行循环。

它不是固定阶段链，也不是根据“缺哪个阶段文档”倒推出下一步的兼容模式。当前调度源是 Work Graph Board 和 Mission Slice：

```text
恢复控制面 -> 选择或恢复 Mission Slice -> 执行当前 lane action -> Stage Gate -> 写回 graph operation -> 判断继续 / checkpoint / 升级 / 收口
```

判断的结果只有四种：

1. **继续**：当前 Mission Slice 仍有可推进的 node / lane action，回到选择或执行。
2. **Checkpoint**：当前 action 命中人工确认点，暂停等待。
3. **升级**：命中风险、范围、设计权或外部依赖决策，暂停等待。
4. **收口**：当前 Mission Slice 的 primary nodes 已达成目标，进入 delivery / retrospective / git close 决策。

## 为什么是 Work Graph Loop

旧口径把生命周期阶段放在主位：需求、方案、技术、拆解、实现、验证、交付。

新口径把长期工作对象放在主位：Requirement、Solution、Technical Design、Task、Research、Follow-up 等 node 才是事实源；Board 派生 ready / active / blocked / deferred 等视图；Mission Slice 是一次会话或一次任务推进时从这些 node 切出的工作切片。

阶段技能仍然存在，但它们不再自己决定“下一阶段”。阶段技能只完成当前 Mission Slice 指定的 lane action，并产出 `lane_action.output_artifact`。是否推进、拆分、阻塞、回退或收口，由 Stage Gate 校验后通过 Work Graph operation 写回。

## Loop 的五个步骤

### 1. 恢复控制面

每轮循环先恢复事实源，而不是凭会话记忆继续干。

AI 应读取：

- `harness-runtime/config/harness.yaml` 中的 `work_graph`、`execution_governance`、`professional_roles`。
- `harness-runtime/harness/work-graph/boards/main.yaml` 和 `_index.yaml`，确认可推进 node。
- 当前 Mission Slice 对应的 mission contract、primary nodes、related nodes、`control_plane.lane`、`control_plane.stage`、`lane_action`、graph operation。
- `harness-runtime/harness/state/trace-log.md` 和最近 traces，确认上一轮是否已完成、阻塞或等待人决策。
- `project-context.md`、项目规格和必要阶段产物，作为当前 action 的输入。

恢复目标是回答一个问题：当前要推进哪个 Work Graph node 的哪一个 action。

### 2. 选择或恢复 Mission Slice

如果已有 active Mission Slice，优先恢复它；如果没有，调用 Board Router 从 Work Graph Board 选择 ready / active node，并创建或恢复 Mission Slice。

选择逻辑：

```text
是否已有 active Mission Slice？
├── 是 -> 读取 slice 的 current lane action
└── 否 -> Board Router 选择可推进 node
    ├── 找到 node -> 创建或恢复 Mission Slice
    └── 没有 node -> 进入收口 / 复盘 / 等待新任务
```

用户在新会话只说“继续任务”时，AI 应按上述恢复逻辑查找 active Mission Slice 和 Board，而不是要求用户复述完整任务。若 Work Graph 未初始化，先停在 intake 的 Work Graph runtime 初始化 gate，不得直接回退到旧 mission-status 阶段队列。

### 3. 执行当前 lane action

当前 action 来自 Mission Slice，而不是固定阶段链。常见映射包括：

| lane action | 常见技能 | 输出 |
|-------------|----------|------|
| `intake` | `intake` | final `mission-contract.md` + seed node / Mission Slice |
| `discovery` | `discovery` | `discovery-brief.md` 或 research evidence |
| `prd` | `prd` | `product/product-definition.md` + product domain/evidence + delta specs |
| `solution` | `design` | `solution.md` |
| `technical_analysis` | `design` | `tech-design.md` |
| `ready_for_dev` | `breakdown` / `execute` | `execution-brief.md` 或代码变更 |
| `verification` | `code-review` / `verify` / `agent-eval` | review / verification evidence |
| `delivery` | `delivery` | `acceptance-result.md` + `delivery-package.md` |

`dependency-impact` 默认不是独立阶段链上的必经节点，而是当前 Mission Slice 的 evidence carrier；只有在 `work_graph.lanes` 显式注册时，才作为独立 graph action 推进。

### 4. Stage Gate 与 Graph Operation

每次 action 完成后，Stage Gate 只检查当前 Mission Slice 声明的内容：

- 当前 action 的 required inputs 是否满足。
- `lane_action.output_artifact` 是否存在且结构合格。
- required execution / review roles 是否有 PASS 或明确 BLOCKED。
- obligations、Evidence Graph slice、验证证据是否覆盖当前 action。
- 待写回的 graph operation 是否与产物证据一致。

Gate PASS 后才能调用 Work Graph operation，例如 `advance_lane`、`split_node`、`block_node`、`complete_node`、`defer_node` 或 `batch`。Gate 不再表达对固定阶段链的放行。

### 5. 判断下一轮

Graph operation 写回后，自治循环重新读取 Board / Mission Slice：

- 若当前 Mission Slice 还有未完成 action，继续执行。
- 若 action 命中 human checkpoint，暂停并展示需要确认的 artifact。
- 若 node 被阻塞，记录 blocker 并选择其他可推进 node。
- 若 primary nodes 完成，进入用户验收、delivery、retrospective 或 branch close。

## 回退与纠偏

纠偏不再“重置某个固定阶段及其后续工作”。纠偏必须定位到 Work Graph node、Mission Slice action 和受影响 artifacts，然后选择 graph operation：

- 产物证据不足 -> 保持当前 lane，补 evidence 或重跑 action。
- 设计或需求变化 -> `split_node` / `block_node` / `defer_node` / 新建 follow-up。
- 实现偏离规格 -> 回到相关 task node 或 verification lane。
- 外部依赖不确定 -> 追加 dependency-impact evidence carrier 或 blocker。

所有回退都必须写入 trace-log，并保留 graph operation 证据。

## 一句话总结

自治循环的当前单位是 Mission Slice，不是固定阶段队列；它围绕 Work Graph node 执行当前 lane action，经 Stage Gate 验证后写回 graph operation，再决定继续、暂停、升级或收口。
