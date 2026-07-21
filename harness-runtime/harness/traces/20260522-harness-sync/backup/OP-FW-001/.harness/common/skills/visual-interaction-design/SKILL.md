---
name: visual-interaction-design
description: '当任务涉及 UI、用户旅程、线框图、原型、可视化交互设计或需要把 interaction.md / interaction-spec 转成给人评审的可预览 HTML/SVG 设计变体和 preview 时使用。'
---

# 可视化交互设计

## 目标

把 PRD 阶段产出的产品定义、领域模型、interaction.md 和 interaction-spec/ 中的用户旅程转成可操作、可预览、可归档、可审查的前端原型 / 可视化交互资产。

本技能不依赖外部设计插件。交互专家负责生成和维护 HTML / SVG / CSS 原型资产；Harness 通过 manifest、contract 和 reviewer 管理覆盖、追溯和审查。`visual-interaction/prototype/index.html` 是唯一默认人类入口，必须尽量还原真实前端页面；说明、状态覆盖、组件清单和 trace 信息只作为内部证据，不默认生成可见页面。AI handoff 仍以 interaction-spec/ 为准。

## 产物

| 产物 | 路径 | 用途 |
|------|------|------|
| 主可操作原型 | `harness-runtime/harness/stages/<mission-id>/visual-interaction/prototype/index.html` | 唯一默认人类入口；面向用户确认的高还原可操作前端页面；不得混入评审说明、AC、trace 或阅读指引 |
| 设计变体 | `harness-runtime/harness/stages/<mission-id>/visual-interaction/variants/` | 归档 HTML / SVG / CSS 设计资产 |
| 内部证据 | `harness-runtime/harness/stages/<mission-id>/visual-interaction/evidence/` | 可选；给 Gate / reviewer 的状态覆盖、截图、说明材料；不作为人类入口 |
| Manifest | `harness-runtime/harness/stages/<mission-id>/visual-interaction/visual-interaction-manifest.json` | 程序化列出变体、来源、hash、覆盖视口和审查状态 |
| 设计 brief | `harness-runtime/harness/stages/<mission-id>/visual-interaction/design-brief.md` | 交互专家生成 HTML / SVG 变体所需的上下文 |
| interaction.md 更新 | `harness-runtime/harness/stages/<mission-id>/interaction.md` | 引用选定变体、用户流程、状态模型和 E2E obligation |

## 集成边界

- Harness 规则负责：上下游追溯、产物归档、manifest、审查 Gate、E2E / screenshot evidence。
- 交互专家负责：基于产品定义、领域模型、interaction-spec 和项目现有风格生成并维护主可操作原型、HTML / SVG / CSS 设计变体和内部证据，并补齐覆盖元数据。
- interaction-reviewer 负责：判断 interaction-spec 和可视化资产是否证明用户路径、状态、错误、权限、键盘 / 焦点和 E2E obligation 设计充分。

## 何时使用

- 任务涉及 `frontend_ui` / `frontend_visual` / `user_journey` / `web_ui`。
- 用户要求“可视化交互设计”“线框图”“原型”“mockup”。
- interaction.md 只有文字，无法支撑前端实现或用户确认。

## 何时不使用

- 纯后端、纯数据、纯 CLI 任务。
- 只需要修改已有文案且没有用户旅程变化。

按 `workflow.md` 执行详细步骤。
