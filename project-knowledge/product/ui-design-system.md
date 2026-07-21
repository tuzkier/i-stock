---
knowledge_type: product
status: draft
source: init
confidence: needs-review
---

# UI 设计系统（索引）

> 项目长期 UI 设计系统：interaction 阶段的原型**从这套系统装配**、下游实现**共用这套系统**，从而原型不再是控件乱堆、迭代不漂移、实现零歧义。
> 本文件是索引；分层正文在 `design-system/`。

## 它是什么（自上而下五层 + 地基 + 横切 + 治理）

```
设计原则 / 产品气质            ← design-system/principles.md          （顶层 WHY，统一所有选择）
整体交互框架                  ← design-system/interaction-framework.md（应用外壳 + 全局导航 + 跨 surface 模式）
  └ surface                  ← interaction-spec/surface-model.md     （有哪些界面边界，每次 mission 产）
      └ 区域树                ← surface-model 布局骨架机器段           （单 surface 怎么排，组成轴）
          └ 业务组件          ← design-system/business-components.md  （填区域，绑 OBJ/SUC，完成业务场景）
              └ 基础组件      ← design-system/base-components.md      （业务组件的积木）
                  └ 设计规范  ← design-system/design-spec.md          （token + 交互约定，视觉地基）
横切维度（每层都带）：状态/反馈 · 内容/术语 · 领域对象表达 · a11y/响应式   ← design-system/design-spec.md
治理：一致性门（原型是否套壳/装业务组件/用 token/canonical 表达/状态完整）  ← harness interaction prototype-check（composition + design-system 类）
```

## 知识 vs 真实可消费物（两个落点）

| 落点 | 内容 | 谁用 |
|------|------|------|
| `project-knowledge/product/design-system/` | **目录 / 契约**：原则、框架、组件目录（绑 OBJ/SUC、状态矩阵、provenance） | 设计/审查/治理门读 |
| 原型工程 `prototype/` | **真实可消费物**：`tokens.css`（真 token）+ `components/`（真基础/业务组件）+ 应用外壳 + `component-library.html`（组件库可视化展示页，按组件 × 全状态矩阵陈列，供人对账） | 原型装配 + 下游实现共用 |

**token 真值只存 `prototype/tokens.css` 一份**，design-spec 只做索引——不在 markdown 里手抄 token 值（避免第二真相源漂移）。

## 蒸馏纪律（怎么产出才准）

每一条（token / 组件 / 约定）必须能指回**真实来源**（代码 / `materials/design/` / 通过审查的 mission 决策）。

- **observe → condense**：从产品真实呈现里观察主导用法，规范化成一小份 canonical 集；不是描述、不是指向庞大原系统、不是编"最佳实践"。
- **挂证据 + 不编**：每条带 `source` + `status`(draft/stable) + `confidence`；没抽到标「待补」，冲突标「⚠ 冲突 + 待人决策」，绝不填默认值。
- **增量不覆盖**：setup 建初版（有来源才建）；业务组件等**逐 mission 增量沉淀**；retrospective merge 时新增/升 confidence/冲突不覆盖，保留 source mission。

> 具体执行步骤写在执行点（`harness-setup` setup 子步、`interaction` 装配步、`retrospective` 沉淀步），不在本文件当"方法论文档"。
