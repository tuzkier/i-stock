---
name: graphify-impact-analysis
description: "当用户想知道改某处会破坏什么，或在改代码前需要安全分析时使用。示例：\"改 X 安全吗？\"\"什么依赖于这个？\"\"会破坏什么？\""
---

# 用 Graphify 做影响分析（Blast Radius）

## 何时使用

- "改这个函数安全吗？"
- "改 X 会破坏什么？"
- "展示影响面"
- "谁用了这段代码？"
- 做非平凡修改前
- commit / 推送前 —— 确认本次改动影响范围

## 工作流

```
1. mcp__graphify__get_neighbors({name: "X", direction: "incoming", depth: 3})
   → 上游依赖（谁在用 X），按 depth 分层

2. mcp__graphify__get_node({name: "X"})
   → 看 X 本身的社区、相关 Rationale、INFERRED / AMBIGUOUS 标记

3. mcp__graphify__query_graph({search_query: "X"}) + 社区交叉
   → 找跨模块的间接依赖（文档 DOCUMENTS / Rationale EXPLAINS X 的地方）

4. mcp__graphify__get_pr_impact({pr_number: N})  ←  如果改动已在 PR
   → 改动节点 + 受影响社区 + 风险分

5. 评估风险并报告
```

> 索引过期 → 终端跑 `graphify .`。

## 检查清单

```
- [ ] get_neighbors(direction=incoming) 找上游依赖
- [ ] 优先 review d=1（一定会破坏）
- [ ] 高置信度（EXTRACTED）边必须修；INFERRED 边要打开源码确认
- [ ] 看 d=1 / d=2 节点是否分布在多个 community（跨模块影响）
- [ ] 检查改动涉及的文档 / Rationale 节点是否需要同步更新
- [ ] 已有 PR：get_pr_impact 拿 typed 风险评分
- [ ] 评估总体风险并向用户报告
```

## Depth 与风险对位

| Depth | 风险级别            | 含义                         |
| ----- | ------------------- | ---------------------------- |
| d=1   | **一定会破坏**      | 直接调用者 / import 者       |
| d=2   | **大概率受影响**    | 间接依赖                     |
| d=3   | **需要测试覆盖**    | 传递性影响                   |

## 置信度过滤

| 置信度          | 处理                                                              |
| --------------- | ----------------------------------------------------------------- |
| `EXTRACTED`     | AST 抽取，必须计入影响面                                          |
| `INFERRED`      | LLM 推断，要打开源码确认；不能因为"LLM 没列出"就跳过依赖          |
| `AMBIGUOUS`     | 不可靠，必须用 Read / grep 交叉验证                               |

> 对位 HarnessV2 `CONFIRMED / UNCERTAIN / ASSUMED`，可直接写入 `dependency-impact` artifact 的 confidence 字段。

## 风险等级

| 受影响范围                        | 风险      |
| --------------------------------- | --------- |
| <5 节点，单 community             | LOW       |
| 5-15 节点，2-5 community           | MEDIUM    |
| >15 节点 或 god node              | HIGH      |
| 关键路径（auth / payments / 迁移）| CRITICAL  |

## 工具

**get_neighbors** —— blast radius 的核心原语：

```
mcp__graphify__get_neighbors({
  name: "validateUser",
  direction: "incoming",
  depth: 3,
  edge_types: ["CALLS", "IMPORTS"],
  min_confidence: "INFERRED"
})

→ d=1（一定会破坏）：
  - loginHandler (src/auth/login.ts:42) [CALLS, EXTRACTED]
  - apiMiddleware (src/api/middleware.ts:15) [CALLS, EXTRACTED]

→ d=2（大概率受影响）：
  - authRouter (src/routes/auth.ts:22) [CALLS, EXTRACTED]
  - sessionManager (src/session.ts:8) [CALLS, INFERRED]
```

**get_pr_impact** —— PR 级别的图谱影响：

```
mcp__graphify__get_pr_impact({pr_number: 42})
→ 改动节点: 5 个跨 3 个文件
→ 受影响社区: LoginFlow, TokenRefresh, APIMiddlewarePipeline
→ 风险: MEDIUM
→ 命中其他 PR 的社区: PR #38 同动 LoginFlow → 注意 merge order
```

## 示例：改 validateUser 会破坏什么？

```
1. mcp__graphify__get_neighbors({name: "validateUser", direction: "incoming", depth: 3})
   → d=1: loginHandler, apiMiddleware（一定破坏）
   → d=2: authRouter, sessionManager（大概率受影响）

2. mcp__graphify__get_node({name: "validateUser"})
   → 社区: AuthFlow（cohesion 0.82）
   → Rationale: "# WHY: must run before rate-limit, see SEC-002"
   → DOCUMENTS: docs/auth.md§"Login Flow" → 改动需同步更新文档

3. 风险评估：
   - d=1 两个直接调用者 + 关键路径（认证）
   - 触及 SEC-002 引用的安全前置条件
   - 风险：HIGH（CRITICAL，如果改动影响安全前置顺序）
```

## 与 HarnessV2 `dependency-impact` skill 的衔接

- 本 skill 的所有 `mcp__graphify__get_neighbors` 输出可直接作为 dependency-impact 的"第二层证据"
- 置信度字段一一对应：`EXTRACTED → CONFIRMED` / `INFERRED → UNCERTAIN` / `AMBIGUOUS → ASSUMED`
- `dependency-validity-reviewer` 会校验 dependency-impact artifact 里每条依赖是否有 graphify 路径证据；缺失需要走 `degradations[]`（`graphify_unavailable` / `graphify_stale`）
