---
name: solution
description: '当 PRD 已完成、需要做方案路线选择 / 关键决策 / 风险边界设计时使用。仅处理 Mission Slice control_plane.stage=solution；不处理 tech-design 与 interaction。用户说"做方案 / 路线选型 / 决策 / 选哪条路 / tradeoff"时触发。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# Solution — stage: solution

## 概述

`control_plane.stage=solution` 专属 skill。把 PRD 的"做什么"转化为可决策的"怎么做"路线，产出 `solution.md` + `contracts/solution.contract.yaml`，由 `solution-effectiveness-reviewer` 审查。

## 何时使用

- Mission Slice `control_plane.stage=solution`
- PRD 已完成、需要做方案路线选择 / 关键决策 / 风险边界设计
- 用户说"做方案 / 路线选型 / 决策 / tradeoff"

## 何时不使用

- `control_plane.stage=technical_analysis` → 转到 `technical_analysis` skill
- `control_plane.stage=interaction` → 转到 `interaction` skill
- PRD 还未完成 → 先 `prd` skill

## 设计原则

- **目标驱动**：先围绕任务目标、现有架构、风险和长期维护完成方案；只有存在真实分歧路线时，才做方案选择
- **反 demo / 反最小改动**：不得把"先做 demo / 改动最小"作为正式路径
- **可追溯**：每个 decision 必须 traces_to upstream AC / FR / NFR / Mission Contract ID

## 快速参考

| 步骤 | 产出 |
|------|------|
| Stage 初始化 + Mission Slice 校验 | inputs |
| 读 PRD + project-context + Mission Contract | inputs |
| 决策点识别 + 候选方案对比 | solution.md decisions[] |
| 填外部 contract（CLI 路径） | solution.contract.yaml |
| reviewer 循环 (max_rounds=3) | role_verdicts |
| Artifact Gate 自检 | gate run PASS |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#solution`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Decision Point | Tech Design / Review | 技术设计直接拍脑袋 |
| Candidate Option | Decision table | 没有真实 tradeoff |
| Decision / Rationale | Tech Design / Breakdown | 下游不知道为什么这样做 |
| Forbidden Path | Tech Design / Review | 实现绕回已拒绝方案 |
| Mitigation / Gate | Stage Gate / Delivery | 风险被隐藏 |

按 `workflow.md` 执行详细步骤。
