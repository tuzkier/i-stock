# 任务状态追踪

## mission-status.yaml 的位置

`RUNTIME_ROOT/mission-status.yaml`（安装后通常是 `harness-runtime/harness/mission-status.yaml`，项目级唯一文件）

## 何时读取

**每次恢复上下文时**（自治循环第 1 步），通过 `harness-cli` 获取当前 Mission 状态快照，确认：

- 当前任务的 status 是否为 `active`
- 当前 Mission Slice 摘要（`work_graph.mission_slice`、primary nodes、lane、stage、lane_action）
- 当前 slice 内已进入阶段的状态
- 已通过哪些 Checkpoint

如果状态不存在，说明这是项目的第一次执行，通过控制面初始化状态。

## 何时更新

**状态变化时立即通过 `harness-cli` 更新**，不要等到执行结束：

| 事件 | 更新内容 |
|------|---------|
| 任务启动 | `status: active`，`started_at: <date>` |
| Stage 开始 | `stages.<stage>: in-progress` |
| Stage 完成 | `stages.<stage>: done` |
| Stage 跳过 | `stages.<stage>: skipped` |
| Checkpoint 通过 | `checkpoints_passed` 追加该stage |
| Board Router 生成 Mission Slice | `work_graph.mission_slice`、`primary_nodes`、`lane`、`stage`、`lane_action` |
| Stage Gate PASS 并应用 graph operation | `work_graph.last_gate_report`、`last_operation_manifest`、`last_operation_status`，并把对应 `stages.<stage>` 置为 `done` |
| 任务完成 | `status: done`，`completed_at: <date>` |
| 任务取消 | `status: cancelled`，`notes` 记录原因 |

## mission-status 不是调度源

`stages` 只记录当前 Mission Slice 内部某个阶段是否 pending / in-progress / done / skipped，不用于扫描"第一个 pending stage"来决定生命周期下一步。下一步由 Mission Slice 的 `control_plane` / `lane_action` 决定；没有 Mission Slice 时由 `board-router` 重建。

## 新建任务时

当用户开启新任务，在写 `mission-contract.md` 之前先通过 `harness-cli` 创建当前 Mission 状态条目。结构语义如下：

```yaml
"<新 mission-id>":
 title: "<用户描述的任务标题>"
 status: "active"
 autonomy_level: "<从任务契约读取：快速执行/专家确认/受控推进>"
 started_at: "<today>"
 completed_at: ""
 work_graph:
   mission_slice: "harness-runtime/harness/work-graph/mission-slices/<mission-id>.yaml"
   primary_nodes: []
   related_nodes: []
   from_lane: ""
   to_lane: ""
   operation: ""
   lane: ""
   stage: ""
   lane_action: {}
   last_gate_report: ""
   last_operation_manifest: ""
   last_operation_status: ""
 stages: {} # 只记录当前 Mission Slice 实际进入过的阶段；不作为全生命周期 pending 队列
 git:
   strategy: "" # stage-worktree | downgraded（由 git-workflow prepare 填写；不使用 branch/shared 作为正常策略）
 base_branch: ""
 mission_branch: ""
 baseline_commit: ""
 current_stage: ""
 current_stage_branch: ""
 current_stage_worktree: ""
 branch_closed: false
 checkpoints_passed: []
 notes: ""
```

## 多任务并行

如果有多个任务同时为 `active` 状态，默认处理列表中最早开始的那个。
用户可以通过明确指定 mission-id 切换当前处理的任务。
