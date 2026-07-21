---
name: trace-log
description: '当需要记录或恢复 Harness 执行日志时使用；技能开始/完成、Stage Gate、Checkpoint、escalation、审查结论、回退、sub-agent 结束或会话恢复时触发。'
---

# 执行日志 — 执行日志

## 概述

自动记录每轮执行的关键信息，支持跨会话恢复和决策回溯。

## 何时使用

- **主路径（默认）**：主 Agent 在每轮恢复协议与自治循环中调度本技能，无需 sub-agent 参与
- 由自治循环自动集成（通常不需要手动触发）
- 跨会话恢复时自动读取

## 记录内容

| 字段 | 说明 |
|------|------|
| timestamp | 时间戳 |
| phase | 当前阶段 |
| 技能 | 使用的技能 |
| decision | 做出的决策 |
| outcome | 结果 |
| 上下文 | 关键上下文 |

按 `workflow.md` 执行详细步骤。
