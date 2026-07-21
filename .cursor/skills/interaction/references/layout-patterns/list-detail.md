# list-detail（列表-详情）

> **何时用**：用户主任务是「浏览一批同类对象，挑一个看详情」。详情可与列表同屏（分栏）或跳转新页（窄屏）。

## 区域树（paste-ready）

| 区域 id | 所属 surface | 父区域 | 排布 | 优先级 | 角色 | 默认承载 | 扫描序 |
|---------|--------------|--------|------|--------|------|----------|--------|
| R-`<SURF>`-header | `<SURF>` | root | row | secondary | header | 标题 / 主操作（新建） | 1 |
| R-`<SURF>`-filters | `<SURF>` | root | row | tertiary | filters | 搜索 / 筛选 / 排序 | 2 |
| R-`<SURF>`-list | `<SURF>` | root | column | primary | content | 对象列表项（OBJ） | 3 |
| R-`<SURF>`-detail | `<SURF>` | root | column | secondary | detail | 选中对象详情字段 | 4 |

## 主次 / 扫描动线默认

- 主区是 list（用户先扫列表）；detail 为 secondary，随选中变化。
- 扫描动线：header → filters → list →（选中）→ detail，左→右 / 上→下。
- 窄屏：detail 退化为 list 项点击后的跳转页（同一 surface 的另一 page_state），区域树不变、carrier 改。

## 状态落区提示

- 空态：list 区放空态 CTA（`placements: {kind: cta, region: R-<SURF>-list}`）。
- 加载：list 区骨架；detail 区未选中时占位。

## 典型坑

- ❌ 把筛选器塞进 list 区顶部当成一行控件——筛选是独立 filters 区，便于扫描与复用。
- ❌ detail 字段堆成一长列不分组——detail 内可再分子区域（基本信息 / 关联 / 操作）。
- ❌ 列表项把对象所有字段平铺——列表只放扫描所需关键字段，其余进 detail。
