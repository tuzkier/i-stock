---
name: graphify-guide
description: "当用户询问 Graphify 本身——可用工具、如何查询知识图谱、MCP 资源、图谱模式或使用参考时使用。示例：\"Graphify 有哪些工具？\"\"怎么用 Graphify？\""
---

# Graphify Guide

Graphify 是 HarnessV2 项目知识图谱底座：把代码、文档、SQL schema、配置、PDF、截图等统一抽成一张可查询的知识图，覆盖单项目内"代码 + 文档 + 设计资产"全部知识来源。本文档是所有 graphify MCP 工具、CLI 命令、资源和图谱模式的快速参考。

## 始终从这里开始

对任何涉及代码理解、缺陷追溯、影响分析、重构的任务项：

1. **读 `mcp__graphify__get_node` 或 `graphify status`** —— 项目图谱概览 + 检查索引新鲜度
2. **将任务项匹配下面的 sub-skill** 并 **读对应的 sub-skill 文件**
3. **遵循 sub-skill 的工作流和检查清单**

> 如果 `graphify status` 报告索引过期或不存在，先建图：用 `graphify-build` 技能（Harness 收编的 graphify 官方构建技能），由当前会话派发子 agent 提取，**免 Key**。纯代码增量可用 `graphify --update`（仅 AST）。不要用终端裸跑 `graphify .` 建文档图——那是独立子进程、会要 Key。

## Sub-skills

| 任务项                                         | sub-skill                       |
| -------------------------------------------- | ------------------------------- |
| 理解架构 / "X 是怎么工作的？"                 | `graphify-exploring`            |
| 影响面 / "改了 X 会破坏什么？"                | `graphify-impact-analysis`      |
| 追溯缺陷 / "X 为什么失败？"                   | `graphify-debugging`            |
| 重命名 / 抽取 / 拆分 / 重构                  | `graphify-refactoring`          |
| 工具、资源、模式参考                          | `graphify-guide`（本文件）      |
| 索引、状态、清理、wiki CLI 命令               | `graphify-cli`                  |
| PR 审查 / 多 PR 冲突判断                      | `graphify-pr-review`            |

## MCP 工具参考

| 工具                            | 给你什么                                                              |
| ------------------------------ | --------------------------------------------------------------------- |
| `mcp__graphify__query_graph`   | 自然语言查询图谱，可附 `top_k` / `search_type`                       |
| `mcp__graphify__get_node`      | 单个节点的 360 度视图：属性、置信度、引用、所属社区                  |
| `mcp__graphify__get_neighbors` | 邻居遍历（按 depth + relation 过滤），影响面分析的基础原语           |
| `mcp__graphify__shortest_path` | 两节点间最短路径，跨模块连接证明用                                    |
| `mcp__graphify__list_prs`      | 当前仓库 PR 列表（含 CI / review / worktree 状态）                   |
| `mcp__graphify__get_pr_impact` | 单个 PR 的图谱影响：改动节点 + 受影响社区 + 风险评分                  |
| `mcp__graphify__triage_prs`    | PR 队列分诊：按图谱风险排序                                          |

> MCP server 未连接时降级到 CLI：`graphify query` / `graphify explain` / `graphify path`，见 `graphify-cli`。

## 索引产物参考

`graphify-out/` 目录入 git，团队共享。关键文件：

| 文件                                | 内容                                                                |
| ----------------------------------- | ------------------------------------------------------------------- |
| `graphify-out/graph.json`           | 知识图原始数据（节点 + 边 + 置信度）                                 |
| `graphify-out/GRAPH_REPORT.md`      | 人读的图谱总结：god nodes / surprising connections / suggested Qs   |
| `graphify-out/manifest.json`        | mtime / 文件清单（CI 应忽略）                                       |
| `graphify-out/cost.json`            | LLM 调用成本（本地，不入 git）                                       |
| `graphify-out/converted/`           | Google Workspace / 视频转录等中间产物                                |
| `graphify-out/cache/`               | 逐文件 AST / 语义抽取缓存（本地增量重建用）——**默认 gitignore，不入 git** |

## 图谱模式（Schema）

**节点类型：**

- 代码：`Function` / `Class` / `Method` / `Module` / `File`
- 文档：`Doc` / `Heading` / `Section`
- Schema：`Table` / `Column` / `Index`
- 资产：`Image` / `Video` / `Diagram` / `PDF`
- 设计：`Rationale`（来自 `NOTE / WHY / HACK / FIXME` 注释 + docstring + 文档里 design rationale 段落）
- 聚类：`Community`（Leiden 社区）

**边类型：** 由 AST + LLM 同时抽取，每条边带置信度 `EXTRACTED / INFERRED / AMBIGUOUS`：

- 代码：`CALLS / IMPORTS / EXTENDS / IMPLEMENTS / DEFINES / MEMBER_OF`
- 跨模态：`DOCUMENTS`（文档 → 代码节点）、`EXPLAINS`（Rationale → 代码节点）、`REFERENCES`（文档 → schema / 资产）
- 聚类：`IN_COMMUNITY`

## 置信度对齐

Graphify 的边置信度直接对位 HarnessV2 探索/影响分析的证据强度词表：

| Graphify       | HarnessV2     | 说明                                                  |
| -------------- | ------------- | ----------------------------------------------------- |
| `EXTRACTED`    | `CONFIRMED`   | AST 直接抽取，机械可证                                |
| `INFERRED`     | `UNCERTAIN`   | LLM 推断或多源交叉，需复核                            |
| `AMBIGUOUS`    | `ASSUMED`     | 推断弱、来源冲突或仅注释提示                          |

下游 `dependency-impact` / `discovery-effectiveness-reviewer` 直接消费 graphify 边的置信度字段。
