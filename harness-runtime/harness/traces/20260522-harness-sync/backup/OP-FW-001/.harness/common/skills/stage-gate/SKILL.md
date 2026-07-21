---
name: stage-gate
description: '当完成当前 Mission Slice 的 stage artifact、准备应用 Work Graph operation 时自动触发——检查当前产物是否齐全、质量是否达标。用户说"检查 Gate""能不能继续""阶段检查"时也触发。'
---

# Stage Gate — Stage Gate

## 概述

当前 Mission Slice 的 Quality Gate。确保当前 `lane_action.output_artifact`、角色 verdict、证据和控制契约齐全且达标后，才允许 Stage Gate 调用 Harness CLI 应用 Work Graph operation。

## 何时使用

- 完成当前 Mission Slice 的 stage artifact，准备应用 Work Graph operation 时（自动触发）
- 用户说"检查 Gate"、"能不能继续"

## 何时不使用

- 阶段内部的工作（→ 使用对应的阶段技能）

<HARD-GATE>
Stage Gate 是不可绕过的质量关卡：
- 当前 Mission Slice 的 stage artifact 完成后，必须先通过 Stage Gate，才能应用 Work Graph operation
- 不得以"任务简单"或"已了解产出"为由跳过执行
- PASS 后自治循环负责调用 `git-workflow commit-artifact`，将当前 stage worktree 合并回 mission branch；FAIL 后必须修复再重新检查，不能合并
- 跳过 Stage Gate 直接推进 Board / Work Graph = 违规
</HARD-GATE>

## Mission Slice 输入

Stage Gate 不维护固定阶段链。它读取当前 Mission Slice 和 `work_graph.lanes.<lane>.stages[]` 注册表：

- `control_plane.lane` / `control_plane.stage`：确定当前 Gate 边界
- `lane_action.output_artifact`：确定本次必须检查的 stage artifact
- `lane_action.required_execution_roles` / `required_review_roles`：确定角色 verdict 要求
- `primary_nodes` / `related_nodes` / `operation` / `graph_operation`：确定 Work Graph 推进约束

Gate PASS 后由 Harness CLI 应用 graph operation 并回到 Board Router 选择下一项工作；不得在本文件硬编码 “A 阶段之后必然是 B 阶段”。

按 `workflow.md` 执行详细步骤。
