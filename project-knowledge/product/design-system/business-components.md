---
knowledge_type: product
status: draft
source: init
confidence: needs-review
---

# 业务组件库（business components）

> **完成一个业务场景的组件**：把领域对象 + 场景 + 操作打包成可复用单元（如「Mission 卡片」「审批步骤条」「订单状态时间线」）。它是领域模型(OBJ) × 业务场景(SUC) 的 **canonical UI 单元**，由基础组件组合，**落进区域树的区域**——这是原型不"乱堆"的核心：从命名业务组件装配，而非散控件堆叠。
> 蒸馏来源：和领域模型一起，观察**复现的领域-场景 UI 单元**；**逐 mission 增量沉淀**（做哪个业务场景就提炼 / 精化那几个业务组件）。每条带 source mission / status。

## 业务组件目录（机器段）

> 列顺序固定，供治理门解析。组件 id 形态 `^UC-[a-z0-9][a-z0-9-]*$`。`业务场景` 引上游 `SUC-xx`、`承载对象` 引上游 `OBJ-xx`（**traces_to 不悬空**：引用的 SUC/OBJ 必须在上游已定义，缺则回流 PRD，不自造）。`组成` 列引 `base-components.md` 的 `BC-*`。原型实现于 `prototype/components/business/`，实例打 `data-bizcomp="UC-…"`。表头 / 分隔行 / `{{…}}` 占位跳过。
> **状态矩阵列必须列全**（default / loading / empty / error / 权限 / 选中…），与行为图 page-states 对齐。

| 组件 id | 名称 | 业务场景(SUC) | 承载对象(OBJ) | 组成(BC) | 状态矩阵（全） | 数据 / 字段 | 实现路径 | source mission | status |
|---------|------|----------------|----------------|----------|----------------|-------------|----------|----------------|--------|
| {{UC-id}} | {{名称}} | {{SUC-xx}} | {{OBJ-xx}} | {{BC-* 列表}} | {{全状态}} | {{字段}} | {{实现路径}} | {{mission:id}} | draft |

<!-- 某 UI mission 沉淀业务组件时复制此行填真值，删除占位行（绑的 SUC/OBJ 必须上游真实存在、组成的 BC 必须在 base-components）：
| UC-mission-card | Mission 卡片 | SUC-03 | OBJ-02 | BC-card + BC-badge + BC-button | default / loading / empty / error / selected | id, title, stage, status | components/business/MissionCard | mission:20260604-x | draft |
-->

> 无现成来源（全新项目 / 首次）时本表只留 `{{...}}` 占位，由各 UI mission 逐个沉淀；不要凭想象造业务组件，绑的 SUC/OBJ 必须真实存在、组成的 BC 必须在 `base-components.md`。
