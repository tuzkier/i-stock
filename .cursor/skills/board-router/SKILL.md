---
name: board-router
description: '当会话恢复、用户说“继续”、active mission 缺少/完成当前 Mission Slice、需要从 Board 选择下一项可推进工作或创建 Mission Slice 时使用；不处理新需求接入、阶段执行或图视图重建。'
---

# Board Router

Board Router 是 Work Graph 模型的调度入口。它读取派生 board，选择一个或一组 node，生成 Mission Slice，并在阶段 Gate PASS 后交给 `harness-cli` 应用图操作。

## 何时使用

- 自治循环恢复或用户说“继续”时，需要确认是否应从 Board 选择下一项可推进 node。
- 当前没有 active Mission Slice，但 Board 中有 active / ready node。
- 当前 Mission Slice 的 graph operation 已应用，需要从更新后的 Board 恢复下一项工作。
- 用户明确说“从看板继续”“推进下一个 node”“恢复 Board”“选择下一项工作”。
- Stage Gate PASS 后需要把当前 Mission Slice 的结果转成下一次 Board 调度输入。

## 何时不使用

- 用户提出一个全新需求或任务 → 先走 `intake`，由 intake 创建或关联 seed node。
- 已经有明确 active Mission Slice 和当前阶段 → 自治循环按该 Mission Slice 的 `lane_action.skill` 调度精确 skill；缺失时才使用 `control_plane.stage` 做确定性 stage-to-skill 映射，不重新选择 Board。
- 需要更新 node / board / index / tree → 调 `work-graph`，Board Router 不直接写图状态。
- 需要实现代码、审查、验证、交付 → 使用对应阶段 skill。

## 边界

- 只通过 `harness board select ... --json` 消费 Board Router 视图；不得直接读取 `boards/main.yaml`。
- 不直接编辑 board / index / tree。
- 需要修改图状态时，输出 graph operation manifest，并通过 `harness-cli` 调用 `harness gate advance` / `harness graph apply`。
- Delta spec 使用 `harness-runtime/harness/artifacts/<mission-id>/product/specs/`，旧 `stages/<mission-id>/specs/` 仅作为历史兼容读取。

## 最小流程

1. 调用 `harness-cli` 执行 `harness board select --mission <mission-id> --json`。
2. 读取当前任务上下文，先按相关性选择 node，再按 node priority / lane action priority 等稳定规则排序。
3. 读取对应 `nodes/**/*.yaml`。
4. 根据 `harness board select` / `harness config snapshot` 返回的 `work_graph.lanes.<lane>.stages[]` 创建或恢复 Mission Slice；若 lane action snapshot 声明 `skill`，后续自治循环必须调用该 skill。
5. 将 Mission Slice 摘要写入 `mission-status.yaml`；`trace-log.md` 不属于 Board Router 的结构化控制面。
6. 阶段完成后，Stage Gate report 决策为 `continue` 时调用 `harness-cli` 执行 `harness gate advance --mission <mission-id> --gate-report <gate-report.json> --json`，由 CLI 生成 graph operation manifest、调用 Work Graph 控制面，并回写 mission-status 的 gate / operation 摘要。
