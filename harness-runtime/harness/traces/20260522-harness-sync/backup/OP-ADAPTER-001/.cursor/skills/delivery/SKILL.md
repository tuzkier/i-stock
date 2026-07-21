---
name: delivery
description: '当 code-review 通过且验证完成、准备打包交付时使用。当用户说"交付""提交成果""生成交付物"时也触发。'
---

> **执行 Agent**：由本阶段 `workflow.md` 的 role policy 声明；若运行时无法调度所需 Agent role，停在 Gate 并报告角色不可用，不得由主 Agent 按本工作流自写自审。

# 交付 — 交付

## 概述

将已验证的成果整理为面向人的验收结果，并生成内部归档交付包。

## 何时使用

- code-review 通过且验证完成
- 用户说"交付"、"打包"、"提交成果"

## 何时不使用

- 验证还未通过（→ 先完成验证）

## 快速参考

| 步骤 | 产出 |
|------|------|
| 读取验证结果 | 确认状态 |
| 生成 `acceptance-result.md` | 用户可验收结果 |
| 生成 `delivery-package.md` | 内部交付归档 |
| PR 或合并 | 代码入库 |
| 通知用户 | 交付完成 |

## Stage Element Model

本阶段必须维护的关键要素见 `.harness/docs/methodologies/stage-element-model.md#delivery`。摘要：

| Element | Used By | Failure If Missing |
|---|---|---|
| Delivered Scope | User acceptance | 用户不知道验收范围 |
| Acceptance Item | User | 交付包不可自验 |
| How To Verify | User | 只能相信 Agent 口头说明 |
| Known Gap / Risk | User / Retrospective | 风险被隐藏 |
| Evidence Link | Audit | 交付不可追溯 |

按 `workflow.md` 执行详细步骤。
