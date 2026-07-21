---
name: graphify-exploring
description: "当用户问代码怎么工作、想理解架构、追溯执行路径或探索不熟悉的代码区域时使用。示例：\"X 是怎么工作的？\"\"什么调用了这个函数？\"\"展示 auth 流程\""
---

# 用 Graphify 探索代码库

## 何时使用

- "认证是怎么工作的？"
- "项目结构是什么样？"
- "主要组件有哪些？"
- "数据库逻辑在哪里？"
- 理解你没见过的代码

## 工作流

```
1. mcp__graphify__query_graph({search_query: "你想理解的概念", top_k: 10})
   → 拿到相关节点（函数/模块/文档/Rationale）+ 所属社区

2. mcp__graphify__get_node({name: "<关键符号>"})
   → 节点全属性 + 邻居预览 + 置信度

3. mcp__graphify__get_neighbors({name: "<符号>", depth: 2})
   → 上下游邻居，按边类型过滤（CALLS / IMPORTS / DOCUMENTS / EXPLAINS）

4. mcp__graphify__shortest_path({from: "A", to: "B"})
   → 跨模块连接（surprising connections）的最短路径

5. READ graphify-out/GRAPH_REPORT.md
   → god nodes / 跨模块惊奇连接 / 4–5 个图谱独占问题，作为整体地图

6. READ 实际源文件 / 文档
   → 确认实现细节
```

> 如果 `graphify status` 报告索引缺失或过期，先终端跑 `graphify .`。

## 检查清单

```
- [ ] 跑 graphify status 确认索引可用且新鲜
- [ ] query_graph 找概念相关节点
- [ ] 阅读返回结果里所属的 community（功能聚类）
- [ ] get_node / get_neighbors 深入关键符号
- [ ] shortest_path 验证跨模块连接
- [ ] 读 GRAPH_REPORT.md 拿 god nodes 视角
- [ ] 阅读源文件 / 文档确认实现
```

## 关键资源

| 资源                                       | 给你什么                                                       |
| ----------------------------------------- | -------------------------------------------------------------- |
| `graphify-out/GRAPH_REPORT.md`            | god nodes、surprising connections、suggested questions（人读） |
| `graphify-out/graph.json`                 | 原始图数据，可直接 jq 查询                                     |
| `mcp__graphify__query_graph`              | 自然语言 → 节点列表 + 关联社区                                 |
| `mcp__graphify__get_node`                 | 节点 360 度视图                                                |
| `mcp__graphify__get_neighbors`            | 多跳邻居遍历                                                   |
| `mcp__graphify__shortest_path`            | 两节点最短路径                                                 |

## 工具

**query_graph** — 找概念相关的执行 / 文档节点：

```
mcp__graphify__query_graph({
  search_query: "支付处理",
  search_type: "GRAPH_COMPLETION",   # 或 CHUNKS / RAG_COMPLETION
  top_k: 10
})
→ 节点列表：processPayment / validateCard / chargeStripe / docs/payment.md
→ 社区：PaymentFlow / RefundFlow / WebhookHandler
```

**get_node** — 单符号 360 度视图：

```
mcp__graphify__get_node({name: "validateUser"})
→ 入边：loginHandler [CALLS, EXTRACTED] / apiMiddleware [CALLS, EXTRACTED]
→ 出边：checkToken / getUserById
→ DOCUMENTS：docs/auth.md§"Login Flow" [INFERRED]
→ Rationale：注释 "# NOTE: must run before rate-limit check"
→ 社区：AuthFlow（cohesion 0.82）
```

**get_neighbors** — 多跳邻居：

```
mcp__graphify__get_neighbors({
  name: "validateUser",
  depth: 2,
  edge_types: ["CALLS", "IMPORTS"]
})
→ d=1：loginHandler, apiMiddleware
→ d=2：authRouter, sessionManager, app.ts
```

## 示例："支付处理是怎么工作的？"

```
1. graphify status → 索引 fresh，918 节点
2. mcp__graphify__query_graph({search_query: "支付处理"})
   → 社区 PaymentFlow：processPayment → validateCard → chargeStripe
   → 社区 RefundFlow：initiateRefund → calculateRefund → processRefund
   → 文档节点：docs/payments.md§"Webhook Contract" DOCUMENTS processPayment
3. mcp__graphify__get_node({name: "processPayment"})
   → 入边：checkoutHandler / webhookHandler
   → 出边：validateCard / chargeStripe / saveTransaction
   → Rationale："# WHY: idempotency key required, see RFC-payment-001"
4. 读 src/payments/processor.ts 确认实现
```

## 与 HarnessV2 的关系

- 既有项目的 `discovery` 强制规则要求至少一条 `existing_solutions[].source` 为 `graphify_symbol` / `graphify_query`，本 skill 的工具调用就是来源
- `discovery-effectiveness-reviewer` 会校验上述证据来源真实可定位
