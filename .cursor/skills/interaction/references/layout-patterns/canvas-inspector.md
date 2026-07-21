# canvas-inspector（画布 + 属性面板）

> **何时用**：用户在**画布上直接操作对象**（节点图、设计器、编辑器、地图、流程图），并在旁边查看 / 编辑选中对象属性。

## 区域树（paste-ready）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-`<SURF>`-toolbar | `<SURF>` | root | row | secondary | toolbar | 工具 / 模式 / 缩放 / 全局操作 | 1 |
| R-`<SURF>`-palette | `<SURF>` | root | column | tertiary | navigation | 可拖入对象 / 图层列表 | 2 |
| R-`<SURF>`-canvas | `<SURF>` | root | stack | primary | content | 对象画布（OBJ 主体） | 3 |
| R-`<SURF>`-inspector | `<SURF>` | root | column | secondary | detail | 选中对象属性 / 操作 | 4 |

## 主次 / 扫描动线默认

- canvas 是绝对核心（primary，stack 排布以承载浮层 / 选框 / 右键菜单）。
- toolbar 在顶、palette 在左、inspector 在右；inspector 随选中对象变化。
- 选中对象 = action edge；属性变更 = 局部 mutation（不整页重渲染）。

## 状态落区提示

- 空画布：canvas 区放空态引导（拖入第一个对象 / 新建）。
- 未选中：inspector 区占位说明"选中对象以编辑"。
- overlay（右键菜单 / 浮层）作为 canvas 的 stack 子层（独立 surface id，page_entry 指宿主 #hash）。

## 典型坑

- ❌ 把属性面板做成弹窗每次打开——inspector 应常驻、随选中即时更新。
- ❌ 工具按钮散落画布四周——收进 toolbar 区，位置稳定。
- ❌ canvas 用 JS 从 fixture 渲染对象——静态块 + 交互胶水，锚点内联（见 R5）。
