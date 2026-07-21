---
name: breakdown
description: '当 tech-design 已完成但还缺执行计划时使用。当需要将大任务拆分为可独立实现的小任务项、确定执行顺序和依赖关系时必须使用。用户说"拆分任务""怎么分步做""执行计划"时也触发。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# 拆解 — 任务拆分

## 概述

将 tech-design 转化为可执行的 `execution-brief.md`。每个 Parent task 都必须在首次产出时带有内嵌 `atomic_task_queue`；简单任务也至少有 1 个 Atomic Task。`writing-plans` 最多作为写盘前内部细化 helper 或手动重规划工具，不是 breakdown 后的常规二次补丁。

## 何时使用

- tech-design 已完成但还缺 execution-brief
- 用户说"拆分任务"、"怎么分步做"、"执行计划"

## 何时不使用

- tech-design 还未完成（→ 先完成设计）
- 已有execution-brief 路径 且不需要修改

## 拆分原则

- **独立性**：每个任务项可独立实现和验证
- **可测试性**：每个任务项有 Red→Green→Refactor 循环
- **粒度适中**：不超过 30 分钟的实现时间
- **依赖明确**：任务项间依赖关系清晰

## 快速参考

| 步骤 | 产出 |
|------|------|
| 读取 tech-design | 输入 |
| 识别实现单元 | Parent tasks + 每个 task 的 Atomic Task Queue |
| 定义 DoD | 每个 Parent task 与 Atomic Task 的完成标准 |
| 设计 TDD 边界 | 每个 Atomic Task 的 Red / Green / Regression 证据要求 |
| 排序 | 依赖拓扑排序 |
| 生成 execution-brief | 最终产出 |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#breakdown`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Parent Task | Execute / Stage Gate | 任务切片只按文件或层拆 |
| Atomic Task | Execute | 子 Agent 无法准确动手 |
| Authorized Path | Execute / Review | 越权改动 |
| Stop Condition | Execute | 失败时继续猜 |
| Required Evidence | Code Review / Verify | 做完但无法证明 |

按 `workflow.md` 执行详细步骤。
