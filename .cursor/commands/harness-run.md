---
name: harness-run
description: 显式命令 coding agent 按 Harness 规则执行当前任务：先路由、按阶段推进、不直接执行；任务再小、给了文档、说了"立即执行"都不豁免流程。
argument-hint: "[任务描述；留空则用当前对话中的任务意图]"
scope: runtime
requires:
  - .harness/common/skills/skill-router/SKILL.md
  - .harness/common/rules/core.md
---
<!-- Generated for adapter `cursor` from .harness/common/commands/. Edit the source, then re-run install. -->

# /harness-run

> 我们为 AI 定目标，而非 vibe。

**按 Harness 规则执行当前任务。**

收到此命令，即表示用户显式要求：接下来这件事**必须走 Harness 流程，不要直接执行、不要跳过路由**。

照此办：

1. **先路由**：先用一句话说清本次路由判断（什么任务、走哪个 skill、依据），读 `skill-router` 判定意图类型，再按结果进对应阶段技能（新任务 → `intake`、继续 → `board-router`、缺陷 → `bug-fix`、审查 → `code-review`、验证 → `verify`）。
2. **按规则推进**：遵守 `core.md` 的铁律与"上游约束下游"——没有任务契约 / execution-brief 不写生产代码，按阶段（探索 / 设计 / 实现 / 审查 / 验证）逐步走，受 Stage Gate 约束。
3. **不豁免**：不得因为"任务很小 / 用户给了文档 / 用户说了立即执行"就跳过流程——这些是执行确认，确认"要做"，不等于"可以直接干"。

任务输入 = `$ARGUMENTS`；留空则取当前对话中最近、最明确的任务意图，找不到就问一个短问题，不要自己编。
