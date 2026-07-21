---
name: generate-context
description: '当项目缺少 project-context.md、AI 不了解项目结构/约定/技术栈时使用。首次接触新项目时自动触发。用户说"生成项目上下文""分析这个项目"时也触发。'
---

# Generate 上下文 — 生成项目上下文

## 概述

自动分析项目结构、技术栈、约定，生成 project-context.md 供后续技能使用。

## 何时使用

- 项目缺少 project-context.md
- 首次接触新项目
- 用户说"生成项目上下文"、"分析这个项目"

## 何时不使用

- project-context.md 已存在且是最新的

## 分析维度

| 维度 | 检查内容 |
|------|---------|
| 技术栈 | package.json / Cargo.toml / go.mod / requirements.txt |
| 目录结构 | src / tests / docs 的组织方式 |
| Git 约定 | 分支名、commit 格式、CI 配置 |
| 测试框架 | jest / pytest / cargo test 等 |
| 代码风格 | eslint / prettier / 现有代码模式 |

按 `workflow.md` 执行详细步骤。
