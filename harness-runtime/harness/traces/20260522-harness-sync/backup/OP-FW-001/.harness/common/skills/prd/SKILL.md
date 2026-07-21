---
name: prd
description: '当任务契约已确认、探索完成（或跳过）、需要把业务诉求产品化为产品定义包时使用。当用户说"写需求""PRD""产品定义""把需求整理一下"时也触发。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# PRD — 产品定义包

## 概述

将任务契约和探索结论转化为产品定义包。`prd` 是历史 stage key，不代表产物文件名。

产品定义包包含：

- `product/product-definition.md`：主产品定义，包含问题诊断、用户场景、范围取舍、FR/NFR/Rule/Scenario、验证闭环和追溯矩阵。
- `product/product-evidence.md`：Knowledge / Spec / GitNexus evidence 与降级记录。
- `product/product-domain-model.md`：按 DDD 组织的产品领域模型，包含战略 DDD（业务域、子域、限界上下文、上下文关系、统一语言、能力边界）和战术 DDD（Actor、聚合、聚合根、实体、值对象、命令、事件、不变量、策略、领域服务、状态机、权限、异常/补偿/幂等）；简单任务也必须说明不适用项及原因。

PRD 阶段不是单个全能专家写一份文档。业务对象分析、验收场景设计和范围策略由专业子专家先产出，再由 `senior-product-expert` 综合成最终产品定义包。

## 何时使用

- 当前 Mission Slice 的 lane action 指向 `prd`
- 探索证据已满足当前 action 输入要求，或治理级别允许跳过并已记录理由
- 用户说"写需求"、"整理需求"、"PRD"、"产品定义"

## 何时不使用

- 任务契约还未确认（→ 先完成任务接入）
- 已有完整产品定义包且不需要修改

## 快速参考

| 步骤 | 产出 |
|------|------|
| 读取任务契约 + 探索结论 | 输入上下文 |
| Evidence gathering | Knowledge / Spec / GitNexus evidence 与降级记录 |
| 业务对象分析 | `product/business-object-analysis.md` |
| 验收场景设计 | `product/acceptance-scenarios.md` |
| 范围策略 | `product/scope-strategy.md` |
| 产品诊断 | 问题定义 + 业务价值 + 用户场景 |
| 领域建模 | DDD 战略建模 + 战术建模 + 规则约束 + 追溯 |
| 范围策略 | In/Out + 取舍 + 阶段化验证路径 |
| 综合定义 | 产品定义 + FR/NFR/Rule/Scenario + 验证闭环 |
| 有效性审查 | 产品定义包 PASS / HOLD |

## 集成

| 技能 | 关系 |
|-------|------|
| `intake` | 输入：任务契约 |
| `discovery` | 输入：技术方案选择 |
| `design` | 输出：产品定义包传递给 solution / interaction / technical_analysis |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#prd--product-definition`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Business Object | Interaction / Solution / Tech Design / Verify | 下游无法判断状态、规则和验收对象 |
| Business Rule | Scenario / AC / Tests | AC 变成泛泛描述 |
| Scenario / AC | Interaction / Breakdown / Verify | 验收不可执行 |
| Scope Decision | Solution / Breakdown / Delivery | 未授权范围进入实现 |
| Validation Signal | Verify / Code Review | 测试通过但需求无法验收 |

按 `workflow.md` 执行详细步骤。
