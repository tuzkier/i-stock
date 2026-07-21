# master-detail-3col（三栏主从）

> **何时用**：用户在「导航类目 → 对象列表 → 单对象详情」三级间频繁切换（邮箱、IM、IDE、文档管理、管理后台）。三栏常驻、上下文不丢。

## 区域树（paste-ready）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-`<SURF>`-nav | `<SURF>` | root | column | secondary | navigation | 类目 / 分组 / workspace 切换 | 1 |
| R-`<SURF>`-list | `<SURF>` | root | column | primary | content | 当前类目下的对象列表 | 2 |
| R-`<SURF>`-detail | `<SURF>` | root | column | primary | detail | 选中对象详情 + 操作 | 3 |
| R-`<SURF>`-detail-actions | `<SURF>` | R-`<SURF>`-detail | row | secondary | actions | 详情主操作（编辑/删除/分享） | 1 |

## 主次 / 扫描动线默认

- nav（左·窄）→ list（中）→ detail（右·宽）；扫描从左到右逐级收敛。
- list 与 detail 都可为 primary（任务核心在中右两栏）。
- 窄屏：三栏退化为可前进/后退的三个 page_state（nav→list→detail 钻取）。

## 状态落区提示

- 每栏独立空态 / 加载（如 nav 已选但 list 为空 → list 区空态）。
- detail 未选中：detail 区放引导占位（placement status）。

## 典型坑

- ❌ 把三栏做成三个独立页面文件——它们是一个 surface 的区域，不是三个 surface。
- ❌ detail 操作散落在字段间——主操作收进 `detail-actions` 子区，位置稳定。
- ❌ nav 铺成 OP/组件树——nav 是用户类目导航，不是把行为图节点搬上去。
