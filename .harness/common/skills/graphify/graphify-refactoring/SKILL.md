---
name: graphify-refactoring
description: "当用户想安全地重命名、抽取、拆分、移动或重组代码时使用。示例：\"重命名这个函数\"\"把这个抽成模块\"\"重构这个类\"\"把它移到单独文件\""
---

# 用 Graphify 做重构

## 何时使用

- 重命名函数 / 类 / 方法
- 把代码抽成新模块
- 拆分大文件
- 跨文件移动符号
- 重构前需要先看影响面

## 工作流

```
1. 确认重构目标符号或模块
   → mcp__graphify__get_node({name: "X"}) 拿当前形态 + 入边/出边

2. mcp__graphify__get_neighbors({name: "X", direction: "incoming", depth: 2})
   → 所有调用方 / import 者（重构后都要同步更新）

3. mcp__graphify__shortest_path({from: "<跨模块调用入口>", to: "X"})
   → 拿到典型调用路径，验证重构不破坏

4. 列出待修改文件清单，按文件分组施工

5. 用 Edit / MultiEdit 实际修改源码
   → graphify 不提供 coordinated rename 工具，必须 AI 显式 edit 每个文件

6. 重构完成后 `graphify --update`，再次 get_node 确认结构正确
```

> 索引过期 → `graphify .`。

## 检查清单

```
- [ ] 确认目标符号当前所有入边（不能漏掉调用方）
- [ ] EXTRACTED 边一定要改；INFERRED / AMBIGUOUS 边必须 Read 源码确认是否需要改
- [ ] 检查相关 Rationale / 文档节点：注释、docstring、docs/ 文档里是否提到旧名字
- [ ] 检查测试节点（test_* / *.test.ts）是否引用旧名
- [ ] 列出按文件分组的修改清单
- [ ] 实际 Edit 修改
- [ ] graphify --update 后再次确认
```

## 关于 coordinated rename

> Graphify **不提供**"多文件 coordinated rename 工具"。重构 = 用图谱定位影响面 + AI 自己用 Edit/MultiEdit 完成实际改动。

替代方案：

1. **图谱定位**：`get_neighbors` 拿到所有调用 / import 者 + 文档引用
2. **批量计划**：列出 `{file_path, old_string, new_string}` 表
3. **批量执行**：Edit / MultiEdit 工具按表施工
4. **回归验证**：`graphify --update` 后再次 `get_node`，确认旧节点消失、新节点存在、入边数量一致

## 影响面查询模板

```
# 1. 入边（谁会受影响）
mcp__graphify__get_neighbors({
  name: "validateUser",
  direction: "incoming",
  depth: 1,
  edge_types: ["CALLS", "IMPORTS"]
})

# 2. 文档 / Rationale 引用
mcp__graphify__get_neighbors({
  name: "validateUser",
  direction: "incoming",
  edge_types: ["DOCUMENTS", "EXPLAINS", "REFERENCES"]
})

# 3. 测试覆盖
mcp__graphify__query_graph({search_query: "validateUser test"})
```

## 示例：把 `validateUser` 重命名为 `authenticateUser`

```
1. mcp__graphify__get_node({name: "validateUser"})
   → 入边 5 个调用者，3 个文件
   → DOCUMENTS：docs/auth.md§"Login Flow"
   → Rationale："# WHY: must run before rate-limit, SEC-002"

2. mcp__graphify__get_neighbors({name: "validateUser", direction: "incoming", depth: 1})
   → src/auth/login.ts:42 loginHandler [CALLS, EXTRACTED]
   → src/api/middleware.ts:15 apiMiddleware [CALLS, EXTRACTED]
   → src/routes/auth.ts:22 authRouter [CALLS, EXTRACTED]
   → src/session.ts:8 sessionManager [CALLS, INFERRED]  ← 打开源码确认
   → tests/auth.test.ts:18 [CALLS, EXTRACTED]

3. 修改清单（按文件）：
   - src/auth/validator.ts: 函数定义
   - src/auth/login.ts: 调用
   - src/api/middleware.ts: 调用
   - src/routes/auth.ts: 调用
   - src/session.ts: 调用（确认后）
   - tests/auth.test.ts: 测试用例
   - docs/auth.md: 文档引用

4. MultiEdit 批量改

5. graphify --update 后 get_node({name: "authenticateUser"}) 确认 5 个入边都在新节点上
```

## 重构后必做

- 跑现有测试套件
- `graphify --update` 让图谱反映新结构
- 如果改动跨多个 community，写 retrospective / acceptance-result 备注：哪些社区被打乱
