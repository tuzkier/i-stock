# Cognee Knowledge 工作流

> **触发条件、搜索策略、结果处理规则见 `SKILL.md`，不在此重复。**

---

## 查询流程

<workflow skill="cognee-knowledge" version="2">

<step n="1" goal="确认 Cognee MCP 可用">
  - 在 Cursor 中通过 **已配置的 Cognee 官方 MCP** 调用（无需改 Harness 内 MCP 配置）。可先 **`list_data`** 或 **`search`** 做轻量探测。

  - 条件：MCP 不可用
    - 备选：运行 `cognee-search.sh health`（依赖 `config.json`）
</step>

<step n="2" goal="确认数据集">
  - 使用 MCP **`list_data`**（或脚本 `cognee-search.sh datasets`）确认目标数据集名称或 ID。

  - 条件：目标系统不在数据中
    - 说明 Cognee 中暂无该知识；可建议用户先入库、cognify 后再查
</step>

<step n="3" goal="搜索">
  - 使用 MCP **`search`**：`search_query` 写清问题；需要限定 dataset 时按 Cognee MCP 入参传递；`search_type` 按场景选 `GRAPH_COMPLETION` / `CHUNKS` / `RAG_COMPLETION` 等。

  - 条件：结果不够具体
    - 收紧关键词或改用 `CHUNKS`
</step>

<step n="4" goal="整理结果">
  - 按 `SKILL.md` 整理证据，回传给依赖影响 / 探索 / prd。
</step>

</workflow>

---

## 反合理化

| 诱惑 | 真相 |
|------|------|
| "Cognee 里肯定没有这个信息" | 查了才知道 |
| "直接问用户比查 Cognee 快" | MCP 一轮工具调用通常更快 |
| "这个信息太细了" | 细节往往在 CHUNKS 中 |
