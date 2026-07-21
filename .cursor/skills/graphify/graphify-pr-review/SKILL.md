---
name: graphify-pr-review
description: "当用户想审查 PR、理解 PR 改了什么、评估 merge 风险，或检查测试覆盖缺失时使用。示例：\"审查这个 PR\"\"PR #42 改了什么？\"\"这个 PR 合并安全吗？\""
---

# 用 Graphify 做 PR 审查

## 何时使用

- "审查这个 PR"
- "PR 改了什么？真实影响面？"
- "合并安全吗？"
- "测试覆盖够不够？"
- "多个 PR 是否会冲入同一片功能区？"

## 工作流

```
1. mcp__graphify__get_pr_impact({pr_number: N})
   → 改动节点 + 受影响 community + 风险分

2. mcp__graphify__list_prs() + triage_prs()
   → 看 PR 队列里是否有共社区的并行 PR（merge order 风险）

3. 对每个改动节点：get_neighbors(direction=incoming) 找未被 PR 更新的调用方
   → 这些是潜在 breakage

4. graphify prs --conflicts
   → 命中同社区的 PR 群组（merge order 风险红色信号）

5. 形成审查输出（风险评级 + 发现 + 推荐）
```

> 索引过期 → `graphify .` 或让 git hook 自动重建（`graphify hook install`）。

## 检查清单

```
- [ ] get_pr_impact 拿 PR 的 typed 影响摘要
- [ ] 找改动节点的所有 incoming，确认调用方都在 diff 里
- [ ] 找改动类型 / schema 的所有 consumer，确认都同步
- [ ] 检查改动是否触发 community 分裂（god node 被改 → 整片功能区受影响）
- [ ] prs --conflicts 看是否跟并行 PR 冲入同一社区
- [ ] 测试覆盖：query_graph 找改动符号的测试节点；缺失即 review 风险
- [ ] 风险评级（LOW / MEDIUM / HIGH / CRITICAL）+ 文字总结
```

## 工具

**get_pr_impact** — PR 改动的图谱影响：

```
mcp__graphify__get_pr_impact({pr_number: 42})
→ 改动节点（5）: validatePayment, PaymentInput, formatAmount, ...
→ 受影响 community: CheckoutFlow, RefundFlow
→ 改动节点的入边总数: 23（含 12 个 EXTRACTED, 8 个 INFERRED, 3 个 AMBIGUOUS）
→ 风险评分: MEDIUM
→ 提示: webhookHandler 在 CheckoutFlow 但不在 PR diff
```

**list_prs / triage_prs** — PR 队列管理：

```
mcp__graphify__list_prs()
→ 所有开放 PR 的 CI / review / worktree 状态

mcp__graphify__triage_prs()
→ AI 按图谱风险给 review 队列排序：优先看影响 god node / 多 community 的 PR
```

**prs --conflicts**（CLI）— 并行 merge 风险：

```bash
graphify prs --conflicts
→ PR #42 和 PR #38 同动 CheckoutFlow community（merge 时要选顺序）
→ PR #51 单独动 OnboardingFlow（安全并行）
```

## 示例审查：PR #42 改了 payment validation

```
1. mcp__graphify__get_pr_impact({pr_number: 42})
   → 改动：validatePayment, PaymentInput, formatAmount
   → 受影响社区：CheckoutFlow, RefundFlow
   → 风险：MEDIUM

2. 对 validatePayment 找 incoming
   → processCheckout（在 PR）
   → webhookHandler（NOT in PR）← 潜在 breakage

3. 对 PaymentInput 类型找 consumer
   → validatePayment（PR），createPayment（NOT in PR）← 破坏性 schema 变更

4. formatAmount 改动是加 optional 参数
   → 12 个调用方，但向后兼容 ✓

5. graphify prs --conflicts
   → PR #38 同动 CheckoutFlow community → merge 顺序需协调

6. 测试覆盖
   → checkout.test.ts 覆盖 processCheckout 路径 ✓
   → 无 webhook 路径测试 ✗

→ 审查输出见下
```

## 审查输出格式

```markdown
## PR Review: <title>

**风险: LOW / MEDIUM / HIGH / CRITICAL**

### 改动概要
- <N> 个节点在 <M> 个文件
- <P> 个 community 受影响：<community 名>
- 与并行 PR 的社区交集：<列表 / 无>

### 发现
1. **[严重度]** 描述
   - 来自 graphify 的证据（节点 / 边 / 置信度）
   - 受影响调用方 / 社区

### 缺失覆盖
- 改动未更新的调用方：…
- 未测试的执行路径：…

### Merge 顺序建议
- 与 PR #38 共动 CheckoutFlow，建议 #42 先 merge 因为它是 schema 源头
- 或：协调拆分

### 推荐
APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
```

## 与 HarnessV2 阶段流的衔接

- `code-review` skill 在涉及代码改动时会调本 skill
- `stage-gate finishing-branch` 决定合并顺序时会读 `graphify prs --conflicts` 的输出
- 风险评级写入 `delivery/acceptance-result.md` 的"风险披露"段
