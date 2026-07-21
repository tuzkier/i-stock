---
name: graphify-debugging
description: "当用户在调试缺陷、追溯错误，或问\"为什么 X 失败\"时使用。示例：\"X 为什么失败？\"\"这个错误从哪里来？\"\"追溯这个缺陷\""
---

# 用 Graphify 调试

## 何时使用

- "这个函数为什么失败？"
- "追溯这个错误的来源"
- "谁调用了这个方法？"
- "这个 endpoint 返回 500"
- 调查缺陷、错误、异常行为

## 工作流

```
1. mcp__graphify__query_graph({search_query: "<错误信息或症状>"})
   → 找相关执行链 + 文档节点 + Rationale 节点

2. mcp__graphify__get_node({name: "<嫌疑函数>"})
   → 入边/出边/所属社区/相关 Rationale

3. mcp__graphify__get_neighbors({name: "<嫌疑函数>", depth: 2, edge_types: ["CALLS"]})
   → 调用链上下游

4. mcp__graphify__shortest_path({from: "<入口>", to: "<嫌疑函数>"})
   → 完整调用路径

5. READ graphify-out/GRAPH_REPORT.md  →  god nodes 看是否有 hot path 经过
```

> 如果索引过期 → 终端跑 `graphify .`。

## 检查清单

```
- [ ] 理解症状（错误信息、异常行为）
- [ ] query_graph 找相关代码或文档
- [ ] 锁定嫌疑函数 / 模块
- [ ] get_node 看入边出边，注意 INFERRED / AMBIGUOUS 边（不可靠！）
- [ ] get_neighbors / shortest_path 重建调用链
- [ ] 检查相关 Rationale 节点（NOTE/WHY/HACK 注释 + 文档）
- [ ] 阅读源文件确认根因
```

## 调试模式

| 症状                | Graphify 方法                                                              |
| ------------------- | -------------------------------------------------------------------------- |
| 错误信息            | `query_graph` 找错误文本 → `get_node` 查 throw 点                          |
| 错误返回值          | `get_node` → 看出边数据流                                                  |
| 间歇性失败          | `get_node` → 看是否有外部 API / async 出边                                 |
| 性能问题            | `get_node` → 关注入边数多的热点（god node 通常是热路径）                   |
| 近期回归            | `graphify prs --triage` 看最近 PR 是否动了相关社区                          |
| 注释暗示的坑        | 看 Rationale 节点（HACK / FIXME / NOTE）                                   |

## 工具

**query_graph** — 找跟错误相关的代码与文档：

```
mcp__graphify__query_graph({
  search_query: "payment validation error",
  search_type: "GRAPH_COMPLETION",
  top_k: 10
})
→ 节点：validatePayment, handlePaymentError, PaymentException
→ Rationale: "# HACK: retry up to 3 times on 503 from Stripe"
→ 文档：docs/payments.md§"Error Codes"
```

**get_node** — 嫌疑符号全视图：

```
mcp__graphify__get_node({name: "validatePayment"})
→ 入边：processCheckout, webhookHandler
→ 出边：verifyCard, fetchRates [INFERRED, possibly external!]
→ Rationale：见 docs/payments.md§"Webhook Contract"
→ 社区：CheckoutFlow（step 3/7）
```

**get_neighbors** — 重建调用链：

```
mcp__graphify__get_neighbors({
  name: "validatePayment",
  depth: 3,
  direction: "outgoing",
  edge_types: ["CALLS"]
})
→ d=1: verifyCard, fetchRates, logAttempt
→ d=2: stripeClient.charge, currencyAPI.get
→ d=3: httpClient.post (← external!)
```

## 示例：支付 endpoint 间歇性 500

```
1. mcp__graphify__query_graph({search_query: "payment error handling"})
   → 节点：validatePayment, handlePaymentError
   → Rationale: "# HACK: external rate API has no timeout"  ← 嫌疑！

2. mcp__graphify__get_node({name: "validatePayment"})
   → 出边: verifyCard, fetchRates [INFERRED 外部]

3. mcp__graphify__get_neighbors({name: "fetchRates", depth: 2, direction: "outgoing"})
   → d=1: currencyAPI.get
   → d=2: httpClient.post（无 timeout）

4. 根因：fetchRates 调外部 API 没设 timeout，rate API 偶发慢，触发上游超时
```

## 关于置信度

调试时**特别注意**置信度标签：

| 置信度          | 调试含义                                                          |
| --------------- | ----------------------------------------------------------------- |
| `EXTRACTED`     | AST 抽取，机械可证，可信                                          |
| `INFERRED`      | LLM 推断，需要打开源码确认                                        |
| `AMBIGUOUS`     | 多源冲突或弱推断，**不要**当根因依据，必须读源码                  |

`INFERRED` / `AMBIGUOUS` 边在调试场景下经常是误导根源 —— 总是配合 Read 源码验证。
