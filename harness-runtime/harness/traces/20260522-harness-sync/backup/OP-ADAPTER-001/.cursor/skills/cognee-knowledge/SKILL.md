---
name: cognee-knowledge
description: '当依赖影响遇到 UNCERTAIN 外部依赖、探索需要调研外部系统、YAPI/接口文档查不到结果、或任何阶段需要从 Cognee 知识图谱获取系统信息、接口定义、架构关系证据时使用。触发词：查知识库、查 Cognee、外部系统信息、接口文档查不到、这个系统有什么接口、查一下依赖信息。'
---

# Cognee Knowledge — 知识图谱证据查询

## 核心定位

**在标记 `[ASSUMED]` 之前，先查 Cognee。**

Cognee 是团队维护的知识图谱，内含已入库的外部系统文档、接口定义、架构关系等信息。
当你在依赖影响、探索、PRD 等阶段遇到不确定的外部依赖时，
**必须先通过 Cognee 查询是否有已有证据，再决定是否标记为 UNCERTAIN/MISSING。**

---

## 何时使用

**自动触发（以下任一条件满足）：**

- 依赖影响第二层（外部业务系统确认）遇到不确定的系统或接口
- 探索需要了解某个外部系统的能力、接口、数据模型
- PRD 引用了外部系统但缺少具体接口信息
- query-api-docs (YAPI) 查不到结果，但该系统可能在 Cognee 中有记录
- 用户说"查一下 XX 系统的信息"、"XX 有什么接口"、"帮我查知识库"

**可跳过：**

- 依赖信息已在代码/项目文档中直接找到（有文件路径证据）
- query-api-docs 已返回完整接口文档
- 用户明确提供了完整的接口信息

---

## 与其他技能的关系

| 技能 | 关系 |
|-------|------|
| `dependency-impact` | **被其调用**：第二层外部系统确认时，作为证据来源 |
| `query-api-docs` | **互补**：YAPI 查实时接口文档，Cognee 查已入库的系统知识 |
| `discovery` | **被其调用**：探索外部系统能力时 |
| `prd` | **被其调用**：需要外部系统约束信息时 |

**优先级**：query-api-docs（实时 YAPI）> cognee-knowledge（知识图谱）> 标记 ASSUMED

---

## 查询方式（主：官方 Cognee MCP）

**使用 Cursor 里已配置的 Cognee 官方 MCP**（例如 `mcp.json` 中的 **`cognee`**，指向本机或内网的 **`.../mcp` HTTP/SSE 端点**）。**不要在 Harness 模板里再新增或合并 MCP 配置**；连接方式与端口以你本地 Cognee 部署为准。工具名与参数以 **Cursor 里该 MCP 的 schema** 为准。

在对话中通过 **MCP 工具** 查询，常见能力包括（以当前 Cognee 版本为准）：

| 工具（示例） | 用途 |
|-------------|------|
| **`search`** | 知识图谱检索：`search_query` + `search_type`（如 `GRAPH_COMPLETION`、`CHUNKS`、`RAG_COMPLETION`）+ `top_k` |
| **`list_data`** | 查看数据集 / 数据项（可选 `dataset_id`） |
| **`cognify_status`** | 查看入库与构建流水线状态（若已暴露） |

需要限定在某个 dataset 时，在 **`search` 的入参**里按该 MCP 暴露的字段传入（与 Cognee 官方 MCP 一致）。

---

## 配置（备选：REST 脚本）

本技能目录下的 **`config.json`** 仅给 **`scripts/cognee-search.sh`** 使用（无 MCP、CI、或需要 curl 直连 REST 时）。与 **官方 Cognee MCP** 的连接**无关**——MCP 由 Cursor 的 `mcp.json` 与 Cognee 服务端配置。

| 字段 | 说明 |
|------|------|
| `api_url` | 后端 API 根地址（脚本用） |
| `api_token` / `auth` | 脚本的鉴权（见 `cognee_token.py`） |
| `default_dataset` | 脚本未传 `--dataset` 时的默认数据集名 |

**前端与 API 端口不同**：浏览器 UI 与 REST API 可能是不同端口；脚本里的 `api_url` 必须指向 API。

---

## 备选：命令行

```bash
bash .harness/common/skills/cognee-knowledge/scripts/cognee-search.sh health
bash .harness/common/skills/cognee-knowledge/scripts/cognee-search.sh datasets
bash .harness/common/skills/cognee-knowledge/scripts/cognee-search.sh search "查询内容" --dataset "数据集名"
```

---

## 搜索策略（MCP `search`）

| 场景 | search_type 示例 | 说明 |
|------|-------------------|------|
| 概况、有哪些接口 | `GRAPH_COMPLETION` | 自然语言 + 图谱上下文 |
| 贴文档原文、参数表 | `CHUNKS` | 原始片段 |
| 偏文档 RAG | `RAG_COMPLETION` | 按 Cognee 支持情况使用 |

---

## 结果处理

1. **有明确结果** → `confirmed`，证据标注 `cognee-knowledge: <查询>`
2. **模糊/不完整** → `uncertain`，需交叉验证
3. **无结果** → 继续 UNCERTAIN/MISSING
4. **与 YAPI/代码冲突** → 以实时源为准

按 `workflow.md` 执行详细步骤。
