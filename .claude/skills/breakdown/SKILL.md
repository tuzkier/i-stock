---
name: breakdown
description: '当 tech-design 已完成但还缺执行计划时使用。当需要将大任务拆分为可独立实现的小任务项、确定执行顺序和依赖关系时必须使用。用户说"拆分任务""怎么分步做""执行计划"时也触发。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# 拆解 — 任务拆分

## 概述

将已成立的技术设计转化为一次受控迭代的执行授权。执行简报（`execution-brief.md`）不只是任务列表，还必须说明本轮增量目标、风险处理顺序、授权变更集、非目标、延后项和停止 / 回流条件。每个父任务（Parent task）都必须在首次产出时带有内嵌 `atomic_task_queue`；简单任务也至少有 1 个原子任务（Atomic Task）。写计划（`writing-plans`）最多作为写盘前内部细化 helper 或手动重规划工具，不是拆解阶段（breakdown）后的常规二次补丁。

## 何时使用

- tech-design 已完成但还缺 execution-brief
- 用户说"拆分任务"、"怎么分步做"、"执行计划"

## 何时不使用

- tech-design 还未完成（→ 先完成设计）
- 已有execution-brief 路径 且不需要修改

## 拆分原则

- **输入先判定**：技术设计不足以拆解时回流技术分析，不在 breakdown 内补造模块、接口、数据或风险验证设计。
- **迭代授权**：每个父任务（Parent task）是本轮增量的工作授权单（work order），必须说明交付结果、风险处理目标和变更集边界。
- **用例纵切**：按用户可观察结果、验收场景 / 条件、领域命令、状态迁移、权限规则和风险边界切片，不按文件层横切。
- **可测试性**：每个任务项有 Red→Green→Refactor 或等价验证循环。
- **依赖明确**：任务项间依赖关系清晰，高风险 / 高不确定性任务优先。

## 快速参考

| 步骤 | 产出 |
|------|------|
| 读取 tech-design | 输入 |
| 判定输入是否足以授权 | 回流或继续 |
| 建立义务映射（obligation map） | 上游义务 → 执行义务 → 授权变更面 → 验证方式 |
| 应用切分约定 | 父任务 / 原子任务（Parent task / Atomic Task）的合并、拆分和命名依据 |
| 识别实现单元 | 父任务（Parent tasks）+ 每个任务的原子任务队列（Atomic Task Queue） |
| 定义迭代边界 | 增量目标、风险焦点、授权变更集、非目标、停止条件 |
| 定义完成定义（DoD） | 每个父任务与原子任务的完成标准 |
| 设计测试驱动开发（TDD）边界 | 每个原子任务的红灯 / 绿灯 / 回归（Red / Green / Regression）证据要求 |
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
