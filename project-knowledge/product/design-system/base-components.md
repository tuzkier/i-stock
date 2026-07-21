---
knowledge_type: product
status: draft
source: init
confidence: needs-review
---

# 基础组件库（base components）

> 通用 UI 原语：业务组件的积木（按钮 / 输入 / 选择 / 弹窗 / 表格 / 标签…）。它们不含业务语义，用 `design-spec.md` 的 token 搭，保证视觉一致。
> 蒸馏来源：盘点产品里**复现的通用控件**（observe → 收敛成 canonical 原语），不是编一套通用组件库；早期盘点 + 偶尔补。每条带 source / status；不存在的组件不写。

## 基础组件目录（机器段）

> 列顺序固定，供治理门解析。组件 id 形态 `^BC-[a-z0-9][a-z0-9-]*$`。原型里有真实实现于 `prototype/components/base/`，实例打 `data-basecomp="BC-…"`。表头 / 分隔行 / `{{…}}` 占位跳过。
> **状态矩阵列必须列全**（不只默认态）——这是治"组件只覆盖 happy path"的完备性要求，与行为图 page-states 对齐。

| 组件 id | 名称 | 构成 | 变体 | 状态矩阵（全） | 用到 token | 实现路径 | source | status |
|---------|------|------|------|----------------|------------|----------|--------|--------|
| {{BC-id}} | {{名称}} | {{构成}} | {{变体}} | {{全状态}} | {{token}} | {{实现路径}} | {{来源}} | draft |

<!-- 盘点出真实复现控件时复制此行填真值，删除占位行（占位行 {{...}} 被解析器跳过 = 未采用，治理门不触发）：
| BC-button | 按钮 | label[+icon] | primary / secondary / danger / text | default / hover / focus / disabled / loading | --color-primary, --radius-1 | components/base/Button | 观察:多页复现 | stable |
-->

> 无现成来源（全新项目 / 未盘点）时本表只留 `{{...}}` 占位，由首个 UI mission 起草；不要凭通用最佳实践硬填。
