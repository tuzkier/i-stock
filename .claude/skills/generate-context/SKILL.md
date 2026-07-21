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

## Graphify 联动（推荐）

`project-context.md` 是文字层面的项目认知。同一时机建议同步建立 Graphify 知识图谱底座，让后续 discovery / dependency-impact / refactoring / pr-review 可以拿到可查询证据，而不只是文字描述。

判断流程：

1. 跑 `harness graphify status --json` 看 `cli_installed` / `available` 字段。
2. `cli_installed=false` ⇒ 提示用户机器层安装 graphify CLI 二进制：`uv tool install graphifyy`（推荐）/ `pipx install graphifyy` / `pip install graphifyy`。PyPI 包名 `graphifyy` 双 y，CLI 命令是 `graphify`。（构建技能 `graphify-build` 随 Harness 一起安装，无需在项目里再跑 graphify install。）
3. `available=false` ⇒ 首次建图：**用 `graphify-build` 技能**（Harness 收编的 graphify 官方构建技能），由当前会话派发子 agent 提取文档——代码走 AST、文档/Markdown 走会话模型，**免 Key**（graphify 不读 `ANTHROPIC_API_KEY` 等环境变量）。**语义分析不准跳过**：文档/Markdown/PDF/图片的语义抽取是建图的一部分，不允许只做代码 AST 就收工；待抽取文件多时**必须派发多个子 agent 并行**（每 ~20-25 文件一个，约 `ceil(待抽取文件数 / 22)` 个），不得因量大而跳过或截断。结果写到 `graphify-out/`：图谱本体（`graph.json` / `GRAPH_REPORT.md` / `graph.html`）建议入 git 团队共享；`graphify-out/manifest.json`、`cost.json`、`cache/` 加进 `.gitignore`（本地/派生产物，默认不入 git）。建图后确认这三条已在 `$TARGET/.gitignore` 里，没有就补上。不要改用终端裸跑 `graphify .` 建文档图——那是独立子进程、拿不到会话模型，文档提取才会要 Key。
4. 可选加固：`graphify hook install` 让 commit 后自动 `--update`（无 LLM 成本）。
5. 可选 MCP 服务：`pip install "graphifyy[mcp]"` + `python -m graphify.serve graphify-out/graph.json`，供后续技能通过 `mcp__graphify__*` 工具调用。

全新项目可以跳过这一步（仅文字 context 足够）；既有项目强烈推荐，否则 discovery 阶段会被 brownfield HARD-GATE 拦下并要求 `degradations[].kind=graphify_unavailable`。

按 `workflow.md` 执行详细步骤。
