---
name: harness-lint
description: '当需要检查 Harness 框架本身完整性、一致性、技能格式、阶段文档、配置或安装资产时使用。'
---

# Harness 自检 — 框架检查

## 概述

检查 HarnessV2 框架本身的健康状态：技能文件格式、配置一致性、阶段文档完整性。

## 何时使用

- 任务完成后自动触发
- 用户说"检查 harness"、"lint harness"
- 修改了 Harness 框架文件后

## 检查维度

| 维度 | 检查内容 |
|------|---------|
| SKILL.md 格式 | frontmatter 是否完整、description 是否症状驱动 |
| workflow.md 存在性 | 每个技能是否有对应的工作流 |
| 配置一致性 | harness.yaml 中的引用是否有效 |
| 阶段文档 | 当前任务的阶段文档是否齐全 |

按 `workflow.md` 执行详细步骤。
