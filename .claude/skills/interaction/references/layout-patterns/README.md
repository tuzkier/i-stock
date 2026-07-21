# 布局 pattern 库（组成轴基底骨架）

> **何时引用**：interaction 阶段为**新建 surface** 写区域树（surface-model 布局骨架机器段）前，先来这里选一个匹配的 pattern 作基底骨架，再按本 surface 实际承载裁剪——**不要从白纸即兴排控件**。改 / 扩既有 surface 不从这里起步，而是继承累积图 `regions` 既有区域树（见 [`../region-tree-schema.md`](../region-tree-schema.md#基线继承两层模型迭代系统必读)）。

每个 pattern 给的是**区域树骨架（线框颗粒）**，不是 HTML 模板：定义页面分哪些区、怎么嵌套、主次与扫描动线，不定义像素 / 配色 / 具体控件样式（那些走项目设计系统基线 `project-knowledge/product/ui-design-system.md`）。

## 怎么选

| 用户主任务形态 | 选 |
|---|---|
| 浏览一批同类对象 + 看某个详情 | [list-detail](list-detail.md) |
| 在导航 / 列表 / 详情间频繁切换（如邮箱、IDE） | [master-detail-3col](master-detail-3col.md) |
| 总览多指标 / 多卡片，快速感知状态 | [dashboard](dashboard.md) |
| 多步骤、有顺序、需引导完成的任务 | [wizard](wizard.md) |
| 录入 / 编辑一组字段并提交 | [form](form.md) |
| 在画布上直接操作对象 + 旁边看 / 改属性 | [canvas-inspector](canvas-inspector.md) |
| 时间序 / 无限滚动的信息流 | [feed](feed.md) |
| 分组的配置项 + 分区编辑 | [settings](settings.md) |

## 用法

1. 选 pattern，复制它的「区域树（paste-ready）」表行到 surface-model 布局骨架机器段。
2. 把区域 id 的 `<SURF>` 占位换成本 surface 缩写（如 `R-<SURF>-main` → `R-BOARD-main`）。
3. 按本 surface 实际承载删 / 增区域；保留主次与扫描序意图，按需调整。
4. 把 page_state 的可见对象用 `objects[].region` 落到这些区域。

> 选不到合适 pattern 时，按 [`../region-tree-schema.md`](../region-tree-schema.md) 的字段自定义区域树；但仍须满足组成门（每个可见对象落区、原型打 `data-region`、声明扫描序）。
