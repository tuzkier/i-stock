# 区域树 schema（组成轴 · 布局骨架机器段）

> **何时引用**：写 `interaction-spec/surface-model.md` 的「布局骨架（机器段）」时。区域树是组成轴的真相源——定义每个 surface「页面怎么排」，停在**线框颗粒**（区域 × 嵌套 × 排布 × 优先级 × 角色 × 扫描序），不下到像素 / 具体控件样式。

## 一句话定位

行为图（behavior-graph）管「有哪些态、怎么流转」；区域树管「页面怎么排」。两者合起来，原型才是「行为图 ⊗ 布局骨架」的可视化实现。缺区域树 → 写 HTML 时空间排布零约束 = 控件乱堆。

## 字段定义（列顺序固定，被 `parse_region_catalog` 解析）

| 列 | 含义 | 约束 |
|----|------|------|
| 区域 id | 区域唯一标识 | 正则 `^R-[A-Z0-9][A-Za-z0-9_-]*$`，建议 `R-<surf缩写>-<语义>`，如 `R-BOARD-main` |
| 所属 surface | 该区域属于哪个 surface | 必须命中 surface 目录机器段的 surf id |
| 父区域 | 嵌套父级 | `root` 或本表已声明的另一个区域 id（构成树） |
| 排布 | 子级如何排列 | `row` / `column` / `grid` / `stack`(叠加,overlay) / `flow` |
| 优先级 | 主次层级 | `primary` / `secondary` / `tertiary`（驱动视觉权重与密度） |
| 角色 | 语义角色 | `navigation` / `content` / `detail` / `toolbar` / `actions` / `filters` / `status` / `header` / `footer` |
| 默认承载 | 本区**意图**承载的 OBJ / 动作组 | 自由中文（意图说明）；实际逐态填充在行为图 `objects[].region` / `placements[].region` |
| 扫描序 | 同父区域内的阅读 / 扫描顺序 | 整数；同父唯一（编码主扫描动线，如左→右 / 上→下） |

## 与行为图的对账

- `behavior-graph.yaml` 每个 `page_state.objects[]`（可见 = `fields` 非空）必须有 `region`，落到本 surface 的某个区域；非 OBJ 内容（动作 / 空态 CTA / 状态）用 `placements[].region`。
- 区域的「所属 surface」必须 == 该 page_state 的 surf。
- 原型 HTML 为每个承载内容的区域打 `data-region="<区域 id>"`。

## 对账门（`harness interaction prototype-check` · category=composition）

| finding | 级别 | 触发 |
|---|---|---|
| `LAYOUT_REGION_MISSING` | FAIL | surface 有 page_state 却无任何区域 |
| `OBJECT_UNPLACED` | FAIL | 可见对象无 `region` |
| `OBJECT_REGION_UNKNOWN` | FAIL | 对象 / placement 的 region 不在区域树 |
| `REGION_SURF_MISMATCH` | FAIL | region 的 surf ≠ page_state 的 surf |
| `REGION_SURF_UNKNOWN` / `REGION_PARENT_UNRESOLVED` / `REGION_BAD_ENUM` | FAIL | 区域树自身不合法 |
| `REGION_NOT_RENDERED` | FAIL | 区域承载内容却无 `data-region` 元素 |
| `REGION_ANCHOR_DANGLING` | FAIL | 原型 `data-region` 不在区域树 |
| `SCAN_ORDER_MISSING` | WARN | 同父区域缺 / 重复扫描序 |
| `REGION_DEAD` | WARN | 区域全程不承载任何内容 |

## 基线继承（两层模型，迭代系统必读）

区域树与行为图共享两层基线机制：

- **新建 surface**（baseline=create）：从 [`layout-patterns/`](layout-patterns/README.md) 选一个匹配 pattern 作基底骨架，再按本 surface 实际承载裁剪。
- **改 / 扩既有 surface**（baseline=modify/extend）：**继承**项目级累积图 `project-knowledge/product/system-use-cases/behavior-graph.yaml#regions` 里既有区域树（及既有原型 `data-region` 结构），只写**增量增改**，不重造；既有区域被合并图回归校验（仍须渲染），删除走 behavior-graph 顶层 `retired: [R-...]`。
- **贴合设计语言**：排布 / 主次 / 组件原语 / 交互约定遵循项目设计系统基线 `project-knowledge/product/ui-design-system.md`，保证与既有界面一致、下游实现无歧义。

## 门的边界（诚实声明）

组成门保证**对象都有家、骨架被忠实渲染、有阅读顺序**，判定不了审美 / 精致度。精致度靠 compose-before-HTML 的低保真 ASCII 线框人评（ASCII 线框正是这棵区域树的人类可读文本渲染）+ interaction-reviewer 组成 lens + 本 pattern 库三者合力。

## 最小示例

```
## 布局骨架（机器段）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-BOARD-toolbar | SURF-BOARD | root | row | secondary | toolbar | 刷新 / workspace 切换 | 1 |
| R-BOARD-main | SURF-BOARD | root | grid | primary | content | OBJ-01 节点 / 空态 CTA | 2 |
| R-BOARD-insp | SURF-BOARD | R-BOARD-main | column | tertiary | detail | 选中节点详情 | 3 |
```
