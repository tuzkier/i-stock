---
name: technical_analysis
description: '当 solution.md 已完成，需要把方案路线落到模块 / 接口 / 数据 / 验证策略的技术设计时使用。仅处理 Mission Slice control_plane.stage=technical_analysis；不处理 solution 与 interaction。用户说"做技术设计 / tech-design / 模块拆分 / interface_changes / data_changes / 实现策略"时触发。Agent 能力实现（## Agent 实现 section）由本 skill 嵌入处理，不另立独立 capability-design skill。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# Technical Analysis — stage: technical_analysis

## 概述

`control_plane.stage=technical_analysis` 专属 skill。基于 solution.md 已确定的方案，产出 `tech-design.md` + `contracts/tech-design.contract.yaml`，覆盖模块/接口/数据/验证策略 + 生产就绪四要素。

`agent-capability-designer` 与 `agent-capability-reviewer` 作为条件角色（capability-design 嵌入式实现），负责 `tech-design.md ## Agent 实现` section + `solution.md ## Agent 架构` section 协同写。

## 何时使用

- Mission Slice `control_plane.stage=technical_analysis`
- solution.md 已完成、方案路线已明确
- 用户说"做技术设计 / 模块拆分 / interface_changes / 数据迁移设计"

## 何时不使用

- solution lane 还未完成 → 先 `solution` skill
- `control_plane.stage=interaction` → 转到 `interaction` skill
- `control_plane.stage=solution` → 转到 `solution` skill

## 设计原则

- **可追溯**：每个 module / interface_change / data_change / verification_strategy 必须 traces_to upstream DEC / FR / NFR / AC
- **生产就绪四要素**：error_handling / compatibility / observability / rollback 必须填实值或 "N/A: 理由"
- **section 级 write_scope**：tech-designer 不得写 `## Agent 实现`；agent-capability-designer 只能写 `## Agent 实现` + solution.md `## Agent 架构`
- **dep-impact 前置**：`harness tech-design check-dep-impact-trigger` 触发时必须先跑 dependency-impact skill 再进入设计

## 快速参考

| 步骤 | 产出 |
|------|------|
| Stage 初始化 + dep-impact 触发判断 + capability 触发判断 | inputs |
| 读 solution.md + PRD + interaction.md / interaction-spec 引用 | inputs |
| tech-designer 起草 tech-design.md | tech-design.md (除 ## Agent 实现) |
| capability-designer 写 ## Agent 实现 + solution ## Agent 架构 | tech-design.md ## Agent 实现 |
| 填外部 contract（CLI 路径，5 typed groups） | tech-design.contract.yaml |
| 3 reviewer 循环（effectiveness + capability + dependency-validity） | role_verdicts |
| Artifact Gate 自检 | gate run PASS |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#technical-analysis` 和 `#agent-capability-design`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Module | Breakdown / Architecture Review | 任务拆分失去边界 |
| Interface Change | Execute / Integration Review | 调用方 / 被调方不一致 |
| Data / State Flow | Execute / TDD / Verify | 实现只改局部，破坏闭环 |
| Error / Compatibility Strategy | Execute / Delivery | 生产风险无处理路径 |
| Verification Strategy | Breakdown / Code Review / Verify | 任务完成无法被证明 |
| Agent Work Rights | Agent implementation / Eval | Agent 只靠 prompt 自律 |

按 `workflow.md` 执行详细步骤。
