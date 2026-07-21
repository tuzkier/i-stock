---
name: work-graph
description: '当 board-router、stage-gate、harness-lint 需要应用 graph operation、重建派生视图、检查 Work Graph 一致性，或用户明确要求修复/重建 Work Graph 时使用；不作为新需求、任务推进或阶段执行入口。'
---

# Work Graph

Work Graph 是 Harness 的长期工作对象事实源。`nodes/**/*.yaml` 是唯一事实源；`boards/main.yaml`、`_index.yaml`、`indexes/*.yaml`、`trees/*.yaml` 是派生视图。

## 何时使用

- `board-router` 已经选定 node，并需要应用 graph operation。
- `stage-gate` PASS 后需要 promotion / advance / split / merge / defer / block 等图状态更新。
- `harness-lint` 或质量检查需要验证 Work Graph node 与派生视图是否一致。
- 用户明确要求“重建 Work Graph 索引”“检查 Work Graph 一致性”“修复 Work Graph 视图漂移”。

## 何时不使用

- 用户提出新任务 / 新需求 → 先走 `intake`。
- 当前 Mission 需要选择下一步 → 先走 `board-router` 或自治循环。
- 阶段文档或代码实现还没完成 → 继续对应阶段 skill。
- 只是想手写 board / index / tree → 禁止，必须通过脚本从 node 重建。

## 固定规则

- AI 只产出 graph operation manifest，不直接手写 board / index / tree。
- 固定、可枚举的 node 更新必须通过 `harness-cli` 调用 `harness graph apply` 执行。
- 每次 node 更新后必须通过 `harness-cli` 运行 `harness graph rebuild` 重建派生视图。
- 每次重建后必须通过 `harness-cli` 运行 `harness graph check` 校验一致性。

## 常用命令

```bash
harness graph rebuild --json
harness graph check --json
harness graph apply --operation <operation.yaml> --json
```

以上命令只展示 CLI 语义；实际执行入口、root 解析和失败处理统一由 `harness-cli` 技能完成。

## 操作 Manifest

当前固定脚本支持：

- `advance_lane`：推进单个 node lane。
- `batch`：一次 Mission Slice 中顺序应用多个 graph operation，常用于多 primary node 推进。
- `split_node`：把一个 node 拆成多个 child node，并建立 `outputs` / `inputs` / `relations.split_from`。
- `merge_nodes`：把多个 source node 汇合成一个 target node，并建立 `relations.merged_from` / `relations.merged_into`。
- `block_node`：把 node 移到 `blocked` lane / status，并记录 `trace.block_reason`。
- `defer_node`：把 node 移到 `deferred` lane / status，并记录 `trace.defer_reason`。
- `supersede_node`：用 replacement node 替代旧 node，并建立 `relations.supersedes` / `relations.superseded_by`。

`advance_lane` 示例：

```yaml
operation_id: OP-001
type: advance_lane
node_id: REQ-001
from_lane: prd
to_lane: solution
mission_id: M-20260507-001
work_graph_artifact:
  node_id: REQ-001
  artifact_version: v1
  promoted_by_mission: M-20260507-001
  source_stage_artifact: harness-runtime/harness/stages/M-20260507-001/solution.md
  canonical_artifact: harness-runtime/harness/work-graph/artifacts/REQ-001/solution.md
  source_contract_artifact: harness-runtime/harness/stages/M-20260507-001/contracts/solution.contract.yaml
  canonical_contract: harness-runtime/harness/work-graph/artifacts/REQ-001/solution.contract.yaml
  change_reason: accepted solution update
  artifact_state:
    status: accepted
```

`split_node` 示例：

```yaml
operation_id: OP-SPLIT-001
type: split_node
node_id: REQ-001
mission_id: M-20260507-001
children:
  - id: SOL-001
    kind: solution
    title: 登录方案
    lane: solution
    status: ready
```

`merge_nodes` 示例：

```yaml
operation_id: OP-MERGE-001
type: merge_nodes
node_ids: [SOL-001, SOL-002]
mission_id: M-20260507-001
target:
  id: TECH-001
  kind: technical_design
  title: 统一技术设计
  lane: breakdown
  status: ready
```

`supersede_node` 示例：

```yaml
operation_id: OP-SUPERSEDE-001
type: supersede_node
node_id: SOL-002
node_ids: [SOL-001]
mission_id: M-20260507-001
```

`batch` 示例：

```yaml
operation_id: OP-BATCH-001
type: batch
mission_id: M-20260507-001
operations:
  - type: advance_lane
    node_id: SOL-001
    from_lane: solution
    to_lane: technical_analysis
  - type: advance_lane
    node_id: SOL-002
    from_lane: solution
    to_lane: technical_analysis
```

Artifact promotion 可附加在任意成功的 graph operation manifest 上；脚本以 `work_graph_artifact.node_id` 指向的 node 为准，复制 canonical markdown / 可选 contract，更新 node 的 `artifact.artifact_state`，并在 canonical artifact 目录追加 `changelog.md`。后续新增操作仍应扩展为 manifest + 脚本处理，不改为手写派生视图。
